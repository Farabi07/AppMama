import os, re, json, base64, uuid
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI
from task.models import Task
import requests
from datetime import datetime, timedelta

# Self‑contained OpenAI + lightweight intent & emotion detectors (no cross‑file imports)
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
GOOGLE_TTS_API_KEY="AIzaSyC69BVmhR-VUyQqfyCwqFs_NP2Y_0lNgxw"
SCHEDULE_SETTINGS_URL = 'https://api.taskmama.app/task/api/v1/task/all/'
PEPTALK_SETTINGS_URL = 'https://api.taskmama.app/peptalk/api/v1/peptalk/all/'

# In-memory pep talk pending state per user
_pep_talk_pending = {}

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
    except Exception:
        pass
    # Local random pick from media/voices folder
    try:
        import random
        base = getattr(settings, 'BASE_DIR', os.getcwd())
        voices_dir = os.path.join(base, 'media', 'voices')
        if os.path.isdir(voices_dir):
            files = [f for f in os.listdir(voices_dir) if f.lower().endswith('.mp3')]
            if files:
                return f"/media/voices/{random.choice(files)}"
    except Exception:
        pass
    return "/media/voices/default_peptalk.mp3"

# -------------------- Basic Heuristic Detectors --------------------

def _detect_task_planning(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['plan my day','schedule','organize','today\'s tasks','set up tasks','make a schedule','create a plan'])

def _detect_recipe(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['cook','recipe','dinner','breakfast','lunch','snack','meal','what can i make'])

def _detect_progress(text: str) -> bool:
    t=(text or '').lower()
    return any(k in t for k in ['%','percent','completed','finished','done','progress','complete'])

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

# -------------------- Progress-related helpers (from task_progress_views.py) --------------------

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
    
    # Determine the text part that contains the task name
    text_for_task_name = t
    if m: # if we found a percentage like "60%"
        text_for_task_name = t[:m.start()]
    elif m2: # if we found a percentage like "60 percent"
        text_for_task_name = t[:m2.start()]

    # More robustly extract task name
    # First remove action/intent verbs
    split_pat = r"\b(?:completed?|complet|complete|fin+ish(?:ed)?|finish(?:ed)?|done|did|do|have to|need to|must|should|going to|gonna|plan to|try to|update|set|progress of|on)\b"
    
    # Also remove assignment-related words
    assignment_pat = r"\b(?:my|his|her|their|our|i|me|partner|spouse|husband|wife|son|daughter|child|kid|kids)\b"
    
    # Iteratively remove all matching keywords from the string
    cleaned_text = text_for_task_name
    for keyword in re.findall(split_pat, cleaned_text, flags=re.IGNORECASE):
        cleaned_text = re.sub(r'\b' + re.escape(keyword) + r'\b', '', cleaned_text, flags=re.IGNORECASE).strip()
    
    # Remove assignment words
    for keyword in re.findall(assignment_pat, cleaned_text, flags=re.IGNORECASE):
        cleaned_text = re.sub(r'\b' + re.escape(keyword) + r'\b', '', cleaned_text, flags=re.IGNORECASE).strip()
    
    # Clean up extra spaces
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()

    task_name = 'task'
    if cleaned_text:
        task_name = cleaned_text
    elif ' of ' in text_for_task_name:
        task_name = text_for_task_name.split(' of ')[-1].strip()
    else:
        words = re.findall(r"\w+", text_for_task_name)
        task_name = ' '.join(words[-6:]) if words else 'task'
        
    return {"task_name": task_name or 'task', "task_percentage": pct}

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

STOPWORDS = {"the","a","an","to","for","of","my","our","me","have","has","had","need","must","got","get","at","on","in","with","and","meet","meeting","please","make","show","give","do","did","does","is","are","was","were","be","been","being","finish","finished","complete","completed","done","i","we","you","have","has","had","task",
            "partner","spouse","husband","wife","son","daughter","child","kid","kids","self","myself"}

