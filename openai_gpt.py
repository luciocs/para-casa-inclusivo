import os
import openai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")  # You'll insert this later

def adapt_text_for_inclusivity(extracted_text):
    """Adapt text for inclusivity using OpenAI GPT."""
    
    # Initialize OpenAI API
    openai.api_key = OPENAI_API_KEY

    # Create a conversation with the prompt and user message
    messages = [
        {
            "role": "system",
            "content": "# PARA CASA INCLUSIVO\nVocê receberá o texto recuperado de um documento de uma atividade escolar.\nSiga os passos abaixo para adaptar essa atividade tonando-a mais inclusiva.\n\n1. Extraia apenas o texto da atividade, ignorando cabeçalhos, rodapés e legendas de imagens.\n\n2. Reescreva o texto extraído no passo 1 seguindo as regras abaixo:\n2.1. Linguagem Simples\n2.2. Reduzir o texto sem perder o contexto\n2.3. Usar emojis para facilitar a compreensão\n2.4. TODAS AS LETRAS EM MAIÚSCULA\n2.5. Separe o texto em parágrafos para facilitar a leitura \n2.6. Destaque as palavras mais importantes de cada parágrafo em **negrito** para facilitar a leitura\n\n3. Sugira uma lista de até 4 imagens que poderiam apoiar e facilitar o entendimento do texto adaptado.\n3.1 As imagens devem ser claras e sem ambiguidade sobre o conceito representado\n3.2 Inclua este marcador  na resposta que indica onde a lista de imagens inicia: \"---------\"\n\n4. Responda apenas com o texto final adaptado e a lista de imagens sugeridas."
        },
        {
            "role": "user",
            "content": extracted_text
        }
    ]

    # Call OpenAI API for Chat Completion
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            temperature=0,
            max_tokens=4976,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        return {"text": response["choices"][0]["message"]["content"]}
    except Exception as e:
        return {"error": str(e)}
