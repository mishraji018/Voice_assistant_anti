
import wikipedia
import ollama
import logging
import functools
import threading

from core.state.runtime_state import state

logger = logging.getLogger(__name__)

# ── Ollama config ─────────────────────────────────────────────────────────────
_OLLAMA_MODEL = "llama3"
_OLLAMA_MAX_RETRIES = 2
_OLLAMA_TIMEOUT = 30  # seconds


def fetch_wiki_summary(query: str) -> str:
    """Fetch a concise summary from Wikipedia."""
    try:
        search_results = wikipedia.search(query)
        if not search_results:
            return ""
        summary = wikipedia.summary(search_results[0], sentences=2)
        return summary
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

    last_error = None
    for attempt in range(_OLLAMA_MAX_RETRIES):
        # Check stop flag before each attempt
        if state.is_stop_requested():
            return ""
        try:
            response = ollama.chat(model=_OLLAMA_MODEL, messages=[
                {'role': 'user', 'content': prompt},
            ])
            content = response.get('message', {}).get('content', '').strip()
            if content:
                return content
            # Empty response — retry
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
    Complete hybrid knowledge flow.
    Runs Wikipedia fetch and AI generation in PARALLEL threads
    for reduced latency. Respects stop flag throughout.
    """
    if state.is_stop_requested():
        return ""

    # ── Run Wikipedia and AI in parallel ──────────────────────────────────────
    wiki_result = {"text": ""}
    ai_result = {"text": ""}

    def _wiki_worker():
        if state.is_stop_requested():
            return
        wiki_result["text"] = _cached_wiki(query)

    def _ai_worker():
        # Start AI generation immediately with empty context
        # If wiki finishes first, we re-run with context (cache handles dedup)
        if state.is_stop_requested():
            return
        ai_result["text"] = _cached_ai(query, "", history)

    wiki_thread = threading.Thread(target=_wiki_worker, name="WikiFetch", daemon=True)
    ai_thread = threading.Thread(target=_ai_worker, name="AIGen", daemon=True)

    wiki_thread.start()
    ai_thread.start()

    # Wait for wiki first (usually faster)
    wiki_thread.join(timeout=10)
    ai_thread.join(timeout=_OLLAMA_TIMEOUT)

    if state.is_stop_requested():
        return ""

    wiki_context = wiki_result["text"]

    # If we got wiki context, generate a better AI response with it
    # (the cache will instantly return if query+""+history was already computed)
    if wiki_context:
        return _cached_ai(query, wiki_context, history)

    # No wiki context — use the parallel AI result
    if ai_result["text"]:
        return ai_result["text"]

    # Both failed — fallback
    return "Sir, abhi mujhe yeh information nahi mil pa rahi. Kya aap thodi der baad phir try karenge?"
