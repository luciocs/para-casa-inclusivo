import os
import logging
import time
import json
import uuid
from flask import Blueprint, request, jsonify
from azure_ocr import azure_ocr
from openai_gpt import (
    adapt_text_for_inclusivity,
    create_dalle_images,
    generate_comic_book,
    create_new_activity
)
from assistant_api import create_thread, handle_message

api = Blueprint('api', __name__)

# Logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)


def error_response(message: str, code: int = 500):
    return jsonify({"success": False, "error": message}), code


# 0. Healthcheck
@api.route('/healthcheck', methods=['GET'])
def healthcheck():
    return jsonify({"status": "ok", "success": True}), 200


# 0.5. OCR Only
@api.route('/ocr', methods=['POST'])
def ocr_only():
    start = time.time()

    # 1. Recebe arquivo
    file = request.files.get('file')
    if not file:
        return error_response("file é obrigatório", 400)

    # 2. Lê 'adaptations' e 'extra' do FormData
    try:
        adaptations = json.loads(request.form.get('adaptations', '{}'))
    except Exception:
        return error_response("adaptations inválido", 400)
    additional_adaptations = request.form.get('additional_adaptations', '')

    # 3. OCR
    ocr = azure_ocr(file.read())
    if isinstance(ocr, dict) and "error" in ocr:
        return error_response("Falha no OCR", 500)
    elapsed = round(time.time() - start, 2)

    return jsonify({
        "success": True,
        "ocr_text": ocr,
        "processing_time": elapsed
    }), 200


# 1. Adaptar Atividade Existente
@api.route('/adapt_activity', methods=['POST'])
def adapt_activity():
    start = time.time()

    # 1. Recebe arquivo
    file = request.files.get('file')
    if not file:
        return error_response("file é obrigatório", 400)

    # 2. Lê ‘adaptations’ e ‘extra’ do FormData
    try:
        adaptations = json.loads(request.form.get('adaptations', '{}'))
    except Exception:
        return error_response("adaptations inválido", 400)
    additional_adaptations = request.form.get('additional_adaptations', '')

    # 3. OCR
    ocr = azure_ocr(file.read())
    if isinstance(ocr, dict) and "error" in ocr:
        return error_response("Falha no OCR", 500)

    # 4. Chama GPT com options + additional_adaptations
    res = adapt_text_for_inclusivity(text=ocr, options=adaptations, extra=additional_adaptations)
    if "error" in res:
        code = 400 if res["error"] == "content_policy_violation" else 500
        return error_response(res["error"], code)

    # 5. Processa resposta
    parts   = res['text'].split("---------")
    adapted = parts[0].strip()
    imgs    = []
    if len(parts) > 1:
        lines = parts[1].strip().split('\n')[1:]
        imgs  = [line.split('. ')[1] if '. ' in line else line for line in lines if line]

    elapsed = round(time.time() - start, 2)

    return jsonify({
        "success": True,
        "adapted_text": adapted,
        "images": imgs,
        "processing_time": elapsed
    }), 200


# 2. Criar Nova Atividade
@api.route('/create_activity', methods=['POST'])
def create_activity():
    start = time.time()
    payload = request.get_json() or {}

    # Campos enviados pelo frontend
    title                   = payload.get('title')
    series                  = payload.get('series')
    subject                 = payload.get('subject')
    bncc_competency         = payload.get('bncc_competency', '')
    learning_style          = payload.get('learning_style', '')
    description             = payload.get('description', '')
    adaptations             = payload.get('adaptations', {})
    additional_adaptations  = payload.get('additional_adaptations', '')

    # Validação
    if not title or not series or not subject:
        return error_response("title, series e subject são obrigatórios", 400)

    # Chama a lógica de geração usando todos os parâmetros
    res = create_new_activity(
        title,
        series,
        subject,
        bncc_competency,         
        learning_style,          
        description,             
        options=adaptations,
        extra=additional_adaptations
    )
    if "error" in res:
        code = 400 if res["error"] == "content_policy_violation" else 500
        return error_response(res["error"], code)

    parts      = res['text'].split("---------")
    activity   = parts[0].strip()
    imgs       = []
    if len(parts) > 1:
        lines = parts[1].strip().split('\n')[1:]
        imgs  = [line.split('. ')[1] if '. ' in line else line for line in lines if line]

    elapsed = round(time.time() - start, 2)
    return jsonify({
        "success": True,
        "activity_text": activity,
        "images": imgs,
        "processing_time": elapsed
    }), 200


# 3. Gerar Imagens de Apoio
@api.route('/generate_images', methods=['POST'])
def generate_images():
    start = time.time()
    payload = request.get_json() or {}

    text = payload.get('text')
    num  = payload.get('num_images', 1)
    if not text:
        return error_response("text é obrigatório", 400)

    result = create_dalle_images(text, n=num)
    if isinstance(result, dict) and "error" in result:
        code = 400 if result["error"] == "content_policy_violation" else 500
        return error_response(result["error"], code)

    images = [{"url": u, "keyword": text, "description": ""} for u in result]
    elapsed = round(time.time() - start, 2)
    return jsonify({
        "success": True,
        "images": images,
        "generation_time": elapsed
    }), 200


