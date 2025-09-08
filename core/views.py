import os
import boto3
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from task.models import *
# from task.serializers import ReceiptSerializer
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
import json
from .ai import (
    chat_with_task_mama,
    get_user_input,
    VoiceRecorder,
    get_mama_response,
    detect_task_planning_request,
    detect_recipe_request,
    generate_task_analysis,
    generate_recipy_suggestion,
    get_meal_type_from_conversation,
    extract_tasks_from_text,
    analyze_mama_emotions,
    wants_pep_talk,
    DynamicTaskPrioritizer,
)

# Initialize the voice recorder
voice_recorder = VoiceRecorder()

# --- OpenAI config ---
from datetime import datetime

def convert_to_24hr_format(time_str):
    try:
        # Convert 12-hour format to 24-hour format
        time_obj = datetime.strptime(time_str, "%I:%M %p")  # %I is 12-hour format, %p is AM/PM
        return time_obj.strftime("%H:%M")  # %H is 24-hour format
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")
@csrf_exempt
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def handle_task_mama_request(request):
    """
    Unified API endpoint for Task Mama:
    - Task planning
    - Recipe suggestions
    - Emotional support
    - Pep talk
    - Task analysis
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)

    if not request.user.is_authenticated:
        return JsonResponse({"error": "User must be authenticated."}, status=403)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    input_mode = data.get('input_mode')
    user_input = data.get('user_input')
    user = request.user

    if not input_mode or not user_input:
        return JsonResponse({"error": "Both input mode and user input are required."}, status=400)

    # Helper: Stricter ingredient detection
    def is_ingredient_list(text):
        food_keywords = [
            "rice", "mutton", "chicken", "egg", "potato", "tomato", "vegetable",
            "seasoning", "salt", "oil", "flour", "milk", "onion", "pepper", "spice", "meat"
        ]
        return ("," in text and any(word in text.lower() for word in food_keywords) and len(text.split()) < 20)

    # 1. Task Planning Request
    if detect_task_planning_request(user_input):
        return JsonResponse({
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you."
        }, status=200)

    # 2. Recipe Request
    if detect_recipe_request(user_input):
        return JsonResponse({
            "response": "I'd love to help you with some delicious recipe ideas! 🍳✨ What items do you have available in your pantry, kitchen, home, or fridge?"
        }, status=200)

    # 3. Emotional Support
    emotions = analyze_mama_emotions(user_input)
    if emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False):
        return JsonResponse({
            "response": "I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?"
        }, status=200)

    # 4. Pep Talk
    if wants_pep_talk(user_input):
        return JsonResponse({
            "response": "😢 I am always here with you, beautiful mama. You are stronger than you know, and tomorrow will be a brighter day. 💕"
        }, status=200)
    elif user_input.lower().strip() in ['no', 'n', 'not now', 'maybe later', 'nope', 'not really', 'no thanks', 'not today']:
        return JsonResponse({
            "response": "That's okay, sweetie. I'm still here to listen and chat with you. 💕"
        }, status=200)

    # 5. Happy Emotions
    if emotions['is_happy']:
        return JsonResponse({"response": "I'm glad to hear you're feeling happy! 💖🌸"}, status=200)

    # 6. Ingredient List (stricter detection)
    if is_ingredient_list(user_input):
        recipe_response = generate_recipy_suggestion(user_input)
        # --- Store recipe task and recipes ---
        recipe_task = save_task_from_ai_response({
            "task_name": f"Recipe suggestion for {recipe_response.get('meal_type', 'meal')}",
            "description": recipe_response.get('items_available', ''),
            "date": recipe_response.get('date'),
            "time": recipe_response.get('time'),
            "task_assigned": "Self",
            "task_category": recipe_response.get('task_category', 'Recipy task'),
            "priority": "medium"
        }, user)
        save_recipe_from_ai_response(recipe_response, recipe_task)
        return JsonResponse(recipe_response, status=200)

    # 7. Normal Task Analysis & Storage (default fallback for planning sentences)
    task_analysis = generate_task_analysis(user_input)
    if task_analysis.get('tasks'):
        for t in task_analysis['tasks']:
            save_task_from_ai_response(t, user)
        return JsonResponse(task_analysis, status=200)

    # 8. If AI returns a recipe (meal_type), handle that
    ai_reply = get_mama_response(user_input)
    try:
        ai_json = json.loads(ai_reply)
        if "meal_type" in ai_json:
            recipe_task = save_task_from_ai_response({
                "task_name": f"Recipe suggestion for {ai_json.get('meal_type', 'meal')}",
                "description": ai_json.get('items_available', ''),
                "date": ai_json.get('date'),
                "time": ai_json.get('time'),
                "task_assigned": "Self",
                "task_category": ai_json.get('task_category', 'Recipy task'),
                "priority": "medium"
            }, user)
            save_recipe_from_ai_response(ai_json, recipe_task)
            return JsonResponse(ai_json, status=200)
    except Exception:
        pass

    # 9. Normal conversational AI fallback
    return JsonResponse({"response": ai_reply}, status=200)


# Function to save tasks into the database
def save_task_from_ai_response(task_data, user):
    """Save task data into the database."""

    # Parse the date if it's a string
    scheduled_date = task_data.get('date')
    if isinstance(scheduled_date, str):
        try:
            scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
        except ValueError:
            scheduled_date = timezone.now().date()

    # Parse the time if it's a string
    scheduled_time = task_data.get('time')
    if isinstance(scheduled_time, str) and scheduled_time != "Not specified":
        try:
            scheduled_time = datetime.strptime(scheduled_time, '%I:%M %p').time()
        except ValueError:
            scheduled_time = None

    # Create a new task instance, where the category is directly saved as a string
    task = Task.objects.create(
        task_name=task_data.get('task_name'),
        description=task_data.get('description', ''),
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        assigned_to_type=task_data.get('task_assigned'),
        assigned_user=user,  # Link to the authenticated user
        task_category=task_data.get('task_category', 'Other'),  # Store category as a string
        priority=task_data.get('priority', 'medium'),
        status='pending',
        created_by=user  # User who created the task
    )
    print(f"Task '{task.task_category}' saved successfully.")
    # Return the saved task object
    return task

# Function to save recipe data into the database
def save_recipe_from_ai_response(recipe_data, task):
    """Save recipe suggestions to the database."""

    # Iterate over each recipe in the response
    for idx, recipe_name in enumerate(recipe_data.get('recipy_name', [])):
        # Create a new recipe instance
        recipe = Recipe.objects.create(
            name=recipe_name,
            meal_type=recipe_data.get('meal_type'),
            task=task,  # Link this recipe to the associated task
            items_available=recipe_data.get('items_available'),
            items_needed=recipe_data.get('items_needed', ''),
            instructions=recipe_data.get('recipy')[idx],  # Recipe steps
            cooking_time_minutes=recipe_data.get('cooking_time_minutes', 30),  # Default to 30 minutes if not provided
            servings=4,  # Default to 4 servings
            ai_generated=True,  # Mark as AI generated
            kid_friendly_tip=recipe_data.get('kid_friendly_tip', ''),
            serving_suggestion=recipe_data.get('serving_suggestion', ''),
            created_by=task.created_by
        )

    return recipe


# # Function to save emotional support responses
# def save_emotional_support(user_input, response):
#     """Store emotional support data in TaskComment or custom EmotionalSupport model."""
#     # Assuming you're storing this in TaskComment for now
#     TaskComment.objects.create(
#         task=None,  # You can link this to a specific task if needed
#         user=None,  # Link this to the user who requested emotional support
#         comment=user_input + "\n\n" + response['response'],
#         created_at=timezone.now(),
#     )

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
        receipt.quantity = structured_data.get('qty', 0)
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
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),  # AWS keys should be set via environment variables
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        
        with open(image_path, 'rb') as img_file:
            img_bytes = img_file.read()

        try:
            # Requesting text extraction from the image
            response = textract_client.detect_document_text(Document={'Bytes': img_bytes})

            # Check if 'Blocks' is in the response
            if 'Blocks' not in response:
                raise ValueError("No 'Blocks' found in the response. Check the document or API response.")

            # Extract lines of text from the Blocks
            lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
            return '\n'.join(lines)
        
        except boto3.exceptions.S3UploadFailedError as e:
            print(f"S3 upload failed: {str(e)}")
            return None
        except ValueError as e:
            print(f"Error: {str(e)}")
            return None
        except Exception as e:
            print(f"Error during OCR extraction: {str(e)}")
        return None


    def categorize_receipt_with_gpt(self, extracted_text):
        prompt = f"""
        You are an AI specialized in extracting and categorizing receipt data and fixing any text that may be unclear due to light, scars, or other issues.
        Fix unrelated and unreadable texts with your knowledge of what it should be. Always check unit price and total price correction.
        Given the following receipt text, extract these fields as JSON: date, time, shop_name, address, payment_method, items (list), services (list), vat_percentage, vat_amount, subtotal, tax, discount, total_cost.
        Receipt text:
        \"\"\"{extracted_text}\"\"\"
        Return only well-formed JSON. Do not add any explanation or text outside JSON.
        """
        response = client.chat.completions.create(model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500)
        return response.choices[0].message.content

    def safe_parse_json(self, raw_json):
        try:
            return json.loads(raw_json)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
            return None  
        
# views.py
import os, json, boto3
from datetime import datetime
from django.http import JsonResponse
from rest_framework.decorators import api_view, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from openai import OpenAI


client = OpenAI()

@api_view(["POST"])
@parser_classes([MultiPartParser, FormParser])
def receipt_preview(request):
    image = request.FILES.get("image")
    if not image:
        return JsonResponse({"error": "No image provided."}, status=400)

    # Save temporary image
    image_path = os.path.join("media/tmp", image.name)
    os.makedirs("media/tmp", exist_ok=True)
    with open(image_path, "wb+") as f:
        for chunk in image.chunks():
            f.write(chunk)

    # Step 1: OCR with AWS Textract
    textract_client = boto3.client(
        "textract",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION"),
    )

    with open(image_path, "rb") as img_file:
        img_bytes = img_file.read()

    response = textract_client.detect_document_text(Document={"Bytes": img_bytes})
    lines = [block["Text"] for block in response["Blocks"] if block["BlockType"] == "LINE"]
    extracted_text = "\n".join(lines)

    # Step 2: GPT categorization
    prompt = f"""
    You are an AI specialized in extracting and categorizing receipt data.
    Fix unreadable parts, ensure unit price and totals are correct.
    Extract JSON with: 
    date, time, shop_name, address, payment_method, 
    items (list of dict: name, qty, unit_price, total_price), 
    services (list of dict), vat_percentage, vat_amount, subtotal, tax, discount, total_cost.
    Receipt text:
    \"\"\"{extracted_text}\"\"\"
    Return only JSON.
    """
    gpt_response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=1500,
    )
    raw_json = gpt_response.choices[0].message.content

    try:
        structured_data = json.loads(raw_json)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Failed to parse GPT response."}, status=500)

    # ✅ Return preview only (not saved in DB yet)
    return JsonResponse(structured_data, safe=False, status=200)


from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser

@api_view(["POST"])
@parser_classes([JSONParser])
def save_final_receipt(request):
    data = request.data
    receipt_type = data.get("receipt_type")

    if receipt_type not in ["expense", "sales"]:
        return JsonResponse(
            {"error": "Invalid receipt_type. Must be 'expense' or 'sales'"},
            status=400
        )

    receipt = Receipt.objects.create(
        date=data.get("date", ""),
        time=data.get("time", ""),
        shop_name=data.get("shop_name", ""),
        address=data.get("address", ""),
        payment_method=data.get("payment_method", ""),
        items=data.get("items", []),
        services=data.get("services", []),
        vat_percentage=data.get("vat_percentage", 0.0),
        vat_amount=data.get("vat_amount", 0.0),
        subtotal=data.get("subtotal", 0.0),
        tax=data.get("tax", 0.0),
        discount=data.get("discount", 0.0),
        quantity=data.get("qty", 0),
        total_cost=data.get("total_cost", 0.0),
        extracted_data=data,
        processed_at=datetime.now(),
        receipt_type=receipt_type  # ✅ store type here
    )

    return JsonResponse(
        {
            "message": f"{receipt_type.title()} receipt saved successfully",
            "receipt_id": receipt.id
        },
        status=201
    )