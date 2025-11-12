import os, json, re
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from openai import OpenAI
from django.utils import timezone
from task.models import Task
from django.conf import settings  # added import for settings access

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Replace hardcoded Google TTS API key with dynamic lookup (settings or env)
GOOGLE_TTS_API_KEY = getattr(settings, 'GOOGLE_API_KEY', None) or os.getenv('GOOGLE_API_KEY')

# Local helpers (no imports from asif_ai)

# --- Simple TTS helper (save MP3 under media/audio) ---
import base64, uuid, requests
# from django.conf import settings  # removed duplicate import

# NEW: Detect natural-language task planning intent ("plan my day", etc.)
def detect_task_planning_request(user_input: str) -> bool:
    """Detect natural-language intent for task planning to trigger prompt phase."""
    if not user_input:
        return False
    text = user_input.lower()
    task_planning_phrases = [
        'plan my day', 'make my schedule', 'create my today\'s plan', 'make my tomorrow\'s plan',
        'give me a schedule', 'make my todays plan', 'give me the task list', 'create my task list',
        'plan my task list', 'help me plan my day', 'organize my day', 'schedule my day',
        'what should i do today', 'plan my tasks', 'organize my tasks', 'create a schedule',
        'help me organize', 'make a plan for', 'daily planning', 'task planning',
        'make my todays schedule', 'make my today schedule', 'make todays schedule',
        'create my todays schedule', 'plan todays schedule', 'organize todays schedule',
        'make my schedule for today', 'create schedule for today', 'plan schedule for today',
        'schedule my today', 'schedule for today', 'todays plan', "today's plan"
    ]
    return any(p in text for p in task_planning_phrases)

def _tts(text: str):
    if not text:
        return None
    try:
        clean = re.sub(r'[^\w\s,.!?-]', '', text)
        # Use dynamic key resolved earlier
        api_key = GOOGLE_TTS_API_KEY
        if not api_key:  # fail fast if missing
            return None
        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        payload = {
            "input": {"text": clean},
            "voice": {"languageCode": "en-US", "name": "en-US-Neural2-F", "ssmlGender": "FEMALE"},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 1.0, "pitch": 0.0}
        }
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers=headers, timeout=15)
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
    text = payload.get('response') or payload.get('message') or ''
    payload['audio_url'] = _tts(text)
    return payload

# --- AI + heuristic task priority analyzer (already present) ---
def _analyze_task_priority(task_description: str, context: str = "") -> dict:
    """Return priority analysis similar to asif_ai DynamicTaskPrioritizer.
    Falls back to heuristic if OpenAI call fails."""
    desc = (task_description or '').strip()
    if not desc:
        return {
            "priority_score": 5.0,
            "priority_level": "Medium Priority",
            "category": "General",
            "reasoning": "Empty description; default medium.",
            "time_flexibility": "flexible",
            "consequences_of_delay": "Medium"
        }
    prompt = f"""
You are a task prioritization assistant for a busy mother.
Analyze this task and return ONLY valid JSON with keys:
priority_score (1-10 float), priority_level (High Priority|Medium Priority|Low Priority), category, reasoning, time_flexibility, consequences_of_delay.

TASK: "{desc}"
CONTEXT: "{context}"
Guidelines:
- High Priority: safety/health, fixed appointments, child school/medical, urgent deadlines.
- Medium Priority: important but movable (shopping, routine chores without urgency).
- Low Priority: leisure, entertainment, non-urgent cleaning, casual social.
Keep reasoning short.
Return ONLY JSON.
"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "Return only JSON."}, {"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=300
        )
        txt = resp.choices[0].message.content.strip()
        if txt.startswith("```json"):
            txt = txt[7:].rstrip('`').strip()
        data = json.loads(txt)
        # basic validation
        lvl = data.get("priority_level", "Medium Priority")
        score = float(data.get("priority_score", 5.0))
        return {
            "priority_score": score,
            "priority_level": lvl,
            "category": data.get("category", "General"),
            "reasoning": data.get("reasoning", "AI analysis"),
            "time_flexibility": data.get("time_flexibility", "flexible"),
            "consequences_of_delay": data.get("consequences_of_delay", "Medium"),
        }
    except Exception:
        # Heuristic fallback
        low_keywords = ["movie", "watch", "friends", "meet friend", "chat", "tv", "game", "entertain"]
        high_keywords = ["doctor", "hospital", "appointment", "school", "deadline", "submit", "medication", "medicine", "pick up", "pickup", "flight"]
        text_l = desc.lower()
        if any(k in text_l for k in high_keywords):
            return {
                "priority_score": 9.0,
                "priority_level": "High Priority",
                "category": "Health/Time-Sensitive",
                "reasoning": "Contains urgent/health/deadline indicators.",
                "time_flexibility": "fixed",
                "consequences_of_delay": "High"
            }
        if any(k in text_l for k in low_keywords):
            return {
                "priority_score": 3.0,
                "priority_level": "Low Priority",
                "category": "Leisure",
                "reasoning": "Leisure/social task.",
                "time_flexibility": "flexible",
                "consequences_of_delay": "Low"
            }
        return {
            "priority_score": 5.0,
            "priority_level": "Medium Priority",
            "category": "General",
            "reasoning": "Default medium priority.",
            "time_flexibility": "flexible",
            "consequences_of_delay": "Medium"
        }

def _to_24h(t: str):
    if not t or t.lower()=="not specified":
        return None
    try:
        if re.match(r'^\d{1,2}:\d{2}', t):
            h,m = t.split(':')[:2]
            h,m = int(h), int(m)
            if 0<=h<=23 and 0<=m<=59:
                return f"{h:02d}:{m:02d}"
        for fmt in ("%I:%M %p","%I%p","%I %p"):
            try:
                return datetime.strptime(t.upper(), fmt).strftime('%H:%M')
            except: pass
        m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', t.lower())
        if m:
            h = int(m.group(1)); mi = int(m.group(2) or 0); p=m.group(3)
            if p=='pm' and h!=12: h+=12
            if p=='am' and h==12: h=0
            return f"{h:02d}:{mi:02d}"
        return t
    except:
        return t

def _extract_tasks(text: str):
    now = datetime.now(); tomorrow = now + timedelta(days=1)
    prompt = f"""
