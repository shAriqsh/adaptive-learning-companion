import json
import os
from typing import Dict, List

DB_FILE = "student_profile.json"

def get_empty_profile():
    return {
        "user_id": "student_01",
        "mastery_map": {
            # Example structure:
            # "Algebra": {"competency": 0.1, "mistakes": [], "strategies": []}
        },
        "preferences": {
            "learning_style": "unknown" # visual, textual, etc.
        }
    }

def load_profile(user_id: str = "student_01") -> dict:
    if not os.path.exists(DB_FILE):
        return get_empty_profile()
    
    try:
        with open(DB_FILE, "r") as f:
            data = json.load(f)
            return data
    except:
        return get_empty_profile()

def update_profile(user_id: str, topic: str, diagnosis: str, style: str):
    data = load_profile(user_id)
    
    # 1. Update Learning Style (Simple heuristic)
    if style and style != "unknown":
        data["preferences"]["learning_style"] = style
    
    # 2. Update Topic Mastery
    if topic not in data["mastery_map"]:
        data["mastery_map"][topic] = {"competency": 0.0, "mistakes": []}
    
    # Heuristic: If diagnosis is positive, boost score. If negative, lower it.
    # In a real app, the "Evaluator Agent" would score this precisely.
    current_score = data["mastery_map"][topic]["competency"]
    
    # Ensure diagnosis is a string for string operations
    diag_str = str(diagnosis).lower()
    
    if "correct" in diag_str or "ready" in diag_str:
        new_score = min(1.0, current_score + 0.1)
    else:
        new_score = max(0.0, current_score - 0.05)
        # Record the mistake
        if len(diag_str) < 50: # Only save short diagnoses
            data["mastery_map"][topic]["mistakes"].append(diagnosis)
            
    data["mastery_map"][topic]["competency"] = round(new_score, 2)
    
    # Save to disk
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)
        
    print(f"💾 [MEMORY] Profile Saved. {topic} Score: {new_score}")