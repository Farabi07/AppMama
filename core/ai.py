# 🌸 Task Mama - Complete Mother-Focused AI Assistant with Voice Input & Auto-Timeout
# Features: Natural Conversations, Emotional Support, Task Management, Recipe Suggestions, Voice & Text Input

from openai import OpenAI
import requests
import random
import time
import json
import warnings
from datetime import datetime, timedelta
import re
import pyaudio
import wave
import threading
import tempfile
import os
import openai
warnings.filterwarnings("ignore")

  # Use your actual API key here
openai.api_key = os.getenv('OPENAI_API_KEY')
# 🎙️ Voice Recording Configuration
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
SILENCE_THRESHOLD = 400  # Adjust based on your microphone sensitivity
SILENCE_DURATION = 3  # seconds of silence before stopping recording
VOICE_TIMEOUT = 4  # seconds of total silence before ending voice conversation

class VoiceRecorder:
    def __init__(self):
        self.audio = pyaudio.PyAudio()
        self.frames = []
        self.is_recording = False
        self.silence_start = None
        self.total_silence_start = None
        self.received_any_input = False
        
    def record_with_timeout(self):
        """Record audio until silence is detected or timeout occurs"""
        stream = self.audio.open(format=FORMAT,
                                channels=CHANNELS,
                                rate=RATE,
                                input=True,
                                frames_per_buffer=CHUNK)
        
        print("🎙️  Task Mama: I'm listening... speak now! (I'll stop when you pause for 3 seconds)")
        print("🎙️  Task Mama: Speak clearly and take your time! 💕")
        
        self.frames = []
        self.is_recording = True
        self.silence_start = None
        self.total_silence_start = time.time()  # Start timeout timer immediately
        self.received_any_input = False
        
        try:
            while self.is_recording:
                data = stream.read(CHUNK)
                self.frames.append(data)
                
                # Convert audio data to check volume level
                import audioop
                volume = audioop.rms(data, 2)
                
                if volume < SILENCE_THRESHOLD:
                    # Check if this is the first silence after receiving input
                    if self.silence_start is None:
                        self.silence_start = time.time()
                    elif time.time() - self.silence_start > SILENCE_DURATION:
                        if self.received_any_input:
                            print("🎙️  Task Mama: Perfect! I heard you loud and clear! Processing your message... 💕")
                            return "input_received"
                        else:
                            # No input received during the entire session
                            if time.time() - self.total_silence_start > VOICE_TIMEOUT:
                                print("🎙️  Task Mama: I didn't hear anything for a while. Let's try a different way to chat! 💕")
                                return "timeout"
                else:
                    # Sound detected - reset silence timers and mark input received
                    self.silence_start = None
                    self.total_silence_start = time.time()  # Reset timeout timer when sound is detected
                    self.received_any_input = True
                    
        except KeyboardInterrupt:
            print("🎙️  Task Mama: Recording stopped by user.")
            return "interrupted"
            
        finally:
            stream.stop_stream()
            stream.close()
            
        return "completed"
    
    def save_audio_to_file(self, frames):
        """Save recorded frames to a temporary WAV file"""
        if not frames:
            return None
            
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_filename = temp_file.name
        temp_file.close()
        
        # Write audio data to the file
        wf = wave.open(temp_filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return temp_filename
    
    def transcribe_audio(self, audio_file_path):
        """Use OpenAI Whisper to transcribe audio to text"""
        if not audio_file_path or not os.path.exists(audio_file_path):
            return None
            
        try:
            with open(audio_file_path, 'rb') as audio_file:
                transcript = openai.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # You can change this or remove to auto-detect
                )
            return transcript.text.strip()
        except Exception as e:
            print(f"🚫 Transcription Error: {e}")
            return None
        finally:
            # Clean up the temporary file
            if os.path.exists(audio_file_path):
                os.remove(audio_file_path)
    
    def cleanup(self):
        """Clean up PyAudio resources"""
        self.audio.terminate()

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
        6. Accept both voice and text input from users
        
        Always respond as if you're talking to a dear friend who is doing her best as a mother.
        Answer questions naturally using your knowledge without triggering special functions unless specifically requested."""
    }
]

# Initialize voice recorder
voice_recorder = VoiceRecorder()

def get_user_input(input_mode):
    """
    Get user input based on selected mode (voice or text).
    Returns tuple: (input_text, status)
    Status can be: 'success', 'timeout', 'interrupted', 'empty'
    """
    if input_mode == "voice":
        return get_voice_input()
    else:
        try:
            user_input = input("💕 You: ").strip()
            return user_input, 'success' if user_input else 'empty'
        except KeyboardInterrupt:
            return "", 'interrupted'

def get_voice_input():
    """Record voice input and convert to text using Whisper"""
    try:
        # Record audio with timeout detection
        recording_result = voice_recorder.record_with_timeout()
        
        if recording_result == "timeout":
            return "", 'timeout'
        elif recording_result == "interrupted":
            return "", 'interrupted'
        elif not voice_recorder.frames or not voice_recorder.received_any_input:
            return "", 'empty'
        
        # Save audio to temporary file
        audio_file_path = voice_recorder.save_audio_to_file(voice_recorder.frames)
        
        if not audio_file_path:
            return "", 'empty'
        
        # Transcribe using Whisper
        print("🌸 Task Mama: Converting your beautiful voice to text... 💭")
        transcribed_text = voice_recorder.transcribe_audio(audio_file_path)
        
        if transcribed_text:
            print(f"🎙️  I heard you say: \"{transcribed_text}\"")
            return transcribed_text, 'success'
        else:
            print("🌸 Task Mama: I'm sorry, I couldn't understand what you said. Could you try speaking a bit louder or clearer? 💕")
            return "", 'empty'
            
    except Exception as e:
        print(f"🚫 Voice Input Error: {e}")
        print("🌸 Task Mama: There was an issue with voice recording. Let me try again! 💕")
        return "", 'error'

def choose_input_mode():
    """Ask user to choose between text or voice input"""
    print("\n🌸 Task Mama: How would you like to chat with me today? 💕")
    print("   1️⃣  Type 'text' for typing your messages")
    print("   2️⃣  Type 'voice' to speak to me")
    
    while True:
        try:
            choice = input("💕 Your choice (text/voice): ").strip().lower()
            if choice in ['text', 'type', 'typing', '1']:
                print("🌸 Task Mama: Perfect! We'll chat by typing. I'm excited to hear from you! 💕")
                return "text"
            elif choice in ['voice', 'speak', 'speaking', 'talk', 'talking', '2']:
                print("🌸 Task Mama: Wonderful! I'll listen to your beautiful voice. Make sure your microphone is working! 🎙️💕")
                print("🎙️  Note: When you speak, I'll wait for 3 seconds of silence before processing your message.")
                print("🎙️  If you remain silent for 4+ seconds total, we'll switch back to choosing input mode.")
                return "voice"
            else:
                print("🌸 Task Mama: Please choose either 'text' or 'voice', sweetie! 💕")
        except KeyboardInterrupt:
            print("\n🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
            return "exit"

# 🎭 Enhanced Emotion Detection - FIXED to be more specific
def analyze_mama_emotions(user_input):
    """Analyze mama's emotional state using OpenAI - Only trigger for explicit emotional distress"""
    try:
        prompt = (
            "Analyze the following message ONLY for explicit emotional distress indicators. "
            "Only return true for emotions if the user explicitly mentions feeling sad, depressed, overwhelmed, stressed, not feeling well, bad mood, or similar negative emotional states. "
            "DO NOT trigger emotions for normal task planning or scheduling requests. "
            "Respond with a JSON object like: "
            "{\"is_sad\": true/false, \"is_overwhelmed\": true/false, \"is_happy\": true/false, \"is_stressed\": true/false, \"sadness_score\": float, \"emotions\": {}}. "
            "Message: " + user_input
        )
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.0
        )
        result_text = response.choices[0].message.content
        # Try to parse JSON from response
        try:
            emotions = json.loads(result_text)
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
                   'i am not feeling well', 'not feeling good', 'feeling down', 'feeling low',
                   'i am stressed', 'feeling stressed', 'i feel stressed', 'bad mood', 'in a bad mood',
                   'feeling overwhelmed', 'i am overwhelmed', 'i feel overwhelmed', 'having a hard time',
                   'struggling today', 'not doing well', 'feeling terrible', 'feeling awful']
    
    # REMOVED: Generic overwhelm keywords that could be confused with normal planning
    overwhelm_keywords = ['feeling swamped', 'completely overwhelmed', 'emotionally overwhelmed',
                         'can\'t cope', 'breaking down', 'falling apart', 'too much stress']
    
    happy_keywords = ['i am happy', 'feeling happy', 'i feel happy', 'feeling great', 'doing great',
                     'i am blessed', 'feeling blessed', 'so grateful', 'feeling wonderful',
                     'having a good day', 'feeling amazing', 'in a good mood']
    
    is_sad = any(keyword in text for keyword in sad_keywords)
    is_overwhelmed = any(keyword in text for keyword in overwhelm_keywords)
    is_happy = any(keyword in text for keyword in happy_keywords)
    
    return {
        'is_sad': is_sad,
        'is_overwhelmed': is_overwhelmed,
        'is_happy': is_happy,
        'sadness_score': 0.7 if is_sad else 0.3 if is_overwhelmed else 0.1,
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

# Task extraction and analysis functions (keeping original functionality)
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
        response = openai.chat.completions.create(
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

class DynamicTaskPrioritizer:
    def __init__(self):
        self.openai_openai = openai

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
            response = self.openai_openai.chat.completions.create(
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
            response = self.openai_openai.chat.completions.create(
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

    def analyze_task_category(self, task_description, context=""):
        """
        Use AI to determine the task_category: Normal task, Health task, or Recipy task.
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
    "task_category": "Normal task"
}}

Possible values for task_category:
- "Normal task"
- "Health task"
- "Recipy task"
"""
        try:
            response = self.openai_openai.chat.completions.create(
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
            return cat_data.get("task_category", "Normal task")
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
            print(f"Detected meal type: {meal}")
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
        response = openai.chat.completions.create(
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



import re

def parse_ai_recipe_response(ai_response, available_items, now, fallback_meal_type="Other meal"):
    """
    Parse AI response and convert to our JSON format, always prefixing each recipe 
    with 'Recipe 1:', 'Recipe 2:', etc. Also explain difficult cooking terms.
    """

    try:
        # --- Extract meal type from AI response ---
        match = re.search(r"meal type[:\-]?\s*([A-Za-z]+)", ai_response, re.IGNORECASE)
        meal_type = match.group(1).capitalize() if match else fallback_meal_type

        # --- Parse recipes ---
        lines = ai_response.split('\n')
        recipes = []
        recipe_names = []
        current_recipe = ""
        current_name = ""
        recipe_count = 0

        for line in lines:
            line = line.strip()
            if re.match(r"^Recipe\s+\d+:", line, re.IGNORECASE):
                if current_recipe and current_name:
                    recipe_count += 1
                    explained_recipe = explain_cooking_terms(current_recipe.strip())
                    recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
                    recipe_names.append(current_name.strip())
                current_name = line
                current_recipe = ""
            elif line and not line.startswith("Recipe"):
                current_recipe += line + " "

        # Add the last recipe
        if current_recipe and current_name:
            recipe_count += 1
            explained_recipe = explain_cooking_terms(current_recipe.strip())
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(current_name.strip())

        # Ensure exactly 3 recipes
        while len(recipes) < 3:
            recipe_count += 1
            fallback = "Cook the available ingredients together with seasonings until tender. Adjust cooking time based on ingredients used."
            explained_recipe = explain_cooking_terms(fallback)
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(f"Recipe {recipe_count}: Mixed Ingredient Dish")

        return {
            "meal_type": meal_type,
            "task_category": "Recipy task",
            "time": now.strftime('%I:%M %p'),
            "date": now.strftime('%Y-%m-%d'),
            "items_available": available_items,
            "items_needed": "Cooking oil, salt, black pepper, water, onions",
            "recipy_name": recipe_names[:3],
            "recipy": recipes[:3]
        }

    except Exception:
        return create_smart_recipe_from_ingredients(available_items, now, fallback_meal_type)



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
        "task_category": "Recipy task",
        "time": now.strftime('%I:%M %p'),
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
            response = openai.chat.completions.create(
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
        task_category = prioritizer.analyze_task_category(
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
            "task_category": task_category
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
                "task_category": task["task_category"]
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
        
        response = openai.chat.completions.create(
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
    print("\n" + "="*70)
    print("🌸 Task Mama: Hello beautiful mama! 💕")
    print("🌸 Task Mama: I'm here to chat with you, support you, and help with anything you need!")
    print("🌸 Task Mama: I can listen to your voice OR you can type to me!")
    print("="*70)

    while True:
        input_mode = choose_input_mode()
        if input_mode == "exit":
            break
            
        conversation_active = True
        
        while conversation_active:
            if input_mode == "voice":
                print("🎙️  Voice Mode Activated! Speak clearly and I'll listen with love! 💕")
                print("🎙️  Remember: I'll wait for 3 seconds of silence before processing your message.")
                print("🎙️  If you remain silent for 4+ seconds total, we'll switch back to choosing input mode.")
                print("   (Say 'exit' or 'goodbye' when you're ready to go)")
            else:
                print("💕 Text Mode: Type your messages and press Enter!")
                print("   (Type 'exit' or 'goodbye' when you're ready to go)")

            try:
                user_input, status = get_user_input(input_mode)

                # Handle different statuses
                if status == 'timeout':
                    print("🌸 Task Mama: I didn't hear anything for a while, sweetie. Let's choose how you'd like to continue chatting! 💕")
                    conversation_active = False  # Break inner loop to restart input mode selection
                    continue
                elif status == 'interrupted':
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return  # Exit completely
                elif status == 'empty':
                    if input_mode == "voice":
                        print("🌸 Task Mama: I didn't catch that, sweetie. Could you try again? 💕")
                    continue
                elif status == 'error':
                    print("🌸 Task Mama: There was a technical issue. Let me try to help you in a different way! 💕")
                    continue

                # Check if user wants to exit
                if user_input and user_input.lower() in ['exit', 'quit', 'bye', 'goodbye']:
                    print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                    return

                # If no valid input, continue
                if not user_input:
                    continue

                # Check for task planning request FIRST
                if detect_task_planning_request(user_input):
                    print("🌸 Task Mama: I'd love to help you organize your day! 📋✨ Please tell me about all the tasks you need to do, and I'll create a beautiful schedule for you.")
                    if input_mode == "voice":
                        print("\n🎙️  Tell me about your tasks... I'm listening! 💕")
                    
                    task_details, task_status = get_user_input(input_mode)
                    
                    if task_status == 'timeout':
                        print("🌸 Task Mama: I didn't hear anything for a while, sweetie. Let's choose how you'd like to continue chatting! 💕")
                        conversation_active = False
                        continue
                    elif task_status == 'interrupted':
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

                # Check for recipe request
                if detect_recipe_request(user_input):
                    print("🌸 Task Mama: I'd love to help you with some delicious recipe ideas! 🍳✨ What items do you have available in your pantry, kitchen, home, or fridge?")
                    if input_mode == "voice":
                        print("\n🎙️  Tell me what ingredients you have... I'm listening! 💕")
                    
                    available_items, recipe_status = get_user_input(input_mode)
                    
                    if recipe_status == 'timeout':
                        print("🌸 Task Mama: I didn't hear anything for a while, sweetie. Let's choose how you'd like to continue chatting! 💕")
                        conversation_active = False
                        continue
                    elif recipe_status == 'interrupted':
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

                # Check for emotional distress ONLY if not a task planning or recipe request
                emotions = analyze_mama_emotions(user_input)
                if (emotions['is_sad'] or emotions['is_overwhelmed'] or emotions.get('is_stressed', False)):
                    print("🌸 I can sense you might not be feeling your best right now. 💕 Would you like me to share a pep talk to motivate you Mama 💖 (yes/no)?")
                    if input_mode == "voice":
                        print("\n🎙️  Just say yes or no... I'm here for you! 💕")
                    
                    user_response, pep_status = get_user_input(input_mode)
                    
                    if pep_status == 'timeout':
                        print("🌸 Task Mama: I didn't hear anything for a while, sweetie. Let's choose how you'd like to continue chatting! 💕")
                        conversation_active = False
                        continue
                    elif pep_status == 'interrupted':
                        print("🌸 Task Mama: Take care, beautiful mama! You're doing amazingly! 💖✨")
                        return
                    elif wants_pep_talk(user_response):
                        print("🌸 Task Mama: 😢 I am always here with you, beautiful mama. You are stronger than you know, and tomorrow will be a brighter day. 💕")
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
    print("🎙️  Checking microphone and voice capabilities...")
    
    # Check if required libraries are available
    try:
        import pyaudio
        print("✅ Voice input ready!")
    except ImportError:
        print("⚠️  Voice input not available. Install pyaudio with: pip install pyaudio")
        print("   Falling back to text-only mode...")
        
    try:
        chat_with_task_mama()
    finally:
        # Clean up voice recorder resources when program truly exits
        try:
            voice_recorder.cleanup()
        except Exception:
            pass