"""
Servicio para enviar mensajes a través de la API oficial de WhatsApp Business de Facebook

Variables de entorno requeridas:
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
import httpx
from typing import Optional




class WhatsAppService:
    """Servicio para enviar mensajes a través de la API oficial de WhatsApp Business de Facebook"""
    
    def __init__(self):
        # Token de acceso: Obtén este valor desde tu cuenta de Meta for Developers
        self.access_token = os.getenv("WHATSAPP_ACCESS_TOKEN")
        
        # ID del número de teléfono: Obtén este valor desde tu cuenta de Meta for Developers
        self.phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
        
        # Número de teléfono destino: Debe incluir código de país sin el signo +
        # Ejemplo: 5491123456789 (Argentina) o 34612345678 (España)
        self.recipient_phone = os.getenv("WHATSAPP_RECIPIENT_PHONE")
        
        # Versión de la API (opcional, por defecto v18.0)
        self.api_version = os.getenv("WHATSAPP_API_VERSION", "v18.0")
        
        # Validar que las variables requeridas estén configuradas
        if not self.access_token:
            raise ValueError("WHATSAPP_ACCESS_TOKEN no está configurado en las variables de entorno")
        if not self.phone_number_id:
            raise ValueError("WHATSAPP_PHONE_NUMBER_ID no está configurado en las variables de entorno")
        if not self.recipient_phone:
            raise ValueError("WHATSAPP_RECIPIENT_PHONE no está configurado en las variables de entorno")
        
        # Construir URL base de la API
        self.base_url = f"https://graph.facebook.com/{self.api_version}/{self.phone_number_id}/messages"
        
        # Cliente HTTP asíncrono
        self.client = httpx.AsyncClient()
    
    async def __aenter__(self):
        """Context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cierra el cliente HTTP"""
        await self.client.aclose()
    
    async def close(self):
        """Cierra el cliente HTTP"""
        await self.client.aclose()
    
    async def send_message(self, message: str, recipient_phone: Optional[str] = None) -> dict:
        """
        Envía un mensaje de texto a WhatsApp
        
        Args:
            message: Texto del mensaje a enviar
            recipient_phone: Número de teléfono destino (opcional, usa el de variables de entorno si no se proporciona)
        
        Returns:
            dict: Respuesta de la API de WhatsApp
        """
        # Usar el número de destino proporcionado o el de variables de entorno
        phone_to_use = recipient_phone or self.recipient_phone
        
        # Formatear el número de teléfono: debe incluir código de país sin el signo +
        # El código automáticamente remueve el + si está presente
        # Ejemplo: +5491123456789 se convierte en 5491123456789
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
            print(f"✅ Mensaje enviado a WhatsApp: {result} y payload: {payload}")
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Error al enviar mensaje a WhatsApp: {e}"
            if e.response is not None:
                error_msg += f" - Respuesta: {e.response.text}"
            print(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Error de conexión al enviar mensaje a WhatsApp: {e}"
            print(error_msg)
            raise Exception(error_msg)
    
    async def send_template_message(self, template_name: str, language_code: str = "es", 
                             parameters: Optional[list] = None,
                             recipient_phone: Optional[str] = None) -> dict:
        """
        Envía un mensaje de plantilla a WhatsApp
        
        Args:
            template_name: Nombre de la plantilla aprobada
            language_code: Código de idioma (por defecto "es")
            parameters: Lista de parámetros para la plantilla
            recipient_phone: Número de teléfono destino (opcional)
        
        Returns:
            dict: Respuesta de la API de WhatsApp
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
            print(f"✅ Mensaje de plantilla enviado a WhatsApp: {result}")
            return result
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Error al enviar mensaje de plantilla a WhatsApp: {e}"
            if e.response is not None:
                error_msg += f" - Respuesta: {e.response.text}"
            print(error_msg)
            raise Exception(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Error de conexión al enviar mensaje de plantilla a WhatsApp: {e}"
            print(error_msg)
            raise Exception(error_msg)

