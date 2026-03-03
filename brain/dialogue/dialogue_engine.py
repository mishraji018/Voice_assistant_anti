"""
dialogue_engine.py  -  Conversational Brain for Jarvis
=======================================================
Handles everything that is NOT a direct system command:
  - Emotions / feelings
  - Identity questions ("who are you?")
  - Meta memory queries ("what did I ask earlier?")
  - Follow-up questions ("tell me more")
  - Small talk, compliments, criticism
  - Name learning ("my name is Prateek")
  - Suggestions bridging conversation -> commands

Works entirely with rule-based patterns + response pools.
No LLM or API required.

Public API
----------
    from dialogue_engine import DialogueEngine
    engine = DialogueEngine(memory, personality)
    response = engine.respond("I'm feeling tired today")
"""

import re
import random
import datetime

# ---------------------------------------------------------------------------
# Emotion detection vocabulary
# ---------------------------------------------------------------------------

EMOTIONS = {
    "tired"   : ["tired", "exhausted", "sleepy", "drained", "fatigued",
                 "thaka", "neend aa rahi", "bore"],
    "happy"   : ["happy", "great", "amazing", "awesome", "wonderful",
                 "excited", "good mood", "khush", "mast"],
    "sad"     : ["sad", "upset", "down", "depressed", "unhappy",
                 "disappointed", "dukhi", "bura lag raha"],
    "stressed": ["stressed", "anxious", "worried", "overwhelmed",
                 "nervous", "tense", "pareshan", "tension"],
    "bored"   : ["bored", "boring", "nothing to do", "free", "bakwaas"],
}

# Suggestions to offer after emotional responses
EMOTION_SUGGESTIONS = {
    "tired"   : ["Want me to play some relaxing music?",
                 "Should I dim things down and put on some calm music?",
                 "How about I search for relaxation tips?"],
    "happy"   : ["Want to celebrate with some upbeat music?",
                 "Shall I note down what's making you happy?"],
    "sad"     : ["Want me to play something cheerful?",
                 "I could search for some motivational content if you like."],
    "stressed": ["Want me to set a reminder to take a break?",
                 "Should I search for stress relief techniques?",
                 "How about some calming music to help focus?"],
    "bored"   : ["Want to hear a joke?",
                 "Shall I play some music?",
                 "I could search for something interesting for you."],
}

# ---------------------------------------------------------------------------
# Conversational pattern table
# Each entry: (label, [regex patterns], handler_method_name)
# Checked in order; first match wins.
# ---------------------------------------------------------------------------

