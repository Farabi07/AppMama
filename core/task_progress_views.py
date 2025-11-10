import os, re, json, uuid, random
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI
from task.models import Task
from django.conf import settings

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

SCHEDULE_SETTINGS_URL = 'https://api.taskmama.app/task/api/v1/task/all/'
PEPTALK_SETTINGS_URL = 'https://api.taskmama.app/peptalk/api/v1/peptalk/all/'

import requests
from datetime import datetime, timedelta

# In-memory pep talk pending state per user
_pep_talk_pending = {}

# --- Helper audio generation (placeholder) ---
def _generate_audio_url(text: str) -> str:
    try:
        base = getattr(settings, 'BASE_DIR', os.getcwd())
        audio_dir = os.path.join(base, 'media', 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        fname = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        fpath = os.path.join(audio_dir, fname)
        # Placeholder empty file (could be replaced with real TTS)
        if not os.path.exists(fpath):
            with open(fpath, 'wb') as f:
                f.write(b'')
        return f"/media/audio/{fname}"
    except Exception:
        return "/media/audio/tts_fallback.mp3"

# --- Helper to fetch pep talk voice url (dynamic) ---
def _fetch_peptalk_voice_url(token: str | None) -> str:
    # Try remote API first
    try:
        headers = {}
        if token:
            headers['Authorization'] = f'Bearer {token}'
        r = requests.get(PEPTALK_SETTINGS_URL, headers=headers, timeout=6)
        if r.status_code == 200:
            data = r.json()
            # Attempt to extract a voice URL from common patterns
            if isinstance(data, dict):
                for k in ('results','voices','items','data'):
                    v = data.get(k)
                    if isinstance(v, list) and v:
                        first = v[0]
                        if isinstance(first, dict):
                            for key in ('voice_url','url','audio','voice'):
                                if key in first and isinstance(first[key], str):
                                    return first[key]
            if isinstance(data, list) and data:
                first = data[0]
                if isinstance(first, dict):
                    for key in ('voice_url','url','audio','voice'):
                        if key in first and isinstance(first[key], str):
                            return first[key]
        # Fallback to local media files if remote fails
    except Exception:
        pass
    # Local random pick
    try:
        base = getattr(settings, 'BASE_DIR', os.getcwd())
        voices_dir = os.path.join(base, 'media', 'voices')
        if os.path.isdir(voices_dir):
            files = [f for f in os.listdir(voices_dir) if f.lower().endswith('.mp3')]
            if files:
                return f"/media/voices/{random.choice(files)}"
    except Exception:
        pass
    return "/media/voices/default_peptalk.mp3"

# --- Simple in-memory conversational state for pep talk follow-up (per user) ---
# Using `_pep_talk_pending` dict for follow-up; legacy state helpers removed.

# --- TTS helper: Google Cloud if available, else safe fallback file ---
try:
    from google.cloud import texttospeech  # type: ignore
except Exception:  # pragma: no cover
    texttospeech = None


def _tts_audio_url(text: str):
    """Synthesize speech to an mp3 file in MEDIA_ROOT/audio and return media URL.
    Falls back to creating a tiny placeholder file if TTS not configured.
    """
    try:
        media_root = getattr(settings, 'MEDIA_ROOT', os.path.join(os.getcwd(), 'media'))
        media_url = getattr(settings, 'MEDIA_URL', '/media/')
        audio_dir = os.path.join(media_root, 'audio')
        os.makedirs(audio_dir, exist_ok=True)
        fname = f"tts_{uuid.uuid4().hex[:8]}.mp3"
        fpath = os.path.join(audio_dir, fname)

        if texttospeech is not None:
            client_tts = texttospeech.TextToSpeechClient()
            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-F",
                ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
            )
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            resp = client_tts.synthesize_speech(input=synthesis_input, voice=voice, audio_config=audio_config)
            with open(fpath, 'wb') as f:
                f.write(resp.audio_content)
        else:
            # Minimal placeholder so callers get a valid URL path
            with open(fpath, 'wb') as f:
                f.write(b"")
        return media_url.rstrip('/') + '/audio/' + fname
    except Exception:
        return None


