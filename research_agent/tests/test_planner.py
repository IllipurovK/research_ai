import pytest
from unittest.mock import patch, AsyncMock
import json
from planner import generate_plan, replan
from models import Step


def test_planner_prompt_exists():
    """Проверка, что промпт planner.txt существует и начинается с ожидаемой строки."""
    with open("research_agent/prompts/planner.txt", "r", encoding="utf-8") as f:
        content = f.read()
    assert content.startswith("Ты — планировщик исследования")


@pytest.mark.asyncio
async def test_generate_plan_returns_list_of_dicts():
    """Мок call_llm возвращает валидный JSON; проверяем, что план не пуст и содержит поля."""
    mock_response = '[{"description": "Найти определение", "expected_keywords": ["определение"]}]'
    with patch("planner.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = mock_response
        plan = await generate_plan(topic="квантовый компьютер", mode="fast")
        assert isinstance(plan, list)
        assert len(plan) > 0
        assert "description" in plan[0]
        assert "expected_keywords" in plan[0]
        assert plan[0]["description"] == "Найти определение"
        assert plan[0]["expected_keywords"] == ["определение"]


@pytest.mark.asyncio
async def test_generate_plan_handles_invalid_json():
    """При ошибке парсинга JSON возвращается fallback-план (не пустой)."""
    with patch("planner.call_llm", new_callable=AsyncMock) as mock_call:
        # Возвращаем невалидный JSON
        mock_call.return_value = "Это не JSON"
        plan = await generate_plan(topic="тема", mode="fast")
        assert isinstance(plan, list)
        assert len(plan) >= 1
        assert "description" in plan[0]


@pytest.mark.asyncio
async def test_replan_returns_original_on_error():
    """При ошибке парсинга replan возвращает исходный список оставшихся шагов."""
    original_steps = [{"description": "шаг1", "expected_keywords": []}]
    last_step = Step(
        step_id=0, description="последний", query="запрос", normalized_query="запрос",
        success=True, result_text="результат"
    )
    all_steps = [last_step]
    with patch("planner.call_llm", new_callable=AsyncMock) as mock_call:
        mock_call.return_value = "не JSON"
        new_steps = await replan(
            remaining_steps=original_steps,
            last_step=last_step,
            all_steps=all_steps,
            mode="fast"
        )
        assert new_steps == original_steps

# pytest research_agent/tests/test_planner.py -v
