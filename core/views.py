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
conversation_context = {} 
import json
from .final_ai import (
    chat_with_task_mama,
    get_user_input,
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
    # NEW IMPORTS for enhanced functionality
    detect_task_progress_update,
    extract_task_progress,
    generate_motivational_message,
    find_task_id_from_database,
    get_peptalk_voice_url,
    
)
from core.uitls import convert_to_24hr_format
def has_cooking_ingredients(text):
    """Enhanced ingredient detection that works with your AI"""
    food_keywords = [
        "rice", "chicken", "mutton", "egg", "potato", "tomato", "vegetable",
        "doi", "curd", "yogurt", "meat", "fish", "onion", "garlic", "spice",
        "salt", "oil", "flour", "milk", "pepper", "seasoning", "beef", "lentil", "bean"
    ]
    
    # Check for "have" + ingredients pattern (your exact case)
    # has_have = any(word in text.lower() for word in ["i have", "have", "got", "available"])
    has_ingredients = any(word in text.lower() for word in food_keywords)
    has_connectors = any(conn in text.lower() for conn in [" and ", ",", " with ", " plus "])
    
    print(f"🔍 Recipe detection: , has_ingredients={has_ingredients}, has_connectors={has_connectors}")

    return has_ingredients and (has_connectors or len(text.split()) <= 15)

