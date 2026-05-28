import asyncio
import time
from typing import List, Dict, Any, Optional, Tuple
from memory import Memory, Step
from planner import generate_plan, replan
from executor import select_tool_by_keywords
from research_agent.tools.wiki_tool import search_wikipedia
from research_agent.tools.duckduckgo_tool import search_duckduckgo
from config import MODES, MAX_GLOBAL_STEPS, TIMEOUT_BUFFER_SEC
from logger import logger
from synthesizer import synthesize_report


def get_remaining_time(start_time: float, timeout_limit: int) -> float:
    """Вычисляет оставшееся время с запасом TIMEOUT_BUFFER_SEC (10 сек)."""
    elapsed = time.time() - start_time
    remaining = timeout_limit - elapsed - TIMEOUT_BUFFER_SEC
    return max(remaining, 0.0)


async def execute_step(step_dict: Dict[str, Any], step_id: int, memory: Memory) -> Step:
    """Выполняет один шаг: выбирает инструмент, вызывает его, возвращает Step."""
    description = step_dict["description"]
    expected_keywords = step_dict.get("expected_keywords", [])
    tool = select_tool_by_keywords(description, expected_keywords)
    def to_wiki_title(desc: str, keywords: List[str]) -> str:
        # Стоп-слова для очистки (можно вынести в конфиг)
        stop_words = {"найти","искать","определение","список","история","термин","факты","описание","в","на","по","для","с","к","у","о","об","и","а","но","или","который","новости","обзор","пример"}
        if keywords:
            # Берём первые 2 ключевых слова как основу названия
            title = ' '.join(keywords[:2]).capitalize()
            # Если получилось слишком коротко (меньше 2 букв) - берём из описания
            if len(title) < 3:
                words = desc.split()
                important = [w for w in words if w.lower() not in stop_words]
                title = ' '.join(important[:2]).capitalize()
        else:
            words = desc.split()
            important = [w for w in words if w.lower() not in stop_words]
            title = ' '.join(important[:2]).capitalize()
        return title.strip()

    # Формируем query в зависимости от инструмента
    if tool == "wiki":
        # Для Wikipedia используем специальную функцию
        query = to_wiki_title(description, expected_keywords)
        # Ещё раз обрезаем до 200 символов на всякий случай
        query = query[:200].strip()
        if not query:
            query = description[:50]
    else:
        # Для web оставляем старый алгоритм (ключевые слова или описание)
        if expected_keywords:
            query = ' '.join(expected_keywords[:4])
        else:
            words = description.split()
            stop_words = {"найти","искать","определение","список","история","термин","факты","описание","в","на","по","для","с","к","у","о","об","и","а","но","или","который"}
            important = [w for w in words if w.lower() not in stop_words]
            query = ' '.join(important[:4]) if important else ' '.join(words[:4])
        query = query[:200].strip()
        if not query:
            query = description[:50]
    # ------------------------------------------------------------------

    normalized_query = memory.normalize_query(query)

    # Дедупликация
    if memory.is_duplicate(normalized_query):
        logger.warning(f"Шаг {step_id}: дубликат запроса '{query}', пропускаем")
        return Step(
            step_id=step_id,
            description=description,
            expected_keywords=expected_keywords,
            query=query,
            normalized_query=normalized_query,
            tool=None,
            result_text="",
            urls=[],
            success=False,
            error_msg="Duplicate step",
            retry_count=0,
            start_time=time.time(),
            end_time=time.time()
        )

    # Выбор инструмента
    logger.info(f"Шаг {step_id}: '{description}' -> инструмент {tool}, запрос '{query}'")

    start = time.time()
    retry_count = 0
    text, urls, success, error = "", [], False, None

    if tool == "wiki":
        # Для wiki одна попытка (WIKI_RETRIES=1)
        text, urls, success, error = await search_wikipedia(query)
        if not success:
            logger.warning(f"Шаг {step_id}: Wiki не удался ('{query}'), пробуем web fallback")
            text, urls, success, error = await search_duckduckgo(query)
            if success:
                tool = "web (fallback)"
                retry_count = 0  # duckduckgo сам делает ретраи
            else:
                # Если и web не помог – оставляем ошибку, но tool оставляем "wiki"
                retry_count = 1
        else:
            retry_count = 0
    else:  # web
        text, urls, success, error = await search_duckduckgo(query)
        retry_count = 0  # внутренние ретраи не отслеживаем
    # ------------------------------------------------------------------

    end = time.time()
    step = Step(
        step_id=step_id,
        description=description,
        expected_keywords=expected_keywords,
        query=query,
        normalized_query=normalized_query,
        tool=tool,
        result_text=text,
        urls=urls,
        success=success,
        error_msg=error,
        retry_count=retry_count,
        start_time=start,
        end_time=end
    )
    return step


