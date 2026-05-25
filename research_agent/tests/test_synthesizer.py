# tests/test_synthesizer.py
import pytest
from unittest.mock import AsyncMock, patch
from memory import Memory
from models import Step
from synthesizer import synthesize_report, _validate_links

# ------------------------------------------------------------
# Фикстуры для создания памяти с шагами
# ------------------------------------------------------------

@pytest.fixture
def memory_with_success_step():
    """Возвращает Memory с одним успешным шагом (step_id=1, url='https://example.com')."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Тестовый шаг",
        expected_keywords=[],
        query="тест",
        normalized_query="тест",
        tool="wiki",
        result_text="Результат теста.",
        urls=["https://example.com"],
        success=True,
        error_msg=None,
        retry_count=0,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)
    return memory

@pytest.fixture
def memory_with_failed_step():
    """Возвращает Memory с одним НЕуспешным шагом."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Неуспешный шаг",
        expected_keywords=[],
        query="тест",
        normalized_query="тест",
        tool="web",
        result_text="",
        urls=[],
        success=False,
        error_msg="Ошибка",
        retry_count=1,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)
    return memory

# ------------------------------------------------------------
# Тесты для _validate_links (прямое тестирование)
# ------------------------------------------------------------

def test_validate_links_success(memory_with_success_step):
    """Корректный URL и ссылка на шаг -> True."""
    report = """
    # Отчёт
    Источник: https://example.com [шаг 1]
    """
    assert _validate_links(report, memory_with_success_step) is True

def test_validate_links_invalid_url(memory_with_success_step):
    """URL не из реальных данных -> False."""
    report = """
    # Отчёт
    Источник: https://fake-url.com [шаг 1]
    """
    assert _validate_links(report, memory_with_success_step) is False

def test_validate_links_invalid_step_ref(memory_with_success_step):
    """Ссылка на несуществующий шаг -> False."""
    report = """
    # Отчёт
    [шаг 999]
    """
    assert _validate_links(report, memory_with_success_step) is False

def test_validate_links_invalid_step_success_false(memory_with_failed_step):
    """Шаг существует, но success=False -> False."""
    report = """
    # Отчёт
    [шаг 1]
    """
    # В memory_with_failed_step есть шаг с step_id=1, но success=False
    assert _validate_links(report, memory_with_failed_step) is False

# ------------------------------------------------------------
# Тесты для synthesize_report
# ------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesizer_no_successful_steps():
    """Нет успешных шагов -> возврат шаблона, LLM не вызывается."""
    memory = Memory()  # пустая
    with patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        report = await synthesize_report(
            topic="Пустая тема",
            memory=memory,
            partial=False,
            mode="fast",
            remaining_time=30.0
        )
        mock_llm.assert_not_awaited()
        assert "# Отчёт по теме: Пустая тема" in report
        assert "Нет успешных шагов" in report

@pytest.mark.asyncio
async def test_synthesizer_validation_fail_then_retry_success():
    """Первый отчёт с плохой ссылкой, второй корректный -> успех."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Шаг",
        expected_keywords=[],
        query="запрос",
        normalized_query="запрос",
        tool="wiki",
        result_text="Результат",
        urls=["https://real.com"],
        success=True,
        error_msg=None,
        retry_count=0,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)

    bad_report = "# Отчёт\n[шаг 999]\n## Источники\n- https://fake.com"
    good_report = "# Отчёт\n[шаг 1]\n## Источники\n- https://real.com"

    with patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [bad_report, good_report]
        report = await synthesize_report(
            topic="Тема",
            memory=memory,
            partial=False,
            mode="fast",
            remaining_time=30.0
        )
        # Проверяем, что было два вызова
        assert mock_llm.await_count == 2
        # Второй вызов должен быть с temperature=0.0
        second_call_kwargs = mock_llm.await_args_list[1][1]
        assert second_call_kwargs["temperature"] == 0.0
        # В системный промпт добавлено предупреждение
        assert "ВНИМАНИЕ: Предыдущая попытка содержала выдуманные ссылки" in second_call_kwargs["system_prompt"]
        # Итоговый отчёт — хороший
        assert "Ошибка генерации" not in report
        assert "[шаг 1]" in report

@pytest.mark.asyncio
async def test_synthesizer_validation_fail_then_retry_fail():
    """Оба отчёта с плохими ссылками -> возврат сообщения об ошибке."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Шаг",
        expected_keywords=[],
        query="запрос",
        normalized_query="запрос",
        tool="wiki",
        result_text="Результат",
        urls=["https://real.com"],
        success=True,
        error_msg=None,
        retry_count=0,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)

    bad_report1 = "# Отчёт\n[шаг 999]"
    bad_report2 = "# Отчёт\n[шаг 888]"

    with patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.side_effect = [bad_report1, bad_report2]
        report = await synthesize_report(
            topic="Тема",
            memory=memory,
            partial=False,
            mode="fast",
            remaining_time=30.0
        )
        assert mock_llm.await_count == 2
        assert report == "Ошибка генерации: LLM сгаллюцинировал ссылки"

@pytest.mark.asyncio
async def test_synthesizer_partial_note_true():
    """partial=True -> в отчёт добавляется примечание."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Шаг",
        expected_keywords=[],
        query="q",
        normalized_query="q",
        tool="wiki",
        result_text="Res",
        urls=["https://real.com"],
        success=True,
        error_msg=None,
        retry_count=0,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)

    good_report = """# Отчёт по теме: Тема

## Введение
Введение

## Ключевые факты
Факт [шаг 1]

## Выводы
Вывод

## Источники
- https://real.com
"""
    with patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = good_report
        report = await synthesize_report(
            topic="Тема",
            memory=memory,
            partial=True,
            mode="fast",
            remaining_time=30.0
        )
        # Проверяем наличие примечания
        assert "> **Примечание:** Исследование выполнено не полностью" in report
        # Примечание должно быть после заголовка
        lines = report.splitlines()
        # Находим строку с заголовком и следующую за ней (возможно пустую)
        for i, line in enumerate(lines):
            if line.startswith("# Отчёт по теме:"):
                # Примечание должно быть на i+1 или i+2 (если есть пустая строка)
                assert any("Примечание" in lines[j] for j in range(i+1, min(i+3, len(lines))))
                break

@pytest.mark.asyncio
async def test_synthesizer_partial_note_false():
    """partial=False -> примечание отсутствует."""
    memory = Memory()
    step = Step(
        step_id=1,
        description="Шаг",
        expected_keywords=[],
        query="q",
        normalized_query="q",
        tool="wiki",
        result_text="Res",
        urls=["https://real.com"],
        success=True,
        error_msg=None,
        retry_count=0,
        start_time=0.0,
        end_time=0.0
    )
    memory.add_step(step)

    good_report = """# Отчёт по теме: Тема

## Введение
Введение

## Ключевые факты
Факт [шаг 1]

## Выводы
Вывод

## Источники
- https://real.com
"""
    with patch("llm_client.call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = good_report
        report = await synthesize_report(
            topic="Тема",
            memory=memory,
            partial=False,
            mode="fast",
            remaining_time=30.0
        )
        assert "> **Примечание:**" not in report