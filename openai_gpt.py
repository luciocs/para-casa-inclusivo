import os
import logging
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError, AzureOpenAI
import requests

# Load environment variables from .env file
load_dotenv()

USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_BASE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_GPT_ENDPOINT = f"{AZURE_OPENAI_BASE_ENDPOINT}/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2024-12-01-preview"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if USE_AZURE_OPENAI:
    client = AzureOpenAI(
        api_version="2024-12-01-preview",
        azure_endpoint=AZURE_OPENAI_BASE_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
    )
else:
    client = OpenAI(api_key=OPENAI_API_KEY)
    
# Create a logger with the __name__ of the module
logger = logging.getLogger(__name__)

def adapt_text_for_inclusivity(
    text: str,
    options: dict = None,
    extra: str = ""
) -> dict:
    """
    Adapta o texto para inclusividade.
    - text: conteúdo original
    - options: dict opcional com chaves enviadas pelo frontend
    - extra: str opcional com instruções adicionais
    Retorna {"text": "..."} ou {"error": "..."}.
    """
    # mapeamento frontend→instrução
    mapping = {
        "simplificar_linguagem": "Use linguagem simples",
        "incluir_emojis": "Insira emojis para facilitar a compreensão",
        "destaque_negrito": "Destaque palavras importantes em **negrito**",
        "caixa_alta": "Coloque TODO O TEXTO EM MAIÚSCULAS",
        "reducao_contexto": "Reduza o texto sem perder o contexto"
    }

    opts = options or {}
    # filtra apenas chaves válidas e ativas
    active_keys = [k for k, v in opts.items() if v and k in mapping]
    # se opcionalmente vier vazio, podemos usar todas exceto 'caixa_alta' por default:
    if not active_keys:
        active_keys = list(mapping.keys())

    instructions = [mapping[k] for k in active_keys]

    # monta system prompt
    system_content = (
        "# PARA CASA INCLUSIVO\nVocê receberá o texto recuperado de um documento de uma atividade escolar.\nSiga os passos abaixo para adaptar essa atividade tonando-a mais inclusiva.\n\n1. Extraia apenas o texto da atividade, ignorando cabeçalhos, rodapés e legendas de imagens.\n\n2. Reescreva o texto extraído no passo 1 seguindo as regras abaixo:"
        + ("\n".join(f"- {instr}" for instr in instructions) if instructions else "- Nenhuma\n")
        + f"\n\n{extra}\n\n"
        + "\n\n"
        "3. Crie uma lista de até 4 descrições de imagens que poderiam apoiar e facilitar o entendimento do texto adaptado.\n3.1 A descrição deve ser criada para geração com modelos de IA\n3.2 As imagens devem ser claras e sem ambiguidade sobre o conceito representado\n3.3 Inclua este marcador  na resposta que indica onde a lista de imagens inicia: \"---------\"\n\n4. Responda apenas com o texto final adaptado e a lista de imagens sugeridas."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user",   "content": text},
    ]

    # chamada à API
    if USE_AZURE_OPENAI:
        headers = {"Content-Type": "application/json", "api-key": AZURE_OPENAI_API_KEY}
        payload = {
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }
        try:
            resp = requests.post(AZURE_OPENAI_GPT_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return {"text": content}
        except Exception as e:
            logger.error("adapt_text_for_inclusivity failed: %s", e, exc_info=True)
            msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
            return {"error": msg}
    else:
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0,
                max_tokens=4096,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            content = resp.choices[0].message.content
            return {"text": content}
        except OpenAIError as e:
            logger.error("adapt_text_for_inclusivity error: %s", e, exc_info=True)
            msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
            return {"error": msg}
        except Exception as e:
            logger.error("adapt_text_for_inclusivity failed: %s", e, exc_info=True)
            return {"error": str(e)}


# openai_gpt.py (trecho ajustado)

def create_new_activity(
    title: str,
    series: str,
    subject: str,
    bncc_competency: str,
    learning_style: str,
    description: str,
    options: dict = None,
    extra: str = ""
) -> dict:
    """
    Gera uma nova atividade escolar completa:
    - title, series, subject, bncc_competency, learning_style, description
    - aplica apenas as regras ativas em `options`
    - retorna {"text", "adaptations_applied", "image_placeholders"} ou {"error"}
    """
    # mapeamento frontend → instrução
    mapping = {
        "simplificar_linguagem": "Use linguagem simples",
        "incluir_emojis": "Insira emojis para facilitar a compreensão",
        "destaque_negrito": "Destaque palavras importantes em **negrito**",
        "caixa_alta": "Coloque TODO O TEXTO EM MAIÚSCULAS",
        "reducao_contexto": "Reduza o texto sem perder o contexto"
    }

    opts = options or {}
    # somente chaves ativas e válidas
    active_keys = [k for k, v in opts.items() if v and k in mapping]
    instructions = [mapping[k] for k in active_keys]

    # constrói o prompt
    system_content = (
        "# PARA CASA INCLUSIVO – NOVA ATIVIDADE\n"
        f"Título: {title}\n"
        f"Série: {series}\n"
        f"Disciplina: {subject}\n"
        f"Competência BNCC: {bncc_competency}\n"
        f"Estilo de Aprendizagem: {learning_style}\n"
        f"Objetivos: {description}\n\n"
        "Regras de adaptação ativas:\n"
        + ("\n".join(f"- {instr}" for instr in instructions) if instructions else "- Nenhuma\n")
        + f"\n\n{extra}\n\n"
        "1. Agora, gere a atividade escolar completa em markdown, seguindo as regras acima.\n"
        "2. Crie uma lista de até 4 descrições de imagens que poderiam apoiar e facilitar o entendimento do texto adaptado.\n2.1 A descrição deve ser criada para geração com modelos de IA\n2.2 As imagens devem ser claras e sem ambiguidade sobre o conceito representado\n2.3 Inclua este marcador  na resposta que indica onde a lista de imagens inicia: \"---------\"\n\n3. Responda apenas com o texto final adaptado e a lista de imagens sugeridas."
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user",   "content": ""}
    ]

    # chamada à API (mesma lógica de adapt_text_for_inclusivity)
    if USE_AZURE_OPENAI:
        headers = {"Content-Type": "application/json", "api-key": AZURE_OPENAI_API_KEY}
        payload = {
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0,
        }
        try:
            resp = requests.post(AZURE_OPENAI_GPT_ENDPOINT, headers=headers, json=payload)
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            return {"text": content}
        except Exception as e:
            logger.error("create_new_activity failed: %s", e, exc_info=True)
            msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
            return {"error": msg}
    else:
        try:
            resp = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0,
                max_tokens=4096,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0,
            )
            content = resp.choices[0].message.content
            return {"text": content}
        except OpenAIError as e:
            logger.error("create_new_activity error: %s", e, exc_info=True)
            msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
            return {"error": msg}
        except Exception as e:
            logger.error("create_new_activity failed: %s", e, exc_info=True)
            return {"error": str(e)}


