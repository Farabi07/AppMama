import os, re, json, base64, uuid, requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
PEPTALK_SETTINGS_URL = 'https://api.taskmama.app/peptalk/api/v1/peptalk/all/'
GOOGLE_API_KEY='AIzaSyC69BVmhR-VUyQqfyCwqFs_NP2Y_0lNgxw'

# Local emotion detection (keywords only, no imports)

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

# TTS helper

def _tts(text: str):
    if not text:
        return None
    try:
        clean = re.sub(r'[^\w\s,.!?-]', '', text)
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GOOGLE_TTS_API_KEY}"
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

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_peptalk(request):
    body=request.data or {}
    emotion=(body.get('emotion') or '').strip().lower()
    user_input=(body.get('user_input') or '').strip()

    # detect primary emotion if needed
    if not emotion and user_input:
        detected=_emotions(user_input)
        emotion=detected.get('primary_emotion','emotion3')

    # fetch from peptalk API
    auth=request.META.get('HTTP_AUTHORIZATION','')
    token=auth[7:] if auth.startswith('Bearer ') else None
    headers={}
    if token: headers['Authorization']=f'Bearer {token}'

    try:
        r=requests.get(PEPTALK_SETTINGS_URL, headers=headers, timeout=6)
        url=None
        if r.status_code==200:
            data=r.json(); groups=[]
            if isinstance(data,dict):
                for k in ('peptalks','cities','results'):
                    if isinstance(data.get(k), list): groups=data[k]
                if not groups:
                    for v in data.values():
                        if isinstance(v,list): groups=v; break
            for g in groups:
                title=(g.get('title') or g.get('name') or '').lower()
                if emotion and emotion in title:
                    items=g.get('items') or g.get('voices') or g.get('children') or []
                    for it in items:
                        v = it.get('voice') if isinstance(it,dict) else str(it)
                        if v:
                            import os
                            url=f"/media/voices/{os.path.basename(v)}"; break
                if url: break
        if not url:
            url='/media/voices/default.mp3'
    except Exception:
        url='/media/voices/default.mp3'

    response={
        "response":"🌸 Here's a special pep talk just for you, beautiful mama! 💕✨",
        "pep_talk": {"url": url, "emotion": emotion or 'emotion3'}
    }
    # add TTS for message
    response['audio_url']=_tts(response['response'])
    return JsonResponse(response, status=200)
