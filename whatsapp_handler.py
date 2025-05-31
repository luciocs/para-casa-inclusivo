from flask import Blueprint, request, Response
import os
import json
import time
import logging
import requests
import mimetypes
import uuid
import boto3
from botocore.config import Config
from azure_ocr import azure_ocr

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

try:
    from openai import AzureOpenAI, OpenAI
except ImportError:
    from openai import OpenAI  # fallback para ambientes sem AzureOpenAI

# Armazena thread_id por número de telefone (em memória)
phone_threads = {}

# Configurações do OpenAI
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
OPENAI_API_KEY = os.getenv("OPENAI_ASS_API_KEY")
ASSISTANT_ID = os.getenv("ASSISTANT_ID")

# Configurações do AWS Social Messaging
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
AWS_PHONE_ID = os.getenv("AWS_PHONE_ID", "phone-number-id-3a6102351fea4ed0965a89deedec14ba")
META_API_VERSION = os.getenv("META_API_VERSION", "v20.0")

# **Atualizado**: usa AWS_S3_BUCKET_NAME em vez de S3_BUCKET_NAME
AWS_S3_BUCKET_NAME = os.getenv("AWS_S3_BUCKET_NAME")
if not AWS_S3_BUCKET_NAME:
    logger.error("Variável AWS_S3_BUCKET_NAME não configurada.")

# Inicializa clientes boto3
social = boto3.client("socialmessaging", region_name=AWS_REGION)
# Configurações do cliente S3 para garantir endpoint com região
s3 = boto3.client(
    "s3",
    region_name="us-east-1",
    config=Config(
        signature_version="s3v4",
        s3={"addressing_style": "virtual"}
    )
)

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

def is_image_url(url: str) -> bool:
    path = url.split("?", 1)[0].lower()
    return any(path.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"])

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
            # 1) Desempacota o JSON interno
            outer_message = json.loads(data.get("Message", "{}"))
            webhook_entry = json.loads(outer_message.get("whatsAppWebhookEntry", "{}"))
            changes = webhook_entry.get("changes", [])
            if not changes:
                return Response("Nenhum conteúdo para processar", status=200)

            message_data = changes[0]["value"]["messages"][0]
            phone_number = message_data.get("from")
            msg_type = message_data.get("type")

            user_message = ""
            file_url = None

            # 2) Tratamento conforme tipo
            if msg_type == "text":
                user_message = message_data.get("text", {}).get("body", "").strip()

            elif msg_type in ("image", "document"):
                media_obj = message_data[msg_type]
                media_id = media_obj.get("id")

                if msg_type == "image":
                    user_message = media_obj.get("caption", "") or ""
                else:
                    user_message = media_obj.get("filename", "") or ""

                if media_id:
                    # Chama AWS para resgatar a URL do arquivo
                    media_resp = social.get_whatsapp_media(
                        originationPhoneNumberId=AWS_PHONE_ID,
                        metaApiVersion=META_API_VERSION,
                        mediaId=media_id
                    )
                    file_url = media_resp.get("url")

            else:
                logger.debug(f"Tipo de mensagem não tratado: {msg_type}")
                return Response("Tipo não suportado", status=200)

            logger.debug(f"Mensagem recebida de {phone_number}: {user_message}")
            logger.debug(f"URL do arquivo (se houver): {file_url}")

            if not phone_number:
                return Response("Número de telefone ausente", status=400)

            # 3) Cria ou recupera thread_id
            if phone_number not in phone_threads:
                thread = client.beta.threads.create()
                phone_threads[phone_number] = thread.id

            thread_id = phone_threads[phone_number]
            content = []

            if user_message:
                content.append({"type": "text", "text": user_message})

            # 4) Se houver arquivo, faz download + OCR
            temp_file_path = None
            if file_url:
                try:
                    resp = requests.get(file_url, timeout=(3, 10))
                    resp.raise_for_status()

                    content_type = resp.headers.get("Content-Type", "application/octet-stream")
                    extension = mimetypes.guess_extension(content_type) or ".bin"
                    # **Nome único** com uuid
                    temp_file_path = f"/tmp/arquivo_{uuid.uuid4()}{extension}"

                    with open(temp_file_path, "wb") as f:
                        f.write(resp.content)

                    with open(temp_file_path, "rb") as f:
                        extracted_text = azure_ocr(f.read())

                    if extracted_text.strip():
                        content.append({"type": "text", "text": extracted_text})

                except Exception as e:
                    logger.error(f"Erro ao processar arquivo recebido: {e}")

                finally:
                    # **Limpeza** do arquivo temporário
                    if temp_file_path and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)

            if not content:
                return Response("Nenhum conteúdo válido recebido", status=400)

            # 5) Envia conteúdo para o OpenAI (thread + mensagem + run)
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=content
            )

            run = client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=ASSISTANT_ID
            )

            # Aguardar até o run finalizar
            while run.status in ["queued", "in_progress"]:
                time.sleep(1)
                run = client.beta.threads.runs.retrieve(
                    thread_id=thread_id,
                    run_id=run.id
                )

            # 6) Se houver ação pendente (p.ex. gerar imagem), processa
            if run.status == "requires_action":
                tool_calls = run.required_action.submit_tool_outputs.tool_calls
                tool_outputs = []
                image_url = None

                for call in tool_calls:
                    if call.function.name == "generate_image":
                        prompt = json.loads(call.function.arguments).get("prompt", "")
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

            # 7) Se o run finalizou, envia texto de volta
            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread_id)
                resposta = messages.data[0].content[0].text.value
                send_whatsapp_response(phone_number, resposta)
                return Response("Mensagem processada com sucesso", status=200)

            return Response(f"Run não finalizado. Status: {run.status}", status=500)

        except Exception as e:
            logger.exception(f"Erro ao processar mensagem: {e}")
            return Response("Erro interno", status=500)

    return Response("Tipo de evento não suportado", status=400)


