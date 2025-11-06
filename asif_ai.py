# 🌸 Task Mama - Complete Mother-Focused AI Assistant
# Features: Natural Conversations, Emotional Support, Task Management, Recipe Suggestions, Text Input, Progress Tracking

import os
from dotenv import load_dotenv

# Load environment variables from .env file FIRST
load_dotenv()

from openai import OpenAI
import openai
import requests
import random
import time
import json
import warnings
import sys
from datetime import datetime, timedelta
import re
import tempfile

warnings.filterwarnings("ignore")

# 🔑 Initialize OpenAI client
# API key loaded from .env file
OPENAI_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_KEY:
    raise RuntimeError("OpenAI API key not found. Please set OPENAI_API_KEY in your .env file.")

client = OpenAI(api_key=OPENAI_KEY)

# --- Session and OpenAI wrapper utilities ---
# Use per-session conversation history to avoid cross-user leakage.
_session_histories = {}

def get_session_history(session_id):
    """Return a list of messages for the given session_id. Initialize if missing."""
    if not session_id:
        # fallback to a single global history for backward compatibility
        session_id = "__global__"
    if session_id not in _session_histories:
        # Initialize with system persona
        _session_histories[session_id] = [
            {
                "role": "system",
                "content": (
                    "You are Task Mama, a gentle, caring AI assistant specifically designed for mothers. "
                    "Speak with a warm, soft, caring voice like a supportive friend. Use nurturing language and emojis."
                )
            }
        ]
    return _session_histories[session_id]

def reset_session_history(session_id):
    if not session_id:
        session_id = "__global__"
    if session_id in _session_histories:
        del _session_histories[session_id]

def openai_chat(messages, *, model="gpt-4o-mini", max_tokens=300, temperature=0.1, seed=None):
    """Central wrapper for OpenAI chat completions.

    - temperature: by default 0.1 (deterministic). Use 0.5 when creativity desired.
    - seed: if provided, include it as a deterministic hint to the model (best-effort).
    Returns the assistant message string.
    """
    # Build kwargs for API call
    call_kwargs = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": float(temperature)
    }
    # Some SDKs accept `seed` or `user` fields; add as metadata if accepted
    if seed is not None:
        # include seed in a system message to help make output deterministic across calls
        messages = [m for m in messages]
        messages.insert(0, {"role": "system", "content": f"seed:{seed}"})
        call_kwargs["messages"] = messages

    resp = client.chat.completions.create(**call_kwargs)
    return resp.choices[0].message.content


# ⭐ NEW FEATURE: API Configuration for Schedule Settings
SCHEDULE_SETTINGS_URL = 'https://api.taskmama.app/task/api/v1/task/all/'
SCHEDULE_BEARER_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzYwODIzNTY0LCJpYXQiOjE3NjAyMTg3NjQsImp0aSI6IjUyOGU1ZjA3NTVlNDQzMWY4NTgxNWE3YTZmNmY4YTMwIiwidXNlcl9pZCI6M30.uVNzy5TRhWY2gID8XVvLp9_RSaz4QmPoEOgqwsX_qdM'

# ⭐ NEW FEATURE: Peptalk API Configuration
PEPTALK_SETTINGS_URL = 'https://api.taskmama.app/peptalk/api/v1/peptalk/all/'

def get_peptalk_voice_url():
    """Fetch peptalk voice URL from the API"""
    try:
        response = requests.get(PEPTALK_SETTINGS_URL)
        if response.status_code == 200:
            data = response.json()
            # New expected shape: { "peptalks": [ { "title": "emotion3", "items": [ {.., "voice": "/media/voices/...mp3"}, ... ] }, ... ] }
            # Backwards compatible: some responses might use 'cities' or other keys.
            groups = []
            if isinstance(data, dict):
                if 'peptalks' in data and isinstance(data['peptalks'], list):
                    groups = data['peptalks']
                elif 'cities' in data and isinstance(data['cities'], list):
                    # older format
                    groups = data['cities']
                elif isinstance(data.get('results'), list):
                    groups = data.get('results')
                else:
                    # try to find any top-level list of groups
                    for v in data.values():
                        if isinstance(v, list):
                            groups = v
                            break

            if not groups:
                print("❌ No peptalk groups found in API response.")
                return None

            # Build mapping: title -> list of voice urls
            group_map = {}
            total_items = 0
            for g in groups:
                title = g.get('title') or g.get('name') or g.get('label') or 'unknown'
                items = g.get('items') or g.get('voices') or g.get('children') or []
                voice_list = []
                if isinstance(items, list):
                    for it in items:
                        # item can be a string or dict containing 'voice' or 'url'
                        if isinstance(it, dict):
                            v = it.get('voice') or it.get('url') or it.get('audio') or ''
                        else:
                            v = str(it)
                        if v:
                            voice_list.append(v)
                if voice_list:
                    group_map[str(title).lower()] = voice_list
                    total_items += len(voice_list)

            if not group_map:
                print("❌ No voice URLs found in peptalk groups")
                return None

            # Choose a random group, then random voice inside it (caller may filter by emotion class later)
            # For backward compatibility with earlier usage, just return a random voice across all groups
            all_voices = []
            for vs in group_map.values():
                all_voices.extend(vs)
            if not all_voices:
                print("❌ No voice URLs available after parsing groups")
                return None

            selected_url = random.choice(all_voices)
            filename = os.path.basename(selected_url)
            formatted_url = f"/media/voices/{filename}"
            print(f"✅ Retrieved peptalks: {len(group_map)} groups, {total_items} items total. Returning a random voice.")
            return formatted_url
        else:
            print(f"❌ Failed to retrieve peptalk entries. HTTP Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching peptalk settings: {e}")
        return None


def get_peptalk_voice_url_by_emotion(emotion_title=None):
    """Fetch a peptalk voice URL for a specific emotion class (e.g. 'emotion1', 'emotion2').

    If emotion_title is None or not found, falls back to a random voice across all groups.
    """
    try:
        response = requests.get(PEPTALK_SETTINGS_URL)
        if response.status_code != 200:
            print(f"❌ Failed to retrieve peptalk entries. HTTP Status Code: {response.status_code}")
            return None

        data = response.json()
        groups = []
        if isinstance(data, dict):
            if 'peptalks' in data and isinstance(data['peptalks'], list):
                groups = data['peptalks']
            elif 'cities' in data and isinstance(data['cities'], list):
                groups = data['cities']
            elif isinstance(data.get('results'), list):
                groups = data.get('results')
            else:
                for v in data.values():
                    if isinstance(v, list):
                        groups = v
                        break

        if not groups:
            print("❌ No peptalk groups found in API response.")
            return None

        # Build map: normalized title -> list of voice urls
        group_map = {}
        for g in groups:
            title = g.get('title') or g.get('name') or g.get('label') or 'unknown'
            items = g.get('items') or g.get('voices') or g.get('children') or []
            voice_list = []
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        v = it.get('voice') or it.get('url') or it.get('audio') or ''
                    else:
                        v = str(it)
                    if v:
                        voice_list.append(v)
            if voice_list:
                group_map[str(title).lower()] = voice_list

        if not group_map:
            print("❌ No voice URLs found in peptalk groups")
            return None

        # If emotion_title provided, try to match it to a group
        if emotion_title:
            key = emotion_title.lower().strip()
            # direct match
            if key in group_map and group_map[key]:
                selected_url = random.choice(group_map[key])
                filename = os.path.basename(selected_url)
                return f"/media/voices/{filename}"
            # partial match heuristic
            for k, vs in group_map.items():
                if key in k or k in key:
                    if vs:
                        selected_url = random.choice(vs)
                        filename = os.path.basename(selected_url)
                        return f"/media/voices/{filename}"

        # Fallback: choose any random voice across all groups
        all_voices = []
        for vs in group_map.values():
            all_voices.extend(vs)
        if not all_voices:
            print("❌ No voice URLs available after parsing groups")
            return None

        selected_url = random.choice(all_voices)
        filename = os.path.basename(selected_url)
        return f"/media/voices/{filename}"
    except Exception as e:
        print(f"❌ Error fetching peptalk settings: {e}")
        return None


def generate_motivational_message_canonical(task_name, percentage, *, session_id=None, seed=None):
    """Canonical motivational message generator used across the codebase.

    - Uses the central openai_chat wrapper when available (respects seed).
    - Default deterministic temperature is applied in the wrapper; this function
      requests a low temperature for consistent responses.
    - Falls back to hard-coded friendly messages if AI call fails.
    """
    try:
        remaining_percentage = max(0, 100 - int(percentage or 0))
        prompt = f"""
Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".

The message should:
1. Acknowledge their progress positively
2. Mention how much is left ({remaining_percentage}%)
3. Be encouraging and supportive
4. Use caring language with emojis like 💕, 🌸, ✨
5. Sound like a supportive friend
6. Be 2-3 sentences long
7. ALWAYS include a caring question about feeling tired and suggest taking a break

IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕"
"""
        messages = [{"role": "user", "content": prompt}]
        # Use deterministic low-temperature by default via the wrapper
        text = openai_chat(messages, max_tokens=200, temperature=0.1, seed=seed)
        return text.strip()
    except Exception as e:
        # Preserve the existing fallback messages (keeps user-facing behavior unchanged)
        try:
            percentage_int = int(percentage)
        except Exception:
            percentage_int = 0
        remaining = max(0, 100 - percentage_int)
        if percentage_int >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage_int >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage_int}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage_int >= 50:
            return f"🌸 Look at you go, mama! You're {percentage_int}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage_int >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage_int}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

def generate_motivational_message(task_name, percentage, *, session_id=None, seed=None):
    """Generate motivational message based on task progress. Uses deterministic low-temp by default.

    Parameters:
    - task_name: str
    - percentage: int
    - session_id: optional session id for history context
    - seed: optional seed to stabilize outputs
    """
    remaining_percentage = max(0, 100 - int(percentage or 0))
    prompt = f"""
Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".

The message should:
1. Acknowledge their progress positively
2. Mention how much is left ({remaining_percentage}%)
3. Be encouraging and supportive
4. Use caring language with emojis like 💕, 🌸, ✨
5. Sound like a supportive friend
6. Be 2-3 sentences long
7. ALWAYS include a caring question about feeling tired and suggest taking a break

IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕"
"""
    try:
        messages = [{"role": "user", "content": prompt}]
        # deterministic by default
        text = openai_chat(messages, max_tokens=200, temperature=0.1, seed=seed)
        return text.strip()
    except Exception as e:
        # fallback
        remaining = remaining_percentage
        if percentage >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage >= 50:
            return f"🌸 Look at you go, mama! You're {percentage}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

# ⭐ NEW FEATURE: Find task ID from database
def find_task_id_from_database(task_name):
    """Find the task ID from the database using the task name.

    Tries exact/partial matching first, then a single AI fuzzy attempt.
    """
    try:
        tasks = get_schedule_settings()
        if not tasks:
            return None
        user_task_name = (task_name or "").lower().strip()
        for task in tasks:
            db_task_name = (task.get("task_name", "") or "").lower().strip()
            if not db_task_name:
                continue
            if user_task_name == db_task_name or user_task_name in db_task_name or db_task_name in user_task_name:
                return task.get("id")
        return find_task_id_with_ai(task_name, tasks)
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return None