def _detect_progress(text: str) -> bool:
    if not text: return False
    t = text.lower()
    if re.search(r"\d+%", t): return True
    if any(w in t for w in ["completed","finished","i did","i've done","i have done","done"]):
        if re.search(r"\d+", t): return True
    return False

def _extract_progress(text: str):
    pct=None; t=text.strip()
    m=re.search(r"(\d{1,3})\s*%", t)
    if m:
        try:
            pct=int(m.group(1))
        except Exception:
            pct=None
    if pct is None:
        if 'half' in t.lower():
            pct=50
    if pct is None:
        m2=re.search(r"(\d{1,3})\s*(percent|pct)?", t.lower())
        if m2:
            try:
                pct=int(m2.group(1))
            except Exception:
                pct=None
    pct = max(0,min(100,int(pct or 0)))
    task_name='task'
    if m:
        before=t[:m.start()]
        if ' of ' in before:
            task_name=before.split(' of ')[-1].strip()
        elif 'completed ' in before:
            task_name=before.split('completed ')[-1].strip()
        else:
            words=re.findall(r"\w+", before)
            task_name=' '.join(words[-6:]) if words else 'task'
    return {"task_name": task_name or 'task', "task_percentage": pct}

# --- External API helpers ---

def _get_tasks_from_api(token: str):
    try:
        headers={}
        if token: headers['Authorization']=f'Bearer {token}'
        r=requests.get(SCHEDULE_SETTINGS_URL, headers=headers, timeout=6)
        if r.status_code!=200: return []
        data=r.json()
        if isinstance(data,list): return data
        if isinstance(data,dict):
            for k in ('results','tasks','data','items'):
                if k in data and isinstance(data[k],list): return data[k]
            for v in data.values():
                if isinstance(v,list): return v
        return []
    except Exception:
        return []


def _fetch_peptalk_voice_url(token: str):
    """Try to get a peptalk voice URL (.mp3). Returns URL or None."""
    try:
        headers={}
        if token: headers['Authorization']=f'Bearer {token}'
        r=requests.get(PEPTALK_SETTINGS_URL, headers=headers, timeout=6)
        if r.status_code!=200:
            return None
        data=r.json()
        def _find_mp3(obj):
            if isinstance(obj, str) and obj.lower().endswith('.mp3'):
                return obj
            if isinstance(obj, dict):
                for v in obj.values():
                    u=_find_mp3(v)
                    if u: return u
            if isinstance(obj, list):
                for it in obj:
                    u=_find_mp3(it)
                    if u: return u
            return None
        url=_find_mp3(data)
        return url
    except Exception:
        return None

# --- Robust task id matching ---
STOPWORDS = {"the","a","an","to","for","of","my","our","me","have","has","had","need","must","got","get","at","on","in","with","and","meet","meeting","please","make","show","give","do","did","does","is","are","was","were","be","been","being","finish","finished","complete","completed","done","i","we","you","have","has","had","task"}


def _normalize_name(s: str):
    s = (s or '').lower()
    s = re.sub(r"[\-_/]", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [w for w in s.split() if w and w not in STOPWORDS]
    # simple stemming for words ending with 'ing'
    tokens = [w[:-3] if w.endswith('ing') and len(w)>5 else w for w in tokens]
    return tokens


def _jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter/union


def _candidate_name(task: dict) -> str:
    if not isinstance(task, dict):
        return ""
    # try common fields first
    for k in ("task_name","name","title","taskTitle","task"):
        v = task.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, dict):
            # nested task object
            for kk in ("task_name","name","title"):
                vv = v.get(kk)
                if isinstance(vv, str) and vv.strip():
                    return vv
    # scan for any stringy field that looks like a name
    for k, v in task.items():
        if isinstance(v, str) and len(v) > 2 and k.lower() in ("label","summary","description"):
            return v
    return ""


