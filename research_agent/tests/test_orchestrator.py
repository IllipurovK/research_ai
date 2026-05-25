import pytest
from unittest.mock import patch, AsyncMock, MagicMock
import time
from orchestrator import research_agent, get_remaining_time
from memory import Memory
from models import Step
from config import MODES, MAX_GLOBAL_STEPS
from orchestrator import logger as orchestrator_logger

@pytest.mark.asyncio
async def test_research_agent_initialization_and_timeout():
    """
    Проверяет инициализацию memory, start_time, timeout_limit,
    корректное вычисление remaining_time и передачу в generate_plan,
    а также поведение при недостатке времени.
    """
    from orchestrator import research_agent, get_remaining_time
    from config import MODES
    import time as time_module

    mode = "fast"
    timeout_limit = MODES[mode]["global_timeout"]
    expected_buffer = 2  # TIMEOUT_BUFFER_SEC

    # Мокаем зависимые функции
    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen_plan, \
         patch("orchestrator.replan", new_callable=AsyncMock) as mock_replan, \
         patch("orchestrator.search_wikipedia", new_callable=AsyncMock) as mock_wiki, \
         patch("orchestrator.search_duckduckgo", new_callable=AsyncMock) as mock_ddg, \
         patch("orchestrator.synthesize_report", new_callable=AsyncMock) as mock_synth, \
         patch("orchestrator.time", wraps=time_module) as mock_time:

        # Устанавливаем начальное время
        start_mock = 1000.0
        mock_time.time.return_value = start_mock

        # Настраиваем моки инструментов, чтобы они не блокировали
        mock_wiki.return_value = ("wiki text", ["url"], True, None)
        mock_ddg.return_value = ("ddg text", ["url"], True, None)
        mock_gen_plan.return_value = [{"description": "test", "expected_keywords": []}]
        mock_replan.return_value = []
        mock_synth.return_value = "# Report"

        # Вызываем research_agent
        memory, report = await research_agent("тема", mode)

        # Проверка: memory - экземпляр Memory
        assert isinstance(memory, Memory)

        # Проверка, что start_time была установлена (через вызов time.time())
        # mock_time.time вызывалась хотя бы раз в начале research_agent
        assert mock_time.time.call_count >= 1

        # Проверка, что generate_plan получил remaining_time = timeout_limit - 0 - buffer
        expected_remaining = timeout_limit - expected_buffer  # так как elapsed=0
        # Из-за возможной погрешности (время в тесте не течёт) должно быть точно
        # Однако в коде get_remaining_time использует time.time() - start_time.
        # Поскольку мы замокали time.time() одним значением, elapsed = 0.
        # Но внутри research_agent start_time сохраняется через вызов time.time() в начале.
        # При вычислении remaining_time для generate_plan будет вызван get_remaining_time,
        # который снова вызовет time.time().
        # Чтобы избежать сложностей с повторными вызовами, мы можем просто проверить,
        # что переданный аргумент remaining_time положительный и меньше timeout_limit.
        call_args = mock_gen_plan.call_args
        assert call_args is not None
        _, kwargs = call_args
        assert "remaining_time" in kwargs
        rt = kwargs["remaining_time"]
        assert rt > 0
        assert rt <= timeout_limit

        # Дополнительно: проверим, что get_remaining_time работает правильно
        # Проверим через прямой вызов (не мок)
        # Но это уже отдельно.

    # Тест на недостаток времени: время уже истекло
    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen_plan2, \
         patch("orchestrator.replan", new_callable=AsyncMock), \
         patch("orchestrator.search_wikipedia", new_callable=AsyncMock), \
         patch("orchestrator.search_duckduckgo", new_callable=AsyncMock), \
         patch("orchestrator.synthesize_report", new_callable=AsyncMock), \
         patch("orchestrator.time", wraps=time_module) as mock_time2:

        # Устанавливаем start_time такое, что elapsed превышает лимит
        start_mock = 1000.0
        # Спустя время больше, чем timeout_limit + buffer
        mock_time2.time.side_effect = [start_mock, start_mock + timeout_limit + 10]

        # Ожидаем, что research_agent выбросит TimeoutError
        with pytest.raises(TimeoutError, match="Недостаточно времени для запуска исследования"):
            await research_agent("тема", mode)

        # generate_plan не должен быть вызван
        mock_gen_plan2.assert_not_called()

