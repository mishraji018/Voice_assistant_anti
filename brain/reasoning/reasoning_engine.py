"""
reasoning_engine.py  –  LLM-based Intent & Planning Engine for Jarvis
====================================================================
This module implements the core "reasoning" logic using the system prompt
provided by the user. It converts cleaned speech into structured JSON.

Stage 4 Upgrade:
  Old: Keyword matching / Simple ML
  New: LLM Reasoning (Stage 4 + Stage 5 integration)

Usage:
    from reasoning_engine import interpret_command
    result = interpret_command("youtube kholo aur gaana chalao")
    # Result is a dict matching the user's requested JSON schema.
"""

import os
import json
import re
from typing import Dict, Any, Optional

# --- Configuration -----------------------------------------------------------
API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# --- System Prompt (Strict JSON version) -------------------------------------
SYSTEM_PROMPT = """You are the reasoning engine for Jarvis.
Output strictly JSON. No markdown. No conversational filler.

Plan Schema:
{
  "action": "command | web_search | answer",
  "target": "target string",
  "confidence": 0.95
}
"""

def llm_reason(text: str) -> Dict[str, Any]:
    """
    Calls Gemini to generate a structured action plan.
    """
    if not text:
        return {"action": "answer", "target": "I didn't hear any input.", "confidence": 1.0}

    try:
        import google.generativeai as genai
        
        if not API_KEY:
            print("[Reasoning] WARNING: No GEMINI_API_KEY found.")
            return _stub_reason(text)

        genai.configure(api_key=API_KEY)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Force JSON response via combined prompt
        prompt = f"{SYSTEM_PROMPT}\n\nUser Question: {text}\n\nReturn JSON:"
        
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        
        # Clean Markdown
        clean_json = re.sub(r"```(json)?", "", raw_text).strip()
        
        return json.loads(clean_json)

    except Exception as e:
        print(f"[Reasoning] LLM Failure: {e}")
        return _stub_reason(text)

def _stub_reason(text: str) -> Dict[str, Any]:
    """Basic pattern matching when LLM is unavailable."""
    t = text.lower()
    if any(k in t for k in ["open", "launch", "kholo", "chalao"]):
        return {"action": "command", "target": text, "confidence": 0.8}
    return {"action": "web_search" if len(t) > 3 else "answer", "target": text, "confidence": 0.6}

if __name__ == "__main__":
    print(llm_reason("Open Chrome"))
