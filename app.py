from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from azure_ocr import azure_ocr
from openai_gpt import adapt_text_for_inclusivity
from openai_gpt import change_activity_theme
from openai_gpt import create_dalle_images
from openai_gpt import generate_comic_book
from stability_ai import create_stability_images, create_bedrock_images
from datetime import datetime
import urllib.parse
import os
import logging
import requests
from assistant_api import assistant_api
from whatsapp_handler import whatsapp_api
from api import api

app = Flask(__name__)
CORS(app) 
app.register_blueprint(assistant_api, url_prefix='/assistant')
app.register_blueprint(whatsapp_api, url_prefix='/whatsapp_api')
app.register_blueprint(api, url_prefix='/api')

IMAGE_PROVIDER = os.environ.get('IMAGE_PROVIDER', 'OpenAI')  # Default to OpenAI
COMIC_BOOK_GENERATION_ENABLED = os.getenv("COMIC_BOOK_GENERATION_ENABLED", "True").lower() == "true"

# Configure the logging
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
logger = logging.getLogger(__name__)

ZAPIER_WEBHOOK_URL = os.environ.get('ZAPIER_WEBHOOK_URL')

@app.route('/feedback', methods=['POST'])
def feedback():
    feedback_data = request.get_json()
    is_positive = feedback_data['positive']
    text_feedback = feedback_data.get('text', '')

    # Get the current date and time
    current_datetime = datetime.now()
    # Format the date and time as a string, e.g., '2023-01-28 14:35:22'
    formatted_datetime = current_datetime.strftime('%Y-%m-%d %H:%M:%S')
    
    # Construct the feedback payload
    payload = {
        'is_positive': is_positive,
        'text_feedback': text_feedback,
        'date_submitted': formatted_datetime,
    }

    # Send the feedback to the Zapier Webhook
    response = requests.post(ZAPIER_WEBHOOK_URL, json=payload)

    # Check if the POST request to the webhook was successful
    if response.status_code == 200:
        return jsonify({'success': True}), 200
    else:
        # Log or handle unsuccessful webhook POST request here
        return jsonify({'success': False, 'message': 'Failed to send feedback to webhook'}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
      try:
          all_files = request.files.to_dict(flat=False)
          concatenated_text = ""

          # Loop through each uploaded file
          for file_key in all_files:
              for file in all_files[file_key]:
                  if file:
                      image_data = file.read()
                      # Call Azure OCR to extract text
                      ocr_result = azure_ocr(image_data)
                      # Check if ocr_result is an error message
                      if isinstance(ocr_result, dict) and "error in azure_ocr" in ocr_result:
                          error_detail = ocr_result["error in azure_ocr"]
                          logger.error(f"Azure OCR error: {error_detail}")
                          return jsonify({"error": "Failed to extract text from images."}), 500
                      concatenated_text += ocr_result + "\n"  # Concatenate OCR results

          if not concatenated_text:
              raise ValueError("No text was concatenated from the images.")

          # Call OpenAI GPT to process the concatenated text
          gpt_result = adapt_text_for_inclusivity(concatenated_text)
          if isinstance(gpt_result, dict) and "error in adapt_text_for_inclusivity" in gpt_result:
              error_detail = gpt_result["error in adapt_text_for_inclusivity"]
              logger.error(f"GPT adaptation error: {error_detail}")
              if error_detail == "content_policy_violation":
                  return jsonify({"error": "Your request was rejected due to a content policy violation."}), 400
              # Handle other errors
              return jsonify({"error": "Failed to adapt text using GPT."}), 500            
            
          # Splitting adapted text and image list
          parts = gpt_result['text'].split("---------")
          adapted_text = parts[0]
          image_list = parts[1].strip().split('\n') if len(parts) > 1 else [] 

          # Remove the first element
          gpt_image_list = image_list[1:]
          # Remove any empty strings
          gpt_image_list = [item for item in gpt_image_list if item]
          # Remove the numbering
          cleaned_image_list = [item.split('. ')[1] if '. ' in item else item for item in gpt_image_list]
          #print(cleaned_image_list)

          # Include WhatsApp sharing URL
          whatsapp_url = generate_whatsapp_url(adapted_text)

          return jsonify({'adapted_text': adapted_text, 'image_keywords': cleaned_image_list, 'whatsapp_url': whatsapp_url})

      except Exception as e:
          logger.exception("An error occurred during image processing or adapting.")
          return jsonify({"error": "An unexpected error occurred during image processing or adapting."}), 500
                
    return render_template('index.html')

@app.route('/change_theme', methods=['POST'])
def change_theme():
    data = request.json
    adapted_text = data.get('adapted_text')
    new_theme = data.get('new_theme')

    # Ensure both adapted_text and new_theme are provided
    if not adapted_text or not new_theme:
        return jsonify({'error': 'Adapted text and new theme are required.'}), 400

    gpt_result = change_activity_theme(adapted_text, new_theme)

    if isinstance(gpt_result, dict) and "error in change_activity_theme" in gpt_result:
        error_detail = gpt_result["error in change_activity_theme"]
        logger.error(f"New Theme adaptation error: {error_detail}")
        if error_detail == "content_policy_violation":
            return jsonify({"error": "Your request was rejected due to a content policy violation."}), 400
        # Handle other errors
        return jsonify({"error": "Failed to adapt text to new theme using GPT."}), 500   

    # Splitting adapted text and image list
    parts = gpt_result['text'].split("---------")
    adapted_text = parts[0]
    image_list = parts[1].strip().split('\n') if len(parts) > 1 else [] 

    # Remove the first element
    gpt_image_list = image_list[1:]
    # Remove any empty strings
    gpt_image_list = [item for item in gpt_image_list if item]
    # Remove the numbering
    cleaned_image_list = [item.split('. ')[1] if '. ' in item else item for item in gpt_image_list]

    # Include WhatsApp sharing URL
    whatsapp_url = generate_whatsapp_url(adapted_text)
      
    return jsonify({'adapted_text': adapted_text, 'image_keywords': cleaned_image_list, 'whatsapp_url': whatsapp_url})
  
@app.route('/generate_images', methods=['POST'])
def generate_images():
    image_keywords = request.json.get('image_keywords', [])
    image_urls = []
    error_message = None
    #Generate images using Dall-E (OpenAI) or Stable Diffusion (Stability)
    for keyword in image_keywords:
        if IMAGE_PROVIDER == 'OpenAI':
            result = create_dalle_images(keyword)
            if isinstance(result, dict) and "error in create_dalle_images" in result:
                error_message = result["error in create_dalle_images"]
                break  # Stop processing further keywords once an error is encountered
            image_urls.append(result)  # Assuming result is a list of URLs
        elif IMAGE_PROVIDER == 'Bedrock':
            url = create_bedrock_images(keyword)
            if url:
                image_urls.append(url)    
        else:
            url = create_stability_images(keyword)
            if url:
                image_urls.append(url)
        
    if error_message:
        logger.error(f"Image Generation error: {error_message}")
        if error_message == "content_policy_violation":
            return jsonify({"error": "Your request was rejected due to a content policy violation."}), 400
        # Handle other errors
        return jsonify({"error": "Falha ao gerar imagem. Por favor, tente novamente mais tarde."}), 500            
    else:
        return jsonify({"image_urls": image_urls})
    
@app.route('/generate_comic_output', methods=['POST'])
def generate_comic_output():
    if not COMIC_BOOK_GENERATION_ENABLED:
        return jsonify({"error": "A criação de Gibi está temporariamente indisponível. Por favor, tente novamente mais tarde."}), 403
        
    adapted_text = request.json.get('adapted_text')
    comic_output = generate_comic_book(adapted_text)
    return jsonify({'comic_output': comic_output.split('\n\n')})  # Split the output into panels

@app.route('/generate_single_comic_panel', methods=['POST'])
def generate_single_comic_panel():
    panel_text = request.json.get('panel_text')
    panel_data = parse_narration_and_images(panel_text)
    panels, error_message = create_panels(panel_data)

    if error_message:
        logger.error(f"Image Generation error: {error_message}")
        if error_message == "content_policy_violation":
            return jsonify({"error": "Your request was rejected due to a content policy violation."}), 400
        # Handle other errors
        return jsonify({"error": "Falha ao gerar imagem. Por favor, tente novamente mais tarde."}), 500            
    else:    
      return jsonify({'comic_panel': panels[0]})  
  
def create_panels(panels_data):
    error_message = None
    for panel in panels_data:
        if IMAGE_PROVIDER == 'OpenAI':
            result = create_dalle_images(panel['image_description'])
            if isinstance(result, dict) and "error in create_dalle_images" in result:
                error_message = result["error in create_dalle_images"]
                break  # Stop processing further panels once an error is encountered
            if not error_message:
                panel['image_url'] = result
        elif IMAGE_PROVIDER == 'Bedrock':
            image_url = create_bedrock_images(panel['image_description'])
            if image_url:
                panel['image_url'] = image_url
        else:
            image_url = create_stability_images(panel['image_description'])
            if image_url:
                panel['image_url'] = image_url

    return panels_data, error_message
  
def parse_narration_and_images(comic_output):
    panels = []
    lines = comic_output.split('\n')
    narration = None
    image_description = None
    for line in lines:
        if "NARRAÇÃO:" in line:
            narration = line.replace("NARRAÇÃO:", "").strip()
        elif "DESCRIÇÃO DE IMAGEM:" in line:
            image_description = line.replace("DESCRIÇÃO DE IMAGEM:", "").strip()
            if narration and image_description:
                panels.append({'narration': narration, 'image_description': image_description + ' Comic Book.'})
                narration = None  # Reset narration for the next panel
                image_description = None  # Reset image_description for the next panel
    return panels

# Function to generate WhatsApp sharing URL
def generate_whatsapp_url(adapted_text):
    base_url = "https://api.whatsapp.com/send?text="
    adapted_text_encoded = urllib.parse.quote(adapted_text)
    return f"{base_url}{adapted_text_encoded}"
    
if __name__ == '__main__':
    app.run()
    
    
