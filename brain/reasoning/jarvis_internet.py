"""
jarvis_internet.py  –  Web research and summarisation for Jarvis
================================================================
Allows Jarvis to search the internet and return concise spoken summaries.

Pipeline:
    query → Google/DuckDuckGo search → fetch top pages
          → extract main text → summarise → spoken output

Dependencies:
    pip install requests beautifulsoup4

Public API
----------
    from jarvis_internet import internet

    result = internet.search_and_summarize("best python books")
    print(result["summary"])    # concise 3–5 sentence answer

    snippet = internet.quick_answer("what is machine learning")
    print(snippet)              # short definition / Wikipedia snippet
"""

import re
import threading
import time
from typing import Optional
from urllib.parse import quote_plus

# ── Optional imports (fail gracefully) ────────────────────────────────────────
try:
    import requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False
    print("[Internet] requests not installed — web features disabled.")

try:
    from bs4 import BeautifulSoup
    _BS4_OK = True
except ImportError:
    _BS4_OK = False
    print("[Internet] beautifulsoup4 not installed — text extraction limited.")


# ── Constants ─────────────────────────────────────────────────────────────────
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9,hi;q=0.8",
}
_TIMEOUT  = 8       # seconds for HTTP requests
_MAX_CHARS = 3000   # max characters to extract from a page


class JarvisInternet:
    """
    Web search and summarisation engine for Jarvis.
    Gracefully degrades when offline or packages are missing.
    """

    def __init__(self):
        self._lock    = threading.Lock()
        self._cache   = {}   # query → result (simple in-memory cache)

    # ── Public API ────────────────────────────────────────────────────────────

    def search_and_summarize(self, query: str, max_results: int = 3) -> dict:
        """
        Search for `query` and return a spoken summary.

        Returns
        -------
        {
            "query"   : str,
            "summary" : str,   # 3-5 sentences, ready to speak
            "sources" : list,  # URLs used
            "ok"      : bool,
        }
        """
        if not _REQUESTS_OK:
            return self._offline_result(query)

        with self._lock:
            if query in self._cache:
                return self._cache[query]

        print(f"[Internet] Searching: {query!r}")
        urls = self._ddg_search(query, max_results)

        if not urls:
            return {
                "query"  : query,
                "summary": f"I couldn't find any results for '{query}'. Please check your internet connection.",
                "sources": [],
                "ok"     : False,
            }

        texts   = []
        sources = []
        for url in urls[:max_results]:
            text = self._fetch_text(url)
            if text:
                texts.append(text)
                sources.append(url)
            time.sleep(0.3)   # polite crawl delay

        combined = "\n\n".join(texts)
        summary  = self._summarize(combined, query)

        result = {
            "query"  : query,
            "summary": summary,
            "sources": sources,
            "ok"     : bool(summary),
        }

        with self._lock:
            self._cache[query] = result   # cache the result

        return result

    def quick_answer(self, query: str) -> str:
        """
        Fast 1-2 sentence answer by scraping a Wikipedia snippet or
        DuckDuckGo instant answer. Returns '' on failure.
        """
        if not _REQUESTS_OK:
            return ""
        try:
            # Try DuckDuckGo instant answer API
            url  = f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1"
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            data = resp.json()

            abstract = data.get("AbstractText", "").strip()
            if abstract:
                return _trim_to_sentences(abstract, 2)

            answer = data.get("Answer", "").strip()
            if answer:
                return answer

        except Exception as exc:
            print(f"[Internet] quick_answer error: {exc}")
        return ""

    def is_online(self) -> bool:
        """Check internet connectivity."""
        if not _REQUESTS_OK:
            return False
        try:
            requests.get("https://www.google.com", timeout=3)
            return True
        except Exception:
            return False

    def offline_warning(self) -> str:
        """Return the required offline warning message."""
        return "O.. o.. you are not connected to the internet. Please connect first."

    # ── DuckDuckGo search ─────────────────────────────────────────────────────

    def _ddg_search(self, query: str, n: int = 3) -> list:
        """
        Use DuckDuckGo HTML search to get top `n` result URLs.
        Returns a list of URL strings.
        """
        try:
            url  = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            if not _BS4_OK:
                return []
            soup  = BeautifulSoup(resp.text, "html.parser")
            links = []
            for a in soup.select("a.result__url"):
                href = a.get("href", "").strip()
                if href and href.startswith("http") and "duckduckgo" not in href:
                    links.append(href)
                    if len(links) >= n:
                        break
            print(f"[Internet] Found {len(links)} results for {query!r}")
            return links
        except Exception as exc:
            print(f"[Internet] DDG search error: {exc}")
            return []

    # ── Page text extraction ──────────────────────────────────────────────────

    def _fetch_text(self, url: str) -> str:
        """
        Download a web page and extract clean main-body text.
        Returns '' on failure.
        """
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            if not _BS4_OK:
                return ""
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove navigation, ads, scripts, styles
            for tag in soup(["script", "style", "nav", "footer",
                              "header", "aside", "form", "noscript"]):
                tag.decompose()

            # Prefer article / main content
            body = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", id=re.compile(r"content|main|article", re.I))
                or soup.body
            )
            if body is None:
                return ""

            text = body.get_text(separator=" ", strip=True)
            text = re.sub(r"\s+", " ", text).strip()
            return text[:_MAX_CHARS]

        except Exception as exc:
            print(f"[Internet] fetch error [{url[:60]}]: {exc}")
            return ""

    # ── Summarisation ─────────────────────────────────────────────────────────

    def _summarize(self, text: str, query: str = "") -> str:
        """
        Extract a concise 3–5 sentence summary from `text`.
        Uses extractive summarization (no LLM call needed).
        """
        if not text:
            return "I found some results but couldn't extract readable content."

        # Split into sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 30]

        if not sentences:
            return "I found some results but the content was unclear."

        # Score sentences by keyword overlap with query
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for s in sentences:
            s_words = set(re.findall(r"\w+", s.lower()))
            score   = len(query_words & s_words)
            scored.append((score, s))

        scored.sort(key=lambda x: -x[0])

        # Pick top 4 sentences, restore original order
        top_indices = set()
        top_sents   = []
        for _, s in scored[:4]:
            idx = sentences.index(s)
            top_indices.add(idx)
            top_sents.append((idx, s))

        top_sents.sort(key=lambda x: x[0])
        summary = " ".join(s for _, s in top_sents)

        return _trim_to_sentences(summary, 4) or "I found results but couldn't form a clean summary."

    # ── Offline fallback ──────────────────────────────────────────────────────

    def _offline_result(self, query: str) -> dict:
        return {
            "query"  : query,
            "summary": self.offline_warning(),
            "sources": [],
            "ok"     : False,
        }


def _trim_to_sentences(text: str, n: int) -> str:
    """Return first n complete sentences from text."""
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return " ".join(parts[:n])


# ── Module singleton ──────────────────────────────────────────────────────────
internet = JarvisInternet()
