# 🌸 Task Mama - Complete Mother-Focused AI Assistant
# Features: Natural Conversations, Emotional Support, Task Management, Recipe Suggestions, Text Input, Progress Tracking

from openai import OpenAI
import requests
import random
import time
import json
import warnings
from datetime import datetime, timedelta
import re
import tempfile
import os

warnings.filterwarnings("ignore")

# 🔑 Initialize OpenAI client


# ⭐ NEW FEATURE: API Configuration for Schedule Settings
SCHEDULE_SETTINGS_URL = 'http://10.10.7.85:8001/task/api/v1/task/all/'

# ⭐ NEW FEATURE: Peptalk API Configuration
PEPTALK_SETTINGS_URL = 'http://10.10.7.85:8001/peptalk/api/v1/peptalk/all/'

def get_peptalk_voice_url():
    """Fetch peptalk voice URL from the API"""
    try:
        response = requests.get(PEPTALK_SETTINGS_URL)
        if response.status_code == 200:
            data = response.json()
            # The API returns a dict with a 'cities' key containing the list
            if isinstance(data, dict) and 'cities' in data:
                cities = data['cities']
                print(f"✅ Successfully retrieved {len(cities)} peptalk entries from API")
                
                # Loop through cities to get the 'voice' URL and return a random one
                voice_urls = []
                for city in cities:
                    voice_url = city.get('voice')
                    if voice_url:
                        voice_urls.append(voice_url)
                
                if voice_urls:
                    # Return a random voice URL
                    selected_url = random.choice(voice_urls)
                    # Format as requested: \media\voices\filename.mp3
                    if selected_url.startswith('/'):
                        formatted_url = selected_url.replace('/', '\\')
                    else:
                        formatted_url = '\\' + selected_url.replace('/', '\\')
                    return formatted_url
                else:
                    print("❌ No voice URLs found in peptalk entries")
                    return None
            else:
                print("❌ API response does not contain 'cities' key.")
                return None
        else:
            print(f"❌ Failed to retrieve peptalk entries. HTTP Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching peptalk settings: {e}")
        return None

def get_schedule_settings():
    """⭐ NEW FEATURE: Fetch company schedule settings from the API"""
    try:
        response = requests.get(SCHEDULE_SETTINGS_URL)
        if response.status_code == 200:
            data = response.json()
            # The API now returns a dict with a 'tasks' key containing the list
            if isinstance(data, dict) and 'tasks' in data:
                tasks = data['tasks']
                print(f"✅ Successfully retrieved {len(tasks)} tasks from company API")
                return tasks
            else:
                print("❌ API response does not contain 'tasks' key.")
                return None
        else:
            print(f"❌ Failed to retrieve tasks. HTTP Status Code: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error fetching schedule settings: {e}")
        return None

# 🧠 Global Variables
user_tasks = []
daily_schedule = {}
conversation_history = [
    {
        "role": "system",
        "content": """You are Task Mama, a gentle, caring AI assistant specifically designed for mothers. 
        
        Your personality:
        - Speak with a warm, soft, caring voice like a supportive friend
        - Use nurturing language with emojis like 💕, 🌸, 🤗, 💖
        - Always acknowledge the challenges of motherhood
        - Be understanding, patient, and encouraging
        - Offer practical advice and emotional support
        - Answer any questions using your knowledge like a helpful friend
        - Be conversational and natural in your responses
        
        Your capabilities:
        1. Normal conversations and answering any questions using your knowledge
        2. Emotional support and understanding mother's feelings
        3. Task management and daily planning assistance (only when specifically requested)
        4. Recipe suggestions (only when specifically requested)
        5. Gentle advice and suggestions on any topic
        6. Accept text input from users
        7. Track task progress and provide motivation
        
        Always respond as if you're talking to a dear friend who is doing her best as a mother.
        Answer questions naturally using your knowledge without triggering special functions unless specifically requested."""
    }
]

def get_user_input():
    """
    Get user input via text.
    Returns tuple: (input_text, status)
    Status can be: 'success', 'interrupted', 'empty'
    """
    try:
        user_input = input("💕 You: ").strip()
        return user_input, 'success' if user_input else 'empty'
    except KeyboardInterrupt:
        return "", 'interrupted'

