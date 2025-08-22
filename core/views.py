# views.py in the 'ocr' app
import os
import boto3
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from task.models import Recipe,Receipt
# from task.serializers import ReceiptSerializer
import json

# AWS and OpenAI configuration (You can store this in settings.py for better security)
AWS_ACCESS_KEY_ID = 'your_aws_access_key_id'
AWS_SECRET_ACCESS_KEY = 'your_aws_secret_access_key'
AWS_REGION = 'your_aws_region'
OPENAI_API_KEY = 'your_openai_api_key'

class ReceiptUploadView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        # Step 1: Get the image from the request
        image = request.FILES.get('image')

        if not image:
            return Response({"error": "No image provided."}, status=400)

        # Step 2: Save the image to the server (optional if you want to store it in your database)
        receipt = Receipt.objects.create(image=image)

        # Step 3: Run your OCR function
        image_path = os.path.join("media", str(receipt.image))  # Adjust based on your media path
        extracted_text = extract_text_from_local_image(image_path)

        # Step 4: Categorize the receipt with GPT-4
        raw_json = categorize_receipt_with_gpt(extracted_text)
        structured_data = safe_parse_json(raw_json)

        # Step 5: Save the extracted data in the database
        receipt.extracted_data = structured_data
        receipt.save()

        # Return the structured data in the response
        if structured_data:
            return Response(structured_data, status=200)
        else:
            return Response({"error": "Failed to parse GPT response."}, status=500)

def extract_text_from_local_image(image_path):
    textract_client = boto3.client(
        'textract',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
    with open(image_path, 'rb') as img_file:
        img_bytes = img_file.read()

    response = textract_client.detect_document_text(Document={'Bytes': img_bytes})

    lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
    return '\n'.join(lines)

def categorize_receipt_with_gpt(extracted_text):
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    prompt = f"""
    You are an AI specialized in extracting and categorizing receipt data and fixing any text that may be unclear due to light, scars, or other issues.
    Fix unrelated and unreadable texts with your knowledge of what it should be. Always check unit price and total price correction.
    Given the following receipt text, extract these fields as JSON: ...
    Receipt text:
    \"\"\"{extracted_text}\"\"\"
    Return only well-formed JSON. Do not add any explanation or text outside JSON.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500,
    )
    return response.choices[0].message.content

def safe_parse_json(raw_json):
    try:
        return json.loads(raw_json)
    except json.JSONDecodeError as e:
        print("JSON decode error:", e)
        return None
