@echo off
setlocal enabledelayedexpansion

rem Переход в папку проекта (где лежит этот .bat)
cd /d "%~dp0"

echo ======================================================
echo  Установка Python 3.11+, venv и запуск сервера
echo ======================================================

rem Проверяем, что есть requirements.txt
if not exist "requirements.txt" (
    echo [ОШИБКА] Файл requirements.txt не найден в текущей папке.
    pause
    exit /b 1
)

rem --- Поиск/установка локального интерпретатора Python (python_portable) ---
set "PYTHON_EXE="
set "PY_VER=3.12.2"
set "INSTALL_DIR=%CD%\python_portable"
set "PY_ZIP=python-%PY_VER%-embed-amd64.zip"

if exist "%INSTALL_DIR%\python.exe" (
    set "PYTHON_EXE=%INSTALL_DIR%\python.exe"
)

if not defined PYTHON_EXE (
    echo Скачивание портативного Python %PY_VER% ...
    curl -L "https://www.python.org/ftp/python/%PY_VER%/%PY_ZIP%" -o "%PY_ZIP%"

    if not exist "%PY_ZIP%" (
        echo [ОШИБКА] Не удалось скачать архив Python.
        pause
        exit /b 1
    )

    echo Распаковка Python в "%INSTALL_DIR%" ...
    if not exist "%INSTALL_DIR%" (
        mkdir "%INSTALL_DIR%"
    )

    powershell -NoLogo -NoProfile -Command "Expand-Archive -Force '%PY_ZIP%' '%INSTALL_DIR%'" 

    del "%PY_ZIP%"

    if exist "%INSTALL_DIR%\python.exe" (
        set "PYTHON_EXE=%INSTALL_DIR%\python.exe"
    ) else (
        echo [ОШИБКА] Не удалось распаковать портативный Python.
        pause
        exit /b 1
    )
)

if not defined PYTHON_EXE (
    echo [ОШИБКА] Подходящий интерпретатор Python не найден.
    pause
    exit /b 1
)

"%PYTHON_EXE%" --version
echo [OK] Используем интерпретатор: %PYTHON_EXE%

rem --- Обеспечиваем наличие pip в локальном python_portable ---
"%PYTHON_EXE%" -m pip --version >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ИНФО] pip не найден, выполняю установку...

    rem Если есть файл python312._pth, включаем import site для поддержки пакетов
    if exist "%INSTALL_DIR%\python312._pth" (
        powershell -NoLogo -NoProfile -Command ^
          "(Get-Content '%INSTALL_DIR%\python312._pth') -replace '#import site','import site' | Set-Content '%INSTALL_DIR%\python312._pth'"
    )

    echo Скачивание get-pip.py ...
    curl -L "https://bootstrap.pypa.io/get-pip.py" -o "%INSTALL_DIR%\get-pip.py"

    if not exist "%INSTALL_DIR%\get-pip.py" (
        echo [ОШИБКА] Не удалось скачать get-pip.py.
        pause
        exit /b 1
    )

    "%PYTHON_EXE%" "%INSTALL_DIR%\get-pip.py"

    rem Перепроверяем, что pip действительно появился
    "%PYTHON_EXE%" -m pip --version >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [ОШИБКА] Не удалось установить pip.
        pause
        exit /b 1
    )
)

echo Установка/обновление зависимостей из requirements.txt...
"%PYTHON_EXE%" -m pip install --upgrade pip
"%PYTHON_EXE%" -m pip install -r requirements.txt

echo Запуск сервера через run_server.py ...
"%PYTHON_EXE%" run_server.py

pause