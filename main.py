"""
API de Chat Bot con integración de WhatsApp Business

Configuración requerida (variables de entorno en archivo .env):
    WHATSAPP_ACCESS_TOKEN: Token de acceso de WhatsApp Business API
        Obtén este valor desde tu cuenta de Meta for Developers: https://developers.facebook.com/
    
    WHATSAPP_PHONE_NUMBER_ID: ID del número de teléfono de WhatsApp Business
        Obtén este valor desde tu cuenta de Meta for Developers
    
    WHATSAPP_RECIPIENT_PHONE: Número de teléfono destino
        IMPORTANTE: Debe incluir código de país sin el signo + (ejemplo: 5491123456789 para Argentina)
        El código automáticamente remueve el + si está presente
    
    WHATSAPP_API_VERSION: Versión de la API de Facebook (opcional, por defecto v18.0)
"""
import os
from fastapi import FastAPI
from models.analize import AnalysisRequest
import base64
from dotenv import load_dotenv
import logging

# Configurar logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("code-analyzer")

from service.googlechat_service import GoogleChatService
from service.whatsapp_service import WhatsAppService
from service.code_analysis_service import CodeAnalysisService

# Cargar variables de entorno
load_dotenv()



app = FastAPI()

@app.get("/")
async def health():
    return {"status": "ok"}

# Inicializar el servicio de WhatsApp
# Si las variables de entorno no están configuradas, la aplicación seguirá funcionando
# pero no enviará mensajes a WhatsApp
try:
    whatsapp_service = WhatsAppService()
except ValueError as e:
    logger.warning(f"⚠️ Advertencia: {e}. El servicio de WhatsApp no estará disponible.")
    whatsapp_service = None

# Inicializar el servicio de análisis de código
code_analysis_service = CodeAnalysisService()


@app.post("/analize")
async def analyze_code(req: AnalysisRequest):
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    # 1️⃣ Decodificar el diff
    try:
        diff_text = base64.b64decode(req.diff_b64).decode("utf-8")
        logger.info("Diff decodificado correctamente")
    except Exception as e:
        logger.error(f"Error al decodificar diff: {e}")
        return {"feedback": f"⚠️ Error al decodificar diff: {e}"}

    # 2️⃣ Determinar provider y loguear
    provider = req.provider or "openai"
    logger.info(f"🔧 Provider seleccionado: {provider} (solicitado: {req.provider or 'por defecto'})")
    
    # 3️⃣ Analizar código usando el servicio de análisis
    try:
        feedback =  code_analysis_service.analyze_code(
            diff_text=diff_text,
            title=req.title,
            repo=req.repo,
            author=req.author,
            url=req.url,
            provider=provider,
            language=req.language
        )
        logger.info(f"✅ Análisis completado exitosamente usando provider: {provider}")
    except Exception as e:
        feedback = f"⚠️ Error al generar feedback IA: {e}"
        logger.error(f"❌ Error al generar feedback IA con provider {provider}: {e}", exc_info=True)
    
    # 4️⃣ Enviar feedback a Google Chat
    try:
        message = {
            "text": (
                f"*🤖 Análisis automático del PR #{req.pr_number}*\n\n"
                f"*Repositorio:* {req.repo}\n"
                f"*Autor:* {req.author}\n"
                f"*Título:* {req.title}\n"
                f"*URL:* {req.url}\n\n"
                f"*Resultado del análisis:*\n{feedback}"
            )
        }
        google_chat_service = GoogleChatService(GOOGLE_CHAT_WEBHOOK_URL)
        await google_chat_service.send_message(message=message["text"])
        logger.info("✅ Mensaje enviado a Google Chat exitosamente")
        await whatsapp_service.send_message(feedback)
        logger.info("✅ Mensaje enviado a WhatsApp exitosamente")        
    except Exception as e:
        feedback += f"\n\n⚠️ Error al enviar mensaje a Google Chat: {e}"
        logger.error(f"❌ Error al enviar mensaje a Google Chat: {e}", exc_info=True)
    
    logger.info(f"📤 Feedback generado y enviado para PR #{req.pr_number} del repositorio {req.repo}")
    # 5️⃣ Retornar feedback para que GitHub lo comente
    return {"feedback": feedback}