Today is {now.strftime('%A')}, {now.strftime('%Y-%m-%d')}.
Extract ALL actionable, scheduled tasks from the message below.
Return JSON array of objects with keys: 
- task_name: keep a clear description PRESERVING the original language about WHO will do it (e.g., "my partner will buy groceries", "my daughter study for exam", "I have a dentist appointment").
- time: 24h HH:MM or 'Not specified' (convert 3pm->15:00, 9 am->09:00)
- date: YYYY-MM-DD (normalize 'today'/'tomorrow')
- assigned_to: one of Self | Partner | Child (based on the subject in the sentence)
Message: {text}
Only JSON array.
"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"system","content":"Return only valid JSON."},{"role":"user","content":prompt}],
        temperature=0.1,
        max_tokens=900
    )
    s = resp.choices[0].message.content.strip()
    if s.startswith("```json"): s = s[7:].rstrip("`").strip()
    arr = json.loads(s)
    out=set()
    result=[]
    for t in arr:
        d = t.get('date') or now.strftime('%Y-%m-%d')
        if str(d).lower()=='tomorrow': d = tomorrow.strftime('%Y-%m-%d')
        if str(d).lower()=='today': d = now.strftime('%Y-%m-%d')
        tm = _to_24h(t.get('time') or 'Not specified') or None
        name = (t.get('task_name') or '').strip()
        assigned_to = (t.get('assigned_to') or '').strip().lower()
        if assigned_to in ['self','partner','child']:
            assigned_norm = assigned_to
        else:
            assigned_norm = ''
        if not name: 
            continue
        key=(name.lower(), tm or '', d)
        if key in out: 
            continue
        out.add(key)
        result.append({"task_name":name, "date":d, "time": tm, "assigned_to": assigned_norm})
    return result

