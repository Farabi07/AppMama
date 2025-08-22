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
from datetime import datetime

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
        extracted_text = self.extract_text_from_local_image(image_path)

        # Step 4: Categorize the receipt with GPT-4
        raw_json = self.categorize_receipt_with_gpt(extracted_text)
        structured_data = self.safe_parse_json(raw_json)

        # Step 5: Save the extracted data in the database
        receipt.extracted_text = extracted_text
        receipt.extracted_data = structured_data
        receipt.date = structured_data.get('date', '')
        receipt.time = structured_data.get('time', '')
        receipt.shop_name = structured_data.get('shop_name', '')
        receipt.address = structured_data.get('address', '')
        receipt.payment_method = structured_data.get('payment_method', '')
        receipt.items = structured_data.get('items', [])
        receipt.services = structured_data.get('services', [])
        receipt.vat_percentage = structured_data.get('vat_percentage', 0.0)
        receipt.vat_amount = structured_data.get('vat_amount', 0.0)
        receipt.subtotal = structured_data.get('subtotal', 0.0)
        receipt.tax = structured_data.get('tax', 0.0)
        receipt.discount = structured_data.get('discount', 0.0)
        receipt.total_cost = structured_data.get('total_cost', 0.0)

        # Set processed_at when receipt is processed
        receipt.processed_at = datetime.now()

        receipt.save()

        # Return the structured data in the response
        if structured_data:
            return Response(structured_data, status=200)
        else:
            return Response({"error": "Failed to parse GPT response."}, status=500)

    def extract_text_from_local_image(self, image_path):
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

    def categorize_receipt_with_gpt(self, extracted_text):
        openai_client = OpenAI(api_key=OPENAI_API_KEY)

        prompt = f"""
        You are an AI specialized in extracting and categorizing receipt data and fixing any text that may be unclear due to light, scars, or other issues.
        Fix unrelated and unreadable texts with your knowledge of what it should be. Always check unit price and total price correction.
        Given the following receipt text, extract these fields as JSON: date, time, shop_name, address, payment_method, items (list), services (list), vat_percentage, vat_amount, subtotal, tax, discount, total_cost.
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

    def safe_parse_json(self, raw_json):
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            return None