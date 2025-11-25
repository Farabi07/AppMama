from urllib import response
import os, re, json, base64, uuid, requests
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
GOOGLE_TTS_API_KEY = "AIzaSyC69BVmhR-VUyQqfyCwqFs_NP2Y_0lNgxw"
PEPTALK_SETTINGS_URL = 'https://api.taskmama.app/peptalk/api/v1/peptalk/all/'


# Local emotion detection (keywords only, no imports)

def _emotions(text: str):
    """Enhanced emotion detection with expanded keywords for better accuracy"""
    t=(text or '').lower()
    
    # Emotion 1: Guilty, behind, self-critical, pressured, failing - GREATLY EXPANDED
    emo1 = any(k in t for k in [
        'guilty', 'guilt', 'feel guilty', 'feeling guilty', 'i feel guilty', 'feeling so guilty',
        'behind', 'behind schedule', 'running behind', 'fall behind', 'falling behind', 'feeling behind',
        'self critical', 'self-critical', 'criticizing myself', 'critical of myself', 'too critical',
        'pressured', 'under pressure', 'feel pressured', 'feeling pressured', 'too much pressure', 'pressure on me',
        'failing', 'feel like failing', 'feeling like a failure', 'failure as', 'fail at', 'failed at',
        'not doing enough', 'not good enough', 'not enough', 'dont do enough', "don't do enough",
        'not measuring up', 'falling short', 'inadequate', 'insufficient', 'not adequate',
        'disappointing', 'let down', 'letting down', 'disappointing myself', 'disappointing others',
        'should be doing more', 'should do more', 'shouldve done', 'should have done',
        'not living up', 'cant keep up', "can't keep up", 'struggling to keep up',
        'never enough', 'always behind', 'constantly behind', 'perpetually behind'
    ])
    
    # Emotion 2: Sad, insecure, unworthy, alone, lonely - GREATLY EXPANDED
    emo2 = any(k in t for k in [
        'sad', 'sadness', 'feel sad', 'feeling sad', 'i feel sad', 'so sad', 'really sad', 'very sad',
        'insecure', 'insecurity', 'feel insecure', 'feeling insecure', 'i feel insecure', 'so insecure',
        'unworthy', 'not worthy', 'feel unworthy', 'feeling unworthy', 'i feel unworthy', 'unworthiness',
        'alone', 'feel alone', 'feeling alone', 'i feel alone', 'all alone', 'so alone',
        'lonely', 'loneliness', 'feel lonely', 'feeling lonely', 'i feel lonely', 'so lonely',
        'worthless', 'feel worthless', 'feeling worthless', 'i feel worthless', 'no worth',
        'self-doubt', 'self doubt', 'self-doubting', 'self doubting', 'doubt myself', 'doubting myself',
        'lost', 'feel lost', 'feeling lost', 'i feel lost', 'so lost', 'completely lost',
        'unappreciated', 'not appreciated', 'feel unappreciated', 'feeling unappreciated', 'underappreciated',
        'unseen', 'invisible', 'feel invisible', 'feeling invisible', 'no one sees me', 'nobody sees',
        'nobody cares', 'no one cares', 'no one understands', 'nobody understands', 'not understood',
        'rejected', 'unwanted', 'unloved', 'not loved', 'not enough', 'never enough',
        'hopeless', 'feel hopeless', 'feeling hopeless', 'no hope', 'without hope',
        'depressed', 'depression', 'feel depressed', 'feeling depressed', 'so down',
        'miserable', 'feel miserable', 'feeling miserable', 'utterly miserable',
        'broken', 'feel broken', 'feeling broken', 'emotionally broken', 'heartbroken',
        'empty', 'feel empty', 'feeling empty', 'emptiness inside', 'hollow inside',
        'abandoned', 'feel abandoned', 'feeling abandoned', 'left alone', 'deserted'
    ])
    
    # Emotion 3: Happy, grateful, blessed, joyful - MASSIVELY EXPANDED
    emo3 = any(k in t for k in [
        'happy', 'happiness', 'feel happy', 'feeling happy', 'i feel happy', 'so happy', 'really happy', 'very happy', 'extremely happy',
        'joyful', 'joy', 'feel joyful', 'feeling joyful', 'full of joy', 'brings me joy', 'filled with joy',
        'grateful', 'gratitude', 'feel grateful', 'feeling grateful', 'i feel grateful', 'so grateful', 'very grateful', 'deeply grateful',
        'blessed', 'feel blessed', 'feeling blessed', 'i feel blessed', 'so blessed', 'truly blessed',
        'wonderful', 'feel wonderful', 'feeling wonderful', 'i feel wonderful', 'so wonderful', 'absolutely wonderful',
        'amazing', 'feel amazing', 'feeling amazing', 'i feel amazing', 'so amazing', 'truly amazing',
        'great', 'feel great', 'feeling great', 'i feel great', 'so great', 'really great', 'feeling so great',
        'fantastic', 'feel fantastic', 'feeling fantastic', 'i feel fantastic', 'absolutely fantastic',
        'good mood', 'in a good mood', 'in good mood', 'good spirits', 'high spirits', 'great mood', 'in a great mood',
        'feeling good', 'feel good', 'feeling really good', 'feeling so good', 'im in a good mood', "i'm in a good mood",
        'thankful', 'feel thankful', 'feeling thankful', 'i feel thankful', 'so thankful', 'very thankful',
        'excited', 'feel excited', 'feeling excited', 'i feel excited', 'so excited', 'really excited', 'very excited',
        'positive', 'feel positive', 'feeling positive', 'so positive', 'very positive',
        'optimistic', 'feel optimistic', 'feeling optimistic', 'optimism', 'hopeful', 'feel hopeful',
        'upbeat', 'feel upbeat', 'feeling upbeat', 'in high spirits', 'cheerful', 'feel cheerful',
        'content', 'feel content', 'feeling content', 'contentment', 'satisfied', 'feel satisfied',
        'pleased', 'feel pleased', 'feeling pleased', 'so pleased', 'very pleased',
        'delighted', 'feel delighted', 'feeling delighted', 'so delighted', 'absolutely delighted',
        'uplifted', 'feel uplifted', 'feeling uplifted', 'lifted up', 'spirits lifted',
        'elated', 'feel elated', 'feeling elated', 'elation', 'euphoric',
        'thrilled', 'feel thrilled', 'feeling thrilled', 'so thrilled', 'absolutely thrilled',
        'greatly happy', 'gretly happy', 'incredibly happy', 'super happy', 'overjoyed',
        'proud', 'feel proud', 'feeling proud', 'proud of myself', 'so proud',
        'accomplished', 'feel accomplished', 'feeling accomplished', 'sense of accomplishment',
        'fulfilled', 'feel fulfilled', 'feeling fulfilled', 'fulfillment', 'complete',
        'peaceful', 'feel peaceful', 'feeling peaceful', 'at peace', 'inner peace',
        'calm', 'feel calm', 'feeling calm', 'so calm', 'very calm', 'relaxed',
        'love', 'feel love', 'feeling loved', 'feel loved', 'so loved', 'feeling the love',
        'appreciated', 'feel appreciated', 'feeling appreciated', 'valued', 'feel valued',
        'confident', 'feel confident', 'feeling confident', 'confidence', 'self-confident',
        'inspired', 'feel inspired', 'feeling inspired', 'inspiration', 'motivated by',
        'alive', 'feel alive', 'feeling alive', 'so alive', 'fully alive', 'vibrant'
    ])
    
    # Emotion 4: Tired, stressed, overwhelmed, frustrated - MASSIVELY EXPANDED
    emo4 = any(k in t for k in [
        'tired', 'feel tired', 'feeling tired', 'i feel tired', 'so tired', 'really tired', 'very tired', 'extremely tired',
        'exhausted', 'feel exhausted', 'feeling exhausted', 'i feel exhausted', 'so exhausted', 'completely exhausted', 'utterly exhausted',
        'unmotivated', 'no motivation', 'lack motivation', 'feel unmotivated', 'feeling unmotivated', 'lost motivation',
        'low energy', 'no energy', 'drained energy', 'energy drained', 'lack energy', 'out of energy', 'running on empty',
        'stressed', 'stress', 'feel stressed', 'feeling stressed', 'i feel stressed', 'so stressed', 'under stress', 'stressed out',
        'overwhelmed', 'feel overwhelmed', 'feeling overwhelmed', 'i feel overwhelmed', 'so overwhelmed', 'completely overwhelmed',
        'frustrated', 'frustration', 'feel frustrated', 'feeling frustrated', 'i feel frustrated', 'so frustrated', 'really frustrated',
        'angry', 'anger', 'feel angry', 'feeling angry', 'i feel angry', 'so angry', 'mad', 'pissed off', 'furious', 'enraged',
        'drained', 'feel drained', 'feeling drained', 'i feel drained', 'completely drained', 'emotionally drained',
        'burned out', 'burnout', 'burn out', 'feel burned out', 'feeling burned out', 'burnt out',
        'scattered', 'feel scattered', 'feeling scattered', 'all over the place', 'cant think straight', "can't think straight",
        'unfocused', "can't focus", 'cannot focus', 'unable to focus', 'distracted', 'cant concentrate', 'lose focus',
        'anxious', 'anxiety', 'feel anxious', 'feeling anxious', 'nervous', 'worried', 'worry', 'worrying',
        'restless', 'agitated', 'irritated', 'annoyed', 'bothered', 'irritable', 'on edge',
        'weary', 'feel weary', 'feeling weary', 'weariness', 'worn out', 'worn down',
        'fatigued', 'fatigue', 'feel fatigued', 'feeling fatigued', 'mental fatigue', 'physical fatigue',
        'depleted', 'feel depleted', 'feeling depleted', 'emotionally depleted', 'resources depleted',
        'frazzled', 'feel frazzled', 'feeling frazzled', 'so frazzled', 'completely frazzled',
        'tense', 'tension', 'feel tense', 'feeling tense', 'so tense', 'under tension',
        'panicked', 'panic', 'feel panicked', 'feeling panicked', 'panicky', 'in a panic',
        'worried sick', 'sick with worry', 'cant stop worrying', "can't stop worrying",
        'breaking down', 'falling apart', 'coming apart', 'cant cope', "can't cope",
        'at my limit', 'reached my limit', 'cant take anymore', "can't take anymore", 'had enough',
        'no patience', 'running out of patience', 'lost my patience', 'impatient', 'short-tempered',
        'cranky', 'grumpy', 'moody', 'irritable', 'short fuse', 'quick to anger',
        'resentful', 'resentment', 'feel resentful', 'feeling resentful', 'bitter', 'bitterness'
    ])
    
    primary='emotion3'
    if emo3: primary='emotion3'
    elif emo1: primary='emotion1'
    elif emo2: primary='emotion2'
    elif emo4: primary='emotion4'
    
    return {
        "is_emotion1":emo1,
        "is_emotion2":emo2,
        "is_emotion3":emo3,
        "is_emotion4":emo4,
        "primary_emotion":primary,
        "confidence": 0.85 if any([emo1, emo2, emo3, emo4]) else 0.1
    }

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

    # Build emotion-specific responses & motivational messages
    msgs = {
        'emotion1': {
            'response': "I hear you - it's okay to feel behind. You're doing your best, mama. 💕",
            'motivational': "You're showing up even when it's hard. Take a small breath and one gentle step - even 5 minutes can help. Remember it's okay to pause and rest. Are you feeling tired? Take a break if you need one! 🌸"
        },
        'emotion2': {
            'response': "I'm so sorry you're feeling this way - you're not alone. 💖",
            'motivational': "It's okay to feel sad or unsure. You matter and your efforts matter. Take a moment to be kind to yourself - a short rest or a warm drink can help. Would you like a calming pep talk? 💕"
        },
        'emotion3': {
            'response': "That's wonderful - what a lovely moment! ✨",
            'motivational': "You're doing great and it's lovely to see you shining. Celebrate this progress and enjoy a little moment of joy - you deserve it! 🌸"
        },
        'emotion4': {
            'response': "You sound exhausted - that is so hard. I'm here with you. 🤗",
            'motivational': "You've been carrying a lot. It's okay to slow down and recharge - consider a restful pause or a short nap. Your wellbeing matters more than any task. Take care, mama. 💖"
        }
    }

    key = (emotion or 'emotion3').lower()
    chosen = msgs.get(key, msgs['emotion3'])

    response = {
        "response": chosen['response'],
        "motivational_message": chosen['motivational'],
        "pep_talk": {"url": url, "emotion": emotion or 'emotion3'}
    }
    # Generate TTS from the richer motivational_message (fallback to short response)
    response['audio_url'] = _tts(response.get('motivational_message') or response.get('response'))
    return JsonResponse(response, status=200)
