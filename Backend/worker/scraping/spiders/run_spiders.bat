@echo off
setlocal

echo ==========================================
echo INICIO SCRAPING - INTERFASCIA
echo ==========================================

REM Ruta al Python del entorno virtual del repositorio
set "PYTHON=%~dp0..\..\..\..\.venv\Scripts\python.exe"

REM Verificar que exista el entorno virtual
if not exist "%PYTHON%" (
    echo ERROR: No se encuentra Python en:
    echo %PYTHON%
    goto error
)

REM Los spiders leen y escriben archivos JSON relativos a esta carpeta
cd /d "%~dp0Convocatorias" || goto error

echo.
echo [1/5] Ejecutando FondoInversor...
"%PYTHON%" -m scrapy runspider fondosspyder.py -O FondosInversores.json
if errorlevel 1 goto error

echo.
echo [2/5] Ejecutando SpiderPDF...
"%PYTHON%" -m scrapy runspider SpiderPDF.py -O FondosConDocumentos.json
if errorlevel 1 goto error

echo.
echo [3/5] Ejecutando SpiderDocumentos...
"%PYTHON%" -m scrapy runspider SpiderDocumentos.py -O Fondos.json
if errorlevel 1 goto error

echo.
echo [4/5] Ejecutando embedding.py...
"%PYTHON%" -u "%~dp0..\procesamiento\embedding.py"
if errorlevel 1 goto error

echo.
echo [5/5] Ejecutando extraer_convocatorias.py...
"%PYTHON%" -u "%~dp0..\procesamiento\extraer_convocatorias.py"
if errorlevel 1 goto error

echo.
echo ==========================================
echo SCRAPING FINALIZADO CORRECTAMENTE
echo ==========================================
pause
exit /b 0

:error
echo.
echo ==========================================
echo ERROR: EL PROCESO SE DETUVO
echo Revisa los mensajes anteriores.
echo ==========================================
pause
exit /b 1