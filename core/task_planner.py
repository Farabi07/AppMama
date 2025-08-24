# ai/task_planner.py

from openai import OpenAI
import json
from datetime import datetime, timedelta
import os
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

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
        f"- time: in HH:MM am/pm format or 'Not specified' (calculate relative times like 'after two hours')\n"
        f"- date: in YYYY-MM-DD format (normalize ANY date expression, e.g., 'tomorrow' = '{tomorrow.strftime('%Y-%m-%d')}', 'today' = '{now.strftime('%Y-%m-%d')}', etc.)\n\n"
        f"CRITICAL INSTRUCTIONS:\n"
        f"1. Include ALL tasks mentioned in the message, even if they conflict with other tasks\n"
        f"2. If tasks overlap at the same time, include BOTH as separate entries\n" 
        f"3. Include tasks even if the person says they're not important or can be rescheduled\n"
        f"4. Only include tasks that are definite actions to be performed, not wishes or possibilities\n\n"
        f"Message: {user_input}\n\n"
        f"Return a JSON array of ALL actionable tasks."
    )
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
            temperature=0.1
        )
        result_text = response.choices[0].message.content
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        gpt_tasks = json.loads(result_text)
        # Post-process to ensure correct date normalization
        for t in gpt_tasks:
            # Fix ambiguous dates if needed
            if "tomorrow" in t["task_name"].lower() or t.get("date", "") in ["tomorrow", "Tomorrow"]:
                t["date"] = tomorrow.strftime('%Y-%m-%d')
            elif "today" in t["task_name"].lower() or t.get("date", "") in ["today", "Today"]:
                t["date"] = now.strftime('%Y-%m-%d')
            # If date is missing, default to today
            if not t.get("date"):
                t["date"] = now.strftime('%Y-%m-%d')
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
