#!/usr/bin/env python
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from dotenv import load_dotenv

# Загрузка переменных окружения
for env_file in ["backend/conf.env", "conf.env", ".env"]:
    env_path = os.path.join(BASE_DIR, env_file)
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True)

load_dotenv(override=False)

# Настройка прокси из окружения при наличии
proxy = os.getenv("HTTPS_PROXY") or os.getenv("HTTP_PROXY") or os.getenv("https_proxy") or os.getenv("http_proxy")
if proxy:
    os.environ["HTTP_PROXY"] = proxy
    os.environ["HTTPS_PROXY"] = proxy
    os.environ["http_proxy"] = proxy
    os.environ["https_proxy"] = proxy

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    print(f"Запуск сервера на http://{host}:{port}")
    print(f"Откройте браузер и перейдите по адресу: http://{host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