def _beautify_task_name(name: str) -> str:
    """Make task name short and natural (2-3 words), performer handled by task_assigned."""
    n = (name or '').strip()
    if not n:
        return 'Task'
    txt = re.sub(r'\s+', ' ', n).lower()

    # Remove common lead-ins
    leadins = [
        r"^i have to ", r"^i need to ", r"^i gotta ", r"^i will ", r"^i'm going to ", r"^i have a ",
        r"^my partner (has|have) to ", r"^my partner will ", r"^partner (has|have) to ",
        r"^my (son|daughter|kid|child) (has|have) to ", r"^my (son|daughter|kid|child) will ",
        r"^i ", r"^my ", r"^we need to ", r"^we have to ", r"^we will ",
    ]
    for pat in leadins:
        txt = re.sub(pat, '', txt).strip()

    # Normalize key phrases
    repl = [
        (r"go to (the )?grocery( store)?( to buy (food|items))?", "grocery shopping"),
        (r"buy groceries", "grocery shopping"),
        (r"shopping to buy .*dinner", "dinner shopping"),
        (r"shopping .* dinner", "dinner shopping"),
        (r"buy items to cook dinner", "dinner shopping"),
        (r"cook dinner", "dinner prep"),
        (r"study .*exam", "exam study"),
        (r"study for .*exam", "exam study"),
        (r"dentist appointment", "dentist appointment"),
        (r"doctor appointment", "doctor appointment"),
        (r"hospital appointment|clinic appointment|therapy appointment", "medical appointment"),
    ]
    for pat, rep in repl:
        txt = re.sub(pat, rep, txt)

    # If contains grocery and not shopping, make shopping
    if 'grocery' in txt and 'shopping' not in txt:
        txt = 'grocery shopping'

    # Generic trims
    txt = txt.replace(' to buy ', ' ')
    txt = txt.replace(' for next day\'s ', ' ')
    txt = txt.replace(' for tomorrow\'s ', ' ')

    # Fallbacks for keywords
    if 'dentist' in txt and 'appointment' not in txt:
        txt = 'dentist appointment'
    if 'study' in txt and 'exam' in txt:
        txt = 'exam study'
    if 'shopping' in txt and 'dinner' in txt:
        txt = 'dinner shopping'

    # Keep to max 3 words
    words = [w for w in re.split(r'[^a-z]+', txt) if w]
    if not words:
        words = ['task']
    short = ' '.join(words[:3])
    # Capitalize nicely
    short = short[:1].upper() + short[1:]

    # If still long or unchanged, optionally try AI (best-effort)
    if len(short.split()) > 3:
        short = ' '.join(short.split()[:3])
    return short

def _analyze_task_responsibility(task_description: str) -> str:
    """Detect who will perform the task (Self/Partner/Child) similar to asif_ai logic."""
    text = (task_description or '').lower()
    # Heuristic first with broader synonyms
    if any(k in text for k in [' my husband',' my wife',' spouse',' partner',' my partner']):
        return 'partner'
    if any(k in text for k in [' my son',' my daughter',' child',' kid',' kids',' daughter ',' son ']):
        return 'child'
    if any(k in text for k in [' i ',' i\'m',' i\'ll',' i will',' i have to',' i need to',' my appointment',' i have a']):
        return 'self'
    # AI refinement
    try:
        prompt = (
            f"Who performs this task? Reply with one word: Self, Partner, or Child. Task: '{task_description}'."
        )
        resp = client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[{"role":"user","content":prompt}],
            temperature=0.1,
            max_tokens=5
        )
        ans = resp.choices[0].message.content.strip().lower()
        if 'partner' in ans: return 'partner'
        if 'child' in ans or 'kid' in ans or 'daughter' in ans or 'son' in ans: return 'child'
        return 'self'
    except Exception:
        return 'self'

def _categorize_task(task_description: str) -> str:
    """Categorize task: Health task / Recipy task / Normal task (similar to asif_ai)."""
    text = (task_description or '').lower()
    if any(k in text for k in ['doctor','hospital','clinic','medicine','medication','appointment','therapy','dentist']):
        return 'Health task'
    if any(k in text for k in ['recipe','cook','cooking','bake','meal','dinner','lunch','breakfast','supper','brunch']):
        return 'Recipy task'
    return 'Normal task'

def _save_task(t: dict, user):
    # --- modified: include AI priority analysis + responsibility + category + fluent name ---
    scheduled_date = t.get('date')
    try:
        scheduled_date = datetime.strptime(scheduled_date, '%Y-%m-%d').date()
    except:
        scheduled_date = timezone.now().date()
    scheduled_time = t.get('time') or None
    original_name = t.get('task_name')
    fluent_name = _beautify_task_name(original_name)
    priority_data = _analyze_task_priority(original_name)
    # Prefer assigned_to from extraction
    assigned = (t.get('assigned_to') or '')
    if assigned not in ['self','partner','child']:
        assigned = _analyze_task_responsibility(original_name)
    category = _categorize_task(original_name)
    task = Task.objects.create(
        task_name=fluent_name,
        task_category=category,
        description=original_name,  # store original raw as description
        scheduled_date=scheduled_date,
        scheduled_time=scheduled_time,
        assigned_to_type=assigned,
        priority=priority_data.get('priority_level'),
        created_by=user,
        generated_by_ai=True,
        raw_ai_response={**t, "priority": priority_data, "assigned_to_type": assigned, "category": category, "fluent_name": fluent_name}
    )
    return task

