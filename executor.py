from typing import List, Optional
from config import WIKI_KEYWORDS

def select_tool_by_keywords(
    description: str,
    expected_keywords: Optional[List[str]] = None
) -> str:
    if expected_keywords:
        if any(kw in ("определение", "википедия", "wiki", "wikipedia") for kw in expected_keywords):
            return "wiki"
    desc_lower = description.lower()
    wiki_phrases = ("определение", "что такое", "википедия", "wiki")
    if any(phrase in desc_lower for phrase in wiki_phrases):
        return "wiki"
    
    web_phrases = ("новости", "пример", "обзор", "цена", "стоимость", "купить", "скачать", "современный")
    if any(phrase in desc_lower for phrase in web_phrases):
        return "web"
    # По умолчанию web (более широкий охват)
    return "web"