import os
import requests
import base64
import uuid
import logging
import boto3
import json
import random
from dotenv import load_dotenv
from botocore.exceptions import ClientError

# Load environment variables
load_dotenv()

# Get the Stability API Key from environment variables
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# Create a logger with the __name__ of the module
logger = logging.getLogger(__name__)

# Initialize the S3 client
s3_client = boto3.client('s3', region_name=os.getenv('AWS_REGION'))

def generate_presigned_url(bucket_name, object_name, expiration=3600):
    """Generate a presigned URL to share an S3 object"""
    response = s3_client.generate_presigned_url('get_object',
                                                Params={'Bucket': bucket_name,
                                                        'Key': object_name},
                                                ExpiresIn=expiration)
    return response

def upload_to_s3(base64_str, bucket_name):
    # Generate a unique identifier
    unique_id = str(uuid.uuid4())

    # Create a unique image name
    image_name = f'image_{unique_id}.png'

    # Convert Base64 to bytes
    image_data = base64.b64decode(base64_str)

    # Upload the image to S3
    s3_client.put_object(Bucket=bucket_name, Key=image_name, Body=image_data, ContentType='image/png')

    # Generate a presigned URL to access the image
    presigned_url = generate_presigned_url(bucket_name, image_name)

    return presigned_url

def save_and_get_image_url(base64_str):
    bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
    # Upload to S3 and get the presigned URL
    image_url = upload_to_s3(base64_str, bucket_name)
    return image_url
  
def create_stability_images(prompt, n=1, size="1024x1024"):
    # Split the size into width and height
    width, height = map(int, size.split("x"))
    
    # Prepare the request body and headers
    body = {
        "steps": 40,
        "width": width,
        "height": height,
        "seed": 0,
        "cfg_scale": 5,
        "samples": n,
        "text_prompts": [
            {
                "text": prompt,
                "weight": 1
            }
        ],
    }
    
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {STABILITY_API_KEY}",
    }
    
    # Make the API request
    url = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
    try:
        response = requests.post(url, headers=headers, json=body)
        if response.status_code == 200:
            data = response.json()
            base64_images = [img["base64"] for img in data["artifacts"]]
            image_urls = [save_and_get_image_url(img) for i, img in enumerate(base64_images)]
            return image_urls
        else:
            return {"error in create_stability_images": "No images generated"}
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)
        return {"error in create_stability_images": str(e)}

def create_bedrock_images(prompt, n=1, size="512x512"):
    # Choose the model based on the environment variable BEDROCK_IMAGE_MODEL
    model_id = os.getenv('BEDROCK_IMAGE_MODEL', 'stability.stable-diffusion-xl-v1')

    # Change the default size to 1024x1024 for stability model
    if model_id == 'stability.stable-diffusion-xl-v1':
        size = "1024x1024"
    # Split the size into width and height
    width, height = map(int, size.split("x"))

    # Calculate the seed before choosing the model
    seed = random.randint(0, 4294967295)

    client = boto3.client('bedrock-runtime', region_name=os.getenv('AWS_REGION'))

    if model_id == "amazon.titan-image-generator-v2:0":
        # Payload for Titan model
        native_request = {
            "textToImageParams": {"text": prompt},
            "taskType": "TEXT_IMAGE",
            "imageGenerationConfig": {
                "cfgScale": 8.0,
                "seed": seed,
                "quality": "standard",
                "width": width,
                "height": height,
                "numberOfImages": n
            }
        }
    else:
        # Payload for Stability AI model
        native_request = {
            "text_prompts": [{"text": prompt}],
            "seed": seed,
            "cfg_scale": 15,
            "steps": 50,
            "width": width,
            "height": height
        }

    request = json.dumps(native_request)
    logger.debug("Image Prompt: %s", str(prompt), exc_info=True)
    try:
        # Call the model using Bedrock runtime
        response = client.invoke_model(
            modelId=model_id,
            body=request
        )
        model_response = json.loads(response["body"].read())
        if model_id == "amazon.titan-image-generator-v2:0":
            # Extract images for Titan model
            base64_images = model_response["images"]
        else:
            # Extract images for Stability model
            base64_images = [artifact['base64'] for artifact in model_response['artifacts']]

        # Save and return images
        image_urls = [save_and_get_image_url(img) for img in base64_images]
        return image_urls

    except ClientError as e:
        error_message = e.response['Error']['Message']
        if 'filtered words' in error_message or 'content filters' in error_message or 'has been filtered' in error_message:
            logger.error("Content Policy block: %s", str(e), exc_info=True)
            return {"error": "content_policy_violation"}
        else:
            logger.error("An error occurred: %s", str(e), exc_info=True)
            return {"error": "Ocorreu um erro ao gerar esta imagem. Por favor, tente novamente mais tarde."}
    except Exception as e:
        logger.error("An error occurred: %s", str(e), exc_info=True)
        return {"error": "Ocorreu um erro ao gerar esta imagem. Por favor, tente novamente mais tarde."}