def find_task_id_with_ai(user_task_name, tasks, *, seed=None):
    try:
        task_list = []
        for task in tasks:
            task_list.append({
                "id": task.get("id"),
                "name": task.get("task_name", ""),
                "date": task.get("scheduled_date", ""),
                "time": task.get("scheduled_time", "")
            })
        prompt = (
            f"Find the most similar task from the database that matches the user's task.\n"
            f"User's task: \"{user_task_name}\"\n"
            f"Available tasks: {json.dumps(task_list, ensure_ascii=False, indent=2)}\n"
            "Return ONLY the ID number of the most similar task, or null."
        )
        text = openai_chat([{"role": "user", "content": prompt}], max_tokens=40, temperature=0.1, seed=seed)
        result = text.strip()
        try:
            return int(result) if result.lower() != "null" else None
        except:
            return None
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return None


# --- Small helper utilities restored after deduplication ---
def get_schedule_settings():
    """Fetch schedule/task settings from configured API. Returns a list of task dicts or empty list on failure."""
    try:
        headers = {"Authorization": f"Bearer {SCHEDULE_BEARER_TOKEN}"} if SCHEDULE_BEARER_TOKEN else {}
        resp = requests.get(SCHEDULE_SETTINGS_URL, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            # Common shapes: list, {results: [...]}, {tasks: [...]}, {data: [...]}
            if isinstance(data, list):
                return data
            if isinstance(data, dict):
                for key in ("results", "tasks", "data", "items"):
                    if key in data and isinstance(data[key], list):
                        return data[key]
                # fallback: return any top-level list value
                for v in data.values():
                    if isinstance(v, list):
                        return v
        return []
    except Exception:
        return []


def get_user_input():
    """Unified user input helper used by interactive chat flows.

    Returns (text, status) where status is one of: 'ok', 'empty', 'interrupted'.
    """
    try:
        # interactive preferred
        if os.isatty(0):
            text = input("You: ").strip()
            if text == "":
                return "", "empty"
            return text, "ok"
        # non-interactive: try to read one line from stdin
        line = sys.stdin.readline()
        if not line:
            return "", "empty"
        text = line.strip()
        return text, "ok" if text else ("", "empty")
    except KeyboardInterrupt:
        return "", "interrupted"
    except Exception:
        return "", "empty"


def detect_task_progress_update(user_input):
    """Heuristic detection for task progress updates (e.g., "I completed 50% of washing dishes")."""
    if not user_input:
        return False
    text = user_input.lower()
    if re.search(r"\d+%", text):
        return True
    # phrases indicating completion with numbers
    if any(w in text for w in ["completed", "finished", "i did", "i've done", "i have done", "done"]):
        if re.search(r"\d+", text):
            return True
    return False


def extract_task_progress(user_input):
    """Extract a best-effort task name and percentage from free text.

    Returns dict: { 'task_name': str, 'task_percentage': int }
    """
    text = (user_input or "").strip()
    pct = None
    # look for explicit percent like '50%'
    m = re.search(r"(\d{1,3})\s*%", text)
    if m:
        try:
            pct = int(m.group(1))
        except Exception:
            pct = None

    # word-based fractions
    if pct is None:
        if "half" in text:
            pct = 50
        elif "quarter" in text:
            pct = 25
        elif "third" in text:
            pct = 33

    if pct is None:
        # look for plain numbers like 'I did 30 of the task' or 'did 30 percent'
        m2 = re.search(r"(\d{1,3})\s*(percent|percent\b|pct|percent\.)?", text)
        if m2:
            try:
                pct = int(m2.group(1))
            except Exception:
                pct = None

    if pct is None:
        pct = 0

    # Extract task name: prefer phrase after 'of' before percentage, or after 'completed'
    task_name = "task"
    # Try pattern: '... X% of TASK'
    if m:
        before = text[:m.start()]
        if " of " in before:
            candidate = before.split(" of ")[-1]
            task_name = candidate.strip()
        elif "completed " in before:
            candidate = before.split("completed ")[-1]
            task_name = candidate.strip()
        else:
            # take last up to 6 words before percent
            tokens = re.findall(r"\w+", before)
            task_name = " ".join(tokens[-6:]) if tokens else "task"
    else:
        # no percent, try after 'completed'
        if "completed " in text:
            candidate = text.split("completed ", 1)[1]
            task_name = candidate.strip().split(" ")[:6]
            task_name = " ".join(task_name).rstrip('.,!?')
        else:
            # fallback: first 6 words
            tokens = re.findall(r"\w+", text)
            task_name = " ".join(tokens[:6]) if tokens else "task"

    # Clean punctuation
    task_name = re.sub(r"[\n\r]+", " ", task_name).strip()
    task_name = task_name.strip().rstrip('.,!?')

    try:
        pct = int(max(0, min(100, int(pct))))
    except Exception:
        pct = 0

    return {"task_name": task_name if task_name else "task", "task_percentage": pct}


def classify_user_emotion_to_peptalk_class(user_input, detected):
    """Map detected emotion dictionary to a peptalk class label (emotion1..emotion4)."""
    if isinstance(detected, dict):
        primary = detected.get('primary_emotion') or detected.get('primary')
        if primary in ('emotion1', 'emotion2', 'emotion3', 'emotion4'):
            return primary
        # fallback based on flags
        if detected.get('is_emotion3') or detected.get('is_happy'):
            return 'emotion3'
        if detected.get('is_emotion4') or detected.get('is_overwhelmed') or detected.get('is_stressed'):
            return 'emotion4'
        if detected.get('is_emotion2') or detected.get('is_sad'):
            return 'emotion2'
    # final fallback
    return 'emotion3'


# Note: removed repeated duplicate definitions of generate_motivational_message,
# find_task_id_from_database, and find_task_id_with_ai. The canonical
# implementations defined earlier (including generate_motivational_message_canonical)
# are preserved and the public name `generate_motivational_message` will be bound
# to the canonical implementation at the end of the file as intended.

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
# ⭐ NEW FEATURE: Find task ID from database
# Subsequent duplicates removed; earlier canonical implementations are retained.

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
def generate_motivational_message(task_name, percentage):
    """Generate motivational message based on task progress - ENHANCED with tired check"""
    try:
        remaining_percentage = 100 - percentage
        
        prompt = f"""
        Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".
        
        The message should:
        1. Acknowledge their progress positively
        2. Mention how much is left ({remaining_percentage}%)
        3. Be encouraging and supportive
        4. Use caring language with emojis like 💕, 🌸, ✨
        5. Sound like a supportive friend
        6. Be 2-3 sentences long
        7. ALWAYS include a caring question about feeling tired and suggest taking a break
        
        Task: {task_name}
        Progress: {percentage}%
        Remaining: {remaining_percentage}%
        
        IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕" or similar caring message about rest.
        
        Create a motivational message that celebrates their achievement and encourages them to continue while caring about their wellbeing.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating motivational message: {e}")
        # Fallback motivational messages with tired check
        remaining = 100 - percentage
        if percentage >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage >= 50:
            return f"🌸 Look at you go, mama! You're {percentage}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

# ⭐ NEW FEATURE: Find task ID from database
def find_task_id_from_database(task_name):
    """Find the task ID from the database using the task name"""
    try:
        # Get all tasks from API
        tasks = get_schedule_settings()
        if not tasks:
            return None
        
        # Search for matching task name
        for task in tasks:
            db_task_name = task.get("task_name", "").lower().strip()
            user_task_name = task_name.lower().strip()
            
            # Check for exact match or partial match
            if (user_task_name in db_task_name or 
                db_task_name in user_task_name or
                user_task_name == db_task_name):
                return task.get("id")
        
        # If no match found, try fuzzy matching using AI
        return find_task_id_with_ai(task_name, tasks)
        
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return None

def find_task_id_with_ai(user_task_name, tasks):
    """Use AI to find the most similar task from database"""
    try:
        task_list = []
        for task in tasks:
            task_info = {
                "id": task.get("id"),
                "name": task.get("task_name", ""),
                "date": task.get("scheduled_date", ""),
                "time": task.get("scheduled_time", "")
            }
            task_list.append(task_info)
        
        prompt = f"""
        Find the most similar task from the database that matches the user's task.
        
        Return only the ID number of the most similar task, or null.
        """
        text = openai_chat([{"role": "user", "content": prompt}], max_tokens=40, temperature=0.1)
        result = text.strip()
        try:
            return int(result) if result.lower() != "null" else None
        except:
            return None
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return None

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
# Subsequent duplicates removed; canonical implementations above are retained.

# ⭐ NEW FEATURE: Find task ID from database
def find_task_id_from_database(task_name):
    """Find the task ID from the database using the task name"""
    try:
        # Get all tasks from API
        tasks = get_schedule_settings()
        if not tasks:
            return None
        
        # Search for matching task name
        for task in tasks:
            db_task_name = task.get("task_name", "").lower().strip()
            user_task_name = task_name.lower().strip()
            
            # Check for exact match or partial match
            if (user_task_name in db_task_name or 
                db_task_name in user_task_name or
                user_task_name == db_task_name):
                return task.get("id")
        
        # If no match found, try fuzzy matching using AI
        return find_task_id_with_ai(task_name, tasks)
        
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return None

def find_task_id_with_ai(user_task_name, tasks):
    """Use AI to find the most similar task from database"""
    try:
        task_list = []
        for task in tasks:
            task_info = {
                "id": task.get("id"),
                "name": task.get("task_name", ""),
                "date": task.get("scheduled_date", ""),
                "time": task.get("scheduled_time", "")
            }
            task_list.append(task_info)
        
        prompt = f"""
        Find the most similar task from the database that matches the user's task.
        
        User's task: "{user_task_name}"
        
        Available tasks in database:
        {json.dumps(task_list, indent=2)}
        
        Return ONLY the task ID (number) of the most similar task.
        If no similar task found, return null.
        
        Consider variations like:
        - "playing football" matches "football match" or "football game"
        - "cleaning kitchen" matches "kitchen cleaning"
        - "studying" matches "homework" or "study session"
        
        Return only the ID number or null.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # Try to parse as integer
        try:
            return int(result) if result.lower() != "null" else None
        except:
            return None
            
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return None

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
def generate_motivational_message(task_name, percentage):
    """Generate motivational message based on task progress - ENHANCED with tired check"""
    try:
        remaining_percentage = 100 - percentage
        
        prompt = f"""
        Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".
        
        The message should:
        1. Acknowledge their progress positively
        2. Mention how much is left ({remaining_percentage}%)
        3. Be encouraging and supportive
        4. Use caring language with emojis like 💕, 🌸, ✨
        5. Sound like a supportive friend
        6. Be 2-3 sentences long
        7. ALWAYS include a caring question about feeling tired and suggest taking a break
        
        Task: {task_name}
        Progress: {percentage}%
        Remaining: {remaining_percentage}%
        
        IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕" or similar caring message about rest.
        
        Create a motivational message that celebrates their achievement and encourages them to continue while caring about their wellbeing.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating motivational message: {e}")
        # Fallback motivational messages with tired check
        remaining = 100 - percentage
        if percentage >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage >= 50:
            return f"🌸 Look at you go, mama! You're {percentage}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

# ⭐ NEW FEATURE: Find task ID from database
def find_task_id_from_database(task_name):
    """Find the task ID from the database using the task name"""
    try:
        # Get all tasks from API
        tasks = get_schedule_settings()
        if not tasks:
            return None
        
        # Search for matching task name
        for task in tasks:
            db_task_name = task.get("task_name", "").lower().strip()
            user_task_name = task_name.lower().strip()
            
            # Check for exact match or partial match
            if (user_task_name in db_task_name or 
                db_task_name in user_task_name or
                user_task_name == db_task_name):
                return task.get("id")
        
        # If no match found, try fuzzy matching using AI
        return find_task_id_with_ai(task_name, tasks)
        
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return None

def find_task_id_with_ai(user_task_name, tasks):
    """Use AI to find the most similar task from database"""
    try:
        task_list = []
        for task in tasks:
            task_info = {
                "id": task.get("id"),
                "name": task.get("task_name", ""),
                "date": task.get("scheduled_date", ""),
                "time": task.get("scheduled_time", "")
            }
            task_list.append(task_info)
        
        prompt = f"""
        Find the most similar task from the database that matches the user's task.
        
        User's task: "{user_task_name}"
        
        Available tasks in database:
        {json.dumps(task_list, indent=2)}
        
        Return ONLY the task ID (number) of the most similar task.
        If no similar task found, return null.
        
        Consider variations like:
        - "playing football" matches "football match" or "football game"
        - "cleaning kitchen" matches "kitchen cleaning"
        - "studying" matches "homework" or "study session"
        
        Return only the ID number or null.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # Try to parse as integer
        try:
            return int(result) if result.lower() != "null" else None
        except:
            return None
            
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return None

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
def generate_motivational_message(task_name, percentage):
    """Generate motivational message based on task progress - ENHANCED with tired check"""
    try:
        remaining_percentage = 100 - percentage
        
        prompt = f"""
        Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".
        
        The message should:
        1. Acknowledge their progress positively
        2. Mention how much is left ({remaining_percentage}%)
        3. Be encouraging and supportive
        4. Use caring language with emojis like 💕, 🌸, ✨
        5. Sound like a supportive friend
        6. Be 2-3 sentences long
        7. ALWAYS include a caring question about feeling tired and suggest taking a break
        
        Task: {task_name}
        Progress: {percentage}%
        Remaining: {remaining_percentage}%
        
        IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕" or similar caring message about rest.
        
        Create a motivational message that celebrates their achievement and encourages them to continue while caring about their wellbeing.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating motivational message: {e}")
        # Fallback motivational messages with tired check
        remaining = 100 - percentage
        if percentage >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage >= 50:
            return f"🌸 Look at you go, mama! You're {percentage}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

# ⭐ NEW FEATURE: Find task ID from database
def find_task_id_from_database(task_name):
    """Find the task ID from the database using the task name"""
    try:
        # Get all tasks from API
        tasks = get_schedule_settings()
        if not tasks:
            return None
        
        # Search for matching task name
        for task in tasks:
            db_task_name = task.get("task_name", "").lower().strip()
            user_task_name = task_name.lower().strip()
            
            # Check for exact match or partial match
            if (user_task_name in db_task_name or 
                db_task_name in user_task_name or
                user_task_name == db_task_name):
                return task.get("id")
        
        # If no match found, try fuzzy matching using AI
        return find_task_id_with_ai(task_name, tasks)
        
    except Exception as e:
        print(f"Error finding task ID: {e}")
        return None

def find_task_id_with_ai(user_task_name, tasks):
    """Use AI to find the most similar task from database"""
    try:
        task_list = []
        for task in tasks:
            task_info = {
                "id": task.get("id"),
                "name": task.get("task_name", ""),
                "date": task.get("scheduled_date", ""),
                "time": task.get("scheduled_time", "")
            }
            task_list.append(task_info)
        
        prompt = f"""
        Find the most similar task from the database that matches the user's task.
        
        User's task: "{user_task_name}"
        
        Available tasks in database:
        {json.dumps(task_list, indent=2)}
        
        Return ONLY the task ID (number) of the most similar task.
        If no similar task found, return null.
        
        Consider variations like:
        - "playing football" matches "football match" or "football game"
        - "cleaning kitchen" matches "kitchen cleaning"
        - "studying" matches "homework" or "study session"
        
        Return only the ID number or null.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=20,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip()
        
        # Try to parse as integer
        try:
            return int(result) if result.lower() != "null" else None
        except:
            return None
            
    except Exception as e:
        print(f"Error in AI task matching: {e}")
        return None

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
# Duplicates removed — canonical implementations above are retained.

# ⭐ MODIFIED: Enhanced motivational message with "feeling tired" check
def generate_motivational_message(task_name, percentage):
    """Generate motivational message based on task progress - ENHANCED with tired check"""
    try:
        remaining_percentage = 100 - percentage
        
        prompt = f"""
        Create a warm, motivational message for a mother who has completed {percentage}% of "{task_name}".
        
        The message should:
        1. Acknowledge their progress positively
        2. Mention how much is left ({remaining_percentage}%)
        3. Be encouraging and supportive
        4. Use caring language with emojis like 💕, 🌸, ✨
        5. Sound like a supportive friend
        6. Be 2-3 sentences long
        7. ALWAYS include a caring question about feeling tired and suggest taking a break
        
        Task: {task_name}
        Progress: {percentage}%
        Remaining: {remaining_percentage}%
        
        IMPORTANT: Always end with something like "Are you feeling tired? Take a break if you need one! 💕" or similar caring message about rest.
        
        Create a motivational message that celebrates their achievement and encourages them to continue while caring about their wellbeing.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.1
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating motivational message: {e}")
        # Fallback motivational messages with tired check
        remaining = 100 - percentage
        if percentage >= 100:
            return f"🌸 Amazing work, mama! You've completed {task_name} 100%! You're absolutely incredible! 💕✨ Are you feeling tired? You deserve a good rest now! 🤗"
        elif percentage >= 75:
            return f"🌸 You're doing so well, beautiful mama! You've finished {percentage}% of {task_name} - only {remaining}% left to go! You've got this! 💕 Are you feeling tired? Take a break if you need one! 🌸"
        elif percentage >= 50:
            return f"🌸 Look at you go, mama! You're {percentage}% done with {task_name} - you're more than halfway there! Just {remaining}% remaining! 🌸💕 Are you feeling tired? Take a break if you need one! 🤗"
        elif percentage >= 25:
            return f"🌸 Great progress, sweetie! You've completed {percentage}% of {task_name}. Keep going - you have {remaining}% left and I believe in you! 💖 Are you feeling tired? Take a break if you need one! 💕"
        else:
            return f"🌸 Every step counts, beautiful mama! You've started {task_name} and that's wonderful! You have {remaining}% left, but you're already on your way! 💕 Are you feeling tired? Take a break if you need one! 🤗"

# 🎭 Enhanced Emotion Detection - UPDATED to detect all 4 emotion categories
def analyze_mama_emotions(user_input, *, seed=None):
    """Analyze mama's emotions. Uses a deterministic low-temp call; falls back to keyword detection."""
    prompt = (
        "Analyze the following message for emotional indicators and return a JSON object with keys: "
        "is_emotion1, is_emotion2, is_emotion3, is_emotion4, primary_emotion, confidence.\nMessage: " + user_input
    )
    try:
        text = openai_chat([{"role": "user", "content": prompt}], max_tokens=150, temperature=0.0, seed=seed)
        try:
            emotions = json.loads(text)
        except Exception:
            emotions = detect_emotions_by_keywords_updated(user_input)
        # Ensure legacy keys exist
        emotions.setdefault('is_sad', emotions.get('is_emotion2', False))
        emotions.setdefault('is_overwhelmed', emotions.get('is_emotion4', False))
        emotions.setdefault('is_happy', emotions.get('is_emotion3', False))
        emotions.setdefault('is_stressed', emotions.get('is_emotion4', False))
        return emotions
    except Exception as e:
        print(f"Emotion analysis error: {e}")
        return detect_emotions_by_keywords_updated(user_input)

def detect_emotions_by_keywords_updated(user_input):
    """Updated keyword-based emotion detection for all 4 emotion categories - ENHANCED for robustness"""
    text = user_input.lower()
    
    # Emotion 1: guilty, exhausted, feeling behind, self critical, pressured - EXPANDED
    emo1_keywords = [
        'guilty', 'guilt', 'feel guilty', 'feeling guilty', 'i feel guilty',
        'exhausted', 'feel exhausted', 'feeling exhausted', 'i feel exhausted', 'so exhausted',
        'feeling behind', 'behind schedule', 'running behind', 'fall behind', 'falling behind',
        'not doing enough', 'not good enough', 'not enough', 'dont do enough', 'don\'t do enough',
        'self critical', 'self-critical', 'criticizing myself', 'critical of myself',
        'pressured', 'under pressure', 'feel pressured', 'feeling pressured', 'too much pressure',
        'failing', 'feel like failing', 'feeling like a failure', 'failure as', 'fail at',
        'not measuring up', 'falling short', 'inadequate', 'insufficient'
    ]
    is_emotion1 = any(keyword in text for keyword in emo1_keywords)
    
    # Emotion 2: sad, insecure, self-doubting, lost, unappreciated, unseen, unworthy - EXPANDED  
    emo2_keywords = [
        'sad', 'sadness', 'feel sad', 'feeling sad', 'i feel sad', 'so sad', 'really sad',
        'insecure', 'insecurity', 'feel insecure', 'feeling insecure', 'i feel insecure',
        'self-doubt', 'self doubt', 'self-doubting', 'self doubting', 'doubt myself', 'doubting myself',
        'lost', 'feel lost', 'feeling lost', 'i feel lost', 'so lost', 'completely lost',
        'unappreciated', 'not appreciated', 'feel unappreciated', 'feeling unappreciated',
        'unseen', 'invisible', 'feel invisible', 'feeling invisible', 'no one sees me',
        'unworthy', 'not worthy', 'feel unworthy', 'feeling unworthy', 'i feel unworthy',
        'worthless', 'feel worthless', 'feeling worthless', 'i feel worthless',
        'nobody cares', 'no one cares', 'no one understands', 'alone', 'lonely',
        'rejected', 'unwanted', 'unloved', 'not loved', 'not enough'
    ]
    is_emotion2 = any(keyword in text for keyword in emo2_keywords)
    
    # Emotion 3: happy - GREATLY EXPANDED for better detection
    emo3_keywords = [
        'happy', 'happiness', 'feel happy', 'feeling happy', 'i feel happy', 'so happy', 'really happy', 'very happy',
        'joyful', 'joy', 'feel joyful', 'feeling joyful', 'full of joy', 'brings me joy',
        'grateful', 'gratitude', 'feel grateful', 'feeling grateful', 'i feel grateful', 'so grateful', 'very grateful',
        'blessed', 'feel blessed', 'feeling blessed', 'i feel blessed', 'so blessed',
        'wonderful', 'feel wonderful', 'feeling wonderful', 'i feel wonderful', 'so wonderful',
        'amazing', 'feel amazing', 'feeling amazing', 'i feel amazing', 'so amazing',
        'great', 'feel great', 'feeling great', 'i feel great', 'so great', 'really great',
        'fantastic', 'feel fantastic', 'feeling fantastic', 'i feel fantastic',
        'good mood', 'in a good mood', 'good spirits', 'high spirits',
        'feeling good', 'feel good', 'feeling really good', 'feeling so good',
        'thankful', 'feel thankful', 'feeling thankful', 'i feel thankful', 'so thankful',
        'excited', 'feel excited', 'feeling excited', 'i feel excited', 'so excited',
        'positive', 'feel positive', 'feeling positive', 'optimistic', 'upbeat',
        'content', 'feel content', 'feeling content', 'satisfied', 'pleased',
        'delighted', 'cheerful', 'uplifted', 'elated', 'thrilled', 'greatly happy', 'gretly happy'
    ]
    is_emotion3 = any(keyword in text for keyword in emo3_keywords)
    
    # Emotion 4: tired, unmotivated, low energy, stressed, overwhelmed, frustrated, angry, drained - EXPANDED
    emo4_keywords = [
        'tired', 'feel tired', 'feeling tired', 'i feel tired', 'so tired', 'really tired', 'very tired',
        'exhausted', 'feel exhausted', 'feeling exhausted', 'i feel exhausted', 'so exhausted',
        'unmotivated', 'no motivation', 'lack motivation', 'feel unmotivated', 'feeling unmotivated',
        'low energy', 'no energy', 'drained energy', 'energy drained', 'lack energy',
        'stressed', 'stress', 'feel stressed', 'feeling stressed', 'i feel stressed', 'so stressed', 'under stress',
        'overwhelmed', 'feel overwhelmed', 'feeling overwhelmed', 'i feel overwhelmed', 'so overwhelmed',
        'frustrated', 'frustration', 'feel frustrated', 'feeling frustrated', 'i feel frustrated', 'so frustrated',
        'angry', 'anger', 'feel angry', 'feeling angry', 'i feel angry', 'so angry', 'mad', 'pissed off',
        'drained', 'feel drained', 'feeling drained', 'i feel drained', 'completely drained',
        'burned out', 'burnout', 'burn out', 'feel burned out', 'feeling burned out',
        'scattered', 'feel scattered', 'feeling scattered', 'all over the place',
        'unfocused', 'can\'t focus', 'cannot focus', 'unable to focus', 'distracted',
        'anxious', 'anxiety', 'feel anxious', 'feeling anxious', 'nervous', 'worried',
        'restless', 'agitated', 'irritated', 'annoyed', 'bothered'
    ]
    is_emotion4 = any(keyword in text for keyword in emo4_keywords)
    
    # Determine primary emotion with priority (happy emotions get priority if multiple detected)
    primary_emotion = 'emotion3'  # Default to positive
    if is_emotion3:
        primary_emotion = 'emotion3'  # Happy gets highest priority
    elif is_emotion1:
        primary_emotion = 'emotion1'
    elif is_emotion2:
        primary_emotion = 'emotion2'
    elif is_emotion4:
        primary_emotion = 'emotion4'
    
    return {
        'is_emotion1': is_emotion1,
        'is_emotion2': is_emotion2,
        'is_emotion3': is_emotion3,
        'is_emotion4': is_emotion4,
        'primary_emotion': primary_emotion,
        'confidence': 0.8 if any([is_emotion1, is_emotion2, is_emotion3, is_emotion4]) else 0.1,
        # Keep legacy keys for backward compatibility
        'is_sad': is_emotion2,
        'is_overwhelmed': is_emotion4,
        'is_happy': is_emotion3,
        'is_stressed': is_emotion4,
        'sadness_score': 0.7 if is_emotion2 else 0.1,
        'emotions': {}
    }

# 📋 Task Planning Detection - UPDATED with more phrases
def detect_task_planning_request(user_input):
    """Detect if mama specifically wants help with task planning or scheduling"""
    text = user_input.lower()
    
    task_planning_phrases = [
        'plan my day', 'make my schedule', 'create my today\'s plan', 'make my tomorrow\'s plan',
        'give me a schedule', 'make my todays plan', 'give me the task list', 'create my task list',
        'plan my task list', 'help me plan my day', 'organize my day', 'schedule my day',
        'what should i do today', 'plan my tasks', 'organize my tasks', 'create a schedule',
        'help me organize', 'make a plan for', 'daily planning', 'task planning',
        # ADDED: New phrases including the user's request
        'make my todays schedule', 'make my today schedule', 'make todays schedule',
        'create my todays schedule', 'plan todays schedule', 'organize todays schedule',
        'make my schedule for today', 'create schedule for today', 'plan schedule for today',
        'schedule my today', 'schedule for today', 'todays plan', 'today\'s plan'
    ]
    
    return any(phrase in text for phrase in task_planning_phrases)

# 🍳 Recipe Request Detection - FIXED VERSION
def detect_recipe_request(user_input):
    """Detect if mama specifically wants recipe suggestions - IMPROVED VERSION"""
    text = user_input.lower()
    
    # Keep original static phrase detection
    recipe_phrases = [
        # General recipe requests
        'give me recipe', 'suggest me recipe', 'suggest me some recipe', 'suggest recipe',
        'help me to cook', 'give me some meal suggestion', 'plan my meals',
        'cooking help', 'what to cook', 'meal ideas', 'cooking suggestions',
        'help with cooking', 'what can i make', 'cooking recipe', 'food recipe',

        # Explicit meal planning and recipe suggestions
        'plan my meal', 'plan my meals', 'suggest me a recipe', 'suggest me some recipes',
        'i want to make breakfast', 'i want to make lunch', 'i want to make brunch',
        'i want to make dinner', 'i want to make supper',

        # What can I cook in specific meals
        'what can i cook in breakfast', 'what can i cook in lunch', 'what can i cook in brunch',
        'what can i cook in dinner', 'what can i cook in supper',

        # Give me meal ideas for specific meals
        'give me meal ideas for breakfast', 'give me meal ideas for lunch', 'give me meal ideas for brunch',
        'give me meal ideas for dinner', 'give me meal ideas for supper',

        # Give me cooking suggestions for specific meals
        'give me cooking suggestions for breakfast', 'give me cooking suggestions for lunch',
        'give me cooking suggestions for brunch', 'give me cooking suggestions for dinner',
        'give me cooking suggestions for supper'
    ]

    # Dynamic fuzzy matching for recipe requests (added feature)
    keywords = [
        'recipe', 'cook', 'meal', 'food', 'dish', 'suggest meal', 'idea meal', 'meal plan', 'make meal/recipe', 'prepare meal/recipe', 'cooking', 'bake', 'dinner meal/recipe', 'lunch meal/recipe', 'breakfast meal/recipe', 'supper meal/recipe', 'brunch meal/recipe'
    ]
    text_words = set(text.split())
    found = False
    for word in keywords:
        if word in text:
            if any(context in text for context in ['give', 'suggest', 'help', 'what', 'how', 'need', 'want', 'show', 'find', 'get']):
                found = True
                break
    patterns = [
        r'(give|suggest|show|find|get|help|need|want|how).*\b(recipe|cook|meal|food|dish|prepare|cooking|bake|dinner|lunch|breakfast|supper|brunch)\b',
        r'\b(recipe|cook|meal|food|dish|prepare|cooking|bake|dinner|lunch|breakfast|supper|brunch)\b.*(please|suggest|help|need|want|show|find|get|give)'
    ]
    import re
    for pattern in patterns:
        if re.search(pattern, text):
            found = True
            break
    # Also dynamically detect meal planning requests (added feature)
    meal_keywords = ['plan', 'make', 'prepare', 'suggest', 'idea', 'cook']
    meal_times = ['dinner', 'lunch', 'breakfast', 'supper', 'brunch', 'meal']
    meal_found = False
    for mk in meal_keywords:
        for mt in meal_times:
            if mk in text and mt in text:
                meal_found = True
                break
        if meal_found:
            break
    # Return True if static, dynamic, or meal planning detection matches
    return any(phrase in text for phrase in recipe_phrases) or found or meal_found

# ⭐ NEW FEATURE: Task Query Detection
def detect_task_query_request(user_input):
    """⭐ NEW FEATURE: Detect if mama wants to check existing tasks - FULLY DYNAMIC"""
    try:
        # Use AI to dynamically detect task query requests
        prompt = f"""
        Analyze this user input to determine if they are asking about existing tasks, schedules, or appointments.
        
        User input: "{user_input}"
        
        Return true if the user is asking about:
        1. Checking existing tasks or schedules
        2. What they have planned for a specific date/time
        3. Their agenda or calendar
        4. Whether they're busy or free
        5. What tasks are assigned to someone
        6. Any variation of these concepts
        
        Return false if they are:
        1. Creating new tasks or schedules
        2. Planning or organizing new activities
        3. Just having normal conversation
        4. Asking for recipes or other unrelated help
        
        Respond with only "true" or "false".
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().lower()
        return result == "true"
        
    except Exception as e:
        print(f"Error in dynamic task query detection: {e}")
        # Fallback to basic keyword detection
        text = user_input.lower()
        basic_keywords = [
            'do i have', 'what task', 'check my', 'show my', 'my schedule',
            'task for', 'any task', 'anything scheduled', 'what\'s planned',
            'busy', 'free', 'available', 'agenda', 'calendar'
        ]
        return any(keyword in text for keyword in basic_keywords)

# ⭐ NEW FEATURE: Fetch tasks from API for specific date/time queries
def query_existing_tasks(user_input):
    """⭐ NEW FEATURE: Query existing tasks based on user's date/time request - FULLY DYNAMIC"""
    try:
        # Get all tasks from API
        tasks = get_schedule_settings()
        if not tasks:
            return {
                "found_tasks": [],
                "total_tasks": 0,
                "query_date": None,
                "message": "❌ Unable to retrieve tasks from the system."
            }
        
        # Use AI to understand what date/time the user is asking about - FULLY DYNAMIC
        today = datetime.now()
        tomorrow = today + timedelta(days=1)
        
        prompt = f"""
        You are an expert assistant for understanding natural language queries about schedules and tasks.
        
        Today's date: {today.strftime('%Y-%m-%d')} ({today.strftime('%A')})
        Tomorrow's date: {tomorrow.strftime('%Y-%m-%d')} ({tomorrow.strftime('%A')})
        Current time: {today.strftime('%H:%M')}
        
        Analyze this user query and extract the following information:
        Query: "{user_input}"
        
        You MUST return ONLY a valid JSON object with these exact fields:
        {{
            "target_date": "YYYY-MM-DD format for the date they're asking about",
            "specific_time": null,
            "time_range": null,
            "assigned_filter": "self or partner or child or all",
            "date_range": null,
            "confidence": "high"
        }}
        
        Rules for assignment detection (learn from the query):
        - Look for "I", "my", "me", "do i have" patterns = "self"
        - Look for "partner", "spouse", "husband", "wife" patterns = "partner"  
        - Look for "son", "daughter", "child", "kid" patterns = "child"
        - If unclear or general = "all"
        
        Rules for date detection (learn from the query):
        - "today" references = "{today.strftime('%Y-%m-%d')}"
        - "tomorrow" references = "{tomorrow.strftime('%Y-%m-%d')}"
        - If no date mentioned, default to "{today.strftime('%Y-%m-%d')}"
        
        Return ONLY the JSON object, no other text or explanations.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.0
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up the response
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
        
        # Try to parse JSON with better error handling
        try:
            query_params = json.loads(result_text)
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"❌ AI Response was: {result_text}")
            # Dynamic fallback - analyze the input directly
            query_params = {
                "target_date": tomorrow.strftime('%Y-%m-%d') if "tomorrow" in user_input.lower() else today.strftime('%Y-%m-%d'),
                "specific_time": None,
                "time_range": None,
                "assigned_filter": "child" if any(word in user_input.lower() for word in ["son", "daughter", "child", "kid"]) else "self",
                "date_range": None,
                "confidence": "medium"
            }
        
        target_date = query_params.get("target_date")
        specific_time = query_params.get("specific_time")
        time_range = query_params.get("time_range")
        assigned_filter = query_params.get("assigned_filter", "all")
        
        # Filter tasks based on the query - DYNAMIC MATCHING
        matching_tasks = []
        for task in tasks:
            task_date = task.get("scheduled_date")
            task_time = task.get("scheduled_time", "").split(".")[0] if task.get("scheduled_time") else None
            task_assigned = task.get("assigned_to_type", "Self")
            
            # Dynamic date matching
            if task_date == target_date:
                # Dynamic assignment matching
                assignment_match = False
                if assigned_filter == "all":
                    assignment_match = True
                elif assigned_filter == "self" and task_assigned.lower() in ["self", "me", "myself"]:
                    assignment_match = True
                elif assigned_filter == "partner" and task_assigned.lower() in ["partner", "spouse", "husband", "wife"]:
                    assignment_match = True
                elif assigned_filter == "child" and task_assigned.lower() in ["child", "son", "daughter", "kid", "kids"]:
                    assignment_match = True
                
                if assignment_match:
                    # Dynamic time matching
                    if specific_time:
                        if task_time and task_time.startswith(specific_time[:5]):
                            matching_tasks.append(task)
                    elif time_range and time_range != "all_day":
                        if task_time and time_range_matches_dynamic(task_time, time_range):
                            matching_tasks.append(task)
                    else:
                        # No specific time mentioned, include all tasks for that date
                        matching_tasks.append(task)
        
        return {
            "found_tasks": matching_tasks,
            "total_tasks": len(matching_tasks),
            "query_date": target_date,
            "query_time": specific_time,
            "query_time_range": time_range,
            "assigned_filter": assigned_filter,
            "message": format_task_query_response(matching_tasks, target_date, specific_time, time_range, assigned_filter)
        }
        
    except Exception as e:
        print(f"❌ Error querying tasks: {e}")
        return {
            "found_tasks": [],
            "total_tasks": 0,
            "query_date": None,
            "message": f"❌ Error retrieving your tasks: {e}"
        }

def time_range_matches_dynamic(task_time, time_range):
    """⭐ NEW FEATURE: Dynamic time range matching that adapts to different interpretations"""
    try:
        # Use AI to determine if task time matches the requested time range
        prompt = f"""
        Does this task time fall within the requested time range?
        
        Task time: {task_time}
        Requested range: {time_range}
        
        Consider flexible interpretations:
        - Morning: 5:00 AM - 12:00 PM
        - Afternoon: 12:00 PM - 6:00 PM  
        - Evening: 6:00 PM - 10:00 PM
        - Night: 10:00 PM - 5:00 AM
        
        Respond with only "true" or "false".
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().lower()
        return result == "true"
        
    except Exception:
        # Fallback to basic hour checking
        try:
            hour = int(task_time.split(":")[0])
            if time_range == "morning":
                return 5 <= hour < 12
            elif time_range == "afternoon":
                return 12 <= hour < 18
            elif time_range == "evening":
                return 18 <= hour < 22
            elif time_range == "night":
                return hour >= 22 or hour < 5
            return False
        except:
            return False

def make_task_name_fluent(task_name, assigned_to):
    """⭐ NEW FEATURE: Convert task name to natural, fluent language - FULLY DYNAMIC"""
    try:
        prompt = f"""
        Convert this task description into natural, fluent English suitable for conversation.
        
        Original task: "{task_name}"
        Assigned to: {assigned_to}
        
        Rules:
        1. Keep the original meaning exactly as it is
        2. Make it sound natural and conversational  
        3. Fix only grammatical errors, don't change the context
        4. Don't add extra words or change who does what
        5. Keep it simple and direct
        6. Use natural language that flows well in conversation
        
        Return ONLY the improved task description, nothing else.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.1
        )
        
        fluent_name = response.choices[0].message.content.strip().replace('"', '').replace("'", "")
        return fluent_name if fluent_name else task_name.strip()
        
    except Exception as e:
        print(f"Error making task name fluent: {e}")
        # Dynamic fallback - just clean and return
        return task_name.strip()

def format_task_query_response(tasks, target_date, specific_time=None, time_range=None, assigned_filter="all"):
    """⭐ NEW FEATURE: Format the task query response in a user-friendly way - FULLY DYNAMIC"""
    try:
        # Use AI to generate completely dynamic responses based on actual task data
        prompt = f"""
        You are Task Mama, a caring AI assistant for mothers. Generate a natural, conversational response about the tasks found.
        
        User asked about: {assigned_filter} tasks for {target_date}
        {f"Specific time: {specific_time}" if specific_time else ""}
        {f"Time range: {time_range}" if time_range else ""}
        
        Tasks found: {len(tasks)}
        Task details: {json.dumps(tasks) if tasks else "No tasks"}
        
        Create a warm, natural response that:
        1. Sounds like a caring friend talking to a mother
        2. Uses emojis like 🌸, 💕, 🤗
        3. Mentions the specific tasks naturally without quotes or technical details
        4. Makes task names flow naturally in conversation
        5. Is encouraging and supportive
        
        If no tasks: Say they're free and can relax
        If 1 task: Mention the task naturally with time
        If multiple tasks: List them in a caring way
        
        Keep it conversational and natural, not technical.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        return response.choices[0].message.content.strip()
        
    except Exception as e:
        print(f"Error generating dynamic response: {e}")
        # Simple fallback
        date_str = datetime.strptime(target_date, '%Y-%m-%d').strftime('%A, %B %d, %Y')
        
        if not tasks:
            return f"🌸 Great news! You're free on {date_str}. Perfect time to relax! 💕"
        elif len(tasks) == 1:
            task = tasks[0]
            task_name = task.get("task_name", "a task")
            task_time = task.get("scheduled_time", "").split(".")[0] if task.get("scheduled_time") else "sometime"
            return f"🌸 You have {task_name} {f'at {task_time}' if task_time != 'sometime' else ''} on {date_str}. 💕"
        else:
            return f"🌸 You have {len(tasks)} tasks scheduled for {date_str}. Let me know if you need the details! 💕"

# Task extraction and analysis functions (keeping original functionality)
def convert_time_to_24hour(time_str):
    """
    Convert any time format to 24-hour format.
    If already in 24-hour format, return as is.
    If in 12-hour format, convert to 24-hour format.
    """
    if not time_str or time_str.strip().lower() in ['not specified', 'none', '']:
        return time_str
    
    time_str = time_str.strip()
    
    try:
        # Check if it's already in 24-hour format (HH:MM or H:MM)
        if re.match(r'^\d{1,2}:\d{2}', time_str):
            parts = time_str.split(':')
            hour = int(parts[0])
            minute = int(parts[1])
            
            # Validate 24-hour format
            if 0 <= hour <= 23 and 0 <= minute <= 59:
                return f"{hour:02d}:{minute:02d}"
        
        # Try to parse 12-hour format
        for fmt in ['%I:%M %p', '%I:%M%p', '%I %p', '%I%p']:
            try:
                parsed_time = datetime.strptime(time_str.upper(), fmt)
                return parsed_time.strftime('%H:%M')
            except ValueError:
                continue
        
        # If no format matched, try to extract numbers and AM/PM
        time_match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)', time_str.lower())
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
            period = time_match.group(3).lower()
            
            # Convert to 24-hour format
            if 'p' in period and hour != 12:
                hour += 12
            elif 'a' in period and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        # Return original if can't parse
        return time_str
        
    except Exception as e:
        print(f"Time conversion error for '{time_str}': {e}")
        return time_str

