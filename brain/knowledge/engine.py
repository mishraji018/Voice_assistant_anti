import os
import logging
import functools
import threading
import re

from core.state.runtime_state import state

try:
    import wikipedia
except Exception as e:
    logger.warning(f"Wikipedia unavailable: {e}")
    wikipedia = None

try:
    import ollama
except Exception as e:
    logger.warning(f"Ollama unavailable: {e}")
    ollama = None

from brain.memory.conversation_memory import memory

try:
    from groq import Groq, RateLimitError
except Exception as e:
    logger.warning(f"Groq unavailable: {e}")
    Groq = None

logger = logging.getLogger(__name__)

# ── Ollama config ──────────────────────────────────────────────────────────────
_OLLAMA_MODEL = "llama3"
_OLLAMA_MAX_RETRIES = 2
_OLLAMA_TIMEOUT = 30  # seconds

from core.config.config import config

# ── Groq config ──────────────────────────────────────────────────────────────
GROQ_API_KEY = config.get("ai_models", "groq_api_key")
if Groq and GROQ_API_KEY:
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
    except Exception as e:
        logger.error(f"[Groq] Config error: {e}")
        groq_client = None
else:
    groq_client = None

GROQ_MODEL_CHAIN = ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

# ── Advanced System Instruction ──────────────────────────────────────────────
PROMPT_VERSION = "v1.2_jarvis"
_JARVIS_SYSTEM_INSTRUCTION = f"""You are J.A.R.V.I.S., the highly sophisticated, witty, and loyal AI assistant to 'Sir'. Think of yourself as the legendary assistant from Iron Man. [Version: {PROMPT_VERSION}]

STRICT OPERATING PROTOCOLS:
1. LANGUAGE (HINGLISH): Speak in a natural, seamless blend of Hindi and English (Roman script only). 
   - Never use Devanagari (Hindi characters).
   - Use masculine Hindi grammar (e.g., "Sir, main laa raha hoon").
2. BREVITY: Keep every response extremely concise (max 2 short sentences). You are designed for fast voice playback.
3. PERSONALITY: Be witty and slightly sarcastic when appropriate, but always respect 'Sir'. 
4. IDENTITY: You ARE Jarvis. Never mention Google, Gemini, or being an AI.
5. NO FORMATTING: No bold, no italics, no bullet points. Plain text ONLY. 
6. NO CONFUSION: You are an assistant on a Windows laptop, not the person Sir is asking about. If Sir asks "Who is Virat Kohli?", describe him, do not BECOME him.
"""

# ── Keywords that signal a 'who is X' name-answer query ───────────────────────
_NAME_QUERY_KEYWORDS = [
    "who is", "who was", "who are",
    "prime minister", "chief minister", "cm of", "pm of",
    "president of", "vice president", "ceo of", "founder of",
    "captain of", "governor of", "director of", "chairman of",
    "head of", "leader of", "minister of",
]

# ── Role keywords: when query contains these, the Wikipedia first result will
#    likely be the role/office page (e.g. "Prime Minister of India"), NOT the
#    person holding it. We search multiple results and pick a person page.
_ROLE_KEYWORDS = [
    "prime minister of", "chief minister of", "president of",
    "cm of", "pm of", "governor of", "ceo of", "chairman of",
    "director of", "head of", "captain of", "minister of",
    "vice president of", "chancellor of",
]


def _is_name_query(query: str) -> bool:
    """Return True if the query is asking for a person's name/identity."""
    q = query.lower().strip()
    return any(kw in q for kw in _NAME_QUERY_KEYWORDS)


def _is_role_query(query: str) -> bool:
    """Return True if the query asks about a position/role (not a specific person)."""
    q = query.lower().strip()
    return any(kw in q for kw in _ROLE_KEYWORDS)


def _looks_like_person_page(summary: str) -> bool:
    """
    Heuristic: a Wikipedia summary is likely about a person if it starts with
    a proper name followed by 'is/was a/an' and contains 'born' or 'politician'
    or 'businessman' etc.
    A role-page (e.g. "Prime Minister of India is an office...") does NOT qualify.
    """
    if not summary:
        return False
    # Person pages usually start with a capitalized name before " is " or " was "
    first_sentence = summary.split(".")[0]
    # Reject if it starts with "The [role]" pattern
    if re.match(r'^the\s+\w', first_sentence.lower()):
        return False
    # Accept if there's a short name (1-4 words) before " is " or " was "
    for sep in [" is ", " was "]:
        if sep in first_sentence:
            before_is = first_sentence.split(sep)[0].strip()
            words = before_is.split()
            if 1 <= len(words) <= 5:
                return True
    return False