def _candidate_id(task: dict):
    if not isinstance(task, dict):
        return None
    for k in ("id","task_id","pk","uuid","taskId"):
        if k in task:
            return task.get(k)
    # nested
    v = task.get("task")
    if isinstance(v, dict):
        for k in ("id","task_id","pk","uuid"):
            if k in v:
                return v.get(k)
    return None


def _find_task_id(task_name: str, tasks: list):
    # 1) exact/substring match on common fields
    name_raw = (task_name or '').strip()
    name_lc = name_raw.lower()
    best_id = None

    for t in tasks or []:
        tname = _candidate_name(t)
        if not tname:
            continue
        tl = tname.lower().strip()
        if name_lc == tl or name_lc in tl or tl in name_lc:
            return _candidate_id(t)

    # 2) token/Jaccard match ignoring stopwords
    name_tokens = set(_normalize_name(name_raw))
    best_score = 0.0
    for t in tasks or []:
        tname = _candidate_name(t)
        if not tname:
            continue
        t_tokens = set(_normalize_name(tname))
        score = _jaccard(name_tokens, t_tokens)
        # Also favor contains-all behavior for short inputs
        contains_all = name_tokens and name_tokens.issubset(t_tokens)
        if score > best_score or (contains_all and score >= best_score):
            best_score = score
            best_id = _candidate_id(t)
    # reasonable threshold; two strong words like 'ramna' 'park' will match
    if best_score >= 0.35:
        return best_id

    return None


def _motivational(task_name: str, pct: int) -> str:
    remaining=max(0,100-int(pct))
    try:
        prompt=f"""Create a warm motivational message for a mother who has completed {pct}% of '{task_name}'. Mention remaining {remaining}%. End with: Are you feeling tired? Take a break if you need one! 💕"""
        resp=client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role":"user","content":prompt}],
            temperature=0.1,
            max_tokens=160
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        if pct>=100: return f"🌸 Amazing work, mama! You've completed {task_name} 100%! Are you feeling tired? Take a break if you need one! 💕"
        if pct>=75: return f"🌸 You're doing so well! {pct}% done with {task_name}. Only {remaining}% left! Are you feeling tired? Take a break if you need one! 💕"
        if pct>=50: return f"🌸 Great momentum! {pct}% of {task_name} finished. {remaining}% remains. Are you feeling tired? Take a break if you need one! 💕"
        if pct>=25: return f"🌸 Lovely progress! {pct}% of {task_name}. {remaining}% left. Are you feeling tired? Take a break if you need one! 💕"
        return f"🌸 Every step counts! You've started {task_name}. {remaining}% left. Are you feeling tired? Take a break if you need one! 💕"

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_progress(request):
    body=request.data or {}
    user_input=(body.get('user_input') or '').strip()

    # Pep talk follow-up handling (yes/no) if pending
    if user_input.lower() in ['yes','no','y','n'] and request.user.is_authenticated:
        pending=_pep_talk_pending.get(request.user.id)
        if pending:
            audio_url=_generate_audio_url(user_input)
            if user_input.lower() in ['yes','y']:
                # Provide pep talk
                auth=request.META.get('HTTP_AUTHORIZATION','')
                token=auth[7:] if auth.startswith('Bearer ') else None
                pep_url=_fetch_peptalk_voice_url(token)
                # Clear pending after fulfilling
                _pep_talk_pending.pop(request.user.id, None)
                return JsonResponse({
                    "response": "🌸 Enjoy this special pep talk just for you, beautiful mama! 💕✨",
                    "pep_talk": {"url": pep_url},
                    "audio_url": audio_url
                }, status=200)
            else:
                _pep_talk_pending.pop(request.user.id, None)
                return JsonResponse({
                    "response": "That's okay, sweetie. I'm still here to listen and chat with you. 💕",
                    "audio_url": audio_url
                }, status=200)
    # Normal progress flow
    task_name=(body.get('task_name') or '').strip()
    pct=body.get('percentage')
    if user_input and not (task_name and pct is not None):
        d=_extract_progress(user_input)
        task_name=d['task_name']; pct=d['task_percentage']
    if not task_name:
        return JsonResponse({"error":"user_input or task_name required"}, status=400)
    pct=int(pct or 0)

    auth=request.META.get('HTTP_AUTHORIZATION','')
    token=auth[7:] if auth.startswith('Bearer ') else None
    tasks=_get_tasks_from_api(token)
    task_id=_find_task_id(task_name, tasks)
    if task_id:
        try:
            task=Task.objects.filter(id=task_id, created_by=request.user).first()
            if task:
                task.task_percentage=pct; task.save()
        except Exception:
            pass
    msg=_motivational(task_name,pct)

    # Friendly response line
    if pct>=100:
        base_resp="That's wonderful progress, sweetie! Let me celebrate your achievement! ✨"
    elif pct>=50:
        base_resp="Beautiful progress, sweetie! Keep that gentle momentum going! ✨"
    elif pct>0:
        base_resp="Lovely start, sweetie! You're moving forward! ✨"
    else:
        base_resp="Let me record that for you, sweetie! ✨"

    # Set pep talk pending state for follow-up
    _pep_talk_pending[request.user.id] = {"task_name": task_name, "pct": pct}

    audio_url=_generate_audio_url(base_resp)
    return JsonResponse({
        "response": base_resp,
        "progress_summary": {"task_name": task_name, "task_percentage": pct, "id": task_id},
        "motivational_message": msg,
        "pep_talk_offer": "🌸 Do you want to hear a pep talk? 💖 (yes/no)",
        "audio_url": audio_url
    }, status=200)

