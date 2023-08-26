import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Azure OCR API endpoint and API key
AZURE_OCR_ENDPOINT = "https://para-casa-inclusivo-ocr.cognitiveservices.azure.com/"
AZURE_OCR_API_KEY = os.getenv("AZURE_OCR_API_KEY")  # You'll insert this later

# Create headers for the API request
headers = {
    "Ocp-Apim-Subscription-Key": AZURE_OCR_API_KEY,
    "Content-Type": "application/octet-stream"
}

# OCR API URL
ocr_url = f"{AZURE_OCR_ENDPOINT}/vision/v3.1/read/analyze"

def azure_ocr(image_data):
    """Perform OCR using Azure OCR API."""
    response = requests.post(ocr_url, headers=headers, data=image_data)
    
    if response.status_code != 202:
        return {"error": "Failed to start OCR job"}
    
    # Retrieve the result
    result_url = response.headers["Operation-Location"]
    
    for _ in range(10):
        result_response = requests.get(result_url, headers={"Ocp-Apim-Subscription-Key": AZURE_OCR_API_KEY})
        result_data = result_response.json()
        
        if result_data.get("status") == "succeeded":
            # Extract text from the OCR result
            text = ""
            for line in result_data["analyzeResult"]["readResults"][0]["lines"]:
                text += line["text"] + "\n"
            return {"text": text.strip()}
        
    return {"error": "OCR timed out"}
