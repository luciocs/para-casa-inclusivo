from flask import request, abort, Response, Blueprint, jsonify
from functools import wraps
from urllib.parse import unquote
import requests
import os
import openai
import time
import json 
from openai import AzureOpenAI
from azure_ocr import azure_ocr
from stability_ai import create_stability_images, create_bedrock_images
from openai_gpt import create_dalle_images

assistant_api = Blueprint('assistant_api', __name__)

# Setup OpenAI and API keys
USE_AZURE_OPENAI = os.getenv("USE_AZURE_OPENAI", "False").lower() == "true"
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-05-01-preview")
OPENAI_API_KEY = os.getenv('OPENAI_ASS_API_KEY')
VALID_API_KEYS = {os.environ.get('PCI_API_KEY'): True}
assistant_id = os.environ.get('ASSISTANT_ID')
IMAGE_PROVIDER = os.getenv('IMAGE_PROVIDER', 'Stability')  # Default to Stability AI

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

        # Check if the run requires action
        if run.status == 'requires_action':
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            tool_outputs = []

            # Iterate over the required tool calls
            for call in tool_calls:
                if call.function.name == 'generate_image':
                    # Extract the prompt argument from the function call
                    prompt = json.loads(call.function.arguments).get('prompt')
                    # Generate the image using the selected provider
                    image_url = generate_image_based_on_provider(prompt)
                    if not image_url:
                        return Response('Failed to generate image.', status=500, mimetype='text/plain')

                    # Add the tool output with the generated image URL
                    tool_outputs.append({
                        "tool_call_id": call.id,
                        "output": json.dumps({"image_url": image_url})
                    })

            # End the run and submit tool outputs
            submit_tool_outputs(thread_id, run.id, tool_outputs)

            # Return the image URL directly to Blip
            return jsonify({"image_url": image_url})
        
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

# Function to generate a single image based on the selected provider
def generate_image_based_on_provider(keyword):
    if IMAGE_PROVIDER == 'OpenAI':
        result = create_dalle_images(keyword)
        if isinstance(result, dict) and "error in create_dalle_images" in result:
            error_message = result["error in create_dalle_images"]
            print(f"Error in OpenAI DALL-E: {error_message}")
            return None
        return result[0]  # Assuming result is a list of URLs and we need just the first one
    elif IMAGE_PROVIDER == 'Bedrock':
        url = create_bedrock_images(keyword)
        return url
    else:
        url = create_stability_images(keyword)
        return url

# Function to submit tool outputs to the assistant and end the run
def submit_tool_outputs(thread_id, run_id, tool_outputs):
    client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run_id,
        tool_outputs=tool_outputs
    )