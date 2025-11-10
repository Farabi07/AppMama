import os, json, re, base64, uuid
import requests
from datetime import datetime
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI

# Self-contained OpenAI client
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Self-contained TTS helpers
# Replace hardcoded API key with dynamic lookup from settings or environment
GOOGLE_TTS_API_KEY = getattr(settings, 'GOOGLE_API_KEY', None) or os.getenv('GOOGLE_API_KEY')

# Helper to detect intent (Phase 1) versus ingredient list (Phase 2)
def _detect_recipe_intent(text: str) -> bool:
    if not text:
        return False
    t = text.lower().strip()
    # Phrases indicating user is asking for suggestions, not giving ingredients yet
    intent_phrases = [
        'give me recipe','give me a recipe','suggest recipe','suggest me recipe','suggest me a recipe','suggest me some recipes',
        'meal ideas','suggest meal','meal suggestion','what can i cook','what should i cook','help me cook','help me to cook',
        'i need a recipe','need recipe','any recipe','any meal idea','plan my meals','plan my meal','recipe ideas','cooking ideas'
    ]
    if any(p in t for p in intent_phrases):
        return True
    # If message looks like a question and has no commas (likely not ingredient list yet)
    if '?' in t and ',' not in t and len(t.split()) < 12:
        return True
    # If it contains verbs like 'suggest', 'give', 'need' but lacks commas or ' and ' plus multiple nouns
    verbs = ['suggest','give','need','help','plan']
    if any(v in t for v in verbs) and (',' not in t) and (' and ' not in t):
        return True
    return False

# Heuristic to determine if text looks like a list of ingredients
def _looks_like_ingredients(text: str) -> bool:
    if not text:
        return False
    t = text.lower()
    # Presence of commas/semicolons, or multiple items separated by ' and '
    if ',' in t or ';' in t:
        return True
    if ' and ' in t and len(t.split()) <= 30:
        return True
    # If it contains common ingredient keywords
    ingr_keywords = ['rice','chicken','salt','oil','water','tomato','onion','garlic','beef','fish','potato','pepper','egg','lentil','dal','flour','milk','butter']
    hits = sum(1 for k in ingr_keywords if k in t)
    return hits >= 2

def _format_items_available(raw: str) -> str:
    items = [i.strip().lower() for i in re.split(r'[;,]', raw) if i.strip()]
    formatted = []
    for it in items:
        if 'fish' in it:
            formatted.append(f"500g {it}")
        elif any(k in it for k in ['dal','lentil','lentils','rice']):
            formatted.append(f"1 kg {it}")
        else:
            formatted.append(it)
    return ', '.join(formatted)