# ⭐ NEW FEATURE: Task Progress Detection
def detect_task_progress_update(user_input):
    """Detect if user is reporting task progress completion"""
    try:
        prompt = f"""
        Analyze this user input to determine if they are reporting progress on a task.
        
        User input: "{user_input}"
        
        Look for patterns like:
        - "I have completed [percentage]% of [task]"
        - "I finished [fraction] of [task]" 
        - "I'm [percentage]% done with [task]"
        - "I completed half/quarter/third of [task]"
        - "I finished [task] partially"
        - Any variation indicating task progress
        
        Return true if the user is reporting task progress, false otherwise.
        
        Respond with only "true" or "false".
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=10,
            temperature=0.1
        )
        
        result = response.choices[0].message.content.strip().lower()
        return result == "true"
        
    except Exception as e:
        print(f"Error detecting task progress: {e}")
        # Fallback to keyword detection
        text = user_input.lower()
        progress_keywords = [
            'completed', 'finished', 'done', '%', 'percent', 'percentage',
            'half', 'quarter', 'third', 'fourth', 'fifth', 'one fourth',
            'one fifth', 'one third', 'one half', 'partially', 'partly'
        ]
        return any(keyword in text for keyword in progress_keywords)

def extract_task_progress(user_input):
    """Extract task name and progress percentage from user input - IMPROVED VERSION"""
    try:
        prompt = f"""
        Analyze this user input to extract task progress information.
        
        User input: "{user_input}"
        
        CRITICAL: Extract the EXACT task name mentioned by the user.
        
        Examples:
        - "i have completed playing football 50%" → task_name: "playing football", task_percentage: 50
        - "i finished half of cleaning kitchen" → task_name: "cleaning kitchen", task_percentage: 50
        - "i completed 25% of homework" → task_name: "homework", task_percentage: 25
        
        Conversion rules for fractions:
        - "half" or "one half" = 50%
        - "quarter" or "one fourth" = 25%
        - "three quarters" or "three fourth" = 75%
        - "one third" = 33%
        - "two thirds" = 67%
        - "one fifth" = 20%
        - "full" or "complete" = 100%
        
        Return ONLY this JSON format:
        {{
            "task_name": "exact task name from user input",
            "task_percentage": 50
        }}
        
        IMPORTANT: 
        - Use the EXACT task name the user mentioned
        - Don't add or remove words from the task name
        - If you can't find a clear task name, use "task"
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.1
        )
        
        result_text = response.choices[0].message.content.strip()
        
        # Clean up the response
        if result_text.startswith("```json"):
            result_text = result_text.replace("```json", "").replace("```", "").strip()
        elif result_text.startswith("```"):
            result_text = result_text.replace("```", "").strip()
        
        try:
            progress_data = json.loads(result_text)
            
            # Validate the extracted data
            task_name = progress_data.get("task_name", "").strip()
            task_percentage = progress_data.get("task_percentage", 0)
            
            # If task name is generic or empty, try fallback
            if not task_name or task_name.lower() in ["task", "unknown task", "the task"]:
                fallback_data = extract_progress_fallback(user_input)
                if fallback_data.get("task_name") != "unknown task":
                    task_name = fallback_data.get("task_name")
            
            return {
                "task_name": task_name if task_name else "task",
                "task_percentage": task_percentage
            }
            
        except json.JSONDecodeError:
            # Fallback extraction
            return extract_progress_fallback(user_input)
            
    except Exception as e:
        print(f"Error extracting task progress: {e}")
        return extract_progress_fallback(user_input)