def extract_tasks_from_text(user_input):
    """
    Use GPT to robustly extract ALL actionable tasks and their scheduled times from the input text.
    Resolves relative times to absolute times using context.
    Returns a list of dicts: [{"task_name": ..., "time": ..., "date": ...}]
    """
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    prompt = (
        f"Today's date is {now.strftime('%A')}, {now.strftime('%Y-%m-%d')}.\n"
        f"Extract ALL actionable, scheduled tasks from the message below. "
        f"For each, return a JSON object with:\n"
        f"- task_name: clear description PRESERVING the original language about WHO will do it\n"
        f"- time: in HH:MM format (24-hour) or 'Not specified' (calculate relative times like 'after two hours', convert 12-hour format like '3pm' to '15:00')\n"
        f"- date: in YYYY-MM-DD format (normalize ANY date expression, e.g., 'tomorrow' = '{tomorrow.strftime('%Y-%m-%d')}', 'today' = '{now.strftime('%Y-%m-%d')}', etc.)\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. Include ALL tasks mentioned in the message, even if they conflict with other tasks\n"
        f"2. If tasks overlap at the same time, include BOTH as separate entries\n" 
        f"3. Include tasks even if the person says they're not important or can be rescheduled\n"
        f"4. Only include tasks that are definite actions to be performed, not wishes or possibilities\n"
        f"5. ALWAYS convert time to 24-hour format: 3pm -> 15:00, 9am -> 09:00, etc.\n\n"
        f"Message: {user_input}\n\n"
        f"Return a JSON array of ALL actionable tasks."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1
        )
        result_text = response.choices[0].message.content
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        gpt_tasks = json.loads(result_text)
        
        # Post-process to ensure correct date normalization and time conversion
        for t in gpt_tasks:
            # Fix ambiguous dates if needed
            if "tomorrow" in t["task_name"].lower() or t.get("date", "") in ["tomorrow", "Tomorrow"]:
                t["date"] = tomorrow.strftime('%Y-%m-%d')
            elif "today" in t["task_name"].lower() or t.get("date", "") in ["today", "Today"]:
                t["date"] = now.strftime('%Y-%m-%d')
            # If date is missing, default to today
            if not t.get("date"):
                t["date"] = now.strftime('%Y-%m-%d')
            
            # Convert time to 24-hour format
            if t.get("time") and t["time"].lower() != "not specified":
                t["time"] = convert_time_to_24hour(t["time"])
        
        # Deduplicate tasks by name, time
        unique = []
        seen = set()
        for t in gpt_tasks:
            key = (t["task_name"].lower(), t.get("time", "").lower(), t.get("date", ""))
            if key not in seen and len(t["task_name"].split()) >= 2:
                unique.append({
                    "task_name": t["task_name"].strip(),
                    "time": t.get("time", "Not specified").strip(),
                    "date": t.get("date", now.strftime('%Y-%m-%d')).strip()
                })
                seen.add(key)
        return unique
    except Exception as e:
        print(f"Task extraction error: {e}")
        return []

