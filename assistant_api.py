from flask import request, abort, Response, Blueprint
from functools import wraps
from urllib.parse import unquote
import requests
import os
import openai
import time
from openai import AzureOpenAI
from azure_ocr import azure_ocr

assistant_api = Blueprint('assistant_api', __name__)

# Setup OpenAI and API keys
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
OPENAI_API_KEY = os.getenv('OPENAI_ASS_API_KEY')
VALID_API_KEYS = {os.environ.get('PCI_API_KEY'): True}
assistant_id = os.environ.get('ASSISTANT_ID')

# Initialize the appropriate OpenAI client
if USE_AZURE_OPENAI:
    client = AzureOpenAI(
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_key=AZURE_OPENAI_API_KEY,
        api_version=AZURE_OPENAI_API_VERSION
    )
else:
    openai.api_key = OPENAI_API_KEY
    client = openai.OpenAI()

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        incoming_api_key = request.headers.get("PCIAPIKEY")
        if incoming_api_key and VALID_API_KEYS.get(incoming_api_key):
            return f(*args, **kwargs)
        else:
            abort(401)  # Unauthorized
    return decorated_function

@assistant_api.route('/create_thread', methods=['POST'])
@require_api_key
def create_thread():
    client.beta.assistants.retrieve(assistant_id=assistant_id)
    thread = client.beta.threads.create()
    thread_id = thread.id
    return Response(thread_id, mimetype='text/plain')

@assistant_api.route('/handle_message', methods=['POST'])
@require_api_key
def handle_message():
    thread_id = request.json.get('thread_id')
    user_message = unquote(request.json.get('user_message'))
    file_url = request.json.get('file_url')

    # Prepare content list
    content = []

    # Add user message to content if it's not empty
    if user_message:
        content.append({"type": "text", "text": user_message})

    # If file_url is provided, download the file and extract text using Azure OCR
    if file_url:
        response = requests.get(file_url)
        response.raise_for_status()  # Ensure the download was successful

        # Save the file locally with an appropriate extension
        file_name = 'downloaded_image.png'
        with open(file_name, 'wb') as file:
            file.write(response.content)

        # Pass the file in binary mode to the OCR function
        with open(file_name, 'rb') as image_data:
            extracted_text = azure_ocr(image_data.read())

        # Check if OCR was successful and append the text
        if isinstance(extracted_text, str) and extracted_text.strip():
            content.append({"type": "text", "text": extracted_text})
        else:
            return Response('Failed to extract text from the file.', status=400, mimetype='text/plain')

    # Ensure content is not empty before sending the message
    if content:
        # Add user message to thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=content
        )
    
        # Create a run for the thread
        run = client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id
        )
    
        # Poll the run status
        while run.status in ['queued', 'in_progress']:
            time.sleep(1)  # Sleep to avoid overwhelming the API with requests
            run = client.beta.threads.runs.retrieve(
                thread_id=thread_id,
                run_id=run.id
            )
    
        # Retrieve messages once the run completes
        if run.status == 'completed':
            messages = client.beta.threads.messages.list(thread_id=thread_id)
            if messages.data:
                return messages.data[0].content[0].text.value
            else:
                return Response('No response from the assistant.', status=404, mimetype='text/plain')
        else:
            return Response(f'Run did not complete successfully. Status: {run.status}', status=500, mimetype='text/plain')
    else:
        return Response('No content to send in the message.', status=400, mimetype='text/plain')