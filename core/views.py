import os
import boto3
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from task.models import *
# from task.serializers import ReceiptSerializer
from rest_framework.decorators import api_view, permission_classes
from datetime import datetime
import openai
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
    analyze_mama_emotions,
    wants_pep_talk
)

# Initialize the voice recorder
voice_recorder = VoiceRecorder()

# --- OpenAI config ---
openai.api_key = os.getenv("OPENAI_API_KEY")
from datetime import datetime

def convert_to_24hr_format(time_str):
    try:
        # Convert 12-hour format to 24-hour format
        time_obj = datetime.strptime(time_str, "%I:%M %p")  # %I is 12-hour format, %p is AM/PM
        return time_obj.strftime("%H:%M")  # %H is 24-hour format
    except ValueError:
        raise ValueError(f"Invalid time format: {time_str}")
    
@csrf_exempt
@permission_classes([IsAuthenticated])  # Ensure user is authenticated
@api_view(['POST'])  # Ensure this is a POST request
def handle_task_mama_request(request):
    """
    A single API endpoint that handles all functionalities:
    - AI response generation (text/voice)
    - Task planning
    - Recipe suggestions
    - Emotional support
    """
    if request.method == 'POST':
        # Check if the user is authenticated
        if not request.user.is_authenticated:
            return JsonResponse({"error": "User must be authenticated."}, status=403)

        try:
            # Parse JSON from the request body
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON format"}, status=400)

        # Extract input_mode and user_input from the request data
        input_mode = data.get('input_mode')
        user_input = data.get('user_input')

        if not input_mode or not user_input:
            return JsonResponse({"error": "Both input mode and user input are required."}, status=400)

        # Now, make sure we pass the authenticated user when saving data
        user = request.user  # Ensure this is the authenticated user

        # Handle Text input for Task Mama AI (Normal conversation)
        if input_mode == 'text':
            # Handle Task Planning (e.g., "Plan my day")
            if detect_task_planning_request(user_input):
                task_analysis = generate_task_analysis(user_input)

                if isinstance(task_analysis, dict) and task_analysis.get('tasks'):
                    # Save tasks to the database
                    for task_data in task_analysis.get('tasks'):
                        # Check if time is "Not specified" or invalid
                        task_time = task_data.get('time', '')
                        if task_time and task_time != "Not specified":
                            task_data['time'] = convert_to_24hr_format(task_time)
                        else:
                            task_data['time'] = None  # Set to None or default value

                        save_task_from_ai_response(task_data, user)

                    return JsonResponse(task_analysis, status=200)
                else:
                    return JsonResponse({"error": "Could not extract tasks. Please try to be more specific."}, status=400)

            # Handle Recipe Request (e.g., "suggest me a recipe for lunch")
            elif detect_recipe_request(user_input):
                # Respond with a prompt asking for available ingredients
                response = {
                    "response": "I'd love to help you with some delicious recipe ideas! 🍳✨ What items do you have available in your pantry, kitchen, home, or fridge?"
                }
                return JsonResponse(response, status=200)

            # Handle Recipe Ingredient Response (User provides ingredients)
            elif user_input:
                available_items = user_input  # assuming user_input has the ingredients in text form
                recipe_suggestions = generate_recipy_suggestion(available_items)

                if recipe_suggestions and "recipy" in recipe_suggestions:
                    # Create a new task for the recipe
                    task = Task.objects.create(
                        task_name="Generated Recipe Task",  # Default task name
                        description="Generated based on AI recipe suggestions.",
                        scheduled_date=timezone.now().date(),
                        scheduled_time=None,
                        assigned_to_type="self",  # Default to self
                        assigned_user=user,  # Link to the authenticated user
                        task_category=None,  # Default category
                        priority="medium",
                        status="pending",
                        created_by=user,  # User who created the task
                    )

                    # Save the recipes for the new task
                    save_recipe_from_ai_response(recipe_suggestions, task)

                    # Return detailed recipe suggestions
                    formatted_recipe_response = {
                        "meal_type": recipe_suggestions.get("meal_type", "Other meal"),
                        "task_category": recipe_suggestions.get("task_category", "Recipe task"),
                        "time": recipe_suggestions.get("time", "Not specified"),
                        "date": recipe_suggestions.get("date", str(timezone.now().date())),
                        "items_available": recipe_suggestions.get("items_available", ""),
                        "items_needed": recipe_suggestions.get("items_needed", ""),
                        "recipy_name": recipe_suggestions.get("recipy_name", []),
                        "recipy": recipe_suggestions.get("recipy", [])
                    }

                    return JsonResponse(formatted_recipe_response, status=200)
                else:
                    return JsonResponse({"error": "Could not generate recipes with the provided ingredients."}, status=400)

            # Handle Emotional Support (e.g., "I'm feeling overwhelmed")
            emotions = analyze_mama_emotions(user_input)
            if emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False):
                response = {
                    "response": "I can sense you might not be feeling your best right now. 💕 Would you like a pep talk to motivate you Mama 💖 (yes/no)?"
                }
                save_emotional_support(user_input, response)
                return JsonResponse(response, status=200)

            # Check if user wants a pep talk
            if wants_pep_talk(user_input):  # Use the imported function here
                pep_talk_response = {
                    "response": "You're doing great, Mama! You have so much strength, and you're capable of amazing things! Keep going 💖💪"
                }
                save_emotional_support(user_input, pep_talk_response)
                return JsonResponse(pep_talk_response, status=200)

            elif emotions['is_happy']:
                response = {
                    "response": "I'm glad to hear you're feeling happy! 💖🌸"
                }
                return JsonResponse(response, status=200)

            # Provide Normal AI Conversation
            response = get_mama_response(user_input)
            return JsonResponse({"response": response}, status=200)

        # Handle Voice input (Converts voice to text and processes)
        elif input_mode == 'voice':
            try:
                # Get voice input from the user
                user_input, status = get_user_input('voice')

                # Handle different voice input statuses
                if status == 'timeout':
                    return JsonResponse({"error": "Voice input timed out. No input received."}, status=408)
                elif status == 'interrupted':
                    return JsonResponse({"error": "Voice recording interrupted."}, status=500)
                elif status == 'empty':
                    return JsonResponse({"error": "No voice input detected."}, status=400)
                elif status == 'error':
                    return JsonResponse({"error": "Error processing the voice input."}, status=500)

                # If voice input was successfully recorded and transcribed, get the response
                response = chat_with_task_mama(user_input)
                return JsonResponse(response, status=200)

            except Exception as e:
                return JsonResponse({"error": f"Error processing voice input: {str(e)}"}, status=500)

        else:
            return JsonResponse({"error": "Invalid input mode. Use 'text' or 'voice'."}, status=400)

    else:
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)


