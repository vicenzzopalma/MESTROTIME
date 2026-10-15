@echo off
setlocal enabledelayedexpansion
title CHRONOS MAESTRO - AUTONOMOUS AI ORCHESTRATOR
color 0B
chcp 65001 >nul

echo ===================================================================
echo             CHRONOS MAESTRO - LOOP AUTONOMO DE IA
echo ===================================================================
echo   Orquestrador Multi-Agente:
echo   - Master Brain: Planejamento continuo (Gemini Flash)
echo   - Engenheiro Core: Execucao de codigo (Codex / GPT-6 Luna)
echo   - Revisor: Inspecao e Quality Gate
echo ===================================================================
echo.

set "MAESTRO_EXE=C:\Users\vicenzzo.palma\AppData\Local\Python\pythoncore-3.14-64\Scripts\maestro.exe"
if not exist "%MAESTRO_EXE%" (
    set "MAESTRO_EXE=maestro"
)

echo Arraste a pasta do seu projeto para esta janela ou digite o caminho.
echo (Pressione ENTER para usar o padrao: D:\MAESTRO TIME)
echo.
set /p "TARGET_REPO=Caminho do Projeto: "

if "%TARGET_REPO%"=="" (
    set "TARGET_REPO=D:\MAESTRO TIME"
)

set "TARGET_REPO=%TARGET_REPO:"=%"

if not exist "%TARGET_REPO%" (
    echo.
    echo [ERRO] A pasta especificada nao existe: "%TARGET_REPO%"
    echo.
    pause
    exit /b 1
)

if not exist "%TARGET_REPO%\.git" (
    echo.
    echo [*] Inicializando repositorio Git no projeto...
    git -C "%TARGET_REPO%" init
)

echo.
echo Qual a duracao do loop de refinamento?
echo Exemplos: 420 (minutos), 90m, 2h, 7h
echo (Pressione ENTER para o padrao: 90m)
set /p "DURATION=Duracao [90m]: "
if "%DURATION%"=="" (
    set "DURATION=90m"
)

echo.
echo ===================================================================
echo   INICIANDO TUI VISUAL DO MAESTRO...
echo   Projeto: %TARGET_REPO%
echo   Tempo:   %DURATION%
echo ===================================================================
echo.

"%MAESTRO_EXE%" run --repo "%TARGET_REPO%" --duration "%DURATION%" --test-cmd "pytest"

echo.
echo Maestro finalizado.
pause
