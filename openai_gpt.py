import os
import logging
from dotenv import load_dotenv
from openai import OpenAI, OpenAIError
import requests

# Load environment variables from .env file
load_dotenv()

USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_BASE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_GPT_ENDPOINT = f"{AZURE_OPENAI_BASE_ENDPOINT}/openai/deployments/gpt-4o/chat/completions?api-version=2024-02-15-preview"
AZURE_OPENAI_DALLE_ENDPOINT = f"{AZURE_OPENAI_BASE_ENDPOINT}/openai/deployments/dall-e-3/images/generations?api-version=2024-02-01"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not USE_AZURE_OPENAI:
    client = OpenAI(api_key=OPENAI_API_KEY)

# Create a logger with the __name__ of the module
logger = logging.getLogger(__name__)

def adapt_text_for_inclusivity(extracted_text):
    """Adapt text for inclusivity using OpenAI GPT or Azure OpenAI."""

    messages = [
        {
            "role": "system",
            "content": "# PARA CASA INCLUSIVO\nVocê receberá o texto recuperado de um documento de uma atividade escolar.\nSiga os passos abaixo para adaptar essa atividade tonando-a mais inclusiva.\n\n1. Extraia apenas o texto da atividade, ignorando cabeçalhos, rodapés e legendas de imagens.\n\n2. Reescreva o texto extraído no passo 1 seguindo as regras abaixo:\n2.1. Linguagem Simples\n2.2. Reduzir o texto sem perder o contexto\n2.3. Usar emojis para facilitar a compreensão\n2.4. TODAS AS LETRAS EM MAIÚSCULA\n2.5. Separe o texto em parágrafos para facilitar a leitura \n2.6. Destaque as palavras mais importantes de cada parágrafo em **negrito** para facilitar a leitura\n\n3. Crie uma lista de até 4 descrições de imagens que poderiam apoiar e facilitar o entendimento do texto adaptado.\n3.1 A descrição deve ser criada em inglês, para geração com modelos de IA\n3.2 As imagens devem ser claras e sem ambiguidade sobre o conceito representado\n3.3 Inclua este marcador  na resposta que indica onde a lista de imagens inicia: \"---------\"\n\n4. Responda apenas com o texto final adaptado e a lista de imagens sugeridas."
        },
        {
            "role": "user",
            "content": extracted_text
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
            return {"error in adapt_text_for_inclusivity": str(e)}
    else:
        try:
            response = client.chat.completions.create(
                model="gpt-4o",
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
                return {"error in adapt_text_for_inclusivity": "content_policy_violation"}
            else:
                logger.error("An error occurred: %s", str(e), exc_info=True)
                return {"error in adapt_text_for_inclusivity": str(e)}
        except Exception as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in adapt_text_for_inclusivity": str(e)}

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
                model="gpt-4o",
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
                model="gpt-4o",
                messages=messages,
                temperature=0,
                max_tokens=4096,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in generate_comic_book": str(e)}
      
def create_dalle_images(prompt, n=1, size="1024x1024"):
    if USE_AZURE_OPENAI:
        headers = {
            "Content-Type": "application/json",
            "api-key": AZURE_OPENAI_API_KEY,
        }
        payload = {
            "prompt": prompt,
            "n": n,
            "size": size
        }
        try:
            response = requests.post(AZURE_OPENAI_DALLE_ENDPOINT, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Check if there's an error with content filtering
            if "error" in data and data["error"]["code"] == "contentFilter":
                logger.error("Content policy violation: %s", data["error"]["message"], exc_info=True)
                return {"error in create_dalle_images": "content_policy_violation"}
            # Check if the 'data' key is in the response to extract image URLs
            if "data" in data:
                return [img["url"] for img in data["data"]]
            else:
                return {"error in create_dalle_images": "No images generated"}
        except requests.RequestException as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in create_dalle_images": str(e)}
    else:
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
            # Check for content policy violation
            if 'content_policy_violation' in str(e):
                logger.error("Content policy violation: %s", str(e), exc_info=True)
                return {"error in create_dalle_images": "content_policy_violation"}
            else:
                logger.error("An error occurred: %s", str(e), exc_info=True)
                return {"error in create_dalle_images": str(e)}
        except Exception as e:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error in create_dalle_images": str(e)}