from flask import Flask, request, jsonify, render_template, url_for
from utils import arrange_text_on_plane,ocr_data_extraction,load_model,prompt_template1,llm_output,data_to_json,prompt_template2
import os
from PIL import Image
from PyPDF2 import PdfReader
from ibm_watsonx_ai.foundation_models import Model
from ibm_watsonx_ai.foundation_models.utils.enums import ModelTypes
import json
import requests
import time
import base64
import warnings
import os
import shutil
import numpy as np
warnings.filterwarnings('ignore')
from doctr.io import DocumentFile
from doctr.models import ocr_predictor
from doctr.io import DocumentFile
import re

model=load_model()
app = Flask(__name__)

UPLOAD_FOLDER = 'static/uploads'

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'files[]' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    files = request.files.getlist('files[]')
    uploaded_files = []
    mock_response={}
   
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            try:
                uploaded_files.append(filename)
                invoice_data=ocr_data_extraction(file_path) 
                prompt=prompt_template1(invoice_data)
                generated_response=llm_output(prompt=prompt,model=model)
                generated_response=generated_response.replace("invoices",filename)
                json_data=data_to_json(generated_response)
                print(json_data)
                try:
                    mock_response[list(json_data.keys())[0]]=json_data[list(json_data.keys())[0]][0]
                except Exception as e:
                    mock_response[list(json_data.keys())[0]]=json_data[list(json_data.keys())[0]]
            except Exception as e:
                print(e)


    return jsonify({
        'files': uploaded_files,    
        'details': mock_response
    })

@app.route('/update-invoice', methods=['POST'])
def update_invoice():
    try:
        # Get the incoming JSON data
        updated_data = request.get_json()
        print(updated_data)
        # Example: print or process the data


        # Respond back with a success message
        return jsonify({"message": "Invoice details updated successfully!"}), 200

    except Exception as e:
        return jsonify({"error": f"Error processing the data: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
