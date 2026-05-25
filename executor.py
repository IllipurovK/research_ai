from typing import List, Optional
from config import WIKI_KEYWORDS

def select_tool_by_keywords(
    description: str,
    expected_keywords: Optional[List[str]] = None
) -> str:
    """
    Определяет, какой инструмент использовать: "wiki" или "web".
    
    Алгоритм:
    1. Если expected_keywords задан и есть пересечение с WIKI_KEYWORDS → "wiki".
    2. Иначе разбиваем description на слова, ищем любое слово из WIKI_KEYWORDS → "wiki".
    3. Иначе → "web".
    """
    # Приведение expected_keywords к нижнему регистру для сравнения
    if expected_keywords:
        expected_lower = [kw.lower() for kw in expected_keywords]
        if any(kw in WIKI_KEYWORDS for kw in expected_lower):
            return "wiki"
    desc_lower = description.lower()
    words = desc_lower.split()
          
    for kw in WIKI_KEYWORDS:
        if ' ' in kw:  # фраза из нескольких слов
            if kw in desc_lower:
                return "wiki"
        else:  # одно слово
            if kw in words:
                return "wiki"
    return "web"