class DynamicTaskPrioritizer:
    def __init__(self):
        self.openai_client = client

    def analyze_task_priority(self, task_description, context=""):
        """
        Use AI to dynamically analyze task priority based on natural language understanding
        rather than static keyword matching
        """
        
        prompt = f"""
You are an expert task prioritization assistant for busy parents and caregivers.

Analyze this task and determine its priority based on natural understanding, context, and real-world implications:

TASK: "{task_description}"
CONTEXT: "{context}"

Consider these factors naturally (don't just look for keywords):
1. SAFETY & WELFARE: Does this affect someone's safety, health, or basic needs?
2. TIME SENSITIVITY: How flexible is the timing? Are there consequences for delay?
3. DEPENDENCIES: Do other people or tasks depend on this being completed?
4. IMPACT: What happens if this task is delayed or not completed?
5. RESPONSIBILITY LEVEL: Is this someone's primary responsibility (like parent duties)?

SMART PRIORITY RULES - Use real-world understanding:
- Meeting friends/social activities = LOW Priority (unless user says it's rare/urgent opportunity)
- Cleaning house = LOW Priority (unless guests are coming = HIGH Priority)
- Watching movies/entertainment = LOW Priority (especially if user says "can do tomorrow")
- Shopping = MEDIUM Priority (unless user says "no grocery left" = HIGH Priority)
- Medical/health appointments = HIGH Priority
- Work meetings/deadlines = HIGH Priority
- Child-related urgent needs = HIGH Priority

EXAMPLES:
- "Meet my friend today" → LOW Priority (casual social meeting)
- "Meet my friend, I won't get another chance" → HIGH Priority (rare opportunity)
- "Clean house" → LOW Priority (routine task)
- "Clean house, guests coming" → HIGH Priority (time-sensitive)
- "Watch movie but can watch tomorrow" → LOW Priority (flexible)
- "Go shopping" → MEDIUM Priority (routine need)
- "Go shopping, no grocery left" → HIGH Priority (urgent need)

Return ONLY this JSON format:
{{
    "priority_score": 3.0,
    "priority_level": "Low Priority",
    "category": "Social & Entertainment",
    "reasoning": "Brief explanation of why this priority was assigned",
    "time_flexibility": "flexible",
    "consequences_of_delay": "Low"
}}

Priority Levels (use exactly these strings):
- "High Priority" (8-10): Cannot be delayed, affects safety/welfare, or has severe consequences
- "Medium Priority" (5-7): Important but some flexibility exists
- "Low Priority" (1-4): Can be postponed without major issues

Only return valid JSON, no other text.
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a task prioritization expert. Always return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up response
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            
            priority_data = json.loads(result_text)
            return priority_data
            
        except Exception as e:
            print(f"Error in priority analysis: {e}")
            # Fallback to medium priority
            return {
                "priority_score": 5.0,
                "priority_level": "Medium Priority",
                "category": "General",
                "reasoning": "Could not analyze - assigned medium priority",
                "time_flexibility": "flexible",
                "consequences_of_delay": "Medium"
            }
    
    def analyze_task_responsibility(self, task_description, context=""):
        """
        Use AI to determine WHO will do the task based on natural language understanding
        """
        
        prompt = f"""
