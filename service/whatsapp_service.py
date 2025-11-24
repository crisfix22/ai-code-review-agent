"""
Service for sending messages through the official Facebook WhatsApp Business API

Required environment variables:
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
import httpx
from typing import Optional

from utils.logger import logger




class WhatsAppService:
    """Service for sending messages through the official Facebook WhatsApp Business API"""
    
    def __init__(self):
        # Access token: Get this value from your Meta for Developers account
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        
        # Phone number ID: Get this value from your Meta for Developers account
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        
        # Destination phone number: Must include country code without the + sign
        # Example: 5491123456789 (Argentina) or 34612345678 (Spain)
        self.recipient_phone = os.getenv("WHATSAPP_RECIPIENT_PHONE")
        
        # API version (optional, defaults to v18.0)
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")
        
        # Validate that required variables are configured
        if not self.access_token:
            raise ValueError("WHATSAPP_ACCESS_TOKEN is not configured in environment variables")
        if not self.phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID is not configured in environment variables")
        if not self.recipient_phone:
            raise ValueError("WHATSAPP_RECIPIENT_PHONE is not configured in environment variables")
        
        # Build API base URL
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        
        # Async HTTP client
        self.client = httpx.AsyncClient()
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the HTTP client"""
        await self.client.aclose()
    
    async def close(self):
        """Closes the HTTP client"""
        await self.client.aclose()
    
    async def send_message(self, message: str, recipient_phone: Optional[str] = None) -> dict:
        """
        Sends a text message to WhatsApp
        
        Args:
            message: Message text to send
            recipient_phone: Destination phone number (optional, uses environment variable if not provided)
        
        Returns:
            dict: WhatsApp API response
        """
        # Use the provided destination number or the one from environment variables
        phone_to_use = recipient_phone or self.recipient_phone
        
        # Format phone number: must include country code without the + sign
        # The code automatically removes the + if present
        # Example: +5491123456789 becomes 5491123456789
        if phone_to_use.startswith("+"):
            phone_to_use = phone_to_use[1:]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_to_use,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message
            }
        }
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                self.base_url,
                json=payload,
                headers=headers
            )            
            result = response.json()
            logger.info(f"✅ Message sent to WhatsApp: {result} and payload: {payload}")
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Error sending message to WhatsApp: {e}"
            if e.response is not None:
                error_msg += f" - Response: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Connection error sending message to WhatsApp: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)
    
    async def send_template_message(self, template_name: str, language_code: str = "es", 
                             parameters: Optional[list] = None,
                             recipient_phone: Optional[str] = None) -> dict:
        """
        Sends a template message to WhatsApp
        
        Args:
            template_name: Name of the approved template
            language_code: Language code (default: "es")
            parameters: List of parameters for the template
            recipient_phone: Destination phone number (optional)
        
        Returns:
            dict: WhatsApp API response
        """
        phone_to_use = recipient_phone or self.recipient_phone
        
        if phone_to_use.startswith("+"):
            phone_to_use = phone_to_use[1:]
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone_to_use,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {
                    "code": language_code
                }
            }
        }
        
        if parameters:
            payload["template"]["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": param} for param in parameters
                    ]
                }
            ]
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        try:
            response = await self.client.post(
                self.base_url,
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"✅ Template message sent to WhatsApp: {result}")
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Error sending template message to WhatsApp: {e}"
            if e.response is not None:
                error_msg += f" - Response: {e.response.text}"
            logger.error(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Connection error sending template message to WhatsApp: {e}"
            logger.error(error_msg)
            raise Exception(error_msg)