class DialogueEngine:
    """
    Main conversational response engine.

    Parameters
    ----------
    memory  : ConversationMemory instance
    persona : PersonalityProfile instance
    """

    def __init__(self, memory, persona):
        self._mem  = memory
        self._pers = persona

        # Pattern table: (label, patterns, handler)
        self._patterns = [
            # Name learning
            ("learn_name",
             [r"my name is (\w+)", r"call me (\w+)", r"i am (\w+)",
              r"mera naam (\w+) hai", r"naam hai mera (\w+)"],
             self._learn_name),

            # Meta memory
            ("meta_query",
             [r"what did i (ask|say|tell)", r"what was my last",
              r"what.?s my name", r"do you know my name", r"who am i",
              r"how long (have we|are we) (been )?talking",
              r"what did we talk about"],
             self._meta_query),

            # Identity questions
            ("who_are_you",
             [r"who are you", r"what are you", r"tell me about yourself",
              r"are you (a robot|an ai|a computer|real)",
              r"tum kaun ho", r"aap kya ho"],
             self._who_are_you),

            # Capability questions
            ("what_can_you_do",
             [r"what can you do", r"what.?s your (ability|skill|feature)",
              r"help me understand you", r"how can you help",
              r"tum kya kar sakte ho"],
             self._capabilities),

            # Compliment
            ("compliment",
             [r"you.?re (great|awesome|amazing|good|the best|smart|intelligent|nice)",
              r"good job", r"well done", r"thanks? (a lot|so much|jarvis)",
              r"shukriya", r"bahut acha"],
             self._compliment),

            # Criticism
            ("criticism",
             [r"you.?re (bad|wrong|stupid|useless|not helping|terrible)",
              r"that.?s (wrong|incorrect|bad|not right)",
              r"bura", r"galat"],
             self._criticism),

            # Follow-up / tell me more
            ("follow_up",
             [r"tell me more", r"aur batao", r"continue",
              r"elaborate", r"explain more", r"and then what",
              r"what else"],
             self._follow_up),

            # Emotions / feelings
            ("emotion",
             [r"i.?m feeling (\w+)", r"i feel (\w+)", r"feeling (\w+)",
              r"i.?m (so |very |quite |really )?(\w+) today",
              r"mujhe (\w+) lag raha", r"bahut (\w+) hoon"],
             self._handle_emotion),

            # Gratitude
            ("thanks",
             [r"^(thank you|thanks|ty|thx)[\W]*$",
              r"thank you (very much|so much|jarvis)",
              r"bahut shukriya"],
             self._thanks),

            # Greeting
            ("greeting",
             [r"^(hello|hi|hey|good morning|good afternoon|good evening|good night)[\W]*$",
              r"(namaste|namaskar|salam)"],
             self._greeting),

            # Farewell
            ("farewell",
             [r"good ?night", r"sleep well", r"see you (later|tomorrow)",
              r"take care", r"bye for now", r"shubh ratri"],
             self._farewell),

            # Opinion / rhetorical
            ("opinion",
             [r"what do you think", r"do you think", r"your opinion",
              r"would you (recommend|suggest)", r"should i"],
             self._opinion),

            # Agreement / affirmation
            ("affirmation",
             [r"^(yes|yeah|yep|sure|okay|ok|alright|go ahead)[\W]*$",
              r"^(haan|theek hai|bilkul)[\W]*$"],
             self._affirmation),
        ]

    # =========================================================================
    # Main entry point
    # =========================================================================

    def respond(self, text: str) -> str:
        """
        Produce a conversational response for the given text.
        Always returns a string.
        """
        norm = text.lower().strip()
        lang = self._mem.get_language() or "en"

        # --- 1. Check Learned Mappings first ---
        learned = self._mem.recall("learned_mappings", {})
        if norm in learned:
            mapping = learned[norm]
            # If it's a learned command, we might actually want to trigger 
            # the command executor, but for the dialogue engine's 'respond',
            # we just acknowledge it.
            res = "Achha, main samajh gayi!" if lang == "hi" else "Got it, I remember that now!"
            return res

        # --- 2. Check patterns ---
        for (_label, patterns, handler) in self._patterns:
            for pattern in patterns:
                m = re.search(pattern, norm)
                if m:
                    self._mem.remember("last_topic", norm)
                    return handler(norm, m, lang=lang)

        # Fallback: generic clarification
        self._mem.remember("last_topic", norm)
        return self._fallback(norm, lang=lang)

    # =========================================================================
    # Handlers
    # =========================================================================

    def _learn_name(self, text: str, match: re.Match, lang: str = "en") -> str:
        name = match.group(1).strip().capitalize()
        self._mem.remember("user_name", name)
        
        if lang == "hi":
            options = [
                f"Samat hi hai, {name} ji! Maine yaad kar liya.",
                f"Thik hai {name} ji, ab se main aapko isi naam se bulaungi.",
                f"Not kar liya hai {name} ji!"
            ]
        else:
            options = [
                f"Nice to meet you, {name}! I'll remember that.",
                f"Great, {name}! I've got your name saved.",
                f"Done! I'll call you {name} from now on.",
            ]
        return random.choice(options)

    def _meta_query(self, text: str, match: re.Match, lang: str = "en") -> str:
        # Note: self._mem.answer_meta_query is currently English-only.
        # We'll leave it for now or wrap it if needed.
        answer = self._mem.answer_meta_query(text)
        if not answer:
            return "Mujhe thik se yaad nahi aa raha." if lang == "hi" else \
                   "I'm not sure what you're referring to."
        return answer

    def _who_are_you(self, text: str, match: re.Match, lang: str = "en") -> str:
        name = self._mem.user_name
        
        if lang == "hi":
            greet = f"Namaste {name or ''}! "
            options = [
                f"{greet}Main Jarvis hoon, aapki personal AI assistant.",
                f"{greet}Main Jarvis hoon. Main aapke system ko control kar sakti hoon aur aapse baat bhi!",
                "J.A.R.V.I.S — Just A Rather Very Intelligent System. Aapki seva mein haazir."
            ]
        else:
            greet = f"Hey {name or ''}! "
            options = [
                f"{greet}I'm Jarvis — your personal AI desktop assistant.",
                f"{greet}I'm Jarvis. Think of me as your calm, professional virtual companion.",
                "J.A.R.V.I.S — Just A Rather Very Intelligent System. At your service, as always."
            ]
        return random.choice(options)

    def _capabilities(self, text: str, match: re.Match, lang: str = "en") -> str:
        if lang == "hi":
            options = [
                "Main apps khol sakti hoon, web search kar sakti hoon, gaane chala sakti hoon aur bahut kuch!",
                "Main aapka system control kar sakti hoon, reminders set kar sakti hoon aur news bhi suna sakti hoon.",
                "Mujhse kuch bhi puchiye — weather, time, ya koi app kholne ko boliye."
            ]
        else:
            options = [
                "I can open apps, search the web, control your system, play music, and much more.",
                "Think of me as your system assistant. Commands, queries, or just a chat — I handle it all.",
                "I'm quite versatile! Try asking me to open an app, check the weather, or set a reminder."
            ]
        return random.choice(options)

    def _compliment(self, text: str, match: re.Match, lang: str = "en") -> str:
        return self._pers.react_to_compliment(lang=lang)

    def _criticism(self, text: str, match: re.Match, lang: str = "en") -> str:
        return self._pers.react_to_criticism(lang=lang)

    def _follow_up(self, text: str, match: re.Match, lang: str = "en") -> str:
        topic = self._mem.last_topic
        if lang == "hi":
            if topic: return f"Ji, '{topic}' ke baare mein aur kya jaanna chahte hain?"
            return "Main aur jaankari de sakti hoon, par kis baare mein?"
        
        if topic:
            return f"Sure, continuing from '{topic}' — what specific aspect would you like more on?"
        return "I'd be happy to go deeper, but what would you like to know more about?"

    def _handle_emotion(self, text: str, match: re.Match, lang: str = "en") -> str:
        detected = None
        for emotion, keywords in EMOTIONS.items():
            for kw in keywords:
                if kw in text:
                    detected = emotion
                    break
            if detected: break

        if not detected: detected = "tired"

        empathy = self._pers.empathise(detected, lang=lang)
        # Suggestions mapping (multilingual)
        sugg_hi = {
            "tired": "Kya main thoda aaram-dayak music chalaoon?",
            "happy": "Kya aap gaane sunna chahenge?",
            "sad": "Main aapka mood thik karne ke liye kuch search karoon?",
            "stressed": "Ek break le lijiye, main reminder set kar deti hoon.",
            "bored": "Ek joke sunaoon?"
        }
        
        suggestion = sugg_hi.get(detected, "") if lang == "hi" else \
                     random.choice(EMOTION_SUGGESTIONS.get(detected, [""]))
        
        return f"{empathy} {suggestion}".strip()

    def _thanks(self, text: str, match: re.Match, lang: str = "en") -> str:
        if lang == "hi":
            options = ["shukriya kehne ki koi zaroorat nahi.", "Khushi hui aapki madad karke!", "Koi baat nahi!"]
        else:
            options = ["Anytime!", "Happy to help!", "Of course — that's what I'm here for!"]
        return random.choice(options)

    def _greeting(self, text: str, match: re.Match, lang: str = "en") -> str:
        hour = datetime.datetime.now().hour
        if lang == "hi":
            time_greeting = "Su-prabhat" if 5 <= hour < 12 else "Namaste"
            options = [f"{time_greeting}. Main aapki kya madad kar sakti hoon?", "Ji, kahiye."]
        else:
            time_greeting = "Good morning" if 5 <= hour < 12 else \
                            "Good afternoon" if 12 <= hour < 17 else \
                            "Good evening" if 17 <= hour < 21 else "Hello"
            options = [f"{time_greeting}. How can I assist you?", "Hi there. Ready when you are."]
        return random.choice(options)

    def _farewell(self, text: str, match: re.Match, lang: str = "en") -> str:
        if lang == "hi":
            options = ["Phir milenge!", "Apna khayal rakhiye.", "Shubh ratri."]
        else:
            options = ["See you later!", "Take care!", "Goodbye for now."]
        return random.choice(options)

    def _opinion(self, text: str, match: re.Match, lang: str = "en") -> str:
        if lang == "hi":
            return "Mujhe lagta hai aapko apne mann ki sunni chahiye, ya main search karoon?"
        return "I'd suggest going with your gut, or should I search for more info?"

    def _affirmation(self, text: str, match: re.Match, lang: str = "en") -> str:
        if lang == "hi":
            options = ["Ji thik hai.", "Aage kahiye.", "Bilkul."]
        else:
            options = ["Alright.", "Go ahead.", "I'm listening."]
        return random.choice(options)

    def _fallback(self, text: str, lang: str = "en") -> str:
        """Escalates to LLM reasoning if no rule matched."""
        try:
            from brain.reasoning.reasoning_engine import llm_reason
            from brain.routing.routing_logic import execute_action
            
            print(f"[Dialogue] No rule matched. Escalating '{text}' to LLM.")
            plan = llm_reason(text)
            result = execute_action(plan, text)
            return result
        except Exception as e:
            print(f"[Dialogue] Escalation failed: {e}")

        if lang == "hi":
            return "Main thik se samajh nahi paayi, kya aap phir se bata sakte hain?"
        return "I'm not entirely sure what you mean."