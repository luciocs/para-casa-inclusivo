from flask import request, abort, Response, Blueprint
from functools import wraps
import requests
import os
import openai
import time

assistant_api = Blueprint('assistant_api', __name__)

# Setup OpenAI and API keys
openai.api_key = os.environ.get('OPENAI_ASS_API_KEY')
VALID_API_KEYS = {os.environ.get('PCI_API_KEY'): True}
assistant_id = os.environ.get('ASSISTANT_ID')
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
    user_message = request.json.get('user_message')
    file_url = request.json.get('file_url')
    file_ids = []
  
    # Check if file_url exists and is not empty
    if file_url:
        # Download the file content from URL
        response = requests.get(file_url)
        response.raise_for_status()  # Ensure the download was successful
        # Upload the file to Assistant
        uploaded_file = client.files.create(
            file= (os.path.basename(file_url), response.content, 'application/octet-stream'),
            purpose="assistants"
        )
        file_ids.append(uploaded_file.id)
    
    # Add user message to thread
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_message,
        file_ids=file_ids
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