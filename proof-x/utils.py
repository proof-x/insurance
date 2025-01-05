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
from PIL import Image

def arrange_text_on_plane(data):
    xmin = min(item["xmin"] for item in data)
    ymin = min(item["ymin"] for item in data)
    xmax = max(item["xmax"] for item in data)
    ymax = max(item["ymax"] for item in data)

    # Normalize data to start from (0, 0)
    for item in data:
        item["xmin"] -= xmin
        item["xmax"] -= xmin
        item["ymin"] -= ymin
        item["ymax"] -= ymin

    for item in data:
        item["midpoint_x"] = (item["xmin"] + item["xmax"]) / 2
        item["midpoint_y"] = (item["ymin"] + item["ymax"]) / 2

    # Define thresholds for merging based on average bounding box size
    avg_width = np.mean([item["xmax"] - item["xmin"] for item in data])
    avg_height = np.mean([item["ymax"] - item["ymin"] for item in data])
    x_threshold = avg_width * 0.3  # Adjust as needed
    y_threshold = avg_height * 0.5  # Adjust as needed

    merged_data = []
    data.sort(key=lambda item: (item["ymin"], item["xmin"]))  

    while data:
        base = data.pop(0)
        group = [base]
        overlapping = []
        for item in data:
            if (abs(item["xmin"] - base["xmax"]) < x_threshold  # Horizontal proximity
                    and abs(item["ymin"] - base["ymin"]) < y_threshold):  # Vertical proximity
                group.append(item)
                overlapping.append(item)
        
        merged_text = " ".join(g["text"] for g in group)
        xmin = min(g["xmin"] for g in group)
        xmax = max(g["xmax"] for g in group)
        ymin = min(g["ymin"] for g in group)
        ymax = max(g["ymax"] for g in group)
        merged_data.append({"text": merged_text, "xmin": xmin, "xmax": xmax, "ymin": ymin, "ymax": ymax})

        data = [item for item in data if item not in overlapping]

    scale_x = (xmax - xmin) / 1.0  
    scale_y = (ymax - ymin) / 1.0  

    plane = {}

    for item in merged_data:
        row = round(item["ymin"] / scale_y)  
        col = round(item["xmin"] / scale_x) 
        plane[(row, col)] = item["text"]

    rows = sorted(set(row for row, _ in plane.keys()))  
    cols = sorted(set(col for _, col in plane.keys()))  

  
    output = ""
    for row in rows:
        line = []
        for col in cols:
            line.append(plane.get((row, col), "").ljust(15))  
        output += " ".join(line) + "\n"

    return output




def ocr_data_extraction(imgpdf_path):
    if imgpdf_path.split(".")[-1]=='pdf':
        single_img_doc = DocumentFile.from_pdf(imgpdf_path)
    elif imgpdf_path.split(".")[-1]=="png" or imgpdf_path.split(".")[-1]=="jpg":
        single_img_doc = DocumentFile.from_images(imgpdf_path)

    model = ocr_predictor(pretrained=True)
    doc = single_img_doc
    result = model(doc)
    data=[]

    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    text = word.value
                    coordinates = word.geometry  
                    x_min=coordinates[0][0]
                    x_max=coordinates[1][0]
                    y_min=coordinates[0][1]
                    y_max=coordinates[1][1]
                    
                    data.append({
                        "text": text,
                        "xmin": x_min*1000,
                        "xmax": x_max*1000,
                        "ymin": y_min*1000,
                        "ymax": y_max*1000
                    })
    invoice_data=arrange_text_on_plane(data)
    invoice_data = re.sub(r"(?<=\d),(?=\d)", "", invoice_data)
    return invoice_data



def load_model():
    with open(r"creds.json", 'r') as f:
        watsonx_cred = json.load(f)

    model = Model(
        model_id=watsonx_cred['model_id'],
        params=watsonx_cred['params'],
        credentials=watsonx_cred['credentials'],
        project_id=watsonx_cred['project_id'],
        space_id=None)
    
    return model


