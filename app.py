from flask import Flask, request, jsonify, render_template
from azure_ocr import azure_ocr
from openai_gpt import adapt_text_for_inclusivity
from openai_gpt import create_dalle_images
from azure_bing import search_images

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['file']
        if file:
            image_data = file.read()
                                   
            # Call Azure OCR to extract text
            ocr_result = azure_ocr(image_data)

            # If ocr_result is None, that means an error occurred
            if ocr_result is None:
                return jsonify({"error": "Failed to extract text from image"}), 400

            #print (ocr_result)
            # Call OpenAI GPT to process text
            gpt_result = adapt_text_for_inclusivity(ocr_result)

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
            
            return jsonify({'adapted_text': adapted_text, 'image_keywords': cleaned_image_list})
              
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
  
if __name__ == '__main__':
    app.run(debug=True)
    
    