async def research_agent(topic: str, mode: str) -> Tuple[Memory, str]:
    """
    Главный orchestrator: планирование, выполнение, replan, синтез отчёта.
    Возвращает (Memory, report_text).
    """
    logger.info(f"Запуск research_agent с темой '{topic}', режим {mode}")
    start_time = time.time()
    mode_config = MODES[mode]
    global_timeout = mode_config["global_timeout"]

    memory = Memory()
    remaining_time = get_remaining_time(start_time, global_timeout)
    if remaining_time <= 0:
        raise TimeoutError("Недостаточно времени для запуска исследования")

    # Начальный план
    plan = await generate_plan(topic, mode, remaining_time=remaining_time)
    if not plan:
        logger.error("Не удалось сгенерировать план")
        plan = [{"description": f"Поиск информации о {topic}", "expected_keywords": []}]

    # Преобразуем план в список словарей (оставшиеся шаги)
    remaining_steps = plan  # list of dicts
    step_counter = 0

    # Цикл выполнения
    while remaining_steps and step_counter < MAX_GLOBAL_STEPS:
        # Проверка глобального таймаута
        remaining_time = get_remaining_time(start_time, global_timeout)
        if remaining_time <= 0:
            logger.warning("Глобальный таймаут, прерывание цикла")
            break

        # Берём следующий шаг из плана
        step_dict = remaining_steps.pop(0)
        step = await execute_step(step_dict, step_counter, memory)
        memory.add_step(step)
        # логирование прогресса в консоль
        logger.info(f"[{step_counter + 1}/{len(memory.steps) + len(remaining_steps)}] {step.description} -> {step.tool} {'успех' if step.success else 'ошибка'}")
        step_counter += 1
        logger.info(f"Шаг {step.step_id} завершён: успех={step.success}")

        # Если после этого шага остались ещё шаги в плане, вызываем replan
        if remaining_steps:
            # Вычисляем оставшееся время для replan
            replan_remaining = get_remaining_time(start_time, global_timeout)
            new_remaining = await replan(
                remaining_steps=remaining_steps,
                last_step=step,
                all_steps=memory.steps,
                mode=mode,
                remaining_time=replan_remaining
            )
            # Обрезаем до MAX_GLOBAL_STEPS
            total_done = len(memory.steps)
            max_allowed_remaining = MAX_GLOBAL_STEPS - total_done
            if max_allowed_remaining <= 0:
                logger.warning("Достигнут лимит шагов, прерывание")
                remaining_steps = []
                break
            if len(new_remaining) > max_allowed_remaining:
                new_remaining = new_remaining[:max_allowed_remaining]
                logger.info(f"Обрезан план после replan: {len(new_remaining)} шагов из {len(remaining_steps)}")
            remaining_steps = new_remaining
            logger.info(f"Replan выполнен, осталось {len(remaining_steps)} шагов")
        else:
            logger.info("План выполнен полностью")

    # После цикла определяем, был ли план выполнен частично
    partial = len(remaining_steps) > 0 or step_counter >= MAX_GLOBAL_STEPS
    if partial:
        logger.warning(f"Исследование завершено частично. Невыполненных шагов: {len(remaining_steps)}")

    # Генерация отчёта
    report_remaining = get_remaining_time(start_time, global_timeout)
    if report_remaining <= 0:
        logger.warning("Недостаточно времени для генерации отчёта, возвращаем заглушку")
        report = f"# Отчёт по теме: {topic}\n\n> **Примечание:** Время истекло, отчёт не сгенерирован."
    else:
        try:
            report = await synthesize_report(topic, memory, partial, mode, remaining_time=report_remaining)
        except NotImplementedError:
            logger.warning("synthesize_report не реализован, используется заглушка")
            report = f"# Отчёт по теме: {topic}\n\n> **Примечание:** Синтезатор отчёта ещё не реализован.\n\n## Выполненные шаги\n" + "\n".join(f"- {s.description}: {'успех' if s.success else 'ошибка'}" for s in memory.steps)
        except Exception as e:
            logger.error(f"Ошибка при синтезе отчёта: {e}")
            report = f"# Отчёт по теме: {topic}\n\nОшибка генерации отчёта: {e}"

    logger.info(f"Исследование завершено. Выполнено шагов: {len(memory.steps)}, отчёт длиной {len(report)} символов")
    return memory, report

