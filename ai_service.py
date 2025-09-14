from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import uvicorn
import json

# Import all AI functions from your 107.py
from 107 import (
    chat_with_task_mama,
    get_mama_response,
    detect_task_planning_request,
    detect_recipe_request,
    generate_task_analysis,
    generate_recipy_suggestion,
    analyze_mama_emotions,
    wants_pep_talk,
    DynamicTaskPrioritizer,
)

app = FastAPI(title="Task Mama AI API")

# ------------------------
# Request/Response Models
# ------------------------
class ChatRequest(BaseModel):
    user_input: str
    input_mode: Optional[str] = "default"


class ChatResponse(BaseModel):
    success: bool
    response: dict


# ------------------------
# Routes
# ------------------------

@app.post("/chat-boot/", response_model=ChatResponse)
async def chat_boot(req: ChatRequest):
    user_input = req.user_input

    try:
        # 1. Task planning
        if detect_task_planning_request(user_input):
            return {"success": True, "response": {
                "type": "task_planning",
                "message": "Please tell me about all the tasks you need to do 📋✨"
            }}

        # 2. Recipe request
        if detect_recipe_request(user_input):
            return {"success": True, "response": {
                "type": "recipe_request",
                "message": "What items do you have in your pantry? 🍳✨"
            }}

        # 3. Emotion analysis
        emotions = analyze_mama_emotions(user_input)
        if emotions.get("is_sad") or emotions.get("is_overwhelmed") or emotions.get("is_stressed"):
            return {"success": True, "response": {
                "type": "emotional_support",
                "message": "I sense you might not feel well 💕 Do you want a pep talk? (yes/no)"
            }}

        if wants_pep_talk(user_input):
            return {"success": True, "response": {
                "type": "pep_talk",
                "message": "You are stronger than you know, and tomorrow will be brighter 💖"
            }}

        if emotions.get("is_happy"):
            return {"success": True, "response": {
                "type": "positive_emotion",
                "message": "I’m glad you’re happy 💖🌸"
            }}

        # 4. Task analysis
        task_analysis = generate_task_analysis(user_input)
        if task_analysis.get("tasks"):
            return {"success": True, "response": {
                "type": "task_analysis",
                "tasks": task_analysis["tasks"]
            }}

        # 5. Recipe detection
        recipe_response = generate_recipy_suggestion(user_input)
        if recipe_response:
            return {"success": True, "response": {
                "type": "recipe_suggestion",
                **recipe_response
            }}

        # 6. AI conversation fallback
        ai_reply = get_mama_response(user_input)
        try:
            ai_json = json.loads(ai_reply)
            return {"success": True, "response": ai_json}
        except Exception:
            return {"success": True, "response": {"type": "chat", "message": ai_reply}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ------------------------
# Run the FastAPI app
# ------------------------
if __name__ == "__main__":
    uvicorn.run("ai_service:app", host="0.0.0.0", port=8000, reload=True)
