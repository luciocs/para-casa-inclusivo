from flask import Flask, request, jsonify, render_template
from azure_ocr import azure_ocr
from openai_gpt import adapt_text_for_inclusivity
from openai_gpt import create_dalle_images
from openai_gpt import generate_comic_book
from azure_bing import search_images
import urllib.parse

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        all_files = request.files.to_dict(flat=False)
        concatenated_text = ""

        # Loop through each uploaded file
        for file_key in all_files:
            for file in all_files[file_key]:
                if file:
                    image_data = file.read()
                    # Call Azure OCR to extract text
                    ocr_result = azure_ocr(image_data)
                    # If ocr_result is None, that means an error occurred
                    if ocr_result is None:
                        return jsonify({"error": "Failed to extract text from one or more images"}), 400
                    
                    concatenated_text += ocr_result + "\n"  # Concatenate OCR results

        # Call OpenAI GPT to process the concatenated text
        gpt_result = adapt_text_for_inclusivity(concatenated_text)
        # If gpt_result is None, that means an error occurred
        if gpt_result is None:
            return jsonify({"error": "Failed to generate text"}), 400

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

    return render_template('index.html')

@app.route('/fetch_images', methods=['POST'])
def fetch_images():
    image_keywords = request.json.get('image_keywords', [])
    #Serachin for the images on the internet
    image_urls = []
    for keyword in image_keywords:
          url = search_images(keyword)
          if url:
              image_urls.append(url)              

    #print(image_urls)  
    return jsonify({'image_urls': image_urls})  

@app.route('/generate_images', methods=['POST'])
def generate_images():
    image_keywords = request.json.get('image_keywords', [])
    #Generate images using Dall-E
    image_urls = []
    for keyword in image_keywords:
          url = create_dalle_images(keyword)
          if url:
              image_urls.append(url)              
        
    return jsonify({"image_urls": image_urls})  

@app.route('/generate_comic', methods=['POST'])
def generate_comic():
    # Get the adapted text from the request
    adapted_text = request.json.get('adapted_text')
    # Generate comic book narration and image descriptions
    comic_output = generate_comic_book(adapted_text)
    # Create the panels
    panels = create_panels(comic_output)
    return jsonify({'comic_panels': panels})    

def create_panels(comic_output):
    panels_data = parse_narration_and_images(comic_output)
    for panel in panels_data:
        image_url = create_dalle_images(panel['image_description'] + " Faça isso em um estilo vector artwork.")
        panel['image_url'] = image_url
    return panels_data
  
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
                panels.append({'narration': narration, 'image_description': image_description})
                narration = None  # Reset narration for the next panel
                image_description = None  # Reset image_description for the next panel
    return panels

# Function to generate WhatsApp sharing URL
def generate_whatsapp_url(adapted_text):
    base_url = "https://api.whatsapp.com/send?text="
    adapted_text_encoded = urllib.parse.quote(adapted_text)
    return f"{base_url}{adapted_text_encoded}"
  
  
if __name__ == '__main__':
    app.run(debug=True)
    
    
