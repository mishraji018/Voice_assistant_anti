
import webbrowser
import requests
from bs4 import BeautifulSoup
import logging
from brain.knowledge.engine import generate_ai_response
from core.state.runtime_state import state

logger = logging.getLogger(__name__)

class BrowserAgent:
    """
    Handles autonomous browser operations, searching, and result extraction.
    """
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def search_and_summarize(self, query: str) -> str:
        """Search Google, extract top results, and summarize them."""
        if state.is_stop_requested(): return ""

        search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        
        # 1. Open browser for visual feedback (optional, but requested)
        webbrowser.open(search_url)

        # 2. Extract results in background
        try:
            response = requests.get(search_url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return "Sir, I couldn't reach Google right now. Please check your internet."

            soup = BeautifulSoup(response.text, "html.parser")
            
            # Extract snippets from Google search results
            snippets = []
            for g in soup.find_all('div', class_='VwiC3b'):
                snippets.append(g.get_text())
                if len(snippets) >= 3: break
            
            if not snippets:
                return "Sir, I found some results on the browser, but I couldn't extract a summary. Aap wahan dekh sakte hain."

            # 3. Summarize using existing AI engine
            context = "\n".join(snippets)
            summary = generate_ai_response(
                query=f"Summarize these search results for: {query}",
                context=context,
                history="You are summarizing web search results for the user."
            )
            
            return f"Sir, according to my research: {summary}"

        except Exception as e:
            logger.error(f"Browser agent error: {e}")
            return "Sir, searching mein kuch dikat aa rahi hai. Maine browser mein search open kar diya hai."

# Singleton instance
browser_agent = BrowserAgent()
