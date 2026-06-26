@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo.
echo ========================================
echo   Murder Mystery - LLM configuration
echo ========================================
echo.
echo This will write a .env file for Murder Mystery.
echo Point it at any OpenAI-compatible endpoint
echo (Ollama, LM Studio, vLLM, llama.cpp, OpenAI, Groq, OpenRouter...).
echo.

set "DEFAULT_URL=http://localhost:11434/v1"
set "DEFAULT_MODEL=llama3.2"

set /p BASE_URL=Base URL [%DEFAULT_URL%]:
if "!BASE_URL!"=="" set "BASE_URL=%DEFAULT_URL%"

set /p MODEL=Default model [%DEFAULT_MODEL%]:
if "!MODEL!"=="" set "MODEL=%DEFAULT_MODEL%"

set /p API_KEY=API key (press Enter for none):

set /p PER_ROLE=Use a different model per role (writer/detective/suspect)? [y/N]:
if /I "!PER_ROLE!"=="y" (
    set /p WRITER_MODEL=  writer model [!MODEL!]:
    if "!WRITER_MODEL!"=="" set "WRITER_MODEL=!MODEL!"
    set /p DETECTIVE_MODEL=  detective model [!MODEL!]:
    if "!DETECTIVE_MODEL!"=="" set "DETECTIVE_MODEL=!MODEL!"
    set /p SUSPECT_MODEL=  suspect model [!MODEL!]:
    if "!SUSPECT_MODEL!"=="" set "SUSPECT_MODEL=!MODEL!"
) else (
    set "WRITER_MODEL="
    set "DETECTIVE_MODEL="
    set "SUSPECT_MODEL="
)

set /p WEB_PORT=Web UI port [7860]:
if "!WEB_PORT!"=="" set "WEB_PORT=7860"

if exist .env (
    copy /Y .env .env.backup >nul
    echo.
    echo Existing .env backed up to .env.backup
)

(
    echo LLM_PROVIDER=openai
    echo LLM_BASE_URL=!BASE_URL!
    echo LLM_API_KEY=!API_KEY!
    echo DEFAULT_MODEL=!MODEL!
    if not "!WRITER_MODEL!"=="" echo WRITER_MODEL=!WRITER_MODEL!
    if not "!DETECTIVE_MODEL!"=="" echo DETECTIVE_MODEL=!DETECTIVE_MODEL!
    if not "!SUSPECT_MODEL!"=="" echo SUSPECT_MODEL=!SUSPECT_MODEL!
    echo.
    echo WEB_HOST=0.0.0.0
    echo WEB_PORT=!WEB_PORT!
) > .env

echo.
echo Configuration saved to .env:
echo   provider:  openai-compatible
echo   base URL:  !BASE_URL!
echo   model:     !MODEL!
if not "!WRITER_MODEL!"=="" echo   writer:    !WRITER_MODEL!
if not "!DETECTIVE_MODEL!"=="" echo   detective: !DETECTIVE_MODEL!
if not "!SUSPECT_MODEL!"=="" echo   suspect:   !SUSPECT_MODEL!
echo   port:      !WEB_PORT!
echo.
echo Run start.bat to launch Murder Mystery.
echo.
endlocal
