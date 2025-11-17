import httpx

from main import logger
class GoogleChatService:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        if not self.webhook_url:
            logger.error("Google Chat webhook URL is not configured")
            raise ValueError("Google Chat webhook URL is not configured")

    async def send_message(self, message: str):
        google_chat_client = httpx.AsyncClient()
        r = await google_chat_client.post(self.webhook_url, json={"text": message})
        await google_chat_client.aclose()
        return r