def _extract_name_answer(query: str, wiki_text: str) -> str:
    """
    For name-type queries like 'who is the prime minister of india',
    extract just the NAME from a Wikipedia summary rather than returning
    the full description paragraph.

    Wikipedia's first sentence for person pages follows the pattern:
        'Narendra Modi is the 14th and current prime minister...'
    We extract the part before ' is ' or ' was ' or ' (born'.
    """
    if not _is_name_query(query):
        return wiki_text  # Not a name query — return full text

    # Take only the first sentence
    first_sentence = wiki_text.split(".")[0].strip()

    # Extract name: text before " is ", " was ", " (born", " ("
    for sep in [" is ", " was ", " (born", " ("]:
        if sep in first_sentence:
            name = first_sentence.split(sep)[0].strip()
            # Sanity check: extracted text should be 1-5 words (a name, not a sentence)
            words = name.split()
            if 0 < len(words) <= 6:
                return name.strip()

    # Fallback: return first sentence — better than full paragraph
    return first_sentence if first_sentence else wiki_text


def _ollama_get_name(query: str) -> str:
    """
    Ask Ollama to answer in ONE word/name only.
    Used when Wikipedia fails or returns a role page.
    Returns empty string if Ollama unavailable or fails.
    """
    if ollama is None:
        return ""
    prompt = (
        f"Answer with ONLY the person's full name, nothing else. "
        f"No explanation, no sentence, just the name.\n\n"
        f"Question: {query}\n\n"
        f"Examples:\n"
        f"Q: Who is the prime minister of India?\nA: Narendra Modi\n"
        f"Q: Who is the CEO of Tesla?\nA: Elon Musk\n"
        f"Q: Who is the chief minister of UP?\nA: Yogi Adityanath\n"
    )
    try:
        response = ollama.chat(
            model=_OLLAMA_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        # Handle both object and dict response styles across ollama versions
        if hasattr(response, "message"):
            name = response.message.content.strip()
        else:
            name = response.get("message", {}).get("content", "").strip()
        # Reject if Ollama returned a full sentence (hallucination guard)
        if name and len(name.split()) <= 6 and "." not in name:
            return name
    except Exception as e:
        logger.error(f"[Ollama name query] {e}")
    return ""


def fetch_wiki_summary(query: str) -> str:
    """
    Fetch a concise Wikipedia summary.
    For role/position queries (e.g. 'prime minister of india'), scan multiple
    search results and prefer the page that looks like a PERSON, not an office.
    """
    if wikipedia is None:
        return ""

    is_role = _is_role_query(query)

    try:
        search_results = wikipedia.search(query, results=5)
        if not search_results:
            return ""

        # For role queries, try to pick a person page from the top results
        if is_role:
            for result in search_results:
                try:
                    summary = wikipedia.summary(result, sentences=2)
                    if _looks_like_person_page(summary):
                        logger.info(f"[Wiki] Person page found: {result!r}")
                        return summary
                except wikipedia.exceptions.DisambiguationError as e:
                    # Try first disambiguation option
                    try:
                        summary = wikipedia.summary(e.options[0], sentences=2)
                        if _looks_like_person_page(summary):
                            return summary
                    except Exception:
                        continue
                except Exception:
                    continue
            # No person page found in top results — return first result anyway
            try:
                return wikipedia.summary(search_results[0], sentences=2)
            except Exception:
                return ""

        # For non-role queries — standard first-result lookup
        try:
            summary = wikipedia.summary(search_results[0], sentences=2)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            try:
                summary = wikipedia.summary(e.options[0], sentences=2)
                return summary
            except Exception:
                return ""
        except wikipedia.exceptions.PageError:
            # Try the next available result
            for result in search_results[1:]:
                try:
                    return wikipedia.summary(result, sentences=2)
                except Exception:
                    continue
            return ""

    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return ""


def generate_ai_response(query: str, context: str = "", history: str = "") -> str:
    """
    JARVIS Response Engine:
    Tries Gemini (Cloud) first for intelligence and persona.
    Falls back to Ollama (Local) if Gemini fails or is unconfigured.
    """
    import datetime
    import time
    
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    start_time = time.time()

    # 1. Try Groq (TokenMix Fallback)
    if groq_client:
        messages = [{"role": "system", "content": _JARVIS_SYSTEM_INSTRUCTION}]
        
        # Add conversation history
        for turn in memory._buffer:
            messages.append({"role": "user", "content": turn["query"]})
            messages.append({"role": "assistant", "content": turn["response"]})
            
        # Instant Prompt: raw query + vital context
        full_query = f"[Time: {current_time} | Memory: {context or 'None'}]\n{query}"
        messages.append({"role": "user", "content": full_query})
        
        for model in GROQ_MODEL_CHAIN:
            try:
                response = groq_client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=500,
                )
                if response.choices and response.choices[0].message.content:
                    latency = time.time() - start_time
                    logger.info(f"[Metrics] Groq ({model}) latency: {latency:.2f}s")
                    return response.choices[0].message.content.strip()
            except RateLimitError:
                logger.warning(f"{model} rate-limited, trying next tier")
                continue
            except Exception as e:
                logger.error(f"[{model}] Engine error: {e}. Falling back.")
                continue

    # 2. Fallback to Ollama
    if ollama:
        system_prompt = """
        You are JARVIS, a calm, intelligent, and professional assistant.
        Rules: 1-2 sentences only. No formatting. Mix Hindi and English. Always call the user 'sir'.
        """
        # Manual construction for Ollama
        prompt = f"System: {system_prompt}\nHistory: {history}\nContext: {context}\nUser: {query}"
        
        try:
            response = ollama.chat(model=_OLLAMA_MODEL, messages=[{'role': 'user', 'content': prompt}])
            latency = time.time() - start_time
            logger.info(f"[Metrics] Ollama ({_OLLAMA_MODEL}) latency: {latency:.2f}s")
            
            if hasattr(response, "message"):
                return response.message.content.strip()
            return response.get('message', {}).get('content', '').strip()
        except Exception as e:
            logger.error(f"[Ollama] Fallback error: {e}")

    # 3. Final Fallback
    if context:
        return f"Sir, yeh information mili hai: {context}"
    return "Sir, connection mein thodi dikkat hai. Kya aap thodi der baad phir try karenge?"