def extract_progress_fallback(user_input):
    """Fallback method to extract progress using basic pattern matching - IMPROVED VERSION"""
    text = user_input.lower()
    
    # Extract percentage
    percentage = 0
    if 'half' in text or 'one half' in text:
        percentage = 50
    elif 'quarter' in text or 'one fourth' in text or '1/4' in text:
        percentage = 25
    elif 'third' in text or 'one third' in text or '1/3' in text:
        percentage = 33
    elif 'fifth' in text or 'one fifth' in text or '1/5' in text:
        percentage = 20
    elif 'full' in text or 'complete' in text or 'finished' in text:
        percentage = 100
    else:
        # Look for explicit percentage
        percentage_match = re.search(r'(\d+)%', text)
        if percentage_match:
            percentage = int(percentage_match.group(1))
    
    # IMPROVED: Extract task name with better logic
    task_name = "unknown task"
    
    # Try multiple patterns to extract task name
    words = user_input.split()
    
    # Pattern 1: "i have completed [task] [percentage]%
    # Pattern 2: "i completed [percentage]% of [task]"
    # Pattern 3: "i have completed [percentage]% [task]"
    
    # Look for task name after common progress indicators
    progress_indicators = ['completed', 'finished', 'done', 'complete']
    
    for i, word in enumerate(words):
        word_lower = word.lower()
        
        # Pattern: "completed playing football 50%"
        if word_lower in progress_indicators and i + 1 < len(words):
            # Get words after the progress indicator until we hit percentage or end
            task_words = []
            for j in range(i + 1, len(words)):
                next_word = words[j]
                # Stop if we hit a percentage or number
                if re.search(r'\d+%|\d+', next_word) or next_word.lower() in ['percent', 'percentage']:
                    break
                # Skip common words
                if next_word.lower() not in ['the', 'a', 'an', 'my', 'of']:
                    task_words.append(next_word)
            
            if task_words:
                task_name = ' '.join(task_words)
                break
        
        # Pattern: "50% of playing football"
        elif 'of' in word_lower and i + 1 < len(words):
            # Get words after "of"
            task_words = []
            for j in range(i + 1, len(words)):
                next_word = words[j]
                if next_word.lower() not in ['the', 'a', 'an', 'my']:
                    task_words.append(next_word)
            
            if task_words:
                task_name = ' '.join(task_words)
                break
    
    # Clean up task name
    task_name = task_name.strip().rstrip('.,!?')
    
    return {
        "task_name": task_name if task_name != "unknown task" else "task",
        "task_percentage": percentage
    }

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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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
            model="gpt-4",
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
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.7
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

# 🎭 Enhanced Emotion Detection - FIXED to be more specific
def analyze_mama_emotions(user_input):
    """Analyze mama's emotional state using OpenAI - Only trigger for explicit emotional distress"""
    try:
        prompt = (
            "Analyze the following message for emotional distress indicators. "
            "Return true for is_sad if the user mentions: sad, depressed, down, low, blue, not feeling good, not feeling well, bad mood, terrible, awful, crying, broken, defeated, hopeless, empty. "
            "Return true for is_overwhelmed if they mention: overwhelmed, swamped, too much, can't cope, breaking down, falling apart. "
            "Return true for is_stressed if they mention: stressed, stress, anxious, worried, pressure. "
            "Return true for is_happy if they mention: happy, great, wonderful, blessed, grateful, amazing, good mood. "
            "DO NOT trigger emotions for normal task planning or scheduling requests. "
            "Respond with a JSON object like: "
            "{\"is_sad\": true/false, \"is_overwhelmed\": true/false, \"is_happy\": true/false, \"is_stressed\": true/false, \"sadness_score\": float, \"emotions\": {}}. "
            "Message: " + user_input
        )
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.0
        )
        result_text = response.choices[0].message.content
        # Try to parse JSON from response
        try:
            emotions = json.loads(result_text)
            # Always check keyword detection as backup and merge results
            keyword_emotions = detect_emotions_by_keywords(user_input)
            
            # If keyword detection finds emotions but API doesn't, use keyword results
            if (keyword_emotions['is_sad'] or keyword_emotions['is_overwhelmed'] or keyword_emotions.get('is_stressed', False)):
                if not (emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False)):
                    print("DEBUG: Using keyword detection as API missed emotions")
                    return keyword_emotions
            
            return emotions
        except Exception:
            # Fallback to keyword detection if parsing fails
            return detect_emotions_by_keywords(user_input)
    except Exception as e:
        print(f"Emotion analysis error: {e}")
        return detect_emotions_by_keywords(user_input)

