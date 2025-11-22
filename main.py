"""
AI Code Review API with optional WhatsApp Business integration

Required configuration (environment variables in .env file):
    WHATSAPP_ACCESS_TOKEN: WhatsApp Business API access token
        Get this value from your Meta for Developers account: https://developers.facebook.com/
    
    WHATSAPP_PHONE_NUMBER_ID: WhatsApp Business phone number ID
        Get this value from your Meta for Developers account
    
    WHATSAPP_RECIPIENT_PHONE: Destination phone number
        IMPORTANT: Must include country code without the + sign (example: 5491123456789 for Argentina)
        The code automatically removes the + if present
    
    WHATSAPP_API_VERSION: Facebook API version (optional, defaults to v18.0)
"""
import os
from fastapi import FastAPI
from models.analize import AnalysisRequest
from typing import Optional
import base64
from dotenv import load_dotenv

from utils.logger import logger

from service.googlechat_service import GoogleChatService
from service.whatsapp_service import WhatsAppService
from service.code_analysis_service import CodeAnalysisService

# Load environment variables
load_dotenv()



app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

# Initialize WhatsApp service
# If environment variables are not configured, the application will continue to work
# but will not send messages to WhatsApp
try:
    whatsapp_service = WhatsAppService()
except ValueError as e:
    logger.warning(f"⚠️ Warning: {e}. WhatsApp service will not be available.")
    whatsapp_service = None

# Initialize code analysis service
code_analysis_service = CodeAnalysisService()


@app.post("/analize")
async def analyze_code(req: AnalysisRequest):
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    SEND_WHATSAPP = os.getenv("SEND_WHATSAPP", "false").lower() == "true"
    SEND_GOOGLE_CHAT = os.getenv("SEND_GOOGLE_CHAT", "false").lower() == "true"
    # 1️⃣ Decode the diff
    try:
        diff_text = base64.b64decode(req.diff_b64).decode("utf-8")
        logger.info("Diff decoded successfully")
    except Exception as e:
        logger.error(f"Error decoding diff: {e}")
        return {"feedback": f"⚠️ Error decoding diff: {e}"}

    # 2️⃣ Determine provider and log
    provider = req.provider or "openai"
    logger.info(f"🔧 Provider selected: {provider} (requested: {req.provider or 'default'})")
    
    # 3️⃣ Analyze code using the analysis service
    try:
        # Determine if RAG should be used (request level or global setting)
        use_rag = req.use_rag if req.use_rag is not None else (os.getenv("USE_RAG", "true").lower() == "true")
        
        feedback =  code_analysis_service.analyze_code(
            diff_text=diff_text,
            title=req.title,
            repo=req.repo,
            author=req.author,
            url=req.url,
            provider=provider,
            language=req.language,
            use_rag=use_rag
        )
        logger.info(f"✅ Analysis completed successfully using provider: {provider}")
    except Exception as e:
        feedback = f"⚠️ Error generating AI feedback: {e}"
        logger.error(f"❌ Error generating AI feedback with provider {provider}: {e}", exc_info=True)
    
    # 4️⃣ Send feedback to Google Chat
    try:
        message = {
            "text": (
                f"*🤖 Automatic PR Analysis #{req.pr_number}*\n\n"
                f"*Repository:* {req.repo}\n"
                f"*Author:* {req.author}\n"
                f"*Title:* {req.title}\n"
                f"*URL:* {req.url}\n\n"
                f"*Analysis Result:*\n{feedback}"
            )
        }
        if SEND_GOOGLE_CHAT:
            google_chat_service = GoogleChatService(GOOGLE_CHAT_WEBHOOK_URL)
            await google_chat_service.send_message(message=message["text"])
            logger.info("✅ Message sent to Google Chat successfully")
        if SEND_WHATSAPP:
            await whatsapp_service.send_message(feedback)
            logger.info("✅ Message sent to WhatsApp successfully")        
    except Exception as e:
        feedback += f"\n\n⚠️ Error sending message to Google Chat: {e}"
        logger.error(f"❌ Error sending message to Google Chat: {e}", exc_info=True)
    
    logger.info(f"📤 Feedback generated and sent for PR #{req.pr_number} from repository {req.repo}")
    # 5️⃣ Return feedback for GitHub to comment
    return {"feedback": feedback}


@app.post("/store")
async def store_document(
    content: str,
    doc_type: str,
    language: Optional[str] = None,
    repo: Optional[str] = None,
    author: Optional[str] = None,
):
    """
    Store a document in the RAG vector database.
    
    Args:
        content: The document content to store
        doc_type: Type of document ("review", "code_snippet", "documentation")
        language: Programming language (optional)
        repo: Repository name (optional)
        author: Author name (optional)
    
    Returns:
        dict: Result with document ID if successful
    """
    from service.rag_service import create_rag_service
    
    rag_service = create_rag_service()
    if not rag_service:
        return {
            "success": False,
            "error": "RAG service not available. Check configuration."
        }
    
    try:
        doc_id = rag_service.store_document(
            content=content,
            doc_type=doc_type,
            language=language,
            repo=repo,
            author=author,
        )
        
        if doc_id:
            logger.info(f"✅ Document stored successfully with ID: {doc_id}")
            return {
                "success": True,
                "document_id": doc_id,
                "message": "Document stored successfully"
            }
        else:
            return {
                "success": False,
                "error": "Failed to store document"
            }
    except Exception as e:
        logger.error(f"❌ Error storing document: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }