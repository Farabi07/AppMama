import os, re, json, base64, uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI

# Self‑contained OpenAI + lightweight intent & emotion detectors (no cross‑file imports)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
GOOGLE_TTS_API_KEY="AIzaSyC69BVmhR-VUyQqfyCwqFs_NP2Y_0lNgxw"

# -------------------- Basic Heuristic Detectors --------------------

def _detect_task_planning(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['plan my day','schedule','organize','today\'s tasks','set up tasks','make a schedule','create a plan'])

def _detect_recipe(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['cook','recipe','dinner','breakfast','lunch','snack','meal','what can i make'])

def _detect_progress(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['%','percent','completed','finished','done','progress'])

def _detect_query(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['what tasks do i have','what do i have today','tasks today','any tasks','do i have tasks'])

def _emotions(text: str):
    t=(text or '').lower()
    emo1 = any(k in t for k in ['guilty','behind','self critical','pressured','failing'])
    emo2 = any(k in t for k in ['sad','insecure','unworthy','alone','lonely','worthless'])
    emo3 = any(k in t for k in ['happy','grateful','blessed','wonderful','amazing','great','excited'])
    emo4 = any(k in t for k in ['tired','exhausted','unmotivated','low energy','stressed','overwhelmed','frustrated','angry','drained'])
    primary='emotion3'
    if emo3: primary='emotion3'
    elif emo1: primary='emotion1'
    elif emo2: primary='emotion2'
    elif emo4: primary='emotion4'
    return {"is_emotion1":emo1,"is_emotion2":emo2,"is_emotion3":emo3,"is_emotion4":emo4,"primary_emotion":primary}

# -------------------- TTS Helper --------------------

def _tts(text: str):
    if not text: return None
    try:
        clean=re.sub(r'[^\w\s,.!?-]','',text)
        url=f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
        payload={"input":{"text":clean},"voice":{"languageCode":"en-US","name":"en-US-Neural2-F","ssmlGender":"FEMALE"},"audioConfig":{"audioEncoding":"MP3","speakingRate":1.0,"pitch":0.0}}
        import requests
        r=requests.post(url,json=payload,headers={"Content-Type":"application/json"},timeout=10)
        if r.status_code!=200: return None
        audio_b64=r.json().get('audioContent');
        if not audio_b64: return None
        audio_data=base64.b64decode(audio_b64)
        audio_dir=os.path.join(settings.MEDIA_ROOT,'audio'); os.makedirs(audio_dir,exist_ok=True)
        filename=f"tts_{uuid.uuid4().hex[:8]}.mp3"; path=os.path.join(audio_dir,filename)
        with open(path,'wb') as f: f.write(audio_data)
        return f"{settings.MEDIA_URL}audio/{filename}"
    except Exception:
        return None

def _with_tts(payload: dict):
    txt=payload.get('response') or payload.get('message') or payload.get('motivational_message') or ''
    payload['audio_url']=_tts(txt)
    return payload

# -------------------- Intent Detection Endpoint --------------------

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_detect_intent(request):
    body=request.data or {}
    user_input=(body.get('user_input') or '').strip()
    if not user_input:
        return JsonResponse({'error':'user_input is required'}, status=400)
    detectors={
        'planning': _detect_task_planning(user_input),
        'recipe': _detect_recipe(user_input),
        'progress': _detect_progress(user_input),
        'query': _detect_query(user_input)
    }
    emotions=_emotions(user_input)
    if detectors['progress']:
        suggested='/api/task-progress/'
    elif detectors['planning']:
        suggested='/api/task-planning/'
    elif detectors['recipe']:
        suggested='/api/recipe/'
    elif detectors['query']:
        suggested='/api/task-query/'
    elif any([emotions.get('is_emotion1'), emotions.get('is_emotion2'), emotions.get('is_emotion4')]):
        suggested='/api/peptalk/'
    else:
        suggested='/api/chat/'
    return JsonResponse({'detectors':detectors,'emotions':emotions,'suggested_endpoint':suggested}, status=200)

# -------------------- Chat Endpoint --------------------

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_chat(request):
    body=request.data or {}
    user_input=(body.get('user_input') or '').strip()
    if not user_input:
        return JsonResponse({'error':'user_input is required'}, status=400)
    # Lightweight AI response
    try:
        prompt=f"You are a warm, concise motivational assistant for mothers. Reply supportively to: '{user_input}'. Keep response under 4 sentences and include one emoji."  # noqa
        resp=client.chat.completions.create(model='gpt-4o-mini',messages=[{"role":"user","content":prompt}],temperature=0.5,max_tokens=220)
        reply=resp.choices[0].message.content.strip()
    except Exception:
        reply="🌸 I'm here with you, beautiful mama. Tell me more and I'll gladly help."
    return JsonResponse(_with_tts({'response': reply}), status=200)

# -------------------- Legacy Combined Conversation (Simplified) --------------------
# Retained for backward compatibility with /api/chat-boot/ clients.

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def handle_task_mama_request(request):
    body=request.data or {}
    user_input=(body.get('user_input') or '').strip()
    if not user_input:
        return JsonResponse({'error':'user_input is required'}, status=400)
    # Run detectors
    if _detect_progress(user_input):
        return JsonResponse(_with_tts({'response':'It looks like you are sharing progress. Please use /api/task-progress/ for updating a task. 💕'}), status=200)
    if _detect_task_planning(user_input):
        return JsonResponse(_with_tts({'response':'Sounds like planning time! Use /api/task-planning/ to structure your tasks. 📋✨'}), status=200)
    if _detect_recipe(user_input):
        return JsonResponse(_with_tts({'response':'Yummy! Head to /api/recipe/ and tell me your available items. 🍳'}), status=200)
    if _detect_query(user_input):
        return JsonResponse(_with_tts({'response':'To check tasks, send the query to /api/task-query/. 🌸'}), status=200)
    emos=_emotions(user_input)
    if any([emos.get('is_emotion1'), emos.get('is_emotion2'), emos.get('is_emotion4')]):
        return JsonResponse(_with_tts({'response':'I sense emotions in your words. You can request a pep talk at /api/peptalk/. 💖'}), status=200)
    # Default chat fallback
    try:
        prompt=f"Provide a gentle, uplifting, concise supportive reply (<=4 sentences) to: '{user_input}'. One emoji."  # noqa
        resp=client.chat.completions.create(model='gpt-4o-mini',messages=[{"role":"user","content":prompt}],temperature=0.5,max_tokens=220)
        reply=resp.choices[0].message.content.strip()
    except Exception:
        reply="🌸 I'm here for you. Tell me anything and I'll help."
    return JsonResponse(_with_tts({'response':reply}), status=200)
