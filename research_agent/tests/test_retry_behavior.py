import pytest
from unittest.mock import patch
from orchestrator import research_agent


@pytest.mark.asyncio
async def test_retry_in_orchestrator():
    """
    Проверяем, что при временных ошибках инструмента (duckduckgo)
    происходит повтор (retry внутри инструмента), и шаг в итоге становится успешным.
    Мокаем _sync_search, а не search_duckduckgo.
    """
    mock_plan = [{"description": "поиск", "expected_keywords": []}]  # будет выбран web

    # Счётчик вызовов _sync_search
    call_count = 0

    def flaky_sync_search(query):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise Exception("Временная ошибка сети")
        else:
            # Текст длиной более 50 символов
            long_text = "успешный текст" * 10
            return [{"body": long_text, "href": "https://example.com"}]

    with patch("orchestrator.generate_plan") as mock_gen, \
         patch("orchestrator.replan") as mock_replan, \
         patch("orchestrator.search_wikipedia") as mock_wiki, \
         patch("research_agent.tools.duckduckgo_tool._sync_search", side_effect=flaky_sync_search) as mock_sync, \
         patch("llm_client.call_llm") as mock_llm:

        mock_gen.return_value = mock_plan
        mock_replan.return_value = []
        mock_wiki.return_value = ("", [], False, "ignored")
        mock_llm.return_value = "# Отчёт"

        memory, report = await research_agent("тема", "fast")

        # Проверяем, что _sync_search вызывался 3 раза (2 ошибки + успех)
        assert mock_sync.call_count == 3

        # Шаг должен быть успешным
        assert len(memory.steps) == 1
        assert memory.steps[0].success is True
        assert "успешный текст" in memory.steps[0].result_text
# pytest research_agent/tests/test_retry_behavior.py -v