# dynamic_task_prioritizer.py
from openai import OpenAI
import json
import os

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

class DynamicTaskPrioritizer:
    def __init__(self):
        self.openai_client = client

    def analyze_task_priority(self, task_description):
        """
        Use AI to dynamically analyze task priority based on natural language understanding.
        """
        prompt = f"""
        You are an expert task prioritization assistant. Analyze this task and determine its priority based on natural language understanding:

        TASK: "{task_description}"

        Consider these factors naturally:
        - SAFETY: Does this affect someone's safety, health, or basic needs?
        - TIME SENSITIVITY: How flexible is the timing? Are there consequences for delay?
        - IMPACT: What happens if this task is delayed or not completed?

        Return only this JSON format:
        {{
            "priority_level": "High Priority" | "Medium Priority" | "Low Priority",
            "priority_score": 8.5,  # A numeric value for the task priority (1-10 scale)
        }}
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.2,
            )
            result_text = response.choices[0].message.content.strip()
            return json.loads(result_text)
        except Exception as e:
            return {"priority_level": "Medium Priority", "priority_score": 5.0}

    def analyze_task_responsibility(self, task_description):
        """
        Determine who is assigned the task (Self, Partner, Child).
        """
        prompt = f"""
        TASK: "{task_description}"

        Who will perform this task? 
        Analyze the task description and return one of the following values:
        - "Self"
        - "Partner"
        - "Child"
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.2,
            )
            result_text = response.choices[0].message.content.strip()
            return result_text
        except Exception as e:
            return "Self"

    def analyze_task_catagory(self, task_description):
        """
        Determine the category of the task (Normal task, Health task, Recipy task).
        """
        prompt = f"""
        TASK: "{task_description}"

        Classify this task into one of the following categories:
        - "Normal task"
        - "Health task"
        - "Recipy task"

        Return only the category name.
        """
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=100,
                temperature=0.2,
            )
            result_text = response.choices[0].message.content.strip()
            return result_text
        except Exception as e:
            return "Normal task"