@csrf_exempt
@permission_classes([IsAuthenticated])
@api_view(['POST'])
def handle_task_mama_request(request):
    global conversation_context
    """
    Enhanced unified API endpoint for Task Mama:
    - Task planning and creation
    - Recipe suggestions
    - Emotional support
    - Pep talk with voice URLs
    - Task progress updates
    - General conversation
    """
    if request.method != 'POST':
        return JsonResponse({"error": "Invalid HTTP method. Use POST."}, status=405)
 
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User must be authenticated."}, status=403)
 
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)
 
    user_input = data.get('user_input')
    user = request.user
 
    if not user_input:
        return JsonResponse({"error": "user_input is required."}, status=400)

    # Helper function to normalize AI field names for database only
    def normalize_ai_fields_for_db(data):
        """Normalize field names from AI response for database storage only"""
        if isinstance(data, dict):
            normalized = data.copy()
            # Handle task_catagory -> task_category for database
            if 'task_catagory' in normalized:
                normalized['task_category'] = normalized['task_catagory']
            # Handle recipy -> recipe fields for database
            if 'recipy_name' in normalized:
                normalized['recipe_name'] = normalized['recipy_name']
            if 'recipy' in normalized:
                normalized['recipe'] = normalized['recipy']
            return normalized
        return data

    # 1. Task Progress Update Detection
    if detect_task_progress_update(user_input):
        progress_data = extract_task_progress(user_input)
        task_name = progress_data.get("task_name", "task")
        percentage = progress_data.get("task_percentage", 0)
        task_id = find_task_id_from_database(task_name)
        
        # Update task percentage in database if task found
        if task_id:
            try:
                task = Task.objects.get(id=task_id, created_by=user)
                task.task_percentage = percentage
                task.save()
                print(f"✅ Updated task {task_id} progress to {percentage}%")
            except Task.DoesNotExist:
                print(f"❌ Task {task_id} not found for user {user}")
                pass
        
        # Generate motivational message
        motivational_message = generate_motivational_message(task_name, percentage)
        
        # Create response matching your format
        progress_summary = {
            "task_name": task_name,
            "task_percentage": percentage,
            "id": task_id
        }
        
        return JsonResponse({
            "response": f"That's wonderful progress, sweetie! Let me celebrate your achievement! ✨",
            "progress_summary": progress_summary,
            "motivational_message": motivational_message,
            "pep_talk_offer": "🌸 Do you want to hear a pep talk? 💖 (yes/no)"
        }, status=200)

    # 2. Task Planning Request
    if detect_task_planning_request(user_input):
        return JsonResponse({
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you."
        }, status=200)
    user_id = request.user.id
    # 3. Recipe Request
    if detect_recipe_request(user_input):
        # Store the original request that contains "dinner"
        conversation_context[user_id] = {
            'recipe_request': user_input,  # This contains "suggest me a recipy for dinner"
            'timestamp': datetime.now()
        }
        return JsonResponse({
            "response": "I'd love to help you with some delicious recipe ideas! 🍳✨ What items do you have available in your pantry, kitchen, home, or fridge?"
        }, status=200)
 
    # 4. Emotional Support
    emotions = analyze_mama_emotions(user_input)
    if emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False):
        return JsonResponse({
            "response": "I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?"
        }, status=200)
 
    # 5. Pep Talk Request - Enhanced with voice URL
    if wants_pep_talk(user_input):
        voice_url = get_peptalk_voice_url()
        pep_talk_response = {
            "url": voice_url or "\\media\\voices\\default.mp3"
        }
        return JsonResponse({
            "response": "🌸 Task Mama: Enjoy this special pep talk just for you, beautiful mama! 💕✨",
            "pep_talk": pep_talk_response
        }, status=200)
    elif user_input.lower().strip() in ['no', 'n', 'not now', 'maybe later', 'nope', 'not really', 'no thanks', 'not today']:
        return JsonResponse({
            "response": "That's okay, sweetie. I'm still here to listen and chat with you. 💕"
        }, status=200)
 
    # 6. Happy Emotions
    if emotions['is_happy']:
        return JsonResponse({"response": "I'm glad to hear you're feeling happy! 💖🌸"}, status=200)

    # 7. Enhanced Ingredient List - FIXED to use stored context
    if has_cooking_ingredients(user_input):
        print(f"✅ Detected ingredients in: '{user_input}'")
        
        try:
            # Get the stored recipe context for this user
            user_context = conversation_context.get(user_id, {})
            original_request = user_context.get('recipe_request', '')
            
            print(f"🔍 Original recipe request: '{original_request}'")
            print(f"🔍 Current ingredients: '{user_input}'")
            
            # FIXED: Pass the original request that contains "dinner"
            recipe_response = generate_recipy_suggestion(user_input, original_request)
            
            # Clear the context after use
            if user_id in conversation_context:
                del conversation_context[user_id]
            
            print(f"🍽️ Meal type in response: {recipe_response.get('meal_type', 'Not detected')}")
            
            # Save to database using normalized field names
            if recipe_response and isinstance(recipe_response, dict):
                normalized_for_db = normalize_ai_fields_for_db(recipe_response)
                saved_recipes = save_recipe_from_ai_response(normalized_for_db, None, user)
                print(f"💾 Saved {len(saved_recipes)} recipes to database")
            
            # Return the original AI response
            return JsonResponse(recipe_response, status=200)
            
        except Exception as e:
            print(f"❌ Error in recipe generation: {e}")
            return JsonResponse({
                "error": "Failed to generate recipe",
                "response": "Sorry, I couldn't generate a recipe right now. Please try again."
            }, status=500)
 
    # 8. Normal Task Analysis & Storage
    task_analysis = generate_task_analysis(user_input)
    if task_analysis.get('tasks'):
        for t in task_analysis['tasks']:
            # Normalize field names before saving to database
            normalized_task = normalize_ai_fields_for_db(t)
            save_task_from_ai_response(normalized_task, user)
        return JsonResponse(task_analysis, status=200)
 
    # 9. AI Response Processing (for recipes that come through normal chat)
    ai_reply = get_mama_response(user_input)
    try:
        ai_json = json.loads(ai_reply)
        if "meal_type" in ai_json or "recipy_name" in ai_json:
            print(f"📄 Detected recipe response from normal AI chat")
            
            # Normalize for database storage
            normalized_for_db = normalize_ai_fields_for_db(ai_json)
            
            # Save recipes to database
            saved_recipes = save_recipe_from_ai_response(normalized_for_db, None, user)
            print(f"💾 Saved {len(saved_recipes)} recipes from AI chat")
            
            # Return original AI response (with original field names)
            return JsonResponse(ai_json, status=200)
            
    except json.JSONDecodeError:
        # AI returned text response, not JSON
        pass
    except Exception as e:
        print(f"❌ Error processing AI response: {e}")
        pass
 
    # 10. Normal conversational AI fallback
    return JsonResponse({"response": ai_reply}, status=200)


# Enhanced function to save tasks with proper field normalization
def save_task_from_ai_response(task_data, user):
    """Save task data into the Task model from the AI response with field normalization."""
    
    # Convert the date if it's in string format
    scheduled_date = task_data.get('date')
    if isinstance(scheduled_date, str):
        try:
            scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
        except ValueError:
            scheduled_date = timezone.now().date()
    elif not scheduled_date:
        scheduled_date = timezone.now().date()
 
    # Convert time to 24-hour format if it's a string
    scheduled_time = task_data.get('time')
    if isinstance(scheduled_time, str) and scheduled_time != "Not specified":
        scheduled_time = convert_to_24hr_format(scheduled_time)
    else:
        scheduled_time = None
 
    # Map task_assigned to assigned_to_type
    assigned_to_type = task_data.get('task_assigned', 'self').lower()
    
    # Get task_category with proper normalization
    task_category = task_data.get('task_category', task_data.get('task_catagory', 'Normal task'))
 
    # Handle priority
    priority = task_data.get('priority', 'Medium Priority')
    
    # Create and save task in the database
    task = Task.objects.create(
        task_name=task_data.get('task_name'),
        task_category=task_category,
        description=task_data.get('description', ''),
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        assigned_to_type=assigned_to_type,
        priority=priority,
        created_by=user,
        generated_by_ai=True,
        raw_ai_response=task_data
    )
    
    print(f"✅ Task '{task.task_name}' saved successfully with category '{task_category}'")
    return task
 