def _tts(text: str):
    if not text:
        return None
    try:
        clean = re.sub(r'[^\w\s,.!?-]', '', text)
        api_key = GOOGLE_TTS_API_KEY
        if not api_key:
            return None
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        payload = {
            "input": {"text": clean},
            "voice": {"languageCode": "en-US", "name": "en-US-Neural2-F", "ssmlGender": "FEMALE"},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.0, "pitch": 0.0}
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code != 200:
            return None
        audio_b64 = resp.json().get("audioContent")
        if not audio_b64:
            return None
        audio_data = base64.b64decode(audio_b64)
        audio_dir = os.path.join(settings.MEDIA_ROOT, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        filename = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        path = os.path.join(audio_dir, filename)
        with open(path, 'wb') as f:
            f.write(audio_data)
        return f"{settings.MEDIA_URL}audio/{filename}"
    except Exception:
        return None

def _with_tts(payload: dict):
    text = payload.get("response") or payload.get("message") or ""
    payload["audio_url"] = _tts(text)
    return payload

# Local helpers (no import from asif_ai)

def _get_meal_type(text: str) -> str:
    t = (text or "").lower()
    for m in ["breakfast","lunch","dinner","snack","snacks","brunch","supper"]:
        if m in t:
            return m.capitalize()
    return "Dinner"

def _fix_unicode(text: str) -> str:
    return (text or "").replace("\u00b0C"," celsius").replace("\u00b0F"," fahrenheit").replace("\u2019","'")

def _generate_recipes(available_items: str, user_conversation: str = "") -> dict:
    meal_type = _get_meal_type(user_conversation)
    prompt = f"""
You are an expert recipe assistant. Create exactly 3 unique recipes using ONLY these ingredients: {available_items}
Requirements:
1. Use ONLY the ingredients mentioned by the user
2. Each recipe must be completely different from the others
3. Provide detailed cooking instructions (5-6 sentences)
4. Include cooking times and temperatures (use C/F words, not symbols)
5. Add kid-friendly tips and a short nutritional note
Return valid JSON with keys: recipe_name (array of 3 short names), recipe (array of 3 detailed descriptions). Only JSON.
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"Return only valid JSON."},{"role":"user","content":prompt}],
        temperature=0.25,
        max_tokens=850
    )
    txt = resp.choices[0].message.content.strip()
    if txt.startswith("```json"):
        txt = txt[7:].rstrip("`").strip()
    data = json.loads(txt)
    names = data.get("recipe_name", [])[:3]
    descs = data.get("recipe", [])[:3]
    # Normalize unicode + prefix
    fixed_names = []
    for idx, n in enumerate(names, start=1):
        n2 = _fix_unicode(str(n))
        if not n2.lower().startswith(f"recipe {idx}:"):
            n2 = f"Recipe {idx}: {n2}" if not n2.lower().startswith("recipe") else n2
        fixed_names.append(n2)
    fixed_descs = []
    for idx, d in enumerate(descs, start=1):
        d2 = _fix_unicode(str(d))
        if not d2.lower().startswith(f"recipe {idx}:"):
            d2 = f"Recipe {idx}: {d2}" if not d2.lower().startswith("recipe") else d2
        fixed_descs.append(d2)
    now = datetime.now()
    formatted_items = _format_items_available(available_items)
    return {
        "meal_type": meal_type,
        "task_catagory": "Recipy task",
        "time": now.strftime('%H:%M'),
        "date": now.strftime('%Y-%m-%d'),
        "items_available": formatted_items,
        "items_needed": "Cooking oil, salt, black pepper, water, onions",
        "recipy_name": fixed_names,
        "recipy": fixed_descs
    }

@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_step1_ask_ingredients(request):
    body = request.data or {}
    user_text = (body.get("user_input") or "").strip()
    meal_type = _get_meal_type(body.get("meal_type") or user_text or "")
    # If user already provided ingredients in first call, jump directly to generation
    if user_text and _looks_like_ingredients(user_text) and not _detect_recipe_intent(user_text):
        recipes = _generate_recipes(user_text, user_text)
        return JsonResponse(_with_tts({
            "type": "recipe",
            "message": "🌸 Here are your AI-suggested recipes:",
            "data": recipes
        }), status=200)
    return JsonResponse(_with_tts({
        "type":"recipe_prompt",
        "response": f"🌸 I'd love to help you with some delicious {meal_type.lower()} ideas! Please list the ingredients you have (e.g., 'rice, chicken, tomato').",
        "data": {"awaiting_ingredients": True, "meal_type": meal_type}
    }), status=200)

@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_step2_generate(request):
    body = request.data or {}
    items_text = (body.get("user_input") or "").strip()
    # Phase 1 intent should not be here; ensure ingredients provided
    if not items_text or _detect_recipe_intent(items_text):
        return JsonResponse({"error":"Provide ingredient list in user_input (comma separated)."}, status=400)
    recipes = _generate_recipes(items_text, items_text)
    return JsonResponse(_with_tts({
        "type":"recipe",
        "message":"🌸 Here are your AI-suggested recipes:",
        "data": recipes
    }), status=200)

@csrf_exempt
@api_view(["POST"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_recipe_combined(request):
    """Unified single recipe endpoint using user_input for both phases.
    Phase 1: user_input contains an intent/question asking for suggestions OR is empty -> return prompt.
    Phase 2: user_input contains ingredient list (commas/and/keywords) -> return recipes.
    """
    body = request.data or {}
    user_input = (body.get("user_input") or "").strip()
    meal_type = _get_meal_type(body.get("meal_type") or user_input or "")

    # Determine phase
    if (not user_input) or _detect_recipe_intent(user_input) or (user_input and not _looks_like_ingredients(user_input)):
        response_text = f"🌸 I'd love to help you with some delicious {meal_type.lower()} ideas! Please list the ingredients you have (e.g., 'rice, chicken, tomato')."
        payload = {
            "type": "recipe_prompt",
            "response": response_text,
            "data": {"awaiting_ingredients": True, "meal_type": meal_type}
        }
        payload["audio_url"] = _tts(response_text)
        return JsonResponse(payload, status=200)

    # Generation phase
    recipes = _generate_recipes(user_input, user_input)
    resp = {
        "type": "recipe",
        "message": "🌸 Here are your AI-suggested recipes:",
        "data": recipes
    }
    resp["audio_url"] = _tts(resp["message"]) 
    return JsonResponse(resp, status=200)
