from openai import OpenAI
import json
import os
from datetime import datetime
import re
# Initialize OpenAI client
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Extract meal type from the conversation
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

# Generate recipe suggestion based on available items
def generate_recipy_suggestion(available_items, user_conversation=None):
    """
    Generate a recipe suggestion based on available items using AI knowledge.
    Returns a JSON with 3 unique recipes using ONLY the ingredients provided.
    Uses meal_type from conversation if specified.
    """
    now = datetime.now()
    
    # Detect meal type from conversation
    meal_type = get_meal_type_from_conversation(user_conversation or "")

    # Prepare the prompt for GPT-4 to generate recipes
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
            messages=[{"role": "system", "content": "You are a helpful recipe expert. Create detailed, unique recipes using only the provided ingredients."},
                      {"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.4
        )
        
        ai_response = response.choices[0].message.content.strip()

        # Parse the AI response and create our JSON structure
        return parse_ai_recipe_response(ai_response, available_items, now, meal_type)
        
    except Exception as e:
        # Fallback to manual recipe creation
        return create_smart_recipe_from_ingredients(available_items, now, meal_type)

# Function to explain cooking terms in recipes
def explain_cooking_terms(text):
    """
    Add explanations for difficult cooking terms in the recipe text.
    For example, 'sauté' will be explained the first time it appears.
    """
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
    
    explained = set()
    for term, explanation in explanations.items():
        pattern = r"\b" + re.escape(term) + r"\b"
        matches = list(re.finditer(pattern, text, flags=re.IGNORECASE))
        if matches:
            first = matches[0]
            start, end = first.span()
            if term not in explained:
                text = text[:start] + explanation + text[end:]
                explained.add(term)
    return text

# Parse AI response and format it into the JSON structure
def parse_ai_recipe_response(ai_response, available_items, now, meal_type):
    """
    Parse AI response and convert it into our JSON format.
    Also, explain difficult cooking terms in the recipe text.
    """
    try:
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

        if current_recipe and current_name:
            recipe_count += 1
            explained_recipe = explain_cooking_terms(current_recipe.strip())
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(current_name.strip())

        while len(recipes) < 3:
            recipe_count += 1
            fallback = "Cook the available ingredients together with seasonings until tender."
            explained_recipe = explain_cooking_terms(fallback)
            recipes.append(f"Recipe {recipe_count}: {explained_recipe}")
            recipe_names.append(f"Recipe {recipe_count}: Mixed Ingredient Dish")

        return {
            "meal_type": meal_type,
            "task_catagory": "Recipy task",
            "time": now.strftime('%I:%M %p'),
            "date": now.strftime('%Y-%m-%d'),
            "items_available": available_items,
            "items_needed": "Cooking oil, salt, black pepper, water, onions",
            "recipy_name": recipe_names[:3],
            "recipy": recipes[:3]
        }

    except Exception as e:
        print(f"Error parsing AI response: {e}")
        return create_smart_recipe_from_ingredients(available_items, now, meal_type)

# Manual recipe creation if AI fails
def create_smart_recipe_from_ingredients(available_items, now, meal_type):
    """
    Fallback recipe generator when AI doesn't respond properly.
    """
    recipes = []
    recipe_names = []
    
    # Analyze available ingredients
    items_lower = available_items.lower()
    
    if "mutton" in items_lower and "rice" in items_lower:
        recipe_names.append("Recipe 1: Mutton Biryani Delight")
        recipes.append("Step-by-step for Mutton Biryani...")

        recipe_names.append("Recipe 2: Mutton Stew")
        recipes.append("Step-by-step for Mutton Stew...")

        recipe_names.append("Recipe 3: Mutton Veggie Pilaf")
        recipes.append("Step-by-step for Mutton Veggie Pilaf...")

    else:
        recipe_names = ["Recipe 1: Veggie Soup", "Recipe 2: Simple Salad", "Recipe 3: Pasta Dish"]
        recipes = ["Step-by-step for Veggie Soup...", "Step-by-step for Simple Salad...", "Step-by-step for Pasta Dish..."]

    return {
        "meal_type": meal_type,
        "task_catagory": "Recipy task",
        "time": now.strftime('%I:%M %p'),
        "date": now.strftime('%Y-%m-%d'),
        "items_available": available_items,
        "items_needed": "Salt, pepper, herbs",
        "recipy_name": recipe_names,
        "recipy": recipes
    }