def send_whatsapp_response(phone_number: str, message_text: str):
    try:
        # Se for URL de imagem, primeiro faz upload para S3 e depois ao WhatsApp
        if is_image_url(message_text):
            # 1) Baixar o conteúdo da imagem
            img_resp = requests.get(message_text, timeout=(3, 10))
            img_resp.raise_for_status()
            content_type = img_resp.headers.get("Content-Type", "application/octet-stream")
            content_bytes = img_resp.content

            # 2) Upload para S3 com **nome único**
            if not AWS_S3_BUCKET_NAME:
                logger.error("AWS_S3_BUCKET_NAME não configurada.")
                return

            key = f"whatsapp_images/{uuid.uuid4()}.png"
            s3.put_object(
                Bucket=AWS_S3_BUCKET_NAME,
                Key=key,
                Body=content_bytes,
                ContentType=content_type
            )

            # 3) Gera URL pré-assinada para leitura, adicionando o ResponseContentType
            presigned_url = s3.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": AWS_S3_BUCKET_NAME,
                    "Key": key,
                    "ResponseContentType": content_type
                },
                ExpiresIn=3600
            )

            # 4) Chama post_whatsapp_message_media incluindo Content-Type em headers
            upload_resp = social.post_whatsapp_message_media(
                originationPhoneNumberId=AWS_PHONE_ID,
                sourceS3PresignedUrl={
                    "url": presigned_url,
                    "headers": {"Content-Type": content_type}
                }
            )
            media_id = upload_resp.get("mediaId")
            if not media_id:
                logger.error(f"Falha no post_whatsapp_message_media: {upload_resp}")
                return

            # 5) Monta payload para enviar imagem
            whatsapp_message = {
                "messaging_product": "whatsapp",
                "to": f"+{phone_number.lstrip('+')}",
                "type": "image",
                "image": {"id": media_id}
            }

        else:
            # É texto simples
            whatsapp_message = {
                "messaging_product": "whatsapp",
                "to": f"+{phone_number.lstrip('+')}",
                "type": "text",
                "text": {"body": message_text}
            }

        # 6) Envia a mensagem de texto ou imagem
        payload = {
            "originationPhoneNumberId": AWS_PHONE_ID,
            "metaApiVersion": META_API_VERSION,
            "message": json.dumps(whatsapp_message).encode("utf-8")
        }

        logger.debug(f"Enviando via boto3.socialmessaging: {json.dumps(whatsapp_message, indent=2)}")
        response = social.send_whatsapp_message(**payload)
        logger.debug(f"Resposta da AWS: {response}")

    except Exception as e:
        logger.exception(f"Erro ao enviar mensagem via boto3: {e}")