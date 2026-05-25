#!/usr/bin/env python3
"""
Research Agent CLI - автоматический сбор информации по теме из Wikipedia и DuckDuckGo
"""

import asyncio
import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from orchestrator import research_agent
from logger import logger
from config import DEEPSEEK_API_KEY


async def main():
    parser = argparse.ArgumentParser(
        description="Research Agent - автоматический сбор информации по теме"
    )
    parser.add_argument(
        "topic",
        type=str,
        help="Тема для исследования"
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["fast", "deep"],
        default="deep",
        help="Режим: fast (2-3 шага, короткие таймауты) или deep (5-7 шагов, длинные таймауты)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Путь к файлу для сохранения отчёта (по умолчанию reports/<topic>_<timestamp>.md)"
    )

    args = parser.parse_args()

    # Проверка наличия API ключа
    if not DEEPSEEK_API_KEY:
        logger.error("DEEPSEEK_API_KEY не задан в переменных окружения")
        print("❌ Ошибка: DEEPSEEK_API_KEY не найден. Проверьте файл .env", file=sys.stderr)
        sys.exit(1)

    # Создаём папку reports, если её нет
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    # Генерируем имя файла, если не указано
    if args.output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = "".join(c for c in args.topic if c.isalnum() or c in " _-").replace(" ", "_")
        filename = f"{safe_topic}_{timestamp}.md"
        output_path = reports_dir / filename
    else:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Запуск исследования темы: '{args.topic}', режим: {args.mode}")
    logger.info(f"Отчёт будет сохранён в: {output_path}")

    try:
        memory, report = await research_agent(args.topic, args.mode)
        
        # Записываем отчёт в файл
        output_path.write_text(report, encoding="utf-8")
        
        logger.success(f"Исследование завершено. Отчёт сохранён: {output_path}")
        print(f"\n✅ Отчёт сохранён: {output_path}")
        print(f"📊 Выполнено шагов: {len(memory.steps)}, успешных: {len(memory.get_successful_steps())}")
        
    except TimeoutError as e:
        logger.error(f"Таймаут: {e}")
        print(f"\n❌ Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        logger.warning("Исследование прервано пользователем")
        print("\n⚠️ Прервано пользователем", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Неожиданная ошибка: {e}")
        print(f"\n❌ Неожиданная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())