# api.py (adicionar/atualizar estes trechos)

# 4. Criar Quadrinhos (texto apenas)
@api.route('/create_comic', methods=['POST'])
def create_comic():
    start = time.time()
    payload = request.get_json() or {}
    adapted_text = payload.get('adapted_text')
    if not adapted_text:
        return error_response("adapted_text é obrigatório", 400)

    # gera narrativa+descrições de imagem
    comic_output = generate_comic_book(adapted_text)
    if isinstance(comic_output, dict) and "error" in comic_output:
        code = 400 if comic_output["error"] == "content_policy_violation" else 500
        return error_response(comic_output["error"], code)

    # parse dos painéis
    panel_data = parse_narration_and_images(comic_output)
    panels = []
    for idx, p in enumerate(panel_data):
        panels.append({
            "panel_number": idx + 1,
            "narration": p["narration"],
            "image_description": p["image_description"]
        })

    elapsed = round(time.time() - start, 2)
    return jsonify({
        "success": True,
        "panels": panels,
        "total_panels": len(panels),
        "generation_time": elapsed
    }), 200


# 5. Gerar Imagem de Único Painel
@api.route('/generate_single_comic_panel', methods=['POST'])
def generate_single_comic_panel():
    payload = request.get_json() or {}
    image_description = payload.get('image_description')
    if not image_description:
        return error_response("image_description é obrigatório", 400)

    # gera imagem para o painel
    result = create_dalle_images(image_description)
    if isinstance(result, dict) and "error" in result:
        code = 400 if result["error"] == "content_policy_violation" else 500
        return error_response(result["error"], code)

    # assume que result é uma lista de URLs, pegamos a primeira
    image_url = result[0] if isinstance(result, list) else result

    return jsonify({
        "success": True,
        "image_url": image_url
    }), 200


# 6. Inicializar ou obter thread de refinamento
@api.route('/initialize_refinement_chat', methods=['POST'])
def initialize_refinement_chat():
    # Cria ou obtém um thread_id novo
    resp = create_thread.__wrapped__()
    thread_id = resp.get_data(as_text=True).strip()
    return jsonify({"success": True, "thread_id": thread_id}), 200


# 7. Refinar Atividade via Chat (retornando só a resposta do agente)
@api.route('/refine_activity', methods=['POST'])
def refine_activity():
    payload      = request.get_json() or {}
    thread_id    = payload.get('thread_id')
    user_message = payload.get('user_message')
    activity_txt = payload.get('activity_text')

    if not user_message:
        return error_response("user_message é obrigatório", 400)

    # cria thread se não existir
    if not thread_id:
        init = create_thread.__wrapped__()
        thread_id = init.get_data(as_text=True).strip()

    # monta mensagem única
    combined = (
        f"# Essa é a atividade que preciso ajustar: {activity_txt}\n\n # E o ajuste que preciso é: {user_message}"
        if activity_txt else
        user_message
    )

    # injetamos no request o JSON esperado pelo handler original
    request._cached_json = {False: {"thread_id": thread_id, "user_message": combined}}

    # chama o handler interno
    resp = handle_message.__wrapped__()

    # prepara retorno
    status = 200
    message = None

    # Caso o handler retorne string simples
    if isinstance(resp, str):
        message = resp

    else:
        # resp é um Response
        status = getattr(resp, "status_code", 200)
        # tenta parsear JSON
        body = resp.get_json(silent=True)
        if isinstance(body, dict):
            # se for um JSON de imagem ou outro payload, repassa inteiro
            if "image_url" in body:
                message = body
            # senão, extrai o texto da IA
            else:
                message = body.get("ai_response") or body.get("text") or body
        else:
            # fallback para texto puro
            message = resp.get_data(as_text=True)

    return jsonify({
        "success": True,
        "thread_id": thread_id,
        "message": message
    }), status


# 8. Upload de Arquivo (opcional)
@api.route('/upload_file', methods=['POST'])
def upload_file():
    file = request.files.get('file')
    if not file:
        return error_response("file é obrigatório", 400)

    extract = request.form.get('extract_text', 'false').lower() == 'true'
    file_id = str(uuid.uuid4())
    resp    = {"success": True, "file_id": file_id}

    if extract:
        text = azure_ocr(file.read())
        if isinstance(text, dict) and "error" in text:
            return error_response("Falha no OCR", 500)
        resp["text"] = text

    return jsonify(resp), 200


# Helpers para quadrinhos

def parse_narration_and_images(comic_output: str):
    panels = []
    narration = None
    for line in comic_output.split('\n'):
        if "NARRAÇÃO:" in line:
            narration = line.replace("NARRAÇÃO:", "").strip()
        elif "DESCRIÇÃO DE IMAGEM:" in line and narration:
            img_desc = line.replace("DESCRIÇÃO DE IMAGEM:", "").strip()
            panels.append({
                'narration': narration,
                'image_description': img_desc + ' Comic Book.'
            })
            narration = None
    return panels