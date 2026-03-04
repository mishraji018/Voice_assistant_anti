
import re

# Precise keywords maps to capability answers
CAPABILITIES = {
    "notepad": "Yes sir, I can open Notepad and write text into it for you.",
    "chrome": "Yes sir, I can launch Google Chrome and search for anything you need.",
    "weather": "Yes sir, I can provide real-time weather updates and temperature information.",
    "nutrition": "Yes sir, I have a built-in nutrition advisor to help you with food choices for various health conditions.",
    "wellness": "Yes sir, I can track your daily water intake, exercise, and sleep as your health coach.",
    "calculator": "Yes sir, I can open the calculator or perform basic math for you.",
    "screenshot": "Yes sir, I can take a screenshot of your current window.",
    "search": "Yes sir, I can search the web or Wikipedia for any information you require."
}

def get_capability_response(query: str) -> str:
    """
    Check if the query is a 'Can you...' question and return a hardcoded yes/no response.
    """
    q = query.lower().strip()
    
    # Check for capability query markers
    # "Can you...", "Kya tum...", "Kya aap..."
    if not any(k in q for k in ["can you", "kya tum", "kya aap", "do you know how to"]):
        return None

    # Match against keywords
    for key, response in CAPABILITIES.items():
        if key in q:
            return response
            
    # Generic positive response if it mentions a supported area
    if any(k in q for k in ["help", "kya kar sakte", "capabilities", "features"]):
        return "Sir, I can help you with system control, web search, health tracking, and providing knowledge. Bas order dijiye mujhe."

    return None