def prompt_template1(invoice_data):
    prompt = """Task: Categorize and Organize Invoices
    You are provided with extracted invoice data, which contains details such as the bill description, amount, and other relevant information. Your goal is to process this data. 

    Assign each invoice to one of the following predefined categories based on the bill description:

    Healthcare
    Shopping
    Utilities
    Food
    Travel
    Miscellaneous (use this if no specific category fits the bill).
    Generate a JSON File
    Extract and store key details from the invoice, including:

    Date: The date of the invoice.
    Category: The assigned category of the bill.
    Summary: A brief summary of the bill description.
    Bill Amount: The total amount of the bill.

    data=** invoices_data **

    Input:
    The extracted invoice data.

    Output (Example):

    if the data is related to PO
    {
      "pos": [
        { 
        "category": "which category the bill belongs",
          "PO_Number": "Unique identifier for the PO",
          "Order_Date": "When the PO was issued",
          "Delivery_Date": "Expected delivery date",
          "Item_Description": "List of items/services requested",
          "Item_Quantity": "Number of units for each item",
          "Unit_Price": "Price per unit",
          "Subtotal": "Total before taxes and additional charges",
          "Shipping_Address": "Where the goods should be delivered",
          "Billing_Address": "Where the invoice should be sent",
          "Approval_Status": "Approved/Pending/Rejected"
        }
      ]
    }



    if the data is related to invoices

    {
      "invoices": 
        {
          ""
          "category": "which category the bill belongs"
          "Invoice_Number": "Unique identifier for the invoice",
          "Invoice_Date": "When the invoice was issued",
          "Due_Date": "When payment is due",
          "PO_Reference_Number": "If the invoice is linked to a PO",
          "Tax_Details": "e.g., VAT, GST, or other applicable taxes",
          "Line_Item_Details": [
            {
              "Item_Name": "Name of the item",
              "Quantity": "Number of units",
              "Unit_Price": "Price per unit",
              "Line_Total": "Total for this line item"
            }
          ],
          "Discounts": "If any",
          "Payment_Received": "Yes/No",
          "Total_amount": "total amount paid",
          "Total_tax" :"total tax paid",
          "Summary" : "summary of entire invocie"
        }
      
    }

    <endofcode>
    Note: Only return the JSON output in your response"""
    prompt=prompt.replace("invoices_data",invoice_data)
    return prompt



def llm_output(prompt,model):
    llm_output1=model.generate(prompt)
    generated_response=llm_output1['results'][0]['generated_text'].replace("<endofcode>","")
    return generated_response



def data_to_json(generated_response):
    data_string =generated_response
    try:
        start = data_string.index('{')
        end = data_string.rindex('}') + 1
        json_string = data_string[start:end]
        json_data = json.loads(json_string)

        return json_data
    except Exception as e:
        print("No valid JSON f ound in the string.",e)


def json_to_output(json_data):
    try:
        if list(json_data.keys())[0]=="invoices":
            with open('output.json', 'r') as file:
                data = json.load(file)
                data['invoices'].append(json_data['invoices'][0])

            with open("output.json","w") as json_file:
                json.dump(data, json_file, indent=4)
                
        print("JSON data saved successfully:", data)
    except Exception as e:
        print("inavlid json")


def prompt_template2(json_data,question):
    prompt=""""I have data stored in JSON format as follows:
    
    **json_data**
    Based on this JSON data, answer the following question:

    Question: **myquesion**

    Instructions:

    Analyze the given JSON data to understand its structure and values.
    If the question requires calculations, perform them step-by-step and clearly show your work.
    Provide a concise and accurate answer in a well-structured format.
    If applicable, include any relevant intermediate steps or explanations.


    note only generate the final answer 
    
    """

    
    prompt=prompt.replace("json_data",str(json_data))
    prompt=prompt.replace("myquesion",question)
    return prompt


def move_file(src_path, dest_folder):
    try:
        os.makedirs(dest_folder, exist_ok=True)
        dest_path = os.path.join(dest_folder, os.path.basename(src_path))
        shutil.move(src_path, dest_path)
        
        print(f"File moved successfully to {dest_path}")
    except FileNotFoundError:
        print(f"Source file not found: {src_path}")
    except Exception as e:
        print(f"An error occurred: {e}")



def rotate_image(image_path, output_path, angle):
    try:
        with Image.open(image_path) as img:
            rotated_img = img.rotate(angle, expand=True)
            rotated_img.save(output_path)
            print(f"Image rotated and saved to {output_path}")
    except FileNotFoundError:
        print(f"File not found: {image_path}")
    except Exception as e:
        print(f"An error occurred: {e}")

