import os
import requests
import base64
import uuid
from dotenv import load_dotenv
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, BlobSasPermissions

# Load environment variables
load_dotenv()

# Get the Stability API Key from environment variables
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")

# Initialize the BlobServiceClient
azure_connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
blob_service_client = BlobServiceClient.from_connection_string(azure_connection_string)

def generate_sas_url(blob_service_client, container_name, blob_name):
    sas_token = generate_blob_sas(
        account_name=blob_service_client.account_name,
        container_name=container_name,
        blob_name=blob_name,
        account_key=blob_service_client.credential.account_key,
        permission=BlobSasPermissions(read=True),
        expiry=datetime.utcnow() + timedelta(hours=24),
        snapshot=None,
        start=datetime.utcnow(),
        version=None,
        cache_control=None,
        content_disposition='inline',
        content_encoding=None,
        content_language=None,
        content_type='image/png'
    )
    sas_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{blob_name}?{sas_token}"
    return sas_url

def upload_to_azure_blob(base64_str):
    # Generate a unique identifier
    unique_id = str(uuid.uuid4())
    
    # Create a unique image name
    image_name = f'image_{unique_id}.png'
    
    # Get the container name from environment variable
    container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME')
    container_client = blob_service_client.get_container_client(container_name)
    
    # Convert Base64 to bytes
    image_data = base64.b64decode(base64_str)
    
    # Get blob client
    blob_client = container_client.get_blob_client(image_name)
    
    # Upload the image
    blob_client.upload_blob(image_data, overwrite=True)
    
    # Generate the blob public URL
    sas_url = generate_sas_url(blob_service_client, container_name, image_name)
    
    return sas_url

def save_and_get_image_url(base64_str):
    
    # Upload to Azure Blob Storage and get the URL
    image_url = upload_to_azure_blob(base64_str)
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
        return {"error in create_stability_images": str(e)}