def _make_progress_key(short_name: str, assigned: str) -> str:
    """Stable key to match progress updates: '<assigned>:<slugified-short-name>'"""
    a = (assigned or 'self').lower()
    base = (short_name or 'task').lower()
    slug = re.sub(r'[^a-z0-9]+', '-', base).strip('-')
    return f"{a}:{slug}" if slug else f"{a}:task"

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_step1_ask_tasks(request):
    # If user sends only intent like "plan my day", still return the prompt
    body = request.data or {}
    if detect_task_planning_request((body.get('tasks_text') or body.get('user_input') or '').strip()):
        return JsonResponse(_with_tts({
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.",
        }), status=200)
    return JsonResponse(_with_tts({
        "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you."
    }), status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_step2_generate(request):
    body = request.data or {}
    text = (body.get('tasks_text') or body.get('user_input') or '').strip()
    if not text:
        return JsonResponse({"error":"tasks_text is required"}, status=400)
    tasks = _extract_tasks(text)
    enriched = []
    for t in tasks:
        try:
            assigned_norm = (t.get('assigned_to') or '')
            if assigned_norm not in ['self','partner','child']:
                assigned_norm = _analyze_task_responsibility(t['task_name'])
            short_name = _beautify_task_name(t['task_name'])
            # Ensure assigned_to is set for saver
            t['assigned_to'] = assigned_norm
            created = _save_task(t, request.user)
            pr = _analyze_task_priority(t['task_name'])
            category = _categorize_task(t['task_name'])
            display = {
                "task_id": created.id,
                "task_name": short_name,
                "time": t.get('time'),
                "date": t.get('date'),
                "task_assigned": assigned_norm.capitalize(),
                "priority": pr['priority_level'],
                "task_catagory": category,
                "progress_key": _make_progress_key(short_name, assigned_norm),
            }
            enriched.append(display)
        except Exception:
            enriched.append({
                "task_name": _beautify_task_name(t.get('task_name')), 
                "time": t.get('time'),
                "date": t.get('date'),
                "task_assigned": "Self",
                "priority": "Medium Priority",
                "task_catagory": "Normal task"
            })
    resp = {
        "tasks": enriched,
        "total_tasks": len(enriched),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "message": "🌸 Here is your beautiful task schedule:",
    }
    return JsonResponse(_with_tts(resp), status=200)

@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser])
def api_task_plan_combined(request):
    body = request.data or {}
    text = (body.get('tasks_text') or body.get('user_input') or '').strip()
    if (not text) or (detect_task_planning_request(text)):
        return JsonResponse(_with_tts({
            "type": "task_planning_prompt",
            "response": "I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.",
            "data": {"awaiting_tasks": True, "recognized_intent": bool(text)},
        }), status=200)

    tasks = _extract_tasks(text)
    enriched = []
    for t in tasks:
        try:
            assigned_norm = (t.get('assigned_to') or '')
            if assigned_norm not in ['self','partner','child']:
                assigned_norm = _analyze_task_responsibility(t['task_name'])
            short_name = _beautify_task_name(t['task_name'])
            t['assigned_to'] = assigned_norm
            created = _save_task(t, request.user)
            pr = _analyze_task_priority(t['task_name'])
            category = _categorize_task(t['task_name'])
            display = {
                "task_id": created.id,
                "task_name": short_name,
                "time": t.get('time'),
                "date": t.get('date'),
                "task_assigned": assigned_norm.capitalize(),
                "priority": pr['priority_level'],
                "task_catagory": category,
                "progress_key": _make_progress_key(short_name, assigned_norm),
            }
            enriched.append(display)
        except Exception:
            enriched.append({
                "task_name": _beautify_task_name(t.get('task_name')),
                "time": t.get('time'),
                "date": t.get('date'),
                "task_assigned": "Self",
                "priority": "Medium Priority",
                "task_catagory": "Normal task"
            })
    resp = {
        "type": "task_plan",
        "tasks": enriched,
        "total_tasks": len(enriched),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        "message": "🌸 Here is your beautiful task schedule:",
    }
    return JsonResponse(_with_tts(resp), status=200)
