from flask import Flask, request, jsonify, render_template
from azure_ocr import azure_ocr
from openai_gpt import adapt_text_for_inclusivity

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

            #print(gpt_result)  
            return jsonify({'adapted_text': gpt_result['text']})
              
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
    
    
