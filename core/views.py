import os
from urllib import response
import boto3
from openai import OpenAI
from rest_framework.views import APIView
from rest_framework.response import Response
from task.models import *
from rest_framework.decorators import api_view, permission_classes, parser_classes
from datetime import datetime
from openai import OpenAI

import logging

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
# Configure module logger to ensure messages are captured by gunicorn/systemd
logger = logging.getLogger("task_mama")
if not logging.getLogger().handlers:
    # Reduce global verbosity to INFO and add simple format
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
# Silence noisy third-party debug logs
for noisy in ['httpx','httpcore','openai','urllib3','botocore','boto3']:
    logging.getLogger(noisy).setLevel(logging.WARNING)
logger.setLevel(logging.INFO)
logger.propagate = False

from rest_framework.parsers import MultiPartParser, FormParser,JSONParser
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.permissions import IsAuthenticated
conversation_context = {} 
import json
import os
import json
import base64
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from task.models import Task, Recipe
from django.utils import timezone
from google.cloud import texttospeech

# Import all functions from asif_ai.py
from core.asif_ai import (
    get_mama_response,
    detect_task_planning_request,
    detect_recipe_request,
    detect_task_query_request,
    detect_task_progress_update,
    extract_task_progress,
    generate_motivational_message,
    find_task_id_from_database,
    get_peptalk_voice_url,
    get_peptalk_voice_url_by_emotion,
    classify_user_emotion_to_peptalk_class,
    analyze_mama_emotions,
    generate_task_analysis,
    generate_recipy_suggestion,
    query_existing_tasks,
    wants_pep_talk,
    add_to_conversation
)

# Store conversation context per user
conversation_context = {}

# Google Cloud TTS Configuration
GOOGLE_TTS_API_KEY = "AIzaSyC69BVmhR-VUyQqfyCwqFs_NP2Y_0lNgxw"


import os
import uuid
from django.conf import settings

