import asyncio
from typing import List, Optional, Tuple
from ddgs import DDGS
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from config import WEB_TIMEOUT, MAX_RESULT_TEXT_LENGTH

def _sync_search(query: str) -> List[dict]:
    """Синхронная обёртка для вызова DDGS.atext."""
    with DDGS() as ddgs:
        results = list(ddgs.atext(query, max_results=5))
        return results

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),  # Повторять при любых исключениях
)

async def _execute_search_with_retry(query: str) -> List[dict]:
    """Выполняет поиск с retry, бросает исключения."""
    results = await asyncio.wait_for(
        asyncio.to_thread(_sync_search, query),
        timeout=WEB_TIMEOUT
    )
    if not results:
        raise Exception("No results from DuckDuckGo")
    return results

async def search_duckduckgo(query: str) -> Tuple[str, List[str], bool, Optional[str]]:
    try:
        results = await _execute_search_with_retry(query)
    except Exception as e:
        return "", [], False, str(e)
    
    # Собираем тексты и URL
    texts = []
    urls = []
    for r in results:
        body = r.get("body", "")
        if body:
            texts.append(body)
        href = r.get("href", "")
        if href and href not in urls:
            urls.append(href)

    combined_text = " ".join(texts)
    if len(combined_text) > MAX_RESULT_TEXT_LENGTH:
        combined_text = combined_text[:MAX_RESULT_TEXT_LENGTH]

    # Проверка успеха
    success = len(combined_text) >= 50 and len(urls) >= 1
    error = None if success else f"Insufficient data: text_len={len(combined_text)}, urls={len(urls)}"

    return combined_text, urls, success, error