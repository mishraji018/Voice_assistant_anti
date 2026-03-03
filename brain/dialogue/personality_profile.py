"""
personality_profile.py  -  Jarvis Personality & Tone Layer
============================================================
Defines Jarvis's voice:
  - Polite, calm, slightly witty
  - Concise but natural
  - Non-robotic (no repeated openers)
  - Personalised (uses user name occasionally)

Public API
----------
    from personality_profile import PersonalityProfile

    persona = PersonalityProfile()
    final   = persona.format_response("I found that for you.", memory, context="confirmation")
    opener  = persona.get_opener("agreement")
"""

import random
from collections import deque

# ---------------------------------------------------------------------------
# Opener pools  (picked to prefix responses; LRU prevents repeats)
# ---------------------------------------------------------------------------

_OPENERS: dict[str, dict[str, list[str]]] = {
    "agreement": {
        "en": ["Sure,", "Of course,", "Absolutely,", "Gladly,", "No problem,"],
        "hi": ["Bilkul,", "Zaroor,", "Haan,", "Ji bilkul,"]
    },
    "confirmation": {
        "en": ["Done.", "Got it.", "All set.", "Noted.", "Consider it done."],
        "hi": ["Ho gaya.", "Thik hai.", "Not kar liya.", "Bilkul ho jayega."]
    },
    "empathy": {
        "en": ["I understand.", "That makes sense.", "I hear you.", "Fair enough."],
        "hi": ["Main samajh sakti hoon.", "Thik keh rahe hain aap.", "Main sun rahi hoon."]
    },
    "thinking": {
        "en": ["Let me check.", "One moment.", "Hold on.", "Give me a second."],
        "hi": ["Ek minute dekhti hoon.", "Zara rukiye.", "Main check karti hoon."]
    },
    "greeting": {
        "en": ["Hello.", "Good to see you.", "Hi there."],
        "hi": ["Namaste.", "Kaise hain aap?", "Namaskar."]
    },
    "neutral": {
        "en": ["Alright,", "Right,", "Okay,", "Well,"],
        "hi": ["Thik hai,", "Achha,", "Zaroor,"]
    },
}

# Witty remarks (kept mostly English unless language is Hindi)
_WITTY_REMARKS = {
    "en": [
        "As always, I'm on it.",
        "Consider it handled — that's what I'm here for.",
        "One step ahead of you, as always."
    ],
    "hi": [
        "Aapki madad karke khushi hui.",
        "Hamesha ki tarah, main taiyar hoon.",
        "Bas ek ishara kijiye, main kar doongi."
    ]
}

# Closing affirmations
_CLOSERS = {
    "en": ["Anything else?", "Let me know if you need more.", "Just say the word."],
    "hi": ["Aur kuch?", "Bataiye agar aur madad chahiye ho.", "Main yahi hoon."]
}