def synthesize_speech_neural2_female_base64(text):
    """Convert text to speech and return audio file URL"""
    try:
        import requests
        import base64
        
        # Clean text for TTS (remove emojis and special characters)
        import re
        clean_text = re.sub(r'[^\w\s,.!?-]', '', text)
        
        # Use Google Cloud TTS REST API with API key
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
        
        payload = {
            "input": {"text": clean_text},
            "voice": {
                "languageCode": "en-US",
                "name": "en-US-Neural2-F",
                "ssmlGender": "FEMALE"
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 1.0,
                "pitch": 0.0
            }
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            result = response.json()
            audio_base64 = result.get("audioContent")
            
            # 🎵 Save audio file to media directory
            audio_data = base64.b64decode(audio_base64)
            filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
            
            # Create audio directory if it doesn't exist
            audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
            os.makedirs(audio_dir, exist_ok=True)
            
            # Save file
            file_path = os.path.join(audio_dir, filename)
            with open(file_path, 'wb') as audio_file:
                audio_file.write(audio_data)
            
            # Return URL instead of base64
            audio_url = f"{settings.MEDIA_URL}audio/{filename}"
            return audio_url
        else:
            print(f"TTS API Error: {response.status_code} - {response.text}")
            return None
        
    except Exception as e:
        print(f"TTS Error: {e}")
        return None

def add_tts_to_response(response_data):
    """Helper function to add TTS audio URL to any response"""
    # Extract the main response text
    response_text = (
        response_data.get("response") or 
        response_data.get("message") or
        response_data.get("motivational_message") or
        ""
    )
    
    # Generate TTS if there's text
    if response_text:
        try:
            audio_url = synthesize_speech_neural2_female_base64(response_text)
            response_data["audio_url"] = audio_url  # URL instead of base64
        except Exception as e:
            print(f"TTS Error: {e}")
            response_data["audio_url"] = None
    else:
        response_data["audio_url"] = None
    
    return response_data

def convert_to_24hr_format(time_str):
    """Convert time to 24-hour format"""
    if not time_str or time_str == "Not specified":
        return None
    try:
        from datetime import datetime
        # Try parsing 12-hour format
        try:
            time_obj = datetime.strptime(time_str, "%I:%M %p")
            return time_obj.strftime("%H:%M")
        except:
            # Already in 24-hour format or other format
            return time_str
    except:
        return time_str

# Simplified conversation states - No name asking
CONVERSATION_STATES = {
    'READY_TO_CHAT': 'ready_to_chat'
}

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def handle_task_mama_request(request):
    """
    Main API endpoint - Direct conversation without name collection
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=400)

    user_input = data.get('user_input')
    user = request.user

    if not user_input:
        return JsonResponse({"error": "user_input is required."}, status=400)

    # Normalize and clean incoming text to avoid encoding/whitespace differences on EC2
    import unicodedata
    raw_input = user_input
    try:
        # ensure string, strip whitespace, normalize unicode (NFKC)
        user_input = str(user_input).strip()
        user_input = unicodedata.normalize('NFKC', user_input)
    except Exception:
        user_input = (user_input or "").strip()

    # DEBUG: log normalized input and detector results (will appear in server logs)
    try:
        is_progress = False
        is_planning = False
        is_recipe = False
        is_query = False
        emotions_preview = {}

        try:
            is_progress = detect_task_progress_update(user_input)
        except Exception as e:
            logger.debug("DEBUG detect_task_progress_update error: %s", e)

        try:
            is_planning = detect_task_planning_request(user_input)
        except Exception as e:
            logger.debug("DEBUG detect_task_planning_request error: %s", e)

        try:
            is_recipe = detect_recipe_request(user_input)
        except Exception as e:
            logger.debug("DEBUG detect_recipe_request error: %s", e)

        try:
            # detect_task_query_request may call external APIs/AI; catch errors to avoid blocking
            is_query = detect_task_query_request(user_input)
        except Exception as e:
            logger.debug("DEBUG detect_task_query_request error: %s", e)
            is_query = False

        try:
            emotions_preview = analyze_mama_emotions(user_input)
        except Exception as e:
            logger.debug("DEBUG analyze_mama_emotions error: %s", e)
            emotions_preview = {}

        logger.debug("handle_task_mama_request - raw_input: %r", raw_input)
        logger.debug("normalized user_input: %r", user_input)
        logger.debug("detectors -> progress:%s, planning:%s, recipe:%s, query:%s", is_progress, is_planning, is_recipe, is_query)
        logger.debug("emotions preview: %s", emotions_preview)
    except Exception as e:
        logger.exception("logging error in handle_task_mama_request")

    # Get current auth token from request headers
    current_token = None
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if auth_header.startswith('Bearer '):
        current_token = auth_header[7:]
    elif auth_header.startswith('Token '):
        current_token = auth_header[6:]
    
    # Check if token has changed or session is new
    stored_token = request.session.get('auth_token')
    stored_user_id = request.session.get('user_id')
    
    # Reset conversation if token changed or user changed
    if (stored_token != current_token) or (stored_user_id != user.id):
        # Clear all session data related to conversation
        request.session.flush()
        # Set new token and user
        request.session['auth_token'] = current_token
        request.session['user_id'] = user.id
        request.session['conversation_state'] = CONVERSATION_STATES['READY_TO_CHAT']
        request.session.modified = True
    
    # Use Django session to store conversation state
    if 'conversation_state' not in request.session:
        request.session['conversation_state'] = CONVERSATION_STATES['READY_TO_CHAT']
    
    current_state = request.session['conversation_state']

    # Direct conversation - No name collection
    if current_state == CONVERSATION_STATES['READY_TO_CHAT']:
        # Use default names from user model
        user_name = user.full_name or user.username or 'beautiful mama'
        bot_name = 'Task Mama'

        # Add to conversation history
        add_to_conversation("user", user_input)

        # 1. Check for Task Progress Update
        if detect_task_progress_update(user_input):
            progress_data = extract_task_progress(user_input)
            task_name = progress_data.get("task_name", "task")
            percentage = progress_data.get("task_percentage", 0)
            # 🌟 PASS BEARER TOKEN TO API CALLS
            task_id = find_task_id_from_database(task_name, bearer_token=current_token)
            
            # Update task in database if found
            if task_id:
                try:
                    task = Task.objects.get(id=task_id, created_by=user)
                    task.task_percentage = percentage
                    task.save()
                except Task.DoesNotExist:
                    pass
            
            # Generate motivational message
            motivational_message = generate_motivational_message(task_name, percentage)
            
            # Store context for potential pep talk
            conversation_context[user.id] = {
                'type': 'task_progress_pep_talk',
                'emotions': analyze_mama_emotions(user_input),
                'timestamp': datetime.now()
            }
            
            # Return progress response with TTS
            progress_response = {
                "response": "That's wonderful progress, sweetie! Let me celebrate your achievement! ✨",
                "progress_summary": {
                    "task_name": task_name,
                    "task_percentage": percentage,
                    "id": task_id
                },
                "motivational_message": motivational_message,
                "pep_talk_offer": "🌸 Do you want to hear a pep talk? 💖 (yes/no)"
            }
            
            add_to_conversation("assistant", motivational_message)
            return JsonResponse(add_tts_to_response(progress_response), status=200)

        # 2. Check for Task Planning Request
        if detect_task_planning_request(user_input):
            # Store context for next message
            conversation_context[user.id] = {
                'type': 'task_planning',
                'timestamp': datetime.now()
            }
            
            response_data = {
                "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you."
            }
            
            add_to_conversation("assistant", response_data["response"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 3. Check if user is providing task details (context-aware)
        user_context = conversation_context.get(user.id, {})
        if user_context.get('type') == 'task_planning':
            task_analysis = generate_task_analysis(user_input)
            
            if task_analysis.get('tasks'):
                # Save tasks to database
                for task_data in task_analysis['tasks']:
                    save_task_from_ai_response(task_data, user)
                
                # Clear context
                if user.id in conversation_context:
                    del conversation_context[user.id]
                
                # Add a message field for TTS
                task_analysis["message"] = "🌸 Here is your beautiful task schedule:"
                return JsonResponse(add_tts_to_response(task_analysis), status=200)
            else:
                response_data = {
                    "response": "I couldn't detect specific tasks from what you shared. Could you be more specific about what you need to do? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'"
                }
                
                add_to_conversation("assistant", response_data["response"])
                return JsonResponse(add_tts_to_response(response_data), status=200)

        # 4. Check for Recipe Request
        if detect_recipe_request(user_input):
            # Store context for next message
            conversation_context[user.id] = {
                'type': 'recipe_request',
                'original_request': user_input,
                'timestamp': datetime.now()
            }
            
            response_data = {
                "type": "recipe_prompt",
                "response": "🌸 I'd love to help you with some delicious recipe ideas! ✨ What items do you have available in your pantry, kitchen, home, or fridge?",
                "data": {
                    "awaiting_ingredients": True
                }
            }

            add_to_conversation("assistant", response_data["response"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 5. Check if user is providing ingredients (context-aware)
        if user_context.get('type') == 'recipe_request':
            original_request = user_context.get('original_request', '')
            recipe_data = generate_recipy_suggestion(user_input, original_request)
            
            if recipe_data:
                # Save recipes to database
                save_recipe_from_ai_response(recipe_data, None, user)
                
                response_data = {
                    "type": "recipe",
                    "message": "🌸 Here is your AI-suggested recipe:",
                    "data": recipe_data
                }
                
                # Clear context
                if user.id in conversation_context:
                    del conversation_context[user.id]
            else:
                response_data = {
                    "type": "recipe",
                    "message": "🌸 I'm having trouble generating recipes right now. Please try again.",
                    "data": {}
                }
            
            add_to_conversation("assistant", response_data["message"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 6. Check for Task Query Request
        if detect_task_query_request(user_input):
            # 🌟 PASS BEARER TOKEN TO QUERY FUNCTION
            task_query_result = query_existing_tasks(user_input, bearer_token=current_token)
            response_data = {
                "response": task_query_result.get("message", "")
            }
            
            add_to_conversation("assistant", response_data["response"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 7. Check for Emotional Support Needs
        emotions = analyze_mama_emotions(user_input)
        
        # Debug logging for emotion detection
        logger.debug("Emotion detection for %r: is_emotion1=%s is_emotion2=%s is_emotion3=%s is_emotion4=%s primary=%s",
                     user_input,
                     emotions.get('is_emotion1', False),
                     emotions.get('is_emotion2', False),
                     emotions.get('is_emotion3', False),
                     emotions.get('is_emotion4', False),
                     emotions.get('primary_emotion', 'unknown'))
        
        needs_support = (
            emotions.get('is_emotion1', False) or 
            emotions.get('is_emotion2', False) or 
            emotions.get('is_emotion4', False) or
            emotions.get('is_sad', False) or 
            emotions.get('is_overwhelmed', False) or 
            emotions.get('is_stressed', False)
        )
        
        if needs_support:
            # Store context for pep talk offer
            conversation_context[user.id] = {
                'type': 'emotional_support',
                'emotions': emotions,
                'timestamp': datetime.now()
            }
            
            response_data = {
                "response": "I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?"
            }
            
            add_to_conversation("assistant", response_data["response"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 8. Check for Pep Talk Response (yes/no)
        if user_context.get('type') in ['emotional_support', 'happy_support', 'task_progress_pep_talk'] or wants_pep_talk(user_input):
            if wants_pep_talk(user_input):
                # Get emotions from context or analyze again
                detected_emotions = user_context.get('emotions', analyze_mama_emotions(user_input))
                peptalk_class = classify_user_emotion_to_peptalk_class(user_input, detected_emotions)
                # 🌟 PASS BEARER TOKEN TO PEPTALK API
                voice_url = get_peptalk_voice_url_by_emotion(peptalk_class, bearer_token=current_token)
                
                if not voice_url:
                    voice_url = get_peptalk_voice_url(bearer_token=current_token)
                
                # Format response to match your expected structure
                pep_talk_response = {
                    "response": "🌸 Enjoy this special pep talk just for you, beautiful mama! 💕✨",
                    "pep_talk": {
                        "url": voice_url or "/media/voices/default.mp3"
                    }
                }
                
                # Clear context
                if user.id in conversation_context:
                    del conversation_context[user.id]
                
                return JsonResponse(add_tts_to_response(pep_talk_response), status=200)
            else:
                # Clear context
                if user.id in conversation_context:
                    del conversation_context[user.id]
                
                response_data = {
                    "response": "That's okay, sweetie. I'm still here to listen and chat with you. 💕"
                }
                
                add_to_conversation("assistant", response_data["response"])
                return JsonResponse(add_tts_to_response(response_data), status=200)

        # 9. Check for Happy Emotions (also offer pep talk)
        if emotions.get('is_emotion3', False) or emotions.get('is_happy', False):
            # Store context for pep talk offer
            conversation_context[user.id] = {
                'type': 'happy_support',
                'emotions': emotions,
                'timestamp': datetime.now()
            }
            
            # Offer pep talk for happy emotions too!
            response_data = {
                "response": "🌸 That's wonderful to hear, mama! I'm so happy you're feeling good! 💕 Would you like to hear a pep talk to celebrate your positive mood? 🎉 (yes/no)"
            }
            
            add_to_conversation("assistant", response_data["response"])
            return JsonResponse(add_tts_to_response(response_data), status=200)

        # 10. Default: General Conversation
        ai_reply = get_mama_response(user_input)
        response_data = {
            "response": ai_reply
        }
        
        add_to_conversation("assistant", ai_reply)
        return JsonResponse(add_tts_to_response(response_data), status=200)

    # Should not reach here, but just in case
    return JsonResponse({"error": "Invalid conversation state"}, status=400)


def save_task_from_ai_response(task_data, user):
    """Save task data from AI response to database"""
    from datetime import datetime
    
    # Convert date
    scheduled_date = task_data.get('date')
    if isinstance(scheduled_date, str):
        try:
            scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
        except ValueError:
            scheduled_date = timezone.now().date()
    elif not scheduled_date:
        scheduled_date = timezone.now().date()
    
    # Convert time
    scheduled_time = task_data.get('time')
    if isinstance(scheduled_time, str) and scheduled_time != "Not specified":
        scheduled_time = convert_to_24hr_format(scheduled_time)
    else:
        scheduled_time = None
    
    # Map fields
    assigned_to_type = task_data.get('task_assigned', 'self').lower()
    task_category = task_data.get('task_category', task_data.get('task_catagory', 'Normal task'))
    priority = task_data.get('priority', 'Medium Priority')
    
    # Create task
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
    
    return task
def save_recipe_from_ai_response(recipe_data, task=None, user=None):
    """Save recipe data from AI response to database"""
    if not recipe_data:
        return []
    
    saved_recipes = []
    
    # Accept both field name variations and both string/list types
    recipe_names = recipe_data.get('recipe_name') or recipe_data.get('recipy_name') or []
    recipe_instructions = recipe_data.get('recipe') or recipe_data.get('recipy') or []

    # Convert to list if string
    if isinstance(recipe_names, str):
        recipe_names = [recipe_names]
    if isinstance(recipe_instructions, str):
        recipe_instructions = [recipe_instructions]
    if not isinstance(recipe_names, list):
        recipe_names = []
    if not isinstance(recipe_instructions, list):
        recipe_instructions = []

    # Process up to 3 recipes
    max_recipes = min(len(recipe_names), len(recipe_instructions), 3)
    
    for idx in range(max_recipes):
        recipe_name = recipe_names[idx]
        instructions = recipe_instructions[idx]
        
        try:
            recipe = Recipe.objects.create(
                name=recipe_name,
                meal_type=recipe_data.get('meal_type', 'Dinner'),
                task=task,
                recipy_name=recipe_names,
                items_available=recipe_data.get('items_available', ''),
                items_needed=recipe_data.get('items_needed', ''),
                instructions=instructions,
                cooking_time_minutes=recipe_data.get('cooking_time_minutes', 30),
                servings=recipe_data.get('servings', 4),
                ai_generated=True,
                created_by=task.created_by if task else user,
                updated_by=user
            )
            saved_recipes.append(recipe)
        except Exception as e:
            logger.exception("Error saving recipe: %s", e)
    
    return saved_recipes

# ==================== SEPARATED VIEWS FOR EACH INPUT TYPE ====================
# Clean separation of views for task planning, task progress, recipe, peptalk and normal chat

# 🍳 RECIPE VIEWS - Complete recipe functionality
@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_step1_ask_ingredients(request):
    """
    Recipe API - Step 1: Ask for Ingredients
    
    Request JSON:
      { "user_input": "I want dinner recipes" }
      OR
      { "meal_type": "dinner" }  # optional: breakfast, lunch, dinner
      
    Returns:
      - Prompt asking user for available ingredients
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        meal_type = (data.get("meal_type") or "dinner").strip().capitalize()
        
        logger.debug("api_recipe_step1 - user_input: %r, meal_type: %s", user_input, meal_type)

        response_data = {
            "type": "recipe_prompt",
            "response": f"🌸 I'd love to help you with some delicious {meal_type.lower()} recipe ideas! ✨ What items do you have available in your pantry, kitchen, home, or fridge?",
            "data": {
                "awaiting_ingredients": True,
                "meal_type": meal_type
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_recipe_step1_ask_ingredients")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_step2_generate(request):
    """
    Recipe API - Step 2: Generate Recipes from Ingredients
    
    Request JSON:
      { "items": "rice and fish, oil" }
      OR
      { "items": "rice and fish, oil", "meal_type": "dinner" }
      
    Returns:
      - 3 AI-generated recipe suggestions
      - Recipes are saved to database
      - TTS audio URL
    """
    try:
        data = request.data or {}
        items = (data.get("items") or "").strip()
        meal_type = (data.get("meal_type") or "Dinner").strip().capitalize()
        user_input = data.get("user_input", f"I want {meal_type.lower()} recipes")
        
        if not items:
            return JsonResponse({"error": "items field is required"}, status=400)

        logger.debug("api_recipe_step2 - items: %r, meal_type: %s", items, meal_type)

        # Generate recipes using AI
        recipe_data = generate_recipy_suggestion(items, user_input)
        
        if recipe_data:
            # Override meal_type if provided
            if meal_type:
                recipe_data["meal_type"] = meal_type
            
            # Save recipes to database
            save_recipe_from_ai_response(recipe_data, None, request.user)
            
            response_data = {
                "type": "recipe",
                "message": "🌸 Here is your AI-suggested recipe:",
                "data": recipe_data
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
        else:
            return JsonResponse({
                "error": "Failed to generate recipes",
                "message": "I'm having trouble creating recipes right now. Please try again."
            }, status=500)
        
    except Exception as e:
        logger.exception("Error in api_recipe_step2_generate")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_combined(request):
    """
    Recipe API - Combined (Legacy Support)
    
    Request JSON examples:
      1. Initial request (no items): 
         { "user_input": "I want dinner recipes" }
         -> Returns prompt asking for ingredients
         
      2. With ingredients:
         { "user_input": "give me recipes", "items": "1 kg rice, 2 onions, chicken" }
         -> Returns 3 recipe suggestions and saves to DB
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        items = (data.get("items") or "").strip()
        
        # Extract bearer token for API calls
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None

        if not user_input and not items:
            return JsonResponse({"error": "user_input or items required"}, status=400)

        logger.debug("api_recipe_combined - user_input: %r, items: %r", user_input, items)

        # If items provided, generate recipes
        if items:
            recipe_data = generate_recipy_suggestion(items, user_input)
            if recipe_data:
                # Save recipes to database
                save_recipe_from_ai_response(recipe_data, None, request.user)
                response_data = {
                    "type": "recipe",
                    "data": recipe_data,
                    "message": "🌸 Here are your delicious recipe suggestions! 💕"
                }
                return JsonResponse(add_tts_to_response(response_data), status=200)
            else:
                return JsonResponse({
                    "error": "Failed to generate recipes",
                    "message": "I'm having trouble creating recipes right now. Please try again."
                }, status=500)

        # No items provided -> ask for ingredients
        response_data = {
            "type": "recipe_prompt",
            "response": "🌸 I'd love to help you with some delicious recipe ideas! ✨ What items do you have available in your pantry, kitchen, home, or fridge?",
            "data": {
                "awaiting_ingredients": True
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_recipe_combined")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# 📋 TASK PLANNING VIEWS - Complete task planning functionality
    """
    Recipe API - Step 2: Generate Recipes from Ingredients
    
    Request JSON:
      { "items": "rice and fish, oil" }
      OR
      { "items": "rice and fish, oil", "meal_type": "dinner" }
      
    Returns:
      - 3 AI-generated recipe suggestions
      - Recipes are saved to database
      - TTS audio URL
    """
    try:
        data = request.data or {}
        items = (data.get("items") or "").strip()
        meal_type = (data.get("meal_type") or "Dinner").strip().capitalize()
        user_input = data.get("user_input", f"I want {meal_type.lower()} recipes")
        
        if not items:
            return JsonResponse({"error": "items field is required"}, status=400)

        logger.debug("api_recipe_step2 - items: %r, meal_type: %s", items, meal_type)

        # Generate recipes using AI
        recipe_data = generate_recipy_suggestion(items, user_input)
        
        if recipe_data:
            # Override meal_type if provided
            if meal_type:
                recipe_data["meal_type"] = meal_type
            
            # Save recipes to database
            save_recipe_from_ai_response(recipe_data, None, request.user)
            
            response_data = {
                "type": "recipe",
                "message": "🌸 Here is your AI-suggested recipe:",
                "data": recipe_data
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
        else:
            return JsonResponse({
                "error": "Failed to generate recipes",
                "message": "I'm having trouble creating recipes right now. Please try again."
            }, status=500)
        
    except Exception as e:
        logger.exception("Error in api_recipe_step2_generate")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_step1_ask_tasks(request):
    """
    Task Planning API - Step 1: Ask for Tasks
    
    Request JSON:
      { "user_input": "I want to plan my day" }
      
    Returns:
      - Prompt asking user for task details
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        logger.debug("api_task_plan_step1 - user_input: %r", user_input)

        response_data = {
            "type": "task_planning_prompt",
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.",
            "data": {
                "awaiting_tasks": True
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_task_plan_step1_ask_tasks")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_step2_generate(request):
    """
    Task Planning API - Step 2: Generate Task Schedule
    
    Request JSON:
      { "tasks_text": "Pick up kids at 3pm, go grocery shopping tomorrow at 10am, doctor appointment on Friday at 2pm" }
      
    Returns:
      - Structured task schedule with priorities, dates, times
      - Tasks are automatically saved to database
      - TTS audio URL
    """
    try:
        data = request.data or {}
        tasks_text = (data.get("tasks_text") or data.get("user_input") or "").strip()
        
        if not tasks_text:
            return JsonResponse({"error": "tasks_text is required"}, status=400)

        logger.debug("api_task_plan_step2 - tasks_text: %r", tasks_text)

        # Generate task analysis using AI
        task_analysis = generate_task_analysis(tasks_text)
        
        if task_analysis.get("tasks"):
            # Save all tasks to database
            for task_data in task_analysis["tasks"]:
                try:
                    save_task_from_ai_response(task_data, request.user)
                except Exception as e:
                    logger.exception("Failed to save task: %s", task_data.get("task_name"))
            
            task_analysis["message"] = "🌸 Here is your beautiful task schedule! I've organized everything for you. 💕"
            return JsonResponse(add_tts_to_response(task_analysis), status=200)
        else:
            response_data = {
                "response": "I couldn't detect specific tasks from what you shared. Could you be more specific? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'",
                "tasks": [],
                "total_tasks": 0
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
            
    except Exception as e:
        logger.exception("Error in api_task_plan_step2_generate")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_combined(request):
    """
    Task Planning API - Combined (Legacy Support)
    
    Request JSON:
      { "tasks_text": "Pick up kids at 3pm, go grocery shopping tomorrow at 10am, doctor appointment on Friday at 2pm" }
      
    Returns:
      - Structured task schedule with priorities, dates, times
      - Tasks are automatically saved to database
    """
    try:
        data = request.data or {}
        tasks_text = (data.get("tasks_text") or data.get("user_input") or "").strip()
        
        if not tasks_text:
            return JsonResponse({"error": "tasks_text is required"}, status=400)

        logger.debug("api_task_plan_combined - tasks_text: %r", tasks_text)

        # Generate task analysis using AI
        task_analysis = generate_task_analysis(tasks_text)
        
        if task_analysis.get("tasks"):
            # Save all tasks to database
            for task_data in task_analysis["tasks"]:
                try:
                    save_task_from_ai_response(task_data, request.user)
                except Exception as e:
                    logger.exception("Failed to save task: %s", task_data.get("task_name"))
            
            task_analysis["message"] = "🌸 Here is your beautiful task schedule! I've organized everything for you. 💕"
            return JsonResponse(add_tts_to_response(task_analysis), status=200)
        else:
            response_data = {
                "response": "I couldn't detect specific tasks from what you shared. Could you be more specific? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'",
                "tasks": [],
                "total_tasks": 0
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
            
    except Exception as e:
        logger.exception("Error in api_task_plan_combined")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# 📊 TASK PROGRESS VIEWS - Complete task progress functionality
    """
    Task Planning API - Step 1: Ask for Tasks
    
    Request JSON:
      { "user_input": "I want to plan my day" }
      
    Returns:
      - Prompt asking user for task details
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        logger.debug("api_task_plan_step1 - user_input: %r", user_input)

        response_data = {
            "type": "task_planning_prompt",
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.",
            "data": {
                "awaiting_tasks": True
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_task_plan_step1_ask_tasks")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_step2_generate(request):
    """
    Task Planning API - Step 2: Generate Task Schedule
    
    Request JSON:
      { "tasks_text": "Pick up kids at 3pm, go grocery shopping tomorrow at 10am, doctor appointment on Friday at 2pm" }
      
    Returns:
      - Structured task schedule with priorities, dates, times
      - Tasks are automatically saved to database
      - TTS audio URL
    """
    try:
        data = request.data or {}
        tasks_text = (data.get("tasks_text") or data.get("user_input") or "").strip()
        
        if not tasks_text:
            return JsonResponse({"error": "tasks_text is required"}, status=400)

        logger.debug("api_task_plan_step2 - tasks_text: %r", tasks_text)

        # Generate task analysis using AI
        task_analysis = generate_task_analysis(tasks_text)
        
        if task_analysis.get("tasks"):
            # Save all tasks to database
            for task_data in task_analysis["tasks"]:
                try:
                    save_task_from_ai_response(task_data, request.user)
                except Exception as e:
                    logger.exception("Failed to save task: %s", task_data.get("task_name"))
            
            task_analysis["message"] = "🌸 Here is your beautiful task schedule! I've organized everything for you. 💕"
            return JsonResponse(add_tts_to_response(task_analysis), status=200)
        else:
            response_data = {
                "response": "I couldn't detect specific tasks from what you shared. Could you be more specific? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'",
                "tasks": [],
                "total_tasks": 0
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
            
    except Exception as e:
        logger.exception("Error in api_task_plan_step2_generate")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# ==================== LEGACY COMBINED ENDPOINTS (For backward compatibility) ====================
# These endpoints combine multiple steps - kept for backward compatibility
# New implementations should use the dedicated step-by-step endpoints above

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_request(request):
    """
    Dedicated Recipe API
    
    Request JSON examples:
      1. Initial request (no items): 
         { "user_input": "I want dinner recipes" }
         -> Returns prompt asking for ingredients
         
      2. With ingredients:
         { "user_input": "give me recipes", "items": "1 kg rice, 2 onions, chicken" }
         -> Returns 3 recipe suggestions and saves to DB
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        items = (data.get("items") or "").strip()
        
        # Extract bearer token for API calls
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None

        if not user_input and not items:
            return JsonResponse({"error": "user_input or items required"}, status=400)

        logger.debug("api_recipe_request - user_input: %r, items: %r", user_input, items)

        # If items provided, generate recipes
        if items:
            recipe_data = generate_recipy_suggestion(items, user_input)
            if recipe_data:
                # Save recipes to database
                save_recipe_from_ai_response(recipe_data, None, request.user)
                response_data = {
                    "type": "recipe",
                    "data": recipe_data,
                    "message": "🌸 Here are your delicious recipe suggestions! 💕"
                }
                return JsonResponse(add_tts_to_response(response_data), status=200)
            else:
                return JsonResponse({
                    "error": "Failed to generate recipes",
                    "message": "I'm having trouble creating recipes right now. Please try again."
                }, status=500)

        # No items provided -> ask for ingredients
        response_data = {
            "type": "recipe_prompt",
            "response": "🌸 I'd love to help you with some delicious recipe ideas! ✨ What items do you have available in your pantry, kitchen, home, or fridge?",
            "data": {
                "awaiting_ingredients": True
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_recipe_request")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan(request):
    """
    Dedicated Task Planning API
    
    Request JSON:
      { "tasks_text": "Pick up kids at 3pm, go grocery shopping tomorrow at 10am, doctor appointment on Friday at 2pm" }
      
    Returns:
      - Structured task schedule with priorities, dates, times
      - Tasks are automatically saved to database
    """
    try:
        data = request.data or {}
        tasks_text = (data.get("tasks_text") or data.get("user_input") or "").strip()
        
        if not tasks_text:
            return JsonResponse({"error": "tasks_text is required"}, status=400)

        logger.debug("api_task_plan - tasks_text: %r", tasks_text)

        # Generate task analysis using AI
        task_analysis = generate_task_analysis(tasks_text)
        
        if task_analysis.get("tasks"):
            # Save all tasks to database
            for task_data in task_analysis["tasks"]:
                try:
                    save_task_from_ai_response(task_data, request.user)
                except Exception as e:
                    logger.exception("Failed to save task: %s", task_data.get("task_name"))
            
            task_analysis["message"] = "🌸 Here is your beautiful task schedule! I've organized everything for you. 💕"
            return JsonResponse(add_tts_to_response(task_analysis), status=200)
        else:
            response_data = {
                "response": "I couldn't detect specific tasks from what you shared. Could you be more specific? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'",
                "tasks": [],
                "total_tasks": 0
            }
            return JsonResponse(add_tts_to_response(response_data), status=200)
            
    except Exception as e:
        logger.exception("Error in api_task_plan")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_progress(request):
    """
    Task Progress API - Update task completion progress
    
    Request JSON:
      { "user_input": "I completed 50% of washing dishes" }
      OR
      { "task_name": "washing dishes", "percentage": 50 }
      
    Returns:
      - Progress summary
      - Motivational message
      - Updates task in database if found
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        task_name = (data.get("task_name") or "").strip()
        percentage = data.get("percentage")

        # Extract progress from text if not provided directly
        if user_input and not (task_name and percentage is not None):
            progress = extract_task_progress(user_input)
            task_name = progress.get("task_name")
            percentage = progress.get("task_percentage", 0)
        elif not task_name:
            return JsonResponse({"error": "user_input or task_name is required"}, status=400)

        logger.debug("api_task_progress - task_name: %r, percentage: %d", task_name, percentage)

        # Extract bearer token for DB lookup
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        # Find and update task in database
        task_id = find_task_id_from_database(task_name, bearer_token=bearer)
        if task_id:
            try:
                task = Task.objects.filter(id=task_id, created_by=request.user).first()
                if task:
                    task.task_percentage = percentage
                    task.save()
                    logger.info("Updated task %d progress to %d%%", task_id, percentage)
            except Exception as e:
                logger.exception("Failed to update task progress in DB")

        # Generate motivational message
        motivational_message = generate_motivational_message(task_name, percentage)
        
        response = {
            "response": "That's wonderful progress, sweetie! 💕",
            "progress_summary": {
                "task_name": task_name,
                "task_percentage": percentage,
                "id": task_id
            },
            "motivational_message": motivational_message,
            "pep_talk_offer": "🌸 Would you like to hear a pep talk? 💖"
        }
        return JsonResponse(add_tts_to_response(response), status=200)
        
    except Exception as e:
        logger.exception("Error in api_task_progress")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_query(request):
    """
    Task Query API - Query existing tasks by date/time
    
    Request JSON:
      { "user_input": "Do I have any tasks for tomorrow?" }
      OR
      { "query_date": "2024-12-10", "assigned_filter": "self" }
      
    Returns:
      - List of matching tasks
      - Natural language summary
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        logger.debug("api_task_query - user_input: %r", user_input)

        # Extract bearer token for API calls
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        # Query existing tasks
        task_query_result = query_existing_tasks(user_input, bearer_token=bearer)
        response_data = {
            "response": task_query_result.get("message", ""),
            "tasks_found": task_query_result.get("found_tasks", []),
            "total_tasks": task_query_result.get("total_tasks", 0),
            "query_date": task_query_result.get("query_date")
        }
        
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_task_query")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# 🎭 PEPTALK VIEWS - Complete emotional support functionality
    """
    Dedicated Task Progress API
    
    Request JSON:
      { "user_input": "I completed 50% of washing dishes" }
      OR
      { "task_name": "washing dishes", "percentage": 50 }
      
    Returns:
      - Progress summary
      - Motivational message
      - Updates task in database if found
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        task_name = (data.get("task_name") or "").strip()
        percentage = data.get("percentage")

        # Extract progress from text if not provided directly
        if user_input and not (task_name and percentage is not None):
            progress = extract_task_progress(user_input)
            task_name = progress.get("task_name")
            percentage = progress.get("task_percentage", 0)
        elif not task_name:
            return JsonResponse({"error": "user_input or task_name is required"}, status=400)

        logger.debug("api_task_progress - task_name: %r, percentage: %d", task_name, percentage)

        # Extract bearer token for DB lookup
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None
        
        # Find and update task in database
        task_id = find_task_id_from_database(task_name, bearer_token=bearer)
        if task_id:
            try:
                task = Task.objects.filter(id=task_id, created_by=request.user).first()
                if task:
                    task.task_percentage = percentage
                    task.save()
                    logger.info("Updated task %d progress to %d%%", task_id, percentage)
            except Exception as e:
                logger.exception("Failed to update task progress in DB")

        # Generate motivational message
        motivational_message = generate_motivational_message(task_name, percentage)
        
        response = {
            "response": "That's wonderful progress, sweetie! 💕",
            "progress_summary": {
                "task_name": task_name,
                "task_percentage": percentage,
                "id": task_id
            },
            "motivational_message": motivational_message,
            "pep_talk_offer": "🌸 Would you like to hear a pep talk? 💖"
        }
        return JsonResponse(add_tts_to_response(response), status=200)
        
    except Exception as e:
        logger.exception("Error in api_task_progress")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_peptalk(request):
    """
    Pep Talk API - Provide emotional support with motivational audio
    
    Request JSON examples:
      1. With specific emotion:
         { "emotion": "emotion1" }  # emotion1, emotion2, emotion3, or emotion4
         
      2. Auto-detect from text:
         { "user_input": "I'm so tired and overwhelmed" }
         -> Analyzes emotion and returns appropriate pep talk
         
    Returns:
      - Pep talk audio URL
      - Encouraging message
      - TTS audio URL
    """
    try:
        data = request.data or {}
        emotion = (data.get("emotion") or "").strip()
        user_input = (data.get("user_input") or "").strip()

        # Extract bearer token for API calls
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None

        if not emotion and not user_input:
            return JsonResponse({"error": "emotion or user_input required"}, status=400)

        # Auto-detect emotion from text if not explicitly provided
        if not emotion and user_input:
            detected = analyze_mama_emotions(user_input)
            emotion = classify_user_emotion_to_peptalk_class(user_input, detected)
            logger.debug("api_peptalk - detected emotion: %s from input: %r", emotion, user_input)

        # Fetch pep talk voice URL
        voice_url = get_peptalk_voice_url_by_emotion(emotion, bearer_token=bearer)
        if not voice_url:
            voice_url = get_peptalk_voice_url(bearer_token=bearer)

        response_data = {
            "response": "🌸 Here's a special pep talk just for you, beautiful mama! 💕✨",
            "pep_talk": {
                "url": voice_url or "/media/voices/default.mp3",
                "emotion": emotion
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_peptalk")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_emotion_analysis(request):
    """
    Emotion Analysis API - Analyze user's emotional state
    
    Request JSON:
      { "user_input": "I'm feeling really tired and stressed today" }
      
    Returns:
      - Detailed emotion analysis
      - Emotion categories (emotion1-4)
      - Confidence scores
      - Suggested peptalk class
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        logger.debug("api_emotion_analysis - user_input: %r", user_input)

        # Analyze emotions
        emotions = analyze_mama_emotions(user_input)
        peptalk_class = classify_user_emotion_to_peptalk_class(user_input, emotions)
        
        response_data = {
            "user_input": user_input,
            "emotions": emotions,
            "suggested_peptalk_class": peptalk_class,
            "needs_support": (
                emotions.get('is_emotion1', False) or 
                emotions.get('is_emotion2', False) or 
                emotions.get('is_emotion4', False)
            ),
            "is_happy": emotions.get('is_emotion3', False)
        }
        return JsonResponse(response_data, status=200)
        
    except Exception as e:
        logger.exception("Error in api_emotion_analysis")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# 💬 NORMAL CHAT VIEWS - General conversation functionality
    """
    Dedicated Pep Talk API
    
    Request JSON examples:
      1. With specific emotion:
         { "emotion": "emotion1" }  # emotion1, emotion2, emotion3, or emotion4
         
      2. Auto-detect from text:
         { "user_input": "I'm so tired and overwhelmed" }
         -> Analyzes emotion and returns appropriate pep talk
         
    Returns:
      - Pep talk audio URL
      - Encouraging message
    """
    try:
        data = request.data or {}
        emotion = (data.get("emotion") or "").strip()
        user_input = (data.get("user_input") or "").strip()

        # Extract bearer token for API calls
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        bearer = auth_header[7:] if auth_header.startswith('Bearer ') else None

        if not emotion and not user_input:
            return JsonResponse({"error": "emotion or user_input required"}, status=400)

        # Auto-detect emotion from text if not explicitly provided
        if not emotion and user_input:
            detected = analyze_mama_emotions(user_input)
            emotion = classify_user_emotion_to_peptalk_class(user_input, detected)
            logger.debug("api_peptalk - detected emotion: %s from input: %r", emotion, user_input)

        # Fetch pep talk voice URL
        voice_url = get_peptalk_voice_url_by_emotion(emotion, bearer_token=bearer)
        if not voice_url:
            voice_url = get_peptalk_voice_url(bearer_token=bearer)

        response_data = {
            "response": "🌸 Here's a special pep talk just for you, beautiful mama! 💕✨",
            "pep_talk": {
                "url": voice_url or "/media/voices/default.mp3",
                "emotion": emotion
            }
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_peptalk")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_chat(request):
    """
    General Chat API - Normal conversational AI chat
    
    Request JSON:
      { "user_input": "Hello! How are you today?" }
      
    Returns:
      - AI-generated conversational response
      - Natural, caring conversation using OpenAI
      - TTS audio URL
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        logger.debug("api_chat - user_input: %r", user_input)

        # Add to conversation history and get AI response
        add_to_conversation("user", user_input)
        ai_reply = get_mama_response(user_input)
        add_to_conversation("assistant", ai_reply)
        
        response_data = {
            "response": ai_reply,
            "type": "chat"
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_chat")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_detect_intent(request):
    """
    Intent Detection Helper API
    
    Request JSON:
      { "user_input": "I want to make dinner", "allow_ai": false }
      
    Returns:
      - Boolean flags for each detector (progress, planning, recipe, query)
      - Detected emotions
      - Suggested endpoint to call
      
    This helps frontend decide which specific endpoint to call.
    Set allow_ai=true to enable query detection (may call OpenAI).
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        allow_ai = bool(data.get("allow_ai", False))
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        # Normalize input
        import unicodedata
        try:
            user_input_norm = unicodedata.normalize("NFKC", str(user_input))
        except Exception:
            user_input_norm = str(user_input)

        results = {
            "input": user_input,
            "normalized_input": user_input_norm,
            "detectors": {
                "progress": False,
                "planning": False,
                "recipe": False,
                "query": False
            },
            "emotions": {},
            "suggested_endpoint": None,
            "ai_used": False
        }

        # Run local detectors (fast, no external calls)
        try:
            results["detectors"]["progress"] = bool(detect_task_progress_update(user_input_norm))
        except Exception as e:
            logger.debug("detect_task_progress_update error: %s", e)

        try:
            results["detectors"]["planning"] = bool(detect_task_planning_request(user_input_norm))
        except Exception as e:
            logger.debug("detect_task_planning_request error: %s", e)

        try:
            results["detectors"]["recipe"] = bool(detect_recipe_request(user_input_norm))
        except Exception as e:
            logger.debug("detect_recipe_request error: %s", e)

        # Query detection may call OpenAI - only run if allowed
        if allow_ai:
            try:
                results["detectors"]["query"] = bool(detect_task_query_request(user_input_norm))
                results["ai_used"] = True
            except Exception as e:
                logger.debug("detect_task_query_request error: %s", e)

        # Emotion detection (keyword-based, fast)
        try:
            results["emotions"] = analyze_mama_emotions(user_input_norm)
        except Exception as e:
            logger.debug("analyze_mama_emotions error: %s", e)

        # Suggest which endpoint to call
        if results["detectors"]["progress"]:
            results["suggested_endpoint"] = "/api/chat/progress/"
        elif results["detectors"]["planning"]:
            results["suggested_endpoint"] = "/api/chat/plan/"
        elif results["detectors"]["recipe"]:
            results["suggested_endpoint"] = "/api/chat/recipe/"
        elif results["detectors"]["query"]:
            results["suggested_endpoint"] = "/api/chat/combined/"  # Use combined for queries
        elif any([results["emotions"].get("is_emotion1"), results["emotions"].get("is_emotion2"), 
                  results["emotions"].get("is_emotion4")]):
            results["suggested_endpoint"] = "/api/chat/peptalk/"
        else:
            results["suggested_endpoint"] = "/api/chat/"

        return JsonResponse(results, status=200)
        
    except Exception as e:
        logger.exception("Error in api_detect_intent")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


# ==================== LEGACY COMBINED ENDPOINTS ====================
# These endpoints combine multiple steps - kept for backward compatibility
    """
    Dedicated General Chat API
    
    Request JSON:
      { "user_input": "Hello! How are you today?" }
      
    Returns:
      - AI-generated conversational response
      - Natural, caring conversation using OpenAI
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        logger.debug("api_chat - user_input: %r", user_input)

        # Add to conversation history and get AI response
        add_to_conversation("user", user_input)
        ai_reply = get_mama_response(user_input)
        add_to_conversation("assistant", ai_reply)
        
        response_data = {
            "response": ai_reply,
            "type": "chat"
        }
        return JsonResponse(add_tts_to_response(response_data), status=200)
        
    except Exception as e:
        logger.exception("Error in api_chat")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_detect_intent(request):
    """
    Intent Detection Helper API (Optional)
    
    Request JSON:
      { "user_input": "I want to make dinner", "allow_ai": false }
      
    Returns:
      - Boolean flags for each detector (progress, planning, recipe, query)
      - Detected emotions
      - Suggested endpoint to call
      
    This helps frontend decide which specific endpoint to call.
    Set allow_ai=true to enable query detection (may call OpenAI).
    """
    try:
        data = request.data or {}
        user_input = (data.get("user_input") or "").strip()
        allow_ai = bool(data.get("allow_ai", False))
        
        if not user_input:
            return JsonResponse({"error": "user_input is required"}, status=400)

        # Normalize input
        import unicodedata
        try:
            user_input_norm = unicodedata.normalize("NFKC", str(user_input))
        except Exception:
            user_input_norm = str(user_input)

        results = {
            "input": user_input,
            "normalized_input": user_input_norm,
            "detectors": {
                "progress": False,
                "planning": False,
                "recipe": False,
                "query": False
            },
            "emotions": {},
            "suggested_endpoint": None,
            "ai_used": False
        }

        # Run local detectors (fast, no external calls)
        try:
            results["detectors"]["progress"] = bool(detect_task_progress_update(user_input_norm))
        except Exception as e:
            logger.debug("detect_task_progress_update error: %s", e)

        try:
            results["detectors"]["planning"] = bool(detect_task_planning_request(user_input_norm))
        except Exception as e:
            logger.debug("detect_task_planning_request error: %s", e)

        try:
            results["detectors"]["recipe"] = bool(detect_recipe_request(user_input_norm))
        except Exception as e:
            logger.debug("detect_recipe_request error: %s", e)

        # Query detection may call OpenAI - only run if allowed
        if allow_ai:
            try:
                results["detectors"]["query"] = bool(detect_task_query_request(user_input_norm))
                results["ai_used"] = True
            except Exception as e:
                logger.debug("detect_task_query_request error: %s", e)

        # Emotion detection (keyword-based, fast)
        try:
            results["emotions"] = analyze_mama_emotions(user_input_norm)
        except Exception as e:
            logger.debug("analyze_mama_emotions error: %s", e)

        # Suggest which endpoint to call
        if results["detectors"]["progress"]:
            results["suggested_endpoint"] = "/api/chat/progress/"
        elif results["detectors"]["planning"]:
            results["suggested_endpoint"] = "/api/chat/plan/"
        elif results["detectors"]["recipe"]:
            results["suggested_endpoint"] = "/api/chat/recipe/"
        elif results["detectors"]["query"]:
            results["suggested_endpoint"] = "/api/chat/combined/"  # Use combined for queries
        elif any([results["emotions"].get("is_emotion1"), results["emotions"].get("is_emotion2"), 
                  results["emotions"].get("is_emotion4")]):
            results["suggested_endpoint"] = "/api/chat/peptalk/"
        else:
            results["suggested_endpoint"] = "/api/chat/"

        return JsonResponse(results, status=200)
        
    except Exception as e:
        logger.exception("Error in api_detect_intent")
        return JsonResponse({"error": "Internal server error", "details": str(e)}, status=500)

# ==================== END DEDICATED ENDPOINTS ====================


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
            logger.exception("S3 upload failed: %s", str(e))
            return None
        except ValueError as e:
            logger.exception("Error: %s", str(e))
            return None
        except Exception as e:
            logger.exception("Error during OCR extraction: %s", str(e))
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
            logger.exception("JSON decode error: %s", e)
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

    # If the receipt type is pantry, save or update the items in the Pantry model
    if receipt_type == "pantry":
        for item in data.get("items", []):
            # Check if the item already exists in the Pantry table
            existing_item = Pantry.objects.filter(name=item.get("name")).first()
            
            if existing_item:
                # If the item exists, increase the quantity
                existing_item.quantity += item.get("qty", 0)
                existing_item.save()
            else:
                # If the item does not exist, create a new entry
                Pantry.objects.create(
                    name=item.get("name"),
                    quantity=item.get("qty", 0)
                )

    # Return a success message with the receipt ID
    return JsonResponse(
        {"message": f"{receipt_type.title()} receipt saved successfully", "receipt_id": receipt.id},
        status=201
    )
