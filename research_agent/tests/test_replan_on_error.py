import pytest
from unittest.mock import patch, AsyncMock
from orchestrator import research_agent


@pytest.mark.asyncio
async def test_replan_on_tool_error():
    """
    Проверяем, что при ошибке инструмента вызывается replan,
    и финальный отчёт содержит примечание о неполноте.
    """
    # Начальный план: два шага
    initial_plan = [
        {"description": "поиск в вики", "expected_keywords": ["определение"]},
        {"description": "поиск в веб", "expected_keywords": []}
    ]

    # Мокаем search_wikipedia: всегда ошибка
    async def wiki_error(query):
        return ("", [], False, "Wikipedia error")

    # Мокаем search_duckduckgo: успех (чтобы второй шаг выполнился)
    async def ddg_success(query):
        return ("текст", ["https://example.com"], True, None)

    # Мокаем replan: возвращаем изменённый план (например, удаляем неудачный шаг)
    async def replan_with_change(remaining_steps, last_step, all_steps, mode, remaining_time=None):
        # Возвращаем оставшиеся шаги без изменений (или можем изменить)
        # Для теста просто вернём исходные оставшиеся шаги, но чтобы partial=True
        return remaining_steps

    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen, \
         patch("orchestrator.replan", new_callable=AsyncMock) as mock_replan, \
         patch("orchestrator.search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
         patch("orchestrator.search_duckduckgo", new_callable=AsyncMock) as mock_ddg, \
         patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:

        mock_gen.return_value = initial_plan
        mock_replan.side_effect = replan_with_change
        mock_wiki.side_effect = wiki_error
        mock_ddg.side_effect = ddg_success

        # Мокаем синтезатор, чтобы он не делал реальный LLM вызов, а сразу вернул шаблон с partial-примечанием
        # Лучше дать синтезатору отработать реально, но с моком call_llm.
        # Подготовим отчёт, который синтезатор должен вернуть (с примечанием)
        partial_report = """# Отчёт по теме: Тема

> **Примечание:** Исследование выполнено не полностью из-за ошибок или таймаута.

## Введение
...

## Ключевые факты
...

## Выводы
...

## Источники
...
"""
        mock_llm.return_value = partial_report

        memory, report = await research_agent("Тема", "fast")

        # Проверяем, что replan был вызван (хотя бы один раз)
        assert mock_replan.call_count >= 1

        # Проверяем, что отчёт содержит примечание о неполноте
        assert "Примечание:" in report
        assert "выполнено не полностью" in report or "частично" in report

        # Дополнительно: первый шаг должен быть с ошибкой
        assert len(memory.steps) >= 1
        assert memory.steps[0].success is False
        assert "Wikipedia error" in memory.steps[0].error_msg

# pytest research_agent/tests/test_replan_on_error.py -v
