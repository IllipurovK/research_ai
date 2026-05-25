import pytest
from executor import select_tool_by_keywords


def test_select_tool_by_keywords():
    # Проверка на ключевых словах из описания
    assert select_tool_by_keywords("что такое квант", None) == "wiki"
    assert select_tool_by_keywords("погода", None) == "web"
    
    # Дополнительные тесты для покрытия expected_keywords
    assert select_tool_by_keywords("любой текст", expected_keywords=["определение"]) == "wiki"
    assert select_tool_by_keywords("любой текст", expected_keywords=["история"]) == "wiki"
    assert select_tool_by_keywords("любой текст", expected_keywords=["неизвестное"]) == "web"
    
    # Проверка на регистронезависимость
    assert select_tool_by_keywords("Здесь есть ФАКТЫ", None) == "wiki"
    assert select_tool_by_keywords("терминология", None) == "web"

# pytest research_agent/tests/test_executor.py -v