class PersonalityProfile:
    """
    Wraps raw dialogue text with Jarvis's personality tone.

    Parameters
    ----------
    use_name_freq : float  0-1, how often to address the user by name (default 0.25)
    wit_freq      : float  0-1, how often to append a witty remark (default 0.15)
    """

    def __init__(self, use_name_freq: float = 0.25, wit_freq: float = 0.15):
        self._name_freq = use_name_freq
        self._wit_freq  = wit_freq
        self._opener_history: deque = deque(maxlen=3)  # LRU per context
        self._last_closer   : str   = ""

    # -------------------------------------------------------------------------
    # Internal text cleaning
    # -------------------------------------------------------------------------

    def _clean_text(self, text: str) -> str:
        """Sanitizes text from LLM artifacts like backticks or extra whitespace."""
        text = text.strip()
        if text.startswith("```"):
            text = text.replace("```", "").replace("json", "").strip()
        text = " ".join(text.split())
        return text

    # -------------------------------------------------------------------------
    # Main entry point
    # -------------------------------------------------------------------------

    def format_response(
        self,
        raw_text: str,
        memory=None,            # ConversationMemory instance (optional)
        context: str = "neutral",
    ) -> str:
        """
        Wrap raw_text with personality:
          1. Pick a non-repeating opener
          2. Personalise with user name (sometimes)
          3. Append witty remark (rarely)
          4. Return final string
        """
        lang = memory.get_language() if memory else "en"
        if lang not in ["en", "hi"]: lang = "en"
        
        parts = []

        # 1. Opener (sometimes skip for very short snappy replies)
        if len(raw_text) > 40:
            opener = self.get_opener(context, lang=lang)
            parts.append(opener)

        # 2. Core response
        cleaned_text = self._clean_text(raw_text)
        parts.append(cleaned_text)

        # 3. Personalise: insert name occasionally
        user_name = memory.user_name if memory else ""
        if user_name and random.random() < self._name_freq:
            # Insert name at a natural join point
            if lang == "hi":
                insert = f"{user_name} ji, " + cleaned_text
            else:
                insert = random.choice([
                    f"{user_name}, " + cleaned_text,
                    cleaned_text.rstrip(".!?") + f", {user_name}.",
                ])
            parts = [insert]

        # 4. Witty remark (rare)
        if random.random() < self._wit_freq:
            pool = _WITTY_REMARKS.get(lang, _WITTY_REMARKS["en"])
            parts.append(random.choice(pool))

        result = " ".join(parts).strip()

        # Ensure proper sentence ending based on script (if possible) or default
        if result and result[-1] not in ".!?":
            result += "."

        return result

    # -------------------------------------------------------------------------
    # Opener selection
    # -------------------------------------------------------------------------

    def get_opener(self, context: str = "neutral", lang: str = "en") -> str:
        """Return a non-repeating opener for the given context and language."""
        pool_dict = _OPENERS.get(context, _OPENERS["neutral"])
        pool = pool_dict.get(lang, pool_dict["en"])
        
        available = [o for o in pool if o not in self._opener_history]
        if not available:
            available = pool
        choice = random.choice(available)
        self._opener_history.append(choice)
        return choice

    def get_closer(self, lang: str = "en") -> str:
        """Return a closing phrase, avoiding the last one used."""
        pool = _CLOSERS.get(lang, _CLOSERS["en"])
        available = [c for c in pool if c != self._last_closer]
        if not available: available = pool
        choice = random.choice(available)
        self._last_closer = choice
        return choice

    # -------------------------------------------------------------------------
    # Tone helpers (callable from dialogue_engine)
    # -------------------------------------------------------------------------

    def empathise(self, emotion: str, lang: str = "en") -> str:
        """Return an empathetic opener appropriate for the given emotion."""
        pools_en = {
            "tired"    : ["Sounds like you need a break.", "Long day? I've got you.",
                          "Rest is important. Want me to help wind down?"],
            "happy"    : ["Great to hear that!", "Love the energy!", "That's wonderful!"],
            "sad"      : ["I'm sorry to hear that.", "That sounds tough.",
                          "I'm here if you need anything."],
            "stressed" : ["Take a breath. I'll help sort things out.",
                          "Let's tackle this one step at a time."],
            "bored"    : ["Let's find you something fun!", "I have some ideas."]
        }
        pools_hi = {
            "tired"    : ["Lag raha hai aaj bahut kaam kiya. Break lenge?", "Thak gaye hain? Main madad karti hoon."],
            "happy"    : ["Yeh toh achhi baat hai!", "Khushi hui sunkar!", "Bahut badhiya!"],
            "sad"      : ["Bura laga sunkar. Kya main kuch kar sakti hoon?", "Main yahi hoon agar aapko baat karni ho."],
            "stressed" : ["Pareshan mat hoiye, sab thik ho jayega.", "Gehri saans lijiye, hum milkar hal nikaal lenge."],
            "bored"    : ["Kuch mazedaar karein?", "Mere paas kuch ideas hain."]
        }
        
        pool = pools_hi.get(emotion, ["Theek hai.", "Main sun rahi hoon."]) if lang == "hi" else \
               pools_en.get(emotion, ["I hear you.", "Understood."])
        return random.choice(pool)

    def react_to_compliment(self, lang: str = "en") -> str:
        options_en = [
            "Thanks — I try my best!",
            "Glad I could help. That's what I'm here for.",
            "Appreciate it! Let me know what else I can do."
        ]
        options_hi = [
            "Shukriya! Main hamesha koshish karti hoon.",
            "Aapki madad karke mujhe khushi hui.",
            "Bahut shukriya! Bataiye aur kya karoon?"
        ]
        return random.choice(options_hi if lang == "hi" else options_en)

    def react_to_criticism(self, lang: str = "en") -> str:
        options_en = [
            "I'll try to do better. What went wrong?",
            "Sorry about that. Let me know how I can improve.",
            "Fair point. I'm always learning."
        ]
        options_hi = [
            "Main behtar karne ki koshish karoongi. Kya galati hui?",
            "Maaf kijiye. Bataiye main kaise sudhaar sakti hoon?",
            "Sahi kaha aapne. Main hamesha seekhti rehti hoon."
        ]
        return random.choice(options_hi if lang == "hi" else options_en)