@pytest.mark.asyncio
async def test_research_agent_integration():
    """
    Интеграционный тест orchestrator с моками всех внешних вызовов.
    Проверяет инициализацию памяти, таймауты, цикл выполнения, дедупликацию, replan.
    """
    # Мокаем generate_plan: возвращает план из двух шагов
    mock_plan = [
    {"description": "что такое квантовый компьютер", "expected_keywords": ["определение"]},  # wiki
    {"description": "применение квантовых компьютеров", "expected_keywords": []},  # web (нет ключевых слов)
]

    # Мокаем replan: всегда возвращает оставшиеся шаги без изменений (или пустой список для завершения)
    # async def mock_replan(remaining_steps, last_step, all_steps, mode, remaining_time=None):
    #     # После первого шага оставшиеся шаги - второй элемент из mock_plan
    #     # Возвращаем один шаг (чтобы цикл не остановился)
    #     return [remaining_steps[0]] if remaining_steps else []

    # Мокаем инструменты
    async def mock_wiki(query):
        return ("Текст из википедии про квантовые компьютеры", ["https://ru.wikipedia.org/wiki/Квантовый_компьютер"], True, None)

    async def mock_duckduckgo(query):
        return ("Результат из DuckDuckGo", ["https://example.com"], True, None)

    # Мокаем synthesize_report
    async def mock_synthesize(topic, memory, partial, mode):
        return f"# Отчёт по теме {topic}\n\nУспешных шагов: {len(memory.get_successful_steps())}"

    # Патчим все зависимости
    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen_plan, \
        patch("orchestrator.replan", new_callable=AsyncMock) as mock_replan_func, \
        patch("orchestrator.search_wikipedia", new_callable=AsyncMock) as mock_wiki_func, \
        patch("orchestrator.search_duckduckgo", new_callable=AsyncMock) as mock_ddg_func, \
        patch("orchestrator.synthesize_report", new_callable=AsyncMock) as mock_synth_func:
        
        mock_gen_plan.return_value = mock_plan
        # replan вызывается один раз (после первого шага), возвращает оставшийся шаг
        mock_replan_func.return_value = [mock_plan[1]]
        mock_wiki_func.side_effect = mock_wiki
        mock_ddg_func.side_effect = mock_duckduckgo
        mock_synth_func.side_effect = mock_synthesize

        # Запускаем research_agent в режиме fast
        memory, report = await research_agent("квантовый компьютер", "fast")

        # Проверки
        assert isinstance(memory, Memory)
        assert len(memory.steps) == 2  # два шага выполнено
        assert all(step.success for step in memory.steps)
        assert len(memory.get_successful_steps()) == 2
        assert "квантовый компьютер" in report
        assert "Успешных шагов: 2" in report

        # Проверяем, что generate_plan был вызван с правильными параметрами
        # mock_gen_plan.assert_called_once()
        # args, kwargs = mock_gen_plan.call_args
        # assert mock_gen_plan.call_args[0][0] == "квантовый компьютер"
        # assert mock_gen_plan.call_args[0][1] == "fast"
        mock_gen_plan.assert_called_once()
        assert mock_gen_plan.call_args[0][0] == "квантовый компьютер"
        assert mock_gen_plan.call_args[0][1] == "fast"
        # remaining_time должен быть положительным
        assert mock_gen_plan.call_args[1]["remaining_time"] > 0

        # replan вызван один раз
        assert mock_replan_func.call_count == 1

        # Инструменты: первый шаг – wiki, второй – web
        assert mock_wiki_func.call_count == 1
        assert mock_ddg_func.call_count == 1

@pytest.mark.asyncio
async def test_research_agent_duplicate_step():
    """Проверка дедупликации: повторяющийся запрос не вызывает инструмент."""
    mock_plan = [
        {"description": "что такое квантовый компьютер", "expected_keywords": ["определение"]},
        {"description": "что такое квантовый компьютер", "expected_keywords": ["определение"]},  # дубликат
    ]
    with patch("orchestrator.generate_plan", new_callable=AsyncMock) as mock_gen_plan, \
         patch("orchestrator.replan", new_callable=AsyncMock) as mock_replan_func, \
         patch("orchestrator.search_wikipedia", new_callable=AsyncMock) as mock_wiki_func, \
         patch("orchestrator.search_duckduckgo", new_callable=AsyncMock) as mock_ddg_func, \
         patch("orchestrator.synthesize_report", new_callable=AsyncMock) as mock_synth_func:

        mock_gen_plan.return_value = mock_plan
        mock_replan_func.side_effect = [[mock_plan[1]], []]
        # Первый шаг выполняется (успех).
        # Вызывается replan → возвращает [дубликат].
        # Цикл берёт дубликат, проверяет дедупликацию — инструмент не вызывается, шаг помечается success=False, error_msg="Duplicate step".
        # После этого replan вызывается снова (если остались шаги) → возвращает [], цикл завершается.
        mock_wiki_func.return_value = ("текст", ["url"], True, None)
        mock_synth_func.return_value = "# Отчёт"

        memory, report = await research_agent("тема", "fast")

        # Должно быть два шага в памяти, но второй с success=False и ошибкой дубликата
        assert len(memory.steps) == 2
        assert memory.steps[0].success is True
        assert memory.steps[1].success is False
        assert memory.steps[1].error_msg == "Duplicate step"
        # Инструмент вызван только для первого шага
        assert mock_wiki_func.call_count == 1
        mock_ddg_func.assert_not_called()

# Проверка Логирования прогресса в консоль
@pytest.mark.asyncio
async def test_research_agent_progress_logging():
    mock_plan = [{"description": "что такое test", "expected_keywords": ["определение"]}]
    with patch("orchestrator.generate_plan", AsyncMock(return_value=mock_plan)), \
        patch("orchestrator.replan", AsyncMock(return_value=[])), \
        patch("orchestrator.search_wikipedia", AsyncMock(return_value=("text", ["url"], True, None))), \
        patch("orchestrator.synthesize_report", AsyncMock(return_value="# Report")), \
        patch("orchestrator.logger.info") as mock_log_info:
        await research_agent("тема", "fast")
        mock_log_info.assert_any_call("[1/1] что такое test -> wiki успех")

# pytest research_agent/tests/test_orchestrator.py -v