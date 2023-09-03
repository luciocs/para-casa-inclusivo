import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up Azure Image Search API endpoint and API key
AZURE_BING_API_ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/search"
AZURE_BING_API_KEY = os.getenv("AZURE_BING_API_KEY")

def search_images(keyword):
    try:
      headers = {"Ocp-Apim-Subscription-Key" : AZURE_BING_API_KEY}
      params  = {"q": keyword, "license": "public", "count": "1", "safeSearch": "Strict"}
      response = requests.get(AZURE_BING_API_ENDPOINT, headers=headers, params=params)
      response.raise_for_status()
      search_results = response.json()
      content_url = [img["contentUrl"] for img in search_results["value"][:16]]
      return content_url
    except Exception as e:
        print(e)
        return {"error": str(e)}