You are an expert task analysis assistant. Your job is to identify WHO WILL PERFORM each task.

TASK: "{task_description}"
CONTEXT: "{context}"

CRITICAL INSTRUCTION: Look for these specific language patterns to identify the doer:

SELF INDICATORS:
- "I have to...", "I need to...", "I will...", "I must..."
- "Meet the doctor", "My appointment", "My meeting"
- No mention of someone else doing it

PARTNER INDICATORS:
- "My partner have to...", "My partner will..."
- "My husband/wife have to...", "My husband/wife will..."
- "My boyfriend/girlfriend have to...", "My boyfriend/girlfriend will..."
- Explicitly states partner/spouse will do the task

CHILD INDICATORS:
- "My son have to...", "My daughter have to..."
- "My child have to...", "Kids have to..."
- "Son will...", "Daughter will..."
- Tasks explicitly assigned to children (studying, homework, going to school)

Return ONLY this JSON format:
{{
    "task_assigned": "Self"
}}

Task Categories (use exactly these strings):
- "Self": You will do it
- "Partner": Partner/spouse/boyfriend/girlfriend will do it  
- "Child": Child/son/daughter will do it

Analyze the EXACT wording to determine who performs the task.
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a task analysis expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=200,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            category_data = json.loads(result_text)
            return category_data.get("task_assigned", "Self")
        except Exception as e:
            print(f"Error in responsibility analysis: {e}")
            return "Self"

    def analyze_task_catagory(self, task_description, context=""):
        """
        Use AI to determine the task_catagory: Normal task, Health task, or Recipy task.
        Only assign 'Recipy task' if the user explicitly asks for a recipe.
        """
        prompt = f"""
You are an expert assistant for mothers. Categorize the following task as one of these types:

- "Normal task": Any general daily task (meeting, pickup, study, clean, cooking, etc.)
- "Health task": Anything related to medical, doctor, hospital, health check, appointment, medicine, etc.
- "Recipy task": ONLY if the user explicitly asks for a recipe or requests a recipe suggestion based on available items.

TASK: "{task_description}"
CONTEXT: "{context}"

Return ONLY this JSON format:
{{
    "task_catagory": "Normal task"
}}

Possible values for task_catagory:
- "Normal task"
- "Health task"
- "Recipy task"
"""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a task categorization expert. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=100,
            )
            result_text = response.choices[0].message.content.strip()
            if result_text.startswith("```json"):
                result_text = result_text.replace("```json", "").replace("```", "").strip()
            cat_data = json.loads(result_text)
            return cat_data.get("task_catagory", "Normal task")
        except Exception as e:
            print(f"Error in catagory analysis: {e}")
            return "Normal task"

