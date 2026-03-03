"""
brain.py – Hybrid AI Orchestrator for Jarvis
============================================
Flow:
    Dialogue (rules)
        ↓
    LLM reasoning (if needed)
        ↓
    Routing (command / web / answer)
        ↓
    Personality formatting
"""

from brain.dialogue.dialogue_engine import DialogueEngine
from brain.dialogue.personality_profile import PersonalityProfile
from brain.reasoning.reasoning_engine import llm_reason
from brain.routing.routing_logic import execute_action
from brain.memory.conversation_memory import ConversationMemory



# ---------------------------------------------------------------------
# Global instances (can later be dependency-injected if needed)
# ---------------------------------------------------------------------

memory = ConversationMemory()
persona = PersonalityProfile()
dialogue_engine = DialogueEngine(memory, persona)


# ---------------------------------------------------------------------
# Main Brain Function
# ---------------------------------------------------------------------

def think(text: str) -> str:
    """
    Hybrid Brain:
    1. Rule-based dialogue
    2. Escalate to LLM if needed
    3. Execute action
    4. Format with personality
    """

    print(f"[Brain] Input: {text}")

    # -------------------------------------------------------------
    # 1️⃣ Rule-Based Dialogue First
    # -------------------------------------------------------------
    dialogue_response = dialogue_engine.respond(text)

    # If dialogue handled it (NOT fallback escalation)
    if dialogue_response and dialogue_response not in [
        "I'm not entirely sure what you mean.",
        "Main thik se samajh nahi paayi, kya aap phir se bata sakte hain?"
    ]:
        return persona.format_response(
            dialogue_response,
            memory,
            context="neutral"
        )

    # -------------------------------------------------------------
    # 2️⃣ LLM Reasoning Escalation
    # -------------------------------------------------------------
    print("[Brain] Escalating to LLM reasoning...")

    plan = llm_reason(text)

    action = plan.get("action", "").lower()

    # -------------------------------------------------------------
    # 3️⃣ Pre-Execution UX (Thinking line for web search)
    # -------------------------------------------------------------
    if action == "web_search":
        thinking_line = persona.get_opener(
            "thinking",
            lang=memory.get_language() or "en"
        )
        thinking_line = persona.get_opener(
            "thinking",
            lang=memory.get_language() or "en"
        )
        speak(thinking_line)

    # -------------------------------------------------------------
    # 4️⃣ Execute Action (command / web / answer)
    # -------------------------------------------------------------
    result = execute_action(plan, text)

    # -------------------------------------------------------------
    # 5️⃣ Personality Context Mapping
    # -------------------------------------------------------------
    context_map = {
        "command": "confirmation",
        "web_search": "thinking",
        "answer": "neutral"
    }

    context = context_map.get(action, "neutral")

    final_response = persona.format_response(
        result,
        memory,
        context=context
    )

    return final_response