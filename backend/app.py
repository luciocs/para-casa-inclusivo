from flask import Flask, request, jsonify, render_template, send_from_directory
from azure_ocr import azure_ocr
from openai_gpt import adapt_text_for_inclusivity
import os

app = Flask(__name__, static_folder='../frontend')

# Serve the index.html file from the frontend directory
@app.route('/')
def index():
    return send_from_directory('../frontend', 'index.html')

# Handle the form submission for file upload and text adaptation
@app.route('/', methods=['POST'])
def process_file():
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

# Serve other static files from the frontend directory
@app.route('/<path:filename>')
def custom_static(filename):
    return send_from_directory('../frontend', filename)

if __name__ == '__main__':
    app.run(debug=True)
