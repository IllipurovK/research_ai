import pytest
from unittest.mock import patch, AsyncMock
from orchestrator import research_agent
from memory import Memory


@pytest.mark.asyncio
async def test_integration_success():
    mock_plan = [{"description": "определение тестового запроса", "expected_keywords": ["определение"]}]

    async def mock_wiki(query):
        return ("Текст из википедии", ["https://ru.wikipedia.org/wiki/%D0%A2%D0%B5%D1%81%D1%82"], True, None)

    async def mock_ddg(query):
        return ("Текст из DuckDuckGo", ["https://example.com"], True, None)

    async def mock_replan(*args, **kwargs):
        return []

    good_report = """# Отчёт по теме: Искусственный интеллект

## Введение
Введение в тему.

## Ключевые факты
Факт 1 [шаг 0]

## Выводы
Выводы по теме.

## Источники
- https://ru.wikipedia.org/wiki/%D0%A2%D0%B5%D1%81%D1%82 [шаг 0]
"""
    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen, \
         patch("orchestrator.replan", new_callable=AsyncMock) as mock_replan_func, \
         patch("orchestrator.search_wikipedia", new_callable=AsyncMock) as mock_wiki_func, \
         patch("orchestrator.search_duckduckgo", new_callable=AsyncMock) as mock_ddg_func, \
         patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:

        mock_gen.return_value = mock_plan
        mock_replan_func.side_effect = mock_replan
        mock_wiki_func.side_effect = mock_wiki
        mock_ddg_func.side_effect = mock_ddg
        mock_llm.return_value = good_report

        memory, report = await research_agent("Искусственный интеллект", "fast")

        assert isinstance(memory, Memory)
        assert len(memory.steps) >= 1
        assert "# Отчёт по теме: Искусственный интеллект" in report
        assert "## Введение" in report
        assert "## Выводы" in report
        assert "## Источники" in report
        assert "Примечание" not in report
        mock_llm.assert_awaited_once()

# pytest research_agent/tests/test_integration_success.py -v