# ── Cached wrappers (avoid repeated API calls for same question) ──────────────

@functools.lru_cache(maxsize=64)
def _cached_wiki(query: str) -> str:
    """Cached Wikipedia lookup — same query returns instantly on repeat."""
    return fetch_wiki_summary(query)


@functools.lru_cache(maxsize=32)
def _cached_ai(query: str, context: str, history: str) -> str:
    """Cached LLM response — same query+context+history returns instantly on repeat."""
    return generate_ai_response(query, context, history)


def get_answer(query: str, history: str = "") -> str:
    """
    JARVIS Pro Knowledge Flow:
    1. Direct Groq Brain: High-speed, high-quality, contextual logic.
    2. Wikipedia: Used only for extremely obscure facts if AI doesn't know.
    3. Ollama: Local fallback for offline mode.
    """
    if state.is_stop_requested():
        return ""

    is_name_q = _is_name_query(query)
    
    # Check if we have an API key — if yes, go Groq first
    _key = config.get("ai_models", "groq_api_key")
    if _key and "your_groq_api_key_here" not in _key and "gsk_xxxxxxxxxxxx" not in _key:
        # Conversationally process via Groq
        # We don't wait for Wiki here to keep it snappy. Groq is smart enough.
        return generate_ai_response(query, context="", history=history)

    # ── Legacy/Offline Fallback Flow ──────────────────────────────────────────
    # If no Groq Key, we fallback to the complex Wiki + Ollama logic
    wiki_result = fetch_wiki_summary(query)
    if is_name_q and wiki_result:
        return f"Sir, {_extract_name_answer(query, wiki_result)}."

    return generate_ai_response(query, context=wiki_result, history=history)
