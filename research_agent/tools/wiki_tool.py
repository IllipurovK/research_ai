import urllib.parse
import asyncio
from typing import List, Optional, Tuple
import aiohttp
from config import WIKI_TIMEOUT, MAX_RESULT_TEXT_LENGTH

USER_AGENT = "ResearchAgent/1.0 (https://github.com/IllipurovK/research_ai; educational)"

async def search_wikipedia(query: str) -> Tuple[str, List[str], bool, Optional[str]]:
    """
    Выполняет поиск статьи в Wikipedia (русскоязычной) по запросу.

    Returns:
        (text, urls, success, error)
    """
    url = "https://ru.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "extracts",
        "exintro": 1,
        "explaintext": 1,
        "format": "json",
        "titles": query,
    }
    headers = {"User-Agent": USER_AGENT}

    try:
        timeout = aiohttp.ClientTimeout(total=WIKI_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return "", [], False, f"HTTP {response.status}"

                data = await response.json()
                pages = data.get("query", {}).get("pages", {})
                if not pages:
                    return "", [], False, "No pages in response"

                for page_id, page in pages.items():
                    if page_id == "-1":
                        continue
                    title = page.get("title", "")
                    extract = page.get("extract", "")
                    if extract:
                        if len(extract) > MAX_RESULT_TEXT_LENGTH:
                            extract = extract[:MAX_RESULT_TEXT_LENGTH]
                        page_url = f"https://ru.wikipedia.org/wiki/{urllib.parse.quote(title)}"
                        return extract, [page_url], True, None

                return "", [], False, f"Page not found for query: {query}"

    except asyncio.TimeoutError:
        return "", [], False, f"Timeout after {WIKI_TIMEOUT}s"
    except Exception as e:
        return "", [], False, str(e)