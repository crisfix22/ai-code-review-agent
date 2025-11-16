import httpx
class GoogleChatService:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    async def send_message(self, message: str):
        google_chat_client = httpx.AsyncClient()
        r = await google_chat_client.post(self.webhook_url, json={"text": message})
        await google_chat_client.aclose()
        return r