def _normalize_name(s: str):
    s = (s or '').lower()
    s = re.sub(r"[\-_/]", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [w for w in s.split() if w and w not in STOPWORDS]
    # simple stemming for words ending with 'ing'
    tokens = [w[:-3] if w.endswith('ing') and len(w)>5 else w for w in tokens]
    # Typo corrections
    REPL = {
        'grocey':'grocery', 'grocerry':'grocery', 'grocry':'grocery', 'groceries':'grocery',
        'recipy':'recipe', 'reciepe':'recipe',
        'appoinment':'appointment', 'apointment':'appointment', 'appointmant':'appointment',
        'finnish':'finish', 'finsh':'finish', 'finised':'finished', 'complte':'complete', 'complet':'complete',
        'byuing':'buy', 'bying':'buy', 'buyin':'buy', 'buying':'buy',
        'supper':'shop', 'shopp':'shop', 'shoping':'shop'
    }
    tokens = [REPL.get(w, w) for w in tokens]
    return tokens

def _jaccard(a: set, b: set) -> float:
    if not a and not b: return 0.0
    inter = len(a & b)
    union = len(a | b) or 1
    return inter/union

def _candidate_name(task: dict) -> str:
    if not isinstance(task, dict): return ""
    for k in ("task_name","name","title","taskTitle","task"):
        v = task.get(k)
        if isinstance(v, str) and v.strip(): return v
        if isinstance(v, dict):
            for kk in ("task_name","name","title"):
                vv = v.get(kk)
                if isinstance(vv, str) and vv.strip(): return vv
    for k, v in task.items():
        if isinstance(v, str) and len(v) > 2 and k.lower() in ("label","summary"):
            return v
    return ""

def _candidate_description(task: dict) -> str:
    """Extract task description for additional matching context."""
    if not isinstance(task, dict): return ""
    desc = task.get('description', '')
    if isinstance(desc, str) and desc.strip():
        return desc.strip()
    return ""

def _candidate_id(task: dict):
    if not isinstance(task, dict): return None
    for k in ("id","task_id","pk","uuid","taskId"):
        if k in task: return task.get(k)
    v = task.get("task")
    if isinstance(v, dict):
        for k in ("id","task_id","pk","uuid"):
            if k in v: return v.get(k)
    return None

def _slugify(s: str) -> str:
    s = (s or '').lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.replace(' ', '-')

def _assignment_filter(text: str):
    t=(text or '').lower()
    if any(w in t for w in ['partner','spouse','husband','wife']): return 'partner'
    if any(w in t for w in ['son','daughter','child','kid','kids']): return 'child'
    if any(w in t for w in ['i ',' my ','i\'m','am i','do i','me ']): return 'self'
    return 'all'

def _find_task_id(task_name: str, tasks: list, who: str | None = None):
    if who in {"self","partner","child"}:
        tokens = _normalize_name(task_name)
        slug = '-'.join(tokens) if tokens else _slugify(task_name)
        pk_guess = f"{who}:{slug}"
        for t in tasks or []:
            pk = t.get('progress_key') or t.get('progressKey')
            if isinstance(pk, str) and pk.lower() == pk_guess:
                return _candidate_id(t)

    name_raw = (task_name or '').strip()
    name_lc = name_raw.lower()
    
    # Sort tasks by creation date, newest first
    try:
        tasks_sorted = sorted(tasks, key=lambda t: datetime.fromisoformat(t.get('created_at', '1970-01-01T00:00:00Z').replace('Z', '+00:00')), reverse=True)
    except Exception:
        tasks_sorted = tasks # Fallback if created_at is missing/malformed

    # Exact match check on sorted tasks (task_name or description)
    for t in tasks_sorted:
        tname = _candidate_name(t)
        tdesc = _candidate_description(t)
        if tname:
            tl = tname.lower().strip()
            if name_lc == tl or name_lc in tl or tl in name_lc:
                return _candidate_id(t)
        # Also check description for exact matches
        if tdesc:
            dl = tdesc.lower().strip()
            if name_lc in dl or dl in name_lc:
                # Verify this is a strong match by checking token overlap
                name_tokens_set = set(_normalize_name(name_lc))
                desc_tokens_set = set(_normalize_name(dl))
                if name_tokens_set and name_tokens_set.issubset(desc_tokens_set):
                    return _candidate_id(t)

    # Fuzzy match with scoring that considers both name and description
    name_tokens = set(_normalize_name(name_raw))
    best_score = 0.0
    best_id = None
    best_task = None
    
    for t in tasks_sorted:
        tname = _candidate_name(t)
        tdesc = _candidate_description(t)
        
        # Score based on task name
        name_score = 0.0
        if tname:
            t_tokens = set(_normalize_name(tname))
            name_score = _jaccard(name_tokens, t_tokens)
            contains_all = name_tokens and name_tokens.issubset(t_tokens)
            if contains_all:
                name_score = max(name_score, 0.7)  # Boost if all input tokens present
        
        # Score based on description (with lower weight)
        desc_score = 0.0
        if tdesc:
            d_tokens = set(_normalize_name(tdesc))
            desc_jaccard = _jaccard(name_tokens, d_tokens)
            # Extra boost if multiple tokens match in description
            matching_tokens = len(name_tokens & d_tokens)
            if matching_tokens >= 2 and len(name_tokens) >= 2:
                desc_score = desc_jaccard * 0.8  # Higher weight for multi-token match
            else:
                desc_score = desc_jaccard * 0.6  # Normal weight
        
        # Combined score: prioritize name but consider description
        combined_score = max(name_score, desc_score * 0.9)
        
        # Boost score if assignment type matches
        if who and who != 'all':
            assigned_type = (t.get('assigned_to_type') or 'Self').lower()
            type_matches = False
            if who == 'self' and assigned_type in ['self','me','myself']:
                type_matches = True
            elif who == 'partner' and assigned_type in ['partner','spouse','husband','wife']:
                type_matches = True
            elif who == 'child' and assigned_type in ['child','son','daughter','kid','kids']:
                type_matches = True
            
            if type_matches:
                combined_score *= 1.2  # 20% boost for matching assignment type
        
        if combined_score > best_score:
            best_score = combined_score
            best_id = _candidate_id(t)
            best_task = t
            # If we have a very high score on a recent item, we can be confident
            if best_score > 0.85:
                break

    # Lower threshold slightly since we're using more sophisticated scoring
    if best_score >= 0.22:  # Lowered from 0.25 to 0.22
        return best_id
    return None

def _motivational(task_name: str, pct: int) -> str:
    remaining=max(0,100-int(pct))
    try:
        prompt=f"""Create a warm motivational message for a mother who has completed {pct}% of '{task_name}'. Mention remaining {remaining}%. End with: Are you feeling tired? Take a break if you need one! 💕"""
        resp=client.chat.completions.create(model='gpt-4o-mini',messages=[{"role":"user","content":prompt}],temperature=0.1,max_tokens=160)
        return resp.choices[0].message.content.strip()
    except Exception:
        if pct>=100: return f"🌸 Amazing work, mama! You've completed {task_name} 100%! Are you feeling tired? Take a break if you need one! 💕"
        if pct>=75: return f"🌸 You're doing so well! {pct}% done with {task_name}. Only {remaining}% left! Are you feeling tired? Take a break if you need one! 💕"
        if pct>=50: return f"🌸 Great momentum! {pct}% of {task_name} finished. {remaining}% remains. Are you feeling tired? Take a break if you need one! 💕"
        if pct>=25: return f"🌸 Lovely progress! {pct}% of {task_name}. {remaining}% left. Are you feeling tired? Take a break if you need one! 💕"
        return f"🌸 Every step counts! You've started {task_name}. {remaining}% left. Are you feeling tired? Take a break if you need one! 💕"

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
    # Prioritize motivational_message for TTS, then fall back to response or message
    txt=payload.get('motivational_message') or payload.get('response') or payload.get('message') or ''
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
    body=request.data or{}
    user_input=(body.get('user_input') or '').strip()
    if not user_input:
        return JsonResponse({'error':'user_input is required'}, status=400)
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    token = auth_header[7:] if auth_header.startswith('Bearer ') else None
    
    # Pep talk follow-up handling (yes/no) if pending
    if user_input.lower() in ['yes','no','y','n'] and request.user.is_authenticated:
        pending = _pep_talk_pending.get(request.user.id)
        if pending:
            if user_input.lower() in ['yes','y']:
                # Provide pep talk
                pep_url = _fetch_peptalk_voice_url(token)
                # Clear pending after fulfilling
                _pep_talk_pending.pop(request.user.id, None)
                response = {
                    "response": "🌸 Enjoy this special pep talk just for you, beautiful mama! 💕✨",
                    "pep_talk": {"url": pep_url}
                }
                return JsonResponse(_with_tts(response), status=200)
            else:
                _pep_talk_pending.pop(request.user.id, None)
                response = {
                    "response": "That's okay, sweetie. I'm still here to listen and chat with you. 💕"
                }
                return JsonResponse(_with_tts(response), status=200)
    
    # Check if this is a progress update
    if _detect_progress(user_input):
        # --- Inline progress handling (same as handle_task_mama_request) ---
        d = _extract_progress(user_input)
        task_name_from_input, pct = d['task_name'], d['task_percentage']
        
        if not task_name_from_input:
            return JsonResponse({"error":"Could not determine task name for progress update."}, status=400)

        tasks = _get_tasks_from_api(token)
        who = _assignment_filter(user_input or task_name_from_input)
        
        task_id = None
        if who and who != 'all':
            def _match_assignment(v):
                v=(v or 'Self').lower()
                if who=='self': return v in ['self','me','myself']
                if who=='partner': return v in ['partner','spouse','husband','wife']
                if who=='child': return v in ['child','son','daughter','kid','kids']
                return True
            tasks_filtered = [t for t in tasks if _match_assignment(t.get('assigned_to_type'))]
            task_id = _find_task_id(task_name_from_input, tasks_filtered, who if who in {'self','partner','child'} else None)
        else:
            task_id = _find_task_id(task_name_from_input, tasks, None)

        final_task_name = task_name_from_input
        if task_id:
            try:
                task = Task.objects.filter(id=task_id, created_by=request.user).first()
                if task:
                    task.task_percentage = pct
                    task.save()
                    final_task_name = task.task_name # Use canonical name from DB
            except Exception:
                pass # Non-critical DB update
        else:
            # Task not found, inform the user
            response = {
                "response": f"I couldn't quite find a task matching '{task_name_from_input}'. Don't worry, we'll figure it out together. 💖",
                "motivational_message": "Sometimes things get missed, and that's okay. What would you like to do next?",
                "pep_talk_offer": "Would a little pep talk help right now? (yes/no)"
            }
            return JsonResponse(_with_tts(response), status=200)

        msg = _motivational(final_task_name, pct)
        
        if pct >= 100: base_resp = f"That's wonderful! I've marked '{final_task_name}' as complete. Let me celebrate your achievement! ✨"
        elif pct >= 50: base_resp = f"Beautiful progress on '{final_task_name}'! Keep that gentle momentum going! ✨"
        elif pct > 0: base_resp = f"Lovely start on '{final_task_name}'! You're moving forward! ✨"
        else: base_resp = "Let me record that for you, sweetie! ✨"

        # Set pep talk pending state for follow-up
        _pep_talk_pending[request.user.id] = {"task_name": final_task_name, "pct": pct}

        payload = {
            "response": base_resp,
            "progress_summary": {"task_name": final_task_name, "task_percentage": pct, "id": task_id},
            "motivational_message": msg,
            "pep_talk_offer": "🌸 Do you want to hear a pep talk? 💖 (yes/no)",
        }
        return JsonResponse(_with_tts(payload), status=200)
    
    # Lightweight AI response for general chat
    try:
        prompt=f"You are a helpful assistant. Reply briefly and directly to: '{user_input}'. Keep it under 2 sentences. Be helpful and friendly."  # noqa
        resp=client.chat.completions.create(model='gpt-4o-mini',messages=[{"role":"user","content":prompt}],temperature=0.3,max_tokens=100)
        reply=resp.choices[0].message.content.strip()
    except Exception:
        reply="I'm here to help! What can I do for you?"
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
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    token = auth_header[7:] if auth_header.startswith('Bearer ') else None

    # Run detectors
    if _detect_progress(user_input):
        # --- Inline progress handling ---
        d = _extract_progress(user_input)
        task_name_from_input, pct = d['task_name'], d['task_percentage']
        
        if not task_name_from_input:
            return JsonResponse({"error":"Could not determine task name for progress update."}, status=400)

        tasks = _get_tasks_from_api(token)
        who = _assignment_filter(user_input or task_name_from_input)
        
        task_id = None
        if who and who != 'all':
            def _match_assignment(v):
                v=(v or 'Self').lower()
                if who=='self': return v in ['self','me','myself']
                if who=='partner': return v in ['partner','spouse','husband','wife']
                if who=='child': return v in ['child','son','daughter','kid','kids']
                return True
            tasks_filtered = [t for t in tasks if _match_assignment(t.get('assigned_to_type'))]
            task_id = _find_task_id(task_name_from_input, tasks_filtered, who if who in {'self','partner','child'} else None)
        else:
            task_id = _find_task_id(task_name_from_input, tasks, None)

        final_task_name = task_name_from_input
        if task_id:
            try:
                task = Task.objects.filter(id=task_id, created_by=request.user).first()
                if task:
                    task.task_percentage = pct
                    task.save()
                    final_task_name = task.task_name # Use canonical name from DB
            except Exception:
                pass # Non-critical DB update
        else:
            # Task not found, inform the user
            response = {
                "response": f"I couldn't quite find a task matching '{task_name_from_input}'. Don't worry, we'll figure it out together. 💖",
                "motivational_message": "Sometimes things get missed, and that's okay. What would you like to do next?",
                "pep_talk_offer": "Would a little pep talk help right now? (yes/no)"
            }
            return JsonResponse(_with_tts(response), status=200)

        msg = _motivational(final_task_name, pct)
        
        if pct >= 100: base_resp = f"That's wonderful! I've marked '{final_task_name}' as complete. Let me celebrate your achievement! ✨"
        elif pct >= 50: base_resp = f"Beautiful progress on '{final_task_name}'! Keep that gentle momentum going! ✨"
        elif pct > 0: base_resp = f"Lovely start on '{final_task_name}'! You're moving forward! ✨"
        else: base_resp = "Let me record that for you, sweetie! ✨"

        payload = {
            "response": base_resp,
            "progress_summary": {"task_name": final_task_name, "task_percentage": pct, "id": task_id},
            "motivational_message": msg,
            "pep_talk_offer": "🌸 Do you want to hear a pep talk? 💖 (yes/no)",
        }
        return JsonResponse(_with_tts(payload), status=200)

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
        prompt=f"You are a helpful assistant. Reply briefly and directly to: '{user_input}'. Keep it under 2 sentences. Be helpful and friendly."  # noqa
        resp=client.chat.completions.create(model='gpt-4o-mini',messages=[{"role":"user","content":prompt}],temperature=0.3,max_tokens=100)
        reply=resp.choices[0].message.content.strip()
    except Exception:
        reply="I'm here to help! What can I do for you?"
    return JsonResponse(_with_tts({'response':reply}), status=200)