def detect_emotions_by_keywords(user_input):
    """Fallback emotion detection using keywords - ONLY for explicit emotional distress"""
    text = user_input.lower()
    
    # UPDATED: More specific sad keywords - only explicit emotional statements
    sad_keywords = ['i am sad', 'feeling sad', 'i feel sad', 'i am depressed', 'feeling depressed', 
                   'i am not feeling well', 'not feeling good', 'feeling down', 'feeling low', 'feeling blue', 'feeling empty',
                   'i am stressed', 'feeling stressed', 'i feel stressed', 'bad mood', 'in a bad mood',
                   'feeling overwhelmed', 'i am overwhelmed', 'i feel overwhelmed', 'having a hard time',
                   'struggling emotionally', 'emotionally struggling', 'feeling terrible emotionally', 
                   'feeling awful emotionally', 'emotionally drained', 'feeling hopeless',
                   'feeling defeated', 'feeling broken', 'crying', 'want to cry']
    
    # REMOVED: Generic overwhelm keywords that could be confused with normal planning
    overwhelm_keywords = ['feeling swamped', 'completely overwhelmed', 'emotionally overwhelmed',
                         'can\'t cope', 'breaking down', 'falling apart', 'too much stress']
    
    happy_keywords = ['i am happy', 'feeling happy', 'i feel happy', 'feeling great', 'doing great',
                     'i am blessed', 'feeling blessed', 'so grateful', 'feeling wonderful',
                     'having a good day', 'feeling amazing', 'in a good mood']
    
    is_sad = any(keyword in text for keyword in sad_keywords)
    is_overwhelmed = any(keyword in text for keyword in overwhelm_keywords)
    is_happy = any(keyword in text for keyword in happy_keywords)
    
    # Check for stressed keywords separately
    is_stressed = any(stress_word in text for stress_word in ['stressed', 'stress', 'feeling stressed', 'i am stressed', 'i feel stressed'])
    
    return {
        'is_sad': is_sad,
        'is_overwhelmed': is_overwhelmed,
        'is_happy': is_happy,
        'is_stressed': is_stressed,
        'sadness_score': 0.7 if is_sad else 0.3 if is_overwhelmed else 0.3 if is_stressed else 0.1,
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
    
    return any(phrase in text for phrase in recipe_phrases)

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
            model="gpt-4",
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
            model="gpt-4",
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
            model="gpt-4",
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
            model="gpt-4",
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
            model="gpt-4",
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
            model="gpt-4",
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

Return ONLY this JSON format:
{{
    "priority_score": 8.5,
    "priority_level": "High Priority",
    "category": "Child Care & Safety",
    "reasoning": "Brief explanation of why this priority was assigned",
    "time_flexibility": "rigid|semi-flexible|flexible",
    "consequences_of_delay": "High|Medium|Low"
}}

Priority Levels (use exactly these strings):
- "High Priority" (8-10): Cannot be delayed, affects safety/welfare, or has severe consequences
- "Medium Priority" (5-7): Important but some flexibility exists
- "Low Priority" (1-4): Can be postponed without major issues

Only return valid JSON, no other text.
"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
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
                model="gpt-4",
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
                model="gpt-4",
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

Create 3 unique recipes with these names:
- Recipe 1: [Creative name using available ingredients]
- Recipe 2: [Different creative name using available ingredients] 
- Recipe 3: [Third different creative name using available ingredients]

For each recipe, write 5-6 sentences with:
- Step-by-step cooking instructions
- Cooking times and temperatures
- Tips for mothers and kids
- Serving suggestions

Format your response as a clear list of 3 recipes with names and detailed descriptions.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
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

def explain_cooking_terms(text):
    """
    Add explanations for difficult cooking terms in the recipe text.
    For example, 'sauté' will be explained the first time it appears.
    """
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

        return {
            "meal_type": meal_type,
            "task_catagory": "Recipy task",
            "time": now.strftime('%H:%M'),  # Changed to 24-hour format
            "date": now.strftime('%Y-%m-%d'),
            "items_available": available_items,
            "items_needed": "Cooking oil, salt, black pepper, water, onions",
            "recipy_name": recipe_names[:3],
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
    
    return {
        "meal_type": meal_type,
        "task_catagory": "Recipy task",
        "time": now.strftime('%H:%M'),  # Changed to 24-hour format
        "date": now.strftime('%Y-%m-%d'),
        "items_available": available_items,
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
                model="gpt-4",
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
            context=f"Other tasks: {all_task_descriptions}"
        )
        task_assigned = prioritizer.analyze_task_responsibility(
            t["task_name"],
            context=f"Other tasks: {all_task_descriptions}"
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
        for idx, task in enumerate(group_sorted):
            # Highest priority in group stays as is, others get downgraded
            if idx == 0:
                final_priority = "High Priority"
            elif idx == 1:
                final_priority = "Medium Priority"
            else:
                final_priority = "Low Priority"
            # Always include all tasks, just adjust priority
            final_tasks.append({
                "task_name": task["task_name"],
                "time": task["time"],
                "date": task["date"],
                "task_assigned": task["task_assigned"],
                "priority": final_priority,
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
    """Add message to conversation history"""
    global conversation_history
    conversation_history.append({"role": role, "content": content})
    
    # Keep manageable history
    if len(conversation_history) > 25:
        conversation_history = [conversation_history[0]] + conversation_history[-24:]

def get_mama_response(user_input):
    """Get AI response with mama's context"""
    try:
        print("💭 Task Mama is thinking of the perfect response...")
        
        add_to_conversation("user", user_input)
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=conversation_history,
            max_tokens=300,
            temperature=0.8
        )
        
        ai_response = response.choices[0].message.content
        add_to_conversation("assistant", ai_response)
        
        return ai_response
        
    except Exception as e:
        print(f"🚫 AI Response Error: {e}")
        
        # Warm fallback responses for mama
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
                motivational_message = generate_motivational_message(task_name, percentage)
                print(f"🌸 Task Mama: {motivational_message}")
                
                # ⭐ NEW: Always ask if they want a pep talk (regardless of completion percentage)
                print("🌸 Do you want to hear a pep talk? 💖 (yes/no)")
                
                pep_response, pep_status = get_user_input()
                
                if pep_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif wants_pep_talk(pep_response):
                    # ⭐ NEW: Show JSON with voice URL from API for pep talk
                    voice_url = get_peptalk_voice_url()
                    if voice_url:
                        pep_talk_json = {
                            "url": voice_url
                        }
                    else:
                        # Fallback to default URL if API fails
                        pep_talk_json = {
                            "url": "\\media\\voices\\default-peptalk.mp3"
                        }
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

            # ⭐ MODIFIED: Check for emotional distress with YouTube pep talk
            emotions = analyze_mama_emotions(user_input)
            #print(f"DEBUG: Emotions detected: {emotions}")  # Debug line
            if (emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False)):
                print("🌸 I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?")
                
                user_response, pep_status = get_user_input()
                
                if pep_status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return
                elif wants_pep_talk(user_response):
                    # ⭐ NEW: Show JSON with voice URL from API for emotional pep talk
                    voice_url = get_peptalk_voice_url()
                    if voice_url:
                        pep_talk_json = {
                            "url": voice_url
                        }
                    else:
                        # Fallback to default URL if API fails
                        pep_talk_json = {
                            "url": "\\media\\voices\\default-peptalk.mp3"
                        }
                    print("🌸 Here's your motivational pep talk:")
                    print(json.dumps(pep_talk_json, indent=2))
                    print("🌸 Task Mama: Enjoy this special pep talk just for you, beautiful mama! 💕✨")
                else:
                    print("🌸 Task Mama: That's okay, sweetie. I'm still here to listen and chat with you. 💕")
                continue

            # Handle happy emotions
            if emotions['is_happy']:
                reply = get_mama_response(user_input)
                print(f"🌸 Task Mama: {reply}")
                continue

            # Default: Normal conversation
            reply = get_mama_response(user_input)
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