# Function to save tasks into the database
def save_task_from_ai_response(task_data, user):
    """Save task data into the database."""
    
    # Get or create the task category based on the task_category in response
    category_name = task_data.get('task_category', 'Other')
    task_category, created = TaskCategory.objects.get_or_create(
        name=category_name,
        created_by=user
    )
    
    # Create a new task instance
    task = Task.objects.create(
        task_name=task_data.get('task_name'),
        description=task_data.get('description', ''),
        scheduled_date=task_data.get('date'),
        scheduled_time=task_data.get('time', None),
        assigned_to_type=task_data.get('task_assigned'),
        assigned_user=user,  # Assuming the task is assigned to the user who created it
        task_category=task_category,
        priority=task_data.get('priority', 'medium'),
        status='pending',
        created_by=user,  # User who created the task
    )
    
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


# Function to save emotional support responses
def save_emotional_support(user_input, response):
    """Store emotional support data in TaskComment or custom EmotionalSupport model."""
    # Assuming you're storing this in TaskComment for now
    TaskComment.objects.create(
        task=None,  # You can link this to a specific task if needed
        user=None,  # Link this to the user who requested emotional support
        comment=user_input + "\n\n" + response["response"],
        created_at=timezone.now(),
    )

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
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),  # AWS keys should also be set via environment variables.
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        with open(image_path, 'rb') as img_file:
            img_bytes = img_file.read()

        response = textract_client.detect_document_text(Document={'Bytes': img_bytes})

        lines = [block['Text'] for block in response['Blocks'] if block['BlockType'] == 'LINE']
        return '\n'.join(lines)

    def categorize_receipt_with_gpt(self, extracted_text):
        prompt = f"""
        You are an AI specialized in extracting and categorizing receipt data and fixing any text that may be unclear due to light, scars, or other issues.
        Fix unrelated and unreadable texts with your knowledge of what it should be. Always check unit price and total price correction.
        Given the following receipt text, extract these fields as JSON: date, time, shop_name, address, payment_method, items (list), services (list), vat_percentage, vat_amount, subtotal, tax, discount, total_cost.
        Receipt text:
        \"\"\"{extracted_text}\"\"\"
        Return only well-formed JSON. Do not add any explanation or text outside JSON.
        """
        response = openai.ChatCompletion.create(
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