from flask import Blueprint, request, Response
import json
import time
import os
import logging
import requests
import mimetypes

from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.session import Session

from azure_ocr import azure_ocr

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    from openai import OpenAI  # fallback para ambientes com apenas openai instalado

# Armazena thread_id por número de telefone (em memória)
phone_threads = {}

# Configurações do OpenAI
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_ASS_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Inicializa o cliente da AWS Messaging
aws_region = os.getenv("AWS_REGION", "us-east-1")
channel_type = "WHATSAPP"
service = "social-messaging"
endpoint = f"https://social-messaging.{aws_region}.amazonaws.com/v1/messages"
from_number = "+15557820821"

# Inicializa cliente OpenAI
if USE_AZURE_OPENAI:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
else:
    client = OpenAI(api_key=OPENAI_API_KEY)

# Blueprint da API do WhatsApp
whatsapp_api = Blueprint("whatsapp_api", __name__)

@whatsapp_api.route("/sns_whatsapp", methods=["POST"])
def sns_whatsapp_handler():
    logger.debug(f"HEADERS: {dict(request.headers)}")
    sns_type = request.headers.get("x-amz-sns-message-type")
    data = request.get_json(force=True)

    logger.debug(f"Payload recebido: {data}")

    if sns_type == "SubscriptionConfirmation":
        subscribe_url = data.get("SubscribeURL")
        logger.debug(f"Confirme a inscrição acessando: {subscribe_url}")
        return Response("Subscription confirmation needed", status=200)

    if sns_type == "Notification":
        try:
            outer_message = json.loads(data.get("Message", "{}"))
            webhook_entry = json.loads(outer_message.get("whatsAppWebhookEntry", "{}"))
            message_data = webhook_entry["changes"][0]["value"]["messages"][0]

            phone_number = message_data.get("from")
            msg_type = message_data.get("type")

            user_message = ""
            file_url = None

            if msg_type == "text":
                user_message = message_data.get("text", {}).get("body", "").strip()

            elif msg_type == "image":
                user_message = message_data.get("image", {}).get("caption", "")
                file_url = message_data.get("image", {}).get("url")

            elif msg_type == "document":
                user_message = message_data.get("document", {}).get("filename", "")
                file_url = message_data.get("document", {}).get("url")

            logger.debug(f"Mensagem recebida de {phone_number}: {user_message}")
            logger.debug(f"URL do arquivo (se houver): {file_url}")

            if not phone_number:
                return Response("Número de telefone ausente", status=400)

            if phone_number not in phone_threads:
                thread = client.beta.threads.create()
                phone_threads[phone_number] = thread.id

            thread_id = phone_threads[phone_number]
            content = []

            if user_message:
                content.append({"type": "text", "text": user_message})

            if file_url:
                try:
                    response = requests.get(file_url)
                    response.raise_for_status()
                    content_type = response.headers.get("Content-Type", "application/octet-stream")
                    extension = mimetypes.guess_extension(content_type) or ".bin"
                    file_path = f"/tmp/arquivo_recebido{extension}"

                    with open(file_path, "wb") as f:
                        f.write(response.content)

                    with open(file_path, "rb") as f:
                        extracted_text = azure_ocr(f.read())

                    if extracted_text.strip():
                        content.append({"type": "text", "text": extracted_text})
                except Exception as e:
                    logger.error(f"Erro ao processar arquivo recebido: {e}")

            if not content:
                return Response("Nenhum conteúdo válido recebido", 400)

            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )

            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            while run.status in ['queued', 'in_progress']:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )

            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                image_url = None

                for call in tool_calls:
                    if call.function.name == "generate_image":
                        prompt = json.loads(call.function.arguments).get("prompt")
                        from openai_gpt import create_dalle_images
                        image_urls = create_dalle_images(prompt)
                        image_url = image_urls[0] if isinstance(image_urls, list) else None
                        if image_url:
                            tool_outputs.append({
                                "tool_call_id": call.id,
                                "output": json.dumps({"image_url": image_url})
                            })

                if tool_outputs:
                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=thread_id,
                        run_id=run.id,
                        tool_outputs=tool_outputs
                    )

                if image_url:
                    send_whatsapp_response(phone_number, image_url)
                    return Response("Imagem gerada e enviada.", status=200)

            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                resposta = messages.data[0].content[0].text.value
                send_whatsapp_response(phone_number, resposta)
                return Response("Mensagem processada com sucesso", status=200)

            return Response(f"Run não finalizado. Status: {run.status}", 500)

        except Exception as e:
            logger.exception(f"Erro ao processar mensagem: {e}")
            return Response("Erro interno", status=500)

    return Response("Tipo de evento não suportado", status=400)

def send_whatsapp_response(phone_number, message_text):
    is_image_url = any(message_text.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])

    if is_image_url:
        content = {
            "image": {
                "url": message_text
            }
        }
    else:
        content = {
            "text": message_text
        }

    payload = {
        "channel": "WHATSAPP",
        "from": from_number,
        "to": phone_number if phone_number.startswith("+") else f"+{phone_number}",
        "content": content
    }
    logger.debug(f"Payload para envio via AWS: {json.dumps(payload, indent=2)}")
    
    session = Session()
    credentials = session.get_credentials().get_frozen_credentials()

    aws_request = AWSRequest(
        method="POST",
        url=endpoint,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )

    SigV4Auth(credentials, "social-messaging", aws_region).add_auth(aws_request)

    response = requests.post(
        endpoint,
        data=aws_request.body,
        headers=dict(aws_request.headers)
    )

    if response.status_code >= 400:
        logger.error(f"Erro ao enviar mensagem para {phone_number}: {response.status_code} - {response.text}")
    else:
        logger.debug(f"Mensagem enviada para {phone_number}: {response.text}")