def get_meal_type_from_conversation(user_input):
    """
    Extract meal type from user input (breakfast, lunch, dinner, snack, etc.).
    If not found, return 'Other meal'.
    """
    meal_types = ["breakfast", "lunch", "dinner", "snack", "snacks", "brunch", "supper"]
    user_input_lower = user_input.lower()
    for meal in meal_types:
        if meal in user_input_lower:
            return meal.capitalize()
    return "Other meal"

def format_items_available(items_text):
    """
    Format items_available to show just items with amounts (e.g., '1 kg rice, 500g chicken breast')
    """
    try:
        prompt = f"""
Extract and format the available items with their amounts in a clean, simple format.

Input: "{items_text}"

Convert to format like: "1 kg rice, 500g chicken breast, 2 onions"

Rules:
- Extract quantities and ingredients only
- Use standard units (kg, g, pieces, etc.)
- Separate multiple items with commas
- Keep it simple and clear

Return only the formatted items list, nothing else.
"""
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=100,
            temperature=0.1
        )
        
        formatted = response.choices[0].message.content.strip()
        return formatted if formatted else items_text
        
    except Exception:
        # Fallback formatting
        return items_text.strip()

def generate_recipy_suggestion(available_items, user_conversation=None):
    """
    Generate a recipe suggestion based on available items using AI knowledge.
    Returns a JSON with 3 unique recipes using ONLY the ingredients provided.
    Uses meal_type from conversation if specified.
    """
    now = datetime.now()
    # Detect meal type from conversation
    meal_type = get_meal_type_from_conversation(user_conversation or "")

    prompt = f"""
You are an expert recipe assistant. Create exactly 3 unique recipes using ONLY these ingredients: {available_items}

Requirements:
1. Use ONLY the ingredients mentioned by the user
2. Each recipe must be completely different from the others
3. Provide detailed cooking instructions
4. Include cooking times and temperatures
5. Add kid-friendly tips and nutritional notes

Meal type: {meal_type}
Available ingredients: {available_items}

Create 3 unique recipes with these names (NO ### symbols):
- Recipe 1: [Creative name using available ingredients]
- Recipe 2: [Different creative name using available ingredients] 
- Recipe 3: [Third different creative name using available ingredients]

For each recipe, write 5-6 sentences with:
- Step-by-step cooking instructions
- Cooking times and temperatures
- Tips for mothers and kids
- Serving suggestions

IMPORTANT: Do NOT use ### symbols or markdown formatting in recipe names. Use plain text only.
Format your response as a clear list of 3 recipes with names and detailed descriptions.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful recipe expert. Create detailed, unique recipes using only the provided ingredients."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.4
        )
        
        ai_response = response.choices[0].message.content.strip()
        
        # Parse the AI response and create our JSON structure
        return parse_ai_recipe_response(ai_response, available_items, now, meal_type)
        
    except Exception as e:
        # Fallback to manual recipe creation
        return create_smart_recipe_from_ingredients(available_items, now, meal_type)

def fix_unicode_encoding(text):
    """
    Fix Unicode encoding issues in recipe text to make temperatures and symbols readable.
    """
    # Fix Unicode temperature symbols
    text = text.replace("\\u00b0C", " celsius")
    text = text.replace("\\u00b0F", " fahrenheit")
    text = text.replace("\u00b0C", " celsius")
    text = text.replace("\u00b0F", " fahrenheit")
    # Fix other Unicode characters
    text = text.replace("\\u2019", "'")
    text = text.replace("\u2019", "'")
    text = text.replace("\\u201c", '"')
    text = text.replace("\u201c", '"')
    text = text.replace("\\u201d", '"')
    text = text.replace("\u201d", '"')
    text = text.replace("\\u2013", "-")
    text = text.replace("\u2013", "-")
    text = text.replace("\\u2014", "—")
    text = text.replace("\u2014", "—")
    return text

def explain_cooking_terms(text):
    """
    Add explanations for difficult cooking terms in the recipe text.
    For example, 'sauté' will be explained the first time it appears.
    """
    # First fix any Unicode encoding issues
    text = fix_unicode_encoding(text)
    
    # Dictionary of terms and their explanations
    explanations = {
        "sauté": "sauté (cook quickly in a small amount of oil or butter over medium-high heat)",
        "blanch": "blanch (briefly boil then cool in ice water to soften or remove skins)",
        "braise": "braise (slow-cook in a small amount of liquid in a covered pot)",
        "julienne": "julienne (cut into thin matchstick-like strips)",
        "deglaze": "deglaze (add liquid to a hot pan to loosen and dissolve browned bits)",
        "poach": "poach (gently cook in simmering liquid just below boiling)",
        "caramelize": "caramelize (cook slowly until sugars turn golden brown and sweet)",
        "fold": "fold (gently combine ingredients using a spatula to keep mixture airy)",
        "reduce": "reduce (boil or simmer to thicken and intensify flavors by evaporating liquid)"
    }
    # Track which terms have been explained
    explained = set()
    for term, explanation in explanations.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        if matches:
            # Only explain the first occurrence
            first = matches[0]
            start, end = first.span()
            if term not in explained:
                text = text[:start] + explanation + text[end:]
                explained.add(term)
    return text

def parse_ai_recipe_response(ai_response, available_items, now, meal_type):
    """
    Parse AI response and convert to our JSON format, always prefixing each recipe with 'Recipe 1:', 'Recipe 2:', etc.
    Also explain difficult cooking terms in the recipe text.
    """
    try:
        # Split response into sections for each recipe
        lines = ai_response.split('\n')
        recipes = []
        recipe_names = []
        current_recipe = ""
        current_name = ""
        recipe_count = 0

        for line in lines:
            line = line.strip()
            if 'Recipe 1:' in line or 'Recipe 2:' in line or 'Recipe 3:' in line:
                if current_recipe and current_name:
                    recipe_count += 1
                    explained_recipe = explain_cooking_terms(current_recipe.strip())
                    recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
                    recipe_names.append(current_name.strip())
                current_name = line
                current_recipe = ""
            elif line and not line.startswith('Recipe'):
                current_recipe += line + " "

        # Add the last recipe
        if current_recipe and current_name:
            recipe_count += 1
            explained_recipe = explain_cooking_terms(current_recipe.strip())
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(current_name.strip())

        # Ensure we have exactly 3 recipes
        while len(recipes) < 3:
            recipe_count += 1
            fallback = "Cook the available ingredients together with seasonings until tender. Adjust cooking time based on ingredients used."
            explained_recipe = explain_cooking_terms(fallback)
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(f"Recipe {recipe_count}: Mixed Ingredient Dish")

        # Clean recipe names to remove ### symbols
        cleaned_recipe_names = [name.replace("###", "").strip() for name in recipe_names[:3]]
        
        # Format items_available to show just items with amounts
        formatted_items = format_items_available(available_items)
        
        return {
            "meal_type": meal_type,
            "task_catagory": "Recipy task",
            "time": now.strftime('%H:%M'),  # Changed to 24-hour format
            "date": now.strftime('%Y-%m-%d'),
            "items_available": formatted_items,
            "items_needed": "Cooking oil, salt, black pepper, water, onions",
            "recipy_name": cleaned_recipe_names,
            "recipy": recipes[:3]
        }

    except Exception:
        return create_smart_recipe_from_ingredients(available_items, now, meal_type)

def create_smart_recipe_from_ingredients(available_items, now, meal_type):
    """
    Create 3 unique, detailed recipes using AI knowledge and the actual ingredients provided
    """
    items_lower = available_items.lower()
    
    # Initialize recipe data
    recipes = []
    recipe_names = []
    
    # Analyze ingredients and create appropriate recipes
    has_mutton = "mutton" in items_lower
    has_rice = "rice" in items_lower or "basmati" in items_lower
    has_vegetables = "vegetable" in items_lower
    has_seasoning = "seasoning" in items_lower or "spice" in items_lower
    
    if has_mutton and has_rice:
        # Recipe 1: Traditional Curry Style
        recipe_names.append("Recipe 1: Traditional Mutton Curry")
        recipes.append(
            "Recipe 1: Traditional Mutton Curry: Cut 1 kg mutton into medium-sized pieces and wash thoroughly under cold water. Heat 3 tablespoons of cooking oil in a heavy-bottomed pot over medium-high heat for 2 minutes. Add the mutton pieces and brown them on all sides for 8-10 minutes until they develop a nice golden color. Add your available vegetables (chopped) and seasonings, then pour enough water to just cover the meat. Bring the mixture to a rolling boil, then reduce heat to low and cover with a tight-fitting lid. Simmer gently for 1.5 to 2 hours, stirring occasionally, until the mutton becomes fork-tender and the curry develops rich flavors. This protein-packed curry is perfect for lunch and provides essential nutrients including iron and protein that growing children need. For kids, you can make smaller, bite-sized pieces and serve with plain rice to make it easier to eat and less spicy."
        )
        
        # Recipe 2: Biryani Style  
        recipe_names.append("Recipe 2: Aromatic Mutton Biryani")
        recipes.append(
            "Recipe 2: Aromatic Mutton Biryani: Begin by soaking 3 cups of basmati rice in lukewarm water for 30 minutes, then drain completely. In a large, heavy-bottomed pot, cook the mutton pieces with chopped vegetables and half of your seasonings in enough water to cover for about 1 hour until 70% cooked. In a separate large pot, bring 6 cups of salted water to boil and add the soaked rice, cooking for 5-7 minutes until 70% done, then drain. Layer the partially cooked rice over the mutton in the first pot, sprinkle remaining seasonings on top, and add dots of oil around the edges. Cover the pot with aluminum foil, then place the lid tightly on top and cook on high heat for 3-4 minutes until steam forms, then reduce to lowest heat and cook for 45 minutes. Let it rest for 10 minutes before opening to allow the flavors to meld perfectly. This aromatic one-pot meal combines the richness of mutton with fragrant basmati rice, creating a complete lunch that kids absolutely love for its colorful presentation and amazing smell. The layered cooking method ensures each grain of rice absorbs the meat flavors while staying fluffy and separate."
        )
        
        # Recipe 3: Simple Rice Bowl Style
        recipe_names.append("Recipe 3: Hearty Mutton Rice Bowl")
        recipes.append(
            "Recipe 3: Hearty Mutton Rice Bowl: Cook 2.5 cups of basmati rice in a rice cooker or pot with 4 cups of water until perfectly fluffy, then set aside and keep warm. Meanwhile, in a large skillet or wok, heat oil over medium heat and add the mutton pieces, cooking them for 12-15 minutes while stirring frequently until they're well-browned and partially cooked. Add your chopped vegetables to the same pan and continue cooking for 5-7 minutes until vegetables are tender-crisp. Pour in enough water to create a light gravy, add all your seasonings, and let everything simmer together for 30-40 minutes until the mutton is completely tender and flavors are well combined. Taste and adjust seasonings as needed, then serve the savory mutton and vegetable mixture generously over bowls of the fluffy rice. This comforting bowl-style meal is perfect for families because everyone can customize their portions, and the simple preparation allows the natural flavors of the mutton and vegetables to shine through. Children will enjoy picking their favorite vegetables from the colorful mix, and the tender mutton provides excellent protein for their growing bodies."
        )
    else:
        # Fallback recipes for other ingredient combinations
        recipe_names = [
            "Recipe 1: Seasoned Ingredient Medley",
            "Recipe 2: Slow-Cooked Comfort Dish", 
            "Recipe 3: Simple Homestyle Preparation"
        ]
        recipes = [
            "Recipe 1: Seasoned Ingredient Medley: Combine all your available ingredients with seasonings and cook slowly until everything is tender and flavorful. This versatile dish works well with any combination of ingredients you have on hand.",
            "Recipe 2: Slow-Cooked Comfort Dish: Layer your ingredients in a pot with seasonings and cook on low heat for maximum flavor development. The slow cooking process ensures all ingredients are perfectly tender.",
            "Recipe 3: Simple Homestyle Preparation: Cook your ingredients with seasonings using traditional methods for a comforting, nutritious meal that the whole family will enjoy."
        ]
    
    # Format items_available to show just items with amounts
    formatted_items = format_items_available(available_items)
    
    return {
        "meal_type": meal_type,
        "task_catagory": "Recipy task",
        "time": now.strftime('%H:%M'),  # Changed to 24-hour format
        "date": now.strftime('%Y-%m-%d'),
        "items_available": formatted_items,
        "items_needed": "Cooking oil, salt, black pepper, water",
        "recipy_name": recipe_names[:3],
        "recipy": recipes[:3]
    }

def generate_task_analysis(user_input):
    """
    Generate structured task analysis with dynamic AI-powered priority analysis.
    """
    extracted = extract_tasks_from_text(user_input)
    if not isinstance(extracted, list) or not extracted:
        return {
            "tasks": [],
            "total_tasks": 0,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        }

    prioritizer = DynamicTaskPrioritizer()
    all_task_descriptions = [t["task_name"] for t in extracted]

    def beautify_task_name(name):
        prompt = (
            f"Make this task description short, clear, and beautiful for a mom's daily planner. "
            f"Example: 'I have to go to the grocery shop to buy some snacks' -> 'Buy snacks'.\n"
            f"Task: \"{name}\"\n"
            f"Return only the short version as a string."
        )
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=20,
                temperature=0.2
            )
            short_name = response.choices[0].message.content.strip().replace('"', '')
            return short_name if short_name else name
        except Exception:
            return name

    # Collect all tasks with their priorities and categories
    raw_tasks = []
    for t in extracted:
        priority_data = prioritizer.analyze_task_priority(
            t["task_name"],
            context=f"Original user input: {user_input}. Other tasks: {all_task_descriptions}"
        )
        # Pass the original user input for better assignment detection
        task_assigned = prioritizer.analyze_task_responsibility(
            t["task_name"],
            context=f"Original user input: {user_input}. Other tasks: {all_task_descriptions}"
        )
        task_catagory = prioritizer.analyze_task_catagory(
            t["task_name"],
            context=f"Other tasks: {all_task_descriptions}"
        )
        short_name = beautify_task_name(t["task_name"])
        raw_tasks.append({
            "task_name": short_name,
            "time": t["time"],
            "date": t["date"],
            "task_assigned": task_assigned,
            "priority": priority_data["priority_level"],
            "priority_score": priority_data.get("priority_score", 5.0),
            "task_catagory": task_catagory
        })

    # For each time slot, sort tasks by priority_score and assign priorities
    grouped = {}
    for task in raw_tasks:
        key = (task["date"], task["time"])
        grouped.setdefault(key, []).append(task)

    final_tasks = []
    for group in grouped.values():
        # Sort by priority_score descending
        group_sorted = sorted(group, key=lambda x: -x["priority_score"])
        for task in group_sorted:
            # Use the AI-determined priority instead of overriding it
            final_tasks.append({
                "task_name": task["task_name"],
                "time": task["time"],
                "date": task["date"],
                "task_assigned": task["task_assigned"],
                "priority": task["priority"],  # Use original AI-determined priority
                "task_catagory": task["task_catagory"]
            })

    # Sort tasks by date, then time, then priority
    def sort_key(task):
        priority_order = {"High Priority": 1, "Medium Priority": 2, "Low Priority": 3}
        return (task["date"], task["time"], priority_order.get(task["priority"], 2))

    final_tasks.sort(key=sort_key)
    return {
        "tasks": final_tasks,
        "total_tasks": len(final_tasks),
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    }

# 💬 Conversation Management
def add_to_conversation(role, content):
    """Add message to a session's conversation history. If session id not provided, use global."""
    # Deprecated: keep signature same for backward compatibility by accepting session embedded in content
    # Expect content possibly as tuple (session_id, text) for internal calls
    if isinstance(content, tuple) and len(content) == 2:
        session_id, text = content
    else:
        # no session provided; use global
        session_id, text = "__global__", content
    hist = get_session_history(session_id)
    hist.append({"role": role, "content": text})
    # Keep manageable history per session
    if len(hist) > 25:
        _session_histories[session_id] = [hist[0]] + hist[-24:]

