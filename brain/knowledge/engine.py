
import wikipedia
import ollama
import logging

logger = logging.getLogger(__name__)

def fetch_wiki_summary(query: str) -> str:
    """Fetch a concise summary from Wikipedia."""
    try:
        # Search for the most relevant page
        search_results = wikipedia.search(query)
        if not search_results:
            return ""
        
        # Get the summary of the first result
        summary = wikipedia.summary(search_results[0], sentences=2)
        return summary
    except Exception as e:
        logger.error(f"Wikipedia error: {e}")
        return ""

def generate_ai_response(query: str, context: str = "") -> str:
    """Refine a response using Ollama LLM with a professional persona."""
    system_prompt = """
    You are JARVIS, a calm and professional Hindi-English female assistant.
    Always address the user as 'sir'.
    Never use slang like 'bhai'.
    Be polite and concise.
    If you are unsure of an answer, ask for clarification instead of guessing or hallucinating.
    Maintain a helpful tone that is professional yet natural for a personal assistant.
    """
    
    prompt = f"""
    System Instructions: {system_prompt}
    
    User Query: {query}
    Context: {context}
    
    Task: Provide a natural, polite, and concise response. 
    Use a mix of Hindi and English (Hinglish) where appropriate.
    Always call the user 'sir'.
    """

    
    try:
        response = ollama.chat(model='llama3', messages=[
            {'role': 'user', 'content': prompt},
        ])
        return response['message']['content']
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        # Fallback to simple context or template
        return f"I found this: {context}" if context else "I'm processing that for you."

def get_answer(query: str) -> str:
    """Complete hybrid knowledge flow."""
    wiki_context = fetch_wiki_summary(query)
    return generate_ai_response(query, wiki_context)
