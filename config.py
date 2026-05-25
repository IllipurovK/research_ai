import os
from dotenv import load_dotenv

# Загружаем переменные окружения из .env
load_dotenv()

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "your-key-here")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")

# Режимы работы
MODES = {
    "fast": {
        "min_steps": 2,
        "max_steps": 3,
        "llm_timeout": 10,
        "global_timeout": 60
    },
    "deep": {
        "min_steps": 5,
        "max_steps": 7,
        "llm_timeout": 30,
        "global_timeout": 180
    }
}

# Retry стратегии
LLM_RETRIES = 2
WEB_RETRIES = 3
WEB_BACKOFF = [2, 4, 8]  # seconds
WIKI_RETRIES = 1

# Ограничения на текст результатов
MIN_TEXT_LENGTH = 50
MAX_RESULT_TEXT_LENGTH = 2000

# Глобальные ограничения
MAX_GLOBAL_STEPS = 15
TIMEOUT_BUFFER_SEC = 10  # запас при вычислении таймаутов

# Таймауты отдельных инструментов (секунды)
WIKI_TIMEOUT = 10
WEB_TIMEOUT = 15

# Ключевые слова для выбора Wikipedia (rule-based executor)
WIKI_KEYWORDS = {
    "определение", "что такое", "история", "термин",
    "факты", "список", "описание"
}