# --- Task Query (self-contained) ---

def _parse_query_date(text: str):
    t=(text or '').lower()
    today=datetime.today()
    if 'tomorrow' in t:
        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
    return today.strftime('%Y-%m-%d')

def _assignment_filter(text: str):
    t=(text or '').lower()
    if any(w in t for w in ['partner','spouse','husband','wife']): return 'partner'
    if any(w in t for w in ['son','daughter','child','kid','kids']): return 'child'
    if any(w in t for w in ['i ',' my ',"i'm","am i","do i","me "]): return 'self'
    return 'all'

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_query(request):
    body=request.data or {}
    user_input=(body.get('user_input') or '').strip()
    if not user_input:
        return JsonResponse({"error":"user_input is required"}, status=400)

    auth=request.META.get('HTTP_AUTHORIZATION','')
    token=auth[7:] if auth.startswith('Bearer ') else None
    tasks=_get_tasks_from_api(token)
    target=_parse_query_date(user_input)
    who=_assignment_filter(user_input)

    def _match_assignment(v):
        v=(v or 'Self').lower()
        if who=='all': return True
        if who=='self': return v in ['self','me','myself']
        if who=='partner': return v in ['partner','spouse','husband','wife']
        if who=='child': return v in ['child','son','daughter','kid','kids']
        return True

    matches=[]
    for t in tasks:
        if t.get('scheduled_date')==target and _match_assignment(t.get('assigned_to_type')):
            matches.append(t)

    if not matches:
        msg=f"🌸 You're free on {target}. Enjoy some rest! 💕"
    elif len(matches)==1:
        tn=matches[0].get('task_name','a task'); tm=(matches[0].get('scheduled_time') or '').split('.')[0]
        msg=f"🌸 You have {tn}{(' at '+tm) if tm else ''} on {target}. 💕"
    else:
        msg=f"🌸 You have {len(matches)} tasks on {target}. Want details? 💕"

    audio_url=_generate_audio_url(msg)
    return JsonResponse({
        "response": msg,
        "found_tasks": matches,
        "total_tasks": len(matches),
        "query_date": target,
        "assigned_filter": who,
        "audio_url": audio_url
    }, status=200)
