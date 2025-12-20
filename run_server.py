#!/usr/bin/env python
"""
Скрипт для запуска сервера устного собеседования
"""
import uvicorn
import os
from dotenv import load_dotenv

# Загружаем переменные окружения (пробуем разные пути)
# ВАЖНО: Используем override=True и правильный порядок
# backend/conf.env имеет наивысший приоритет
load_dotenv("backend/conf.env", override=True)  # Самый приоритетный
load_dotenv("conf.env", override=True)  # Второй приоритет
load_dotenv(".env", override=True)  # Третий приоритет
load_dotenv(override=True)  # Стандартный .env в корне

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))
    
    print(f"🚀 Запуск сервера на http://{host}:{port}")
    print(f"📝 Откройте браузер и перейдите по адресу: http://{host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

