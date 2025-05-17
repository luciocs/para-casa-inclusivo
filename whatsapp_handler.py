from flask import Blueprint, request, Response
import json
import time
import os
import logging
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from botocore.credentials import get_credentials
from botocore.session import Session

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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

# Inicializa o cliente da AWS Messaging (ex: Amazon Connect ou Amazon SNS para WhatsApp)
aws_region = os.getenv("AWS_REGION", "us-east-1")
channel_type = "WHATSAPP"  # fixo para esse canal
service = "social-messaging"
endpoint = f"https://social-messaging.{aws_region}.amazonaws.com/v1/messages"
from_number = "15557485682"  # seu número conectado na AWS

# Inicializa cliente
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
    logger.info(f"HEADERS: {dict(request.headers)}")
    sns_type = request.headers.get("x-amz-sns-message-type")
    data = request.json
    logger.info(f"Tipo SNS: {sns_type}")
    if sns_type == "SubscriptionConfirmation":
        subscribe_url = data.get("SubscribeURL")
        logger.info(f"Confirme a inscrição acessando: {subscribe_url}")
        return Response("Subscription confirmation needed", status=200)

    if sns_type == "Notification":
        try:
            message = json.loads(data.get("Message", "{}"))
            user_message = message.get("message", {}).get("text", "").strip()
            phone_number = message.get("message", {}).get("from")

            if not user_message or not phone_number:
                return Response("Dados incompletos", status=400)

            # Recupera ou cria novo thread_id
            if phone_number not in phone_threads:
                thread = client.beta.threads.create()
                phone_threads[phone_number] = thread.id

            thread_id = phone_threads[phone_number]

            # Envia mensagem do usuário
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=[{"type": "text", "text": user_message}]
            )

            # Executa o Assistant
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

            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                resposta = messages.data[0].content[0].text.value
            else:
                resposta = f"Desculpe, não consegui responder. Status: {run.status}"

            send_whatsapp_response(phone_number, resposta)

            return Response("Mensagem processada com sucesso", status=200)

        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return Response("Erro interno", status=500)

    return Response("Tipo de evento não suportado", status=400)

def send_whatsapp_response(phone_number, message_text):
    def format_phone_number(number):
        return number.replace(" ", "").replace("-", "")

    payload = {
        "channel": "WHATSAPP",
        "from": from_number,
        "to": format_phone_number(phone_number if phone_number.startswith("+") else f"+{phone_number}"),
        "content": {
            "text": message_text
        }
    }

    session = Session()
    credentials = session.get_credentials().get_frozen_credentials()

    aws_request = AWSRequest(
        method="POST",
        url=endpoint,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    )
    SigV4Auth(credentials, service, aws_region).add_auth(aws_request)

    response = requests.post(
        endpoint,
        data=aws_request.body,
        headers=dict(aws_request.headers)
    )

    if response.status_code >= 400:
        logger.error(f"Erro ao enviar mensagem: {response.status_code} - {response.text}")
    else:
        logger.error(f"Mensagem enviada para {phone_number}: {response.text}")
        