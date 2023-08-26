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
            ocr_result = azure_ocr(image_data)
            if 'error' in ocr_result:
                return jsonify(ocr_result), 400
            
            extracted_text = ocr_result['text']
            adaptation_result = adapt_text_for_inclusivity(extracted_text)
            if 'error' in adaptation_result:
                return jsonify(adaptation_result), 400
            
            return jsonify({'adapted_text': adaptation_result['text']})
    
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
