import sys
from loguru import logger

# Удаляем стандартный обработчик loguru (чтобы избежать дублирования)
logger.remove()

# Добавляем вывод в консоль с уровнем INFO и форматированием
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# Добавляем вывод в файл с уровнем DEBUG, ротацией 10 MB и хранением 5 бэкапов
logger.add(
    "research_agent.log",
    rotation="10 MB",
    retention=5,
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

# Экспортируем объект logger
__all__ = ["logger"]