def change_activity_theme(adapted_text, new_theme):
    """Adapt text for inclusivity using OpenAI GPT or Azure OpenAI."""

    messages = [
        {
            "role": "system",
            "content": "# PARA CASA INCLUSIVO\nA seguir está um texto adaptado para uma atividade educacional. Re-adapte este texto de acordo com o novo tema fornecido, tornando mais atrativa para a criança.\n\n1. Siga os passos abaixo para adaptar essa atividade.\n\n1.1. Linguagem Simples\n1.2. Usar emojis para facilitar a compreensão\n1.3. TODAS AS LETRAS EM MAIÚSCULA\n1.4. Separe o texto em parágrafos para facilitar a leitura \n1.5. Destaque as palavras mais importantes de cada parágrafo em **negrito** para facilitar a leitura\n\n2. Crie uma lista de até 4 descrições de imagens que poderiam apoiar e facilitar o entendimento do texto adaptado.\n2.1 A descrição deve ser criada em inglês, para geração com modelos de IA\n2.2 As imagens devem ser claras e sem ambiguidade sobre o conceito representado\n2.3 Inclua este marcador na resposta que indica onde a lista de imagens inicia: \"---------\"\n\n3. Responda apenas com o texto final adaptado e a lista de imagens sugeridas."
        },
        {
            "role": "user",
            "content": adapted_text
        },
        {
            "role": "user",
            "content": "Novo tema: " + new_theme
        }
    ]

    if USE_AZURE_OPENAI:
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY,
        }
        payload = {
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        try:
            response = requests.post(AZURE_OPENAI_GPT_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            return {"text": response.json()["choices"][0]["message"]["content"]}
        except requests.RequestException as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in change_activity_theme": str(e)}
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0,
                max_tokens=4096,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return {"text": response.choices[0].message.content}
        except OpenAIError as e:
            if 'content_policy_violation' in str(e):
                logger.error("Content policy violation: %s", str(e), exc_info=True)
                return {"error in change_activity_theme": "content_policy_violation"}
            else:
                logger.error("An error occurred: %s", str(e), exc_info=True)
                return {"error in change_activity_theme": str(e)}
        except Exception as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in change_activity_theme": str(e)}

def generate_comic_book(adapted_text):
    """Generate comic book narration and image descriptions using OpenAI GPT or Azure OpenAI."""

    messages=[
        {
            "role": "system",
            "content": "# PARA CASA INCLUSIVO - VERSÃO QUADRINHOS\nVocê receberá o texto adaptado de uma atividade escolar. Sua tarefa é transformá-lo em narração e descrições de imagens para um livro de quadrinhos com 4 painéis por página, 2 em cada linha.\n\n1. Divida o texto adaptado em segmentos menores que serão usados em cada painel do quadrinho.\n2. Escreva a narração para cada painel de forma que complemente as ilustrações que serão geradas. O texto deve seguir as diretrizes:\n2.1. Linguagem Simples\n2.2. Usar emojis para facilitar a compreensão\n2.3. TODAS AS LETRAS EM MAIÚSCULA\n2.4. Destaque as palavras mais importantes de cada parágrafo em **negrito** para facilitar a leitura\n3. Para cada painel, inclua também uma descrição de imagem para ser gerada pelo modelo dall-e-3\n3.1 A descrição deve ser criada em inglês\n4. Certifique-se de que a narração e as descrições de imagem fluiam bem e façam sentido como uma história em quadrinhos.\n5. Indique claramente onde começa e termina a narração e a descrição de cada painel, para facilitar a montagem posterior.\n\nResponda apenas com a narração e descrições de imagem para os painéis, no seguinte formato:\n**PAINEL 1:**\nNARRAÇÃO: [TEXTO DE NARRAÇÃO]\nDESCRIÇÃO DE IMAGEM:  [IMAGE DESCRIPTION]"
        },
        {
            "role": "user",
            "content": adapted_text
        }
    ]
    
    if USE_AZURE_OPENAI:
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY,
        }
        payload = {
            "messages": messages,
            "temperature": 0,
            "max_tokens": 4096,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }
        try:
            response = requests.post(AZURE_OPENAI_GPT_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in generate_comic_book": str(e)}
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                messages=messages,
                temperature=0,
                max_tokens=4096,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return response.choices[0].message.content
        except OpenAIError as e:
            logger.error("generate_comic_book error: %s", e, exc_info=True)
            msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
            return {"error": msg}
        except Exception as e:
            logger.error("generate_comic_book failed: %s", e, exc_info=True)
            return {"error": str(e)}
      
def create_dalle_images(prompt, n=1, size="1024x1024"):
    try:
        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            n=n,
            size=size
        )
        if response and response.data:
            return [img.url for img in response.data]
        else:
            return {"error in create_dalle_images": "No images generated"}
    except OpenAIError as e:
        logger.error("create_dalle_images error: %s", e, exc_info=True)
        msg = "content_policy_violation" if "policy" in str(e).lower() else str(e)
        return {"error": msg}
    except Exception as e:
        logger.error("create_dalle_images failed: %s", e, exc_info=True)
        return {"error": str(e)}