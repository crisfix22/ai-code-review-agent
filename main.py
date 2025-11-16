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
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import json
from models.analize import AnalysisRequest
import base64
from openai import OpenAI
from dotenv import load_dotenv

import httpx

from service.googlechat_service import GoogleChatService
from service.whatsapp_service import WhatsAppService

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
    print(f"⚠️ Advertencia: {e}. El servicio de WhatsApp no estará disponible.")
    whatsapp_service = None



@app.post("/chat/events")
async def chat_events(request: Request):
    try:
        body = await request.json()
        print("\n==================== EVENTO RECIBIDO ====================")
        print(json.dumps(body, indent=2))

        # ✅ Obtener tipo de evento (si viene en el nuevo modelo)
        event_type = body.get("commonEventObject", {}).get("eventType")

        # ✅ Si es un mensaje
        if "chat" in body and "messagePayload" in body["chat"]:
            payload = body["chat"]["messagePayload"]

            text = payload.get("message", {}).get("text", "")
            user = body["chat"]["user"].get("displayName", "Usuario")
            thread = payload.get("message", {}).get("thread", {})
            thread_name = thread.get("name")

            print(f"👤 Usuario: {user}")
            print(f"💬 Mensaje: {text}")
            print(f"🧵 Thread: {thread_name}")

            # ✅ Enviar mensaje a WhatsApp
            if whatsapp_service:
                try:
                    # Construir mensaje para WhatsApp
                    whatsapp_message = f"📩 Nuevo mensaje de {user}:\n\n{text}"
                    if thread_name:
                        whatsapp_message += f"\n\n🧵 Thread: {thread_name}"
                    
                    await whatsapp_service.send_message(whatsapp_message)
                    print("✅ Mensaje enviado a WhatsApp exitosamente")
                except Exception as whatsapp_error:
                    print(f"❌ Error al enviar mensaje a WhatsApp: {whatsapp_error}")
                    # Continuar con la respuesta aunque falle el envío a WhatsApp

            # ✅ Responder fuera de thread
            return JSONResponse(
                content={
                    "text": f"Hola {user}, recibí tu mensaje"
                },
                status_code=200,
                headers={"Content-Type": "application/json; charset=utf-8"}
            )
        print(f"Responde fuera del hilo")


        # ✅ Si el bot fue agregado a un espacio
        if event_type == "ADDED_TO_SPACE":
            space_name = body["chat"]["messagePayload"]["space"]["name"]
            print(f"Bot agregado a: {space_name}")
            return JSONResponse({"text": "¡Gracias por invitarme al espacio! 🚀"})

        # ✅ Si lo eliminaron del espacio
        if event_type == "REMOVED_FROM_SPACE":
            print("Bot eliminado del espacio")
            return JSONResponse({"status": "ok"})

        # ✅ Evento desconocido
        print("⚠ Evento recibido sin mensaje, tipo:", event_type)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        print(f"Error al obtener el body: {e}")
        return JSONResponse({"status": "error", "message": "Error al obtener el body"})


@app.post("/analize")
async def analyze_code(req: AnalysisRequest):
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    GOOGLE_CHAT_WEBHOOK_URL = os.getenv("GOOGLE_CHAT_WEBHOOK_URL")
    # 1️⃣ Decodificar el diff
    try:
        diff_text = base64.b64decode(req.diff_b64).decode("utf-8")
    except Exception as e:
        return {"feedback": f"⚠️ Error al decodificar diff: {e}"}

    # 2️⃣ Crear el prompt de análisis
    prompt = f"""
Actúa como un revisor de código experto en ingeniería de software.
Analiza el siguiente diff de código y genera un resumen con:

1. Posibles bugs o errores lógicos.
2. Mejores prácticas incumplidas.
3. Sugerencias de optimización o refactorización.
4. Riesgos futuros o problemas de escalabilidad.

Pull Request: {req.title}
Repositorio: {req.repo}
Autor: {req.author}
URL: {req.url}

--- Diff del PR ---
{diff_text}
"""

    # 3️⃣ Llamar al modelo IA
    try:
        response =  openai_client.chat.completions.create(
            model="gpt-5",
            messages=[
                {"role": "system", "content": "Eres un ingeniero senior especializado en revisión de código."},
                {"role": "user", "content": prompt}
            ],
        )
        feedback = response.choices[0].message.content.strip()
    except Exception as e:
        feedback = f"⚠️ Error al generar feedback IA: {e}"
        print(f"Error al generar feedback IA: {e}")
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
            r = await google_chat_service.send_message(message=message["text"])
            await whatsapp_service.send_message(feedback)
            r.raise_for_status()
    except Exception as e:
        feedback += f"\n\n⚠️ Error al enviar mensaje a Google Chat: {e}"
        print(f"Error al enviar mensaje a Google Chat: {e}")
    print(f"Feedback enviado a Google Chat: {feedback}")
    # 5️⃣ Retornar feedback para que GitHub lo comente
    return {"feedback": feedback}