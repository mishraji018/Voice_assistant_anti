import requests
from bs4 import BeautifulSoup

def search_web(query: str) -> str:
    """
    Performs a web search using DuckDuckGo (HTML version) and returns a summary.
    """
    print(f"[WebSearch] Searching for: {query}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        url = f"https://html.duckduckgo.com/html/?q={query}"
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        results = soup.find_all('div', class_='result')
        
        if not results:
            return "I couldn't find any direct results for that online."
            
        summary_parts = []
        for i, res in enumerate(results[:3]):
            title = res.find('a', class_='result__a')
            snippet = res.find('a', class_='result__snippet')
            if title and snippet:
                summary_parts.append(f"{i+1}. {title.text.strip()}: {snippet.text.strip()}")
            
        return "\n".join(summary_parts) if summary_parts else "No snippets found."
        
    except Exception as e:
        print(f"[WebSearch] Error: {e}")
        return f"Web search encounterd an error: {str(e)}"

if __name__ == "__main__":
    print(search_web("Current weather in Delhi"))