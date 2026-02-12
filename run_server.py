#!/usr/bin/env python
import os
import sys

proxy_url = "http://UMSU2N:U0sVm3@45.85.162.40:8000"

os.environ["http_proxy"] = proxy_url
os.environ["https_proxy"] = proxy_url
os.environ["HTTP_PROXY"] = proxy_url
os.environ["HTTPS_PROXY"] = proxy_url

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import uvicorn
from dotenv import load_dotenv

load_dotenv("backend/conf.env", override=True)
load_dotenv("conf.env", override=True)
load_dotenv(".env", override=True)
load_dotenv(override=True)

if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", 8000))

    # region agent log
    try:
        import json, time
        log_entry = {
            "id": f"log_{int(time.time() * 1000)}",
            "timestamp": int(time.time() * 1000),
            "location": "run_server.py:28",
            "message": "server_start_config",
            "data": {"host": host, "port": port},
            "runId": "pre-fix",
            "hypothesisId": "H1",
        }
        log_path = os.path.join(
            BASE_DIR,
            ".cursor",
            "debug.log",
        )
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        pass
    # endregion agent log

    print(f"Запуск сервера на http://{host}:{port}")
    print(f"Откройте браузер и перейдите по адресу: http://{host}:{port}")
    
    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )

