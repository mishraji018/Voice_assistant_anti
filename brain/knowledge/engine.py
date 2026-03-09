import logging
import functools
import threading
import re

from core.state.runtime_state import state

try:
    import wikipedia
except Exception:
    wikipedia = None

try:
    import ollama
except Exception:
    ollama = None

logger = logging.getLogger(__name__)

# ── Ollama config ──────────────────────────────────────────────────────────────
_OLLAMA_MODEL = "llama3"
_OLLAMA_MAX_RETRIES = 2
_OLLAMA_TIMEOUT = 30  # seconds

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
    Refine a response using Ollama LLM with a professional persona.
    Retries once on failure, then falls back to context or a polite message.
    """
    system_prompt = """
    You are JARVIS, a calm, intelligent, and professional Hindi-English female assistant.
    Rules:
    - Always address the user as 'sir'.
    - Never use slang like 'bhai' or 'yaar'.
    - Be polite, warm, and concise. Slightly affectionate but never overact.
    - If unsure, ask for clarification — never hallucinate or guess.
    - Use a mix of Hindi and English naturally (Hinglish).
    - Respond in 2-3 sentences maximum unless asked for detail.
    - You MUST use the provided conversation context to resolve pronouns like 'he', 'she', 'it', 'that', 'they'.
    """

    prompt = f"""
    System Instructions: {system_prompt}

    {history}

    Current User Query: {query}
    Current Wiki Context: {context}

    Task: Provide a natural, polite, and concise response.
    Use a mix of Hindi and English (Hinglish) where appropriate.
    Always call the user 'sir'.
    """

    if ollama is None:
        if context:
            return f"Sir, yeh information mili hai: {context}"
        return "Sir, local AI model (Ollama) abhi available nahi hai. Aap Ollama install/start karke phir try kariye."

    last_error = None
    for attempt in range(_OLLAMA_MAX_RETRIES):
        if state.is_stop_requested():
            return ""
        try:
            response = ollama.chat(model=_OLLAMA_MODEL, messages=[
                {'role': 'user', 'content': prompt},
            ])
            # Handle both object and dict response styles
            if hasattr(response, "message"):
                content = response.message.content.strip()
            else:
                content = response.get('message', {}).get('content', '').strip()
            if content:
                return content
            logger.warning(f"[Ollama] Empty response on attempt {attempt + 1}")
        except ConnectionError as e:
            last_error = e
            logger.error(f"[Ollama] Connection error (attempt {attempt + 1}): {e}")
        except Exception as e:
            last_error = e
            logger.error(f"[Ollama] Error (attempt {attempt + 1}): {e}")

    # ── Graceful fallback chain ───────────────────────────────────────────────
    if context:
        logger.info("[Ollama] Falling back to Wikipedia context.")
        return f"Sir, yeh information mili hai: {context}"

    logger.warning(f"[Ollama] All {_OLLAMA_MAX_RETRIES} attempts failed. Last error: {last_error}")
    return "Sir, abhi mujhe yeh information nahi mil pa rahi. Kya aap thodi der baad phir try karenge?"


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
    Complete hybrid knowledge flow:
    1. Fetch Wikipedia in a thread (with smart person-page selection).
    2. Extract name if it's a 'who is' query; for clean short names return directly.
    3. If extraction fails, ask Ollama with a name-only prompt.
    4. For descriptive queries, pass wiki context to full AI response.
    5. Respects stop flag throughout.
    """
    if state.is_stop_requested():
        return ""

    is_name_q = _is_name_query(query)

    # ── Run Wikipedia and AI in parallel ──────────────────────────────────────
    wiki_result = {"text": ""}
    ai_result = {"text": ""}

    def _wiki_worker():
        if state.is_stop_requested():
            return
        raw = _cached_wiki(query)
        # Apply name extraction for 'who is' type queries
        wiki_result["text"] = _extract_name_answer(query, raw) if raw else ""

    def _ai_worker():
        if state.is_stop_requested():
            return
        # Only run the general AI worker for non-name queries to save latency
        if not is_name_q:
            ai_result["text"] = _cached_ai(query, "", history)

    wiki_thread = threading.Thread(target=_wiki_worker, name="WikiFetch", daemon=True)
    ai_thread = threading.Thread(target=_ai_worker, name="AIGen", daemon=True)

    wiki_thread.start()
    ai_thread.start()

    wiki_thread.join(timeout=10)
    ai_thread.join(timeout=_OLLAMA_TIMEOUT)

    if state.is_stop_requested():
        return ""

    wiki_context = wiki_result["text"]

    # ── Name queries: return the name directly ────────────────────────────────
    if is_name_q:
        if wiki_context:
            words = wiki_context.split()
            # If extracted text is short enough to be a real name, return it directly
            if 1 <= len(words) <= 5:
                return f"Sir, {wiki_context}."
            # Extracted text is too long (probably a full sentence) — ask Ollama
            name = _ollama_get_name(query)
            if name:
                return f"Sir, {name}."
            # Ollama also failed — fall back to first sentence from wiki
            first_sentence = wiki_context.split(".")[0].strip()
            if first_sentence:
                return f"Sir, {first_sentence}."

        # No wiki result at all — ask Ollama directly
        name = _ollama_get_name(query)
        if name:
            return f"Sir, {name}."

        return "Sir, mujhe abhi yeh information nahi mili. Kya aap thodi der baad try karenge?"

    # ── Descriptive queries: use wiki context + AI ────────────────────────────
    if wiki_context:
        return _cached_ai(query, wiki_context, history)

    if ai_result["text"]:
        return ai_result["text"]

    return "Sir, abhi mujhe yeh information nahi mil pa rahi. Internet check kariye ya thodi der baad try karein."
