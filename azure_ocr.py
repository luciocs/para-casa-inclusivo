import os
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

# Load environment variables from .env file
load_dotenv()

# Set up Azure OCR API endpoint and API key
AZURE_OCR_ENDPOINT = "https://para-casa-inclusivo-ocr.cognitiveservices.azure.com/"
AZURE_OCR_API_KEY = os.getenv("AZURE_OCR_API_KEY")  # You'll insert this later

def azure_ocr(image_data):
    """
    Perform OCR on an image using Azure's Document Analysis Client.
    """
    # Initialize the Document Analysis client
    document_analysis_client = DocumentAnalysisClient(endpoint=AZURE_OCR_ENDPOINT, credential=AzureKeyCredential(AZURE_OCR_API_KEY))

    # Start the OCR process
    try:
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-document", image_data)
        result = poller.result()
    except Exception as e:
        return {"error": f"Failed to start OCR job: {str(e)}"}

    # Extract text from the OCR result
    extracted_text = []
    for page in result.pages:
        for line in page.lines:
            extracted_text.append(line.content)

    return " ".join(extracted_text)