# Enhanced function to save recipes with proper field normalization
def save_recipe_from_ai_response(recipe_data, task=None, user=None):
    """Save recipe suggestions to the database with enhanced field handling."""
    
    if not recipe_data:
        print("❌ No recipe data provided")
        return []
    
    saved_recipes = []
    
    # Handle both normalized and original field names
    recipe_names = (recipe_data.get('recipe_name') or 
                   recipe_data.get('recipy_name', []))
    recipe_instructions = (recipe_data.get('recipe') or 
                          recipe_data.get('recipy', []))
    
    # Ensure we have lists to work with
    if not isinstance(recipe_names, list):
        recipe_names = []
    if not isinstance(recipe_instructions, list):
        recipe_instructions = []
    
    print(f"📝 Processing {len(recipe_names)} recipe names and {len(recipe_instructions)} instructions")
    
    # If we have valid recipe data, process each recipe
    if recipe_names and recipe_instructions:
        try:
            # Process up to 3 recipes (matching your AI response format)
            max_recipes = min(len(recipe_names), len(recipe_instructions), 3)
            
            for idx in range(max_recipes):
                recipe_name = recipe_names[idx]
                instructions = recipe_instructions[idx]
                
                # Create recipe in database
                recipe = Recipe.objects.create(
                    name=recipe_name,
                    meal_type=recipe_data.get('meal_type', 'Dinner'),
                    task=task,
                    recipy_name=recipe_names,  # Store all recipe names as JSON
                    items_available=recipe_data.get('items_available', ''),
                    items_needed=recipe_data.get('items_needed', ''),
                    instructions=instructions,
                    cooking_time_minutes=recipe_data.get('cooking_time_minutes', 30),
                    servings=recipe_data.get('servings', 4),
                    ai_generated=True,
                    kid_friendly_tip=recipe_data.get('kid_friendly_tip', ''),
                    serving_suggestion=recipe_data.get('serving_suggestion', ''),
                    created_by=task.created_by if task else user,
                    updated_by=user
                )
                saved_recipes.append(recipe)
                print(f"✅ Recipe '{recipe_name}' saved successfully (ID: {recipe.id})")
                
        except Exception as e:
            print(f"❌ Error saving recipes: {e}")
            # Still try to save basic recipe info
            try:
                fallback_recipe = Recipe.objects.create(
                    name="AI Generated Recipe",
                    meal_type=recipe_data.get('meal_type', 'Other meal'),
                    task=task,
                    recipy_name=recipe_names if recipe_names else ["Generated Recipe"],
                    items_available=recipe_data.get('items_available', ''),
                    items_needed=recipe_data.get('items_needed', ''),
                    instructions="Recipe generated from available ingredients",
                    ai_generated=True,
                    created_by=task.created_by if task else user,
                    updated_by=user
                )
                saved_recipes.append(fallback_recipe)
                print(f"✅ Fallback recipe saved (ID: {fallback_recipe.id})")
            except Exception as fallback_error:
                print(f"❌ Even fallback recipe save failed: {fallback_error}")
    
    return saved_recipes
 
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
@permission_classes([IsAuthenticated])
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
@permission_classes([IsAuthenticated])
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
@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def save_receipt_by_type(request, receipt_type):
    # Validate that the receipt_type is one of the allowed types
    if receipt_type not in ["sales", "expense", "pantry"]:
        return JsonResponse(
            {"error": "Invalid receipt_type. Must be 'sales', 'expense', or 'pantry'"},
            status=400
        )
 
    # Extract data from the request
    data = request.data
 
    # Validate required fields
    required_fields = ["date", "time", "shop_name", "address", "payment_method", "items", "subtotal", "total_cost"]
    for field in required_fields:
        if field not in data:
            return JsonResponse({"error": f"Missing required field: {field}"}, status=400)
 
    # Save the receipt data into the database
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
        receipt_type=receipt_type  # Set the receipt_type from the URL
    )
 
    # Return a success message with the receipt ID
    return JsonResponse(
        {"message": f"{receipt_type.title()} receipt saved successfully", "receipt_id": receipt.id},
        status=201
    )
 