def get_mama_response(user_input):
    """Get AI response with mama's context.

    Backwards-compatible: uses global session if no session_id provided. New callers should pass session_id to avoid cross-user mixing.
    """
    return get_mama_response_for_session(user_input, session_id=None, creative=False)


def get_mama_response_for_session(user_input, session_id=None, creative=False, seed=None):
    """Get assistant response using session-scoped history.

    creative=False uses temperature=0.1 (deterministic). creative=True uses temperature=0.5.
    """
    try:
        print("💭 Task Mama is thinking of the perfect response...")
        sid = session_id or "__global__"
        hist = get_session_history(sid)
        hist.append({"role": "user", "content": user_input})
        temp = 0.5 if creative else 0.1
        ai_text = openai_chat(hist, max_tokens=300, temperature=temp, seed=seed)
        # append assistant reply
        hist.append({"role": "assistant", "content": ai_text})
        return ai_text
    except Exception as e:
        print(f"🚫 AI Response Error: {e}")
        fallback_responses = [
            "Oh sweetie, I'm having a little technical hiccup, but I'm still here for you! 💕 Tell me what's on your heart.",
            "Mama, I'm experiencing some connection issues, but you're not alone! 🤗 How can I support you right now?",
            "Beautiful mama, there's a little glitch on my end, but I'm still here to listen and help! 🌸 What do you need?"
        ]
        return random.choice(fallback_responses)

# 🤗 Response Analysis
def wants_pep_talk(user_response):
    positive = ['yes', 'y', 'sure', 'okay', 'ok', 'please', 'yeah', 'yep', 
               'i need that', 'that would help', 'i could use that']
    return user_response.lower().strip() in positive

def doesnt_want_pep_talk(user_response):
    negative = ['no', 'n', 'not now', 'maybe later', 'nope', 'not really', 
               'no thanks', 'not today']
    return user_response.lower().strip() in negative

# 🌸 Main Task Mama Chat Function - WITH ENHANCED VOICE SUPPORT & AUTO-TIMEOUT
def chat_with_task_mama():
    """Main conversation function with Task Mama - Text input only"""
    print("\n" + "="*70)
    print("🌸 Task Mama: Hello beautiful mama! 💕")
    print("🌸 Task Mama: I'm here to chat with you, support you, and help with anything you need!")
    print("🌸 Task Mama: Type your messages and I'll be here to help! 💖")
    print("="*70)

    # create a session id per chat run to isolate conversation histories
    session_id = f"session_{int(time.time()*1000)}_{random.randint(1000,9999)}"
    while True:
        try:
            # Get user input via text
            user_input, status = get_user_input()

            # Handle different statuses
            if status == 'interrupted':
                print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                return
            elif status == 'empty':
                print("🌸 Task Mama: I'm still here whenever you're ready to chat, sweetie! 💕")
                continue

            # Check if user wants to exit
            if user_input and user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                # If stdin is interactive, confirm; if piped (non-interactive), just exit
                try:
                    if os.isatty(0):
                        confirm = input("🌸 Are you sure you want to exit? (yes/no): ").strip().lower()
                        if confirm in ['y', 'yes']:
                            print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                            return
                        else:
                            print("🌸 Task Mama: Okay, I'm still here whenever you are ready! 💕")
                            continue
                    else:
                        # non-interactive stdin (piped) - exit immediately
                        print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                        return
                except Exception:
                    # On any error determining tty, just exit safely
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return

            # If no valid input, continue
            if not user_input:
                continue

            # ⭐ MODIFIED: Enhanced task progress detection with pep talk option
            if detect_task_progress_update(user_input):
                print("🌸 Task Mama: That's wonderful progress, sweetie! Let me celebrate your achievement! ✨")
                
                # Extract task progress information
                progress_data = extract_task_progress(user_input)
                task_name = progress_data.get("task_name", "your task")
                percentage = progress_data.get("task_percentage", 0)
                
                # ⭐ NEW: Find task ID from database
                task_id = find_task_id_from_database(task_name)
                
                # Generate JSON output with task ID
                progress_json = {
                    "task_name": task_name,
                    "task_percentage": percentage,
                    "id": task_id
                }
                
                # Print the JSON output
                print("🌸 Here's your progress summary:")
                print(json.dumps(progress_json, indent=2))
                
                # Generate motivational message (now includes tired check)
                # deterministic motivational message (seed can be provided per session for reproducibility)
                motivational_message = generate_motivational_message(task_name, percentage, session_id=session_id, seed=42)
                print(f"🌸 Task Mama: {motivational_message}")
                
                # ⭐ NEW: Always ask if they want a pep talk (regardless of completion percentage)
                print("🌸 Do you want to hear a pep talk? 💖 (yes/no)")
                
                pep_response, pep_status = get_user_input()
                
                if pep_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif wants_pep_talk(pep_response):
                    # ⭐ NEW: Classify emotion and fetch peptalk from that emotion group
                    detected = analyze_mama_emotions(user_input, seed=42)
                    peptalk_class = classify_user_emotion_to_peptalk_class(user_input, detected)
                    voice_url = get_peptalk_voice_url_by_emotion(peptalk_class)
                    if not voice_url:
                        # Fallback to generic fetch
                        voice_url = get_peptalk_voice_url()

                    if voice_url:
                        pep_talk_json = {"url": voice_url, "class": peptalk_class}
                    else:
                        # Fallback to default URL if API fails
                        pep_talk_json = {"url": "\\media\\voices\\default-peptalk.mp3", "class": peptalk_class}
                    print("🌸 Here's your motivational pep talk:")
                    print(json.dumps(pep_talk_json, indent=2))
                    print("🌸 Task Mama: Enjoy this special pep talk just for you, beautiful mama! 💕✨")
                else:
                    print("🌸 Task Mama: That's okay, sweetie. I'm still here to listen and chat with you. 💕")
                continue

            # Check for task planning request
            if detect_task_planning_request(user_input):
                print("🌸 Task Mama: I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.")
                
                task_details, task_status = get_user_input()
                
                if task_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif task_details:
                    print("🌸 Task Mama: Perfect! Let me organize these tasks for you...")
                    task_analysis = generate_task_analysis(task_details)
                    if isinstance(task_analysis, dict) and task_analysis.get('tasks'):
                        print("🌸 Here is your beautiful task schedule:")
                        print(json.dumps(task_analysis, indent=2))
                    else:
                        print("🌸 Task Mama: I couldn't detect specific tasks from what you shared. Could you be more specific about what you need to do? For example: 'I need to pick up kids at 3pm, go grocery shopping, and meet doctor tomorrow at 10am'")
                else:
                    print("🌸 Task Mama: No worries! Whenever you're ready to plan your day, just let me know! 💕")
                continue

            # Check for task query request
            if detect_task_query_request(user_input):
                print("🌸 Task Mama: Let me check your existing tasks for you! 🔍✨")
                task_response = query_existing_tasks(user_input)
                if task_response and task_response.get("message"):
                    print(task_response.get("message"))
                else:
                    print("🌸 Task Mama: I couldn't retrieve your tasks right now. Please try again later! 💕")
                continue

            # Check for recipe request
            if detect_recipe_request(user_input):
                print("🌸 Task Mama: I'd love to help you with some delicious recipe ideas! 🍳✨ What items do you have available in your pantry, kitchen, home, or fridge?")
                
                available_items, recipe_status = get_user_input()
                
                if recipe_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif available_items:
                    print("🌸 Task Mama: Wonderful! Let me create some amazing recipes for you...")
                    recipe_suggestions = generate_recipy_suggestion(available_items, user_input)
                    if recipe_suggestions and ("recipy" in recipe_suggestions or "recipy_name" in recipe_suggestions):
                        print("🌸 Here is your AI-suggested recipe:")
                        print(json.dumps(recipe_suggestions, indent=2))
                    else:
                        print("🌸 Task Mama: I'm having trouble generating recipes right now. Let me try again...")
                        fallback_recipe = generate_recipy_suggestion(available_items)
                        print("🌸 Here is your AI-suggested recipe:")
                        print(json.dumps(fallback_recipe, indent=2))
                else:
                    print("🌸 Task Mama: No problem! When you want cooking ideas, just tell me what you have available! 💕")
                continue

            # ⭐ UPDATED: Check for any emotional state that needs support (all 4 emotion types)
            emotions = analyze_mama_emotions(user_input, seed=42)
            #print(f"DEBUG: Emotions detected: {emotions}")  # Debug line
            
            # Check if any negative emotion is detected (emotion1, emotion2, or emotion4)
            needs_support = (emotions.get('is_emotion1', False) or 
                           emotions.get('is_emotion2', False) or 
                           emotions.get('is_emotion4', False) or
                           emotions.get('is_sad', False) or 
                           emotions.get('is_overwhelmed', False) or 
                           emotions.get('is_stressed', False))
            
            if needs_support:
                print("🌸 I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?")
                
                user_response, pep_status = get_user_input()
                
                if pep_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif wants_pep_talk(user_response):
                    # ⭐ NEW: Classify emotion and fetch peptalk for that emotion
                    peptalk_class = classify_user_emotion_to_peptalk_class(user_input, emotions)
                    voice_url = get_peptalk_voice_url_by_emotion(peptalk_class)
                    if not voice_url:
                        voice_url = get_peptalk_voice_url()

                    if voice_url:
                        pep_talk_json = {"url": voice_url, "class": peptalk_class}
                    else:
                        pep_talk_json = {"url": "\\media\\voices\\default-peptalk.mp3", "class": peptalk_class}
                    print("🌸 Here's your motivational pep talk:")
                    print(json.dumps(pep_talk_json, indent=2))
                    print("🌸 Task Mama: Enjoy this special pep talk just for you, beautiful mama! 💕✨")
                else:
                    print("🌸 Task Mama: That's okay, sweetie. I'm still here to listen and chat with you. 💕")
                continue

            # Handle happy emotions (emotion3) - NOW WITH PEP TALK SUPPORT
            if emotions.get('is_emotion3', False) or emotions.get('is_happy', False):
                # for normal replies, use deterministic low-temp response unless creativity desired
                reply = get_mama_response_for_session(user_input, session_id=session_id, creative=False, seed=None)
                print(f"🌸 Task Mama: {reply}")
                
                # ⭐ NEW: Also offer pep talk for happy emotions to celebrate and encourage
                print("🌸 You sound so positive! Would you like me to share an uplifting pep talk to celebrate your happiness? 💖 (yes/no)")
                
                pep_response, pep_status = get_user_input()
                
                if pep_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif wants_pep_talk(pep_response):
                    # ⭐ NEW: Classify emotion and fetch peptalk for happy emotion
                    peptalk_class = classify_user_emotion_to_peptalk_class(user_input, emotions)
                    voice_url = get_peptalk_voice_url_by_emotion(peptalk_class)
                    if not voice_url:
                        voice_url = get_peptalk_voice_url()

                    if voice_url:
                        pep_talk_json = {"url": voice_url, "class": peptalk_class}
                    else:
                        pep_talk_json = {"url": "\\media\\voices\\default-peptalk.mp3", "class": peptalk_class}
                    print("🌸 Here's your celebratory pep talk:")
                    print(json.dumps(pep_talk_json, indent=2))
                    print("🌸 Task Mama: Enjoy this special celebration pep talk just for you, beautiful mama! 💕✨")
                else:
                    print("🌸 Task Mama: That's okay, sweetie. Keep shining with that beautiful positivity! 💕")
                continue

            # Default: Normal conversation
            reply = get_mama_response_for_session(user_input, session_id=session_id, creative=False, seed=None)
            print(f"🌸 Task Mama: {reply}")

        except KeyboardInterrupt:
            print("\n🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
            return
        except Exception as e:
            print(f"\n🚫 Error: {e}")
            print("🌸 Task Mama: Something went wrong, but I'm still here for you! 💕")
            continue

# Replace main execution with this:
if __name__ == "__main__":
    print("🚀 Task Mama is starting up...")
    
    try:
        chat_with_task_mama()
    except KeyboardInterrupt:
        print("\n🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")

from google.cloud import texttospeech
import base64
import os
from django.conf import settings

def synthesize_speech_neural2_female_base64(text):
    """Convert text to speech and return base64-encoded audio (no file storage)"""
    # Set the API key from environment
    if hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY:
        os.environ['GOOGLE_API_KEY'] = settings.GOOGLE_API_KEY
    
    client = texttospeech.TextToSpeechClient()
    
    synthesis_input = texttospeech.SynthesisInput(text=text)
    
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Neural2-F",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    
    # Return base64-encoded audio
    audio_base64 = base64.b64encode(response.audio_content).decode('utf-8')
    return audio_base64


# Final binding: ensure the canonical motivational function is used at runtime
# (this overrides any earlier duplicate definitions that may remain in the file)
try:
    generate_motivational_message = generate_motivational_message_canonical
except NameError:
    # If for any reason the canonical implementation isn't present, leave as-is
    pass