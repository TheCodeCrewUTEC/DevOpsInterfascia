@echo off
setlocal

echo ==========================================
echo SCRAPING COMPLETO - INTERFASCIA
echo ==========================================

REM En el servidor: set PYTHON=C:\ruta\al\venv\Scripts\python.exe
REM y despues ejecutar este bat. Si PYTHON no esta definida, usa "python" del PATH.
if not defined PYTHON set "PYTHON=python"

"%PYTHON%" -c "import sys; print(sys.executable)"
if errorlevel 1 (
    echo ERROR: No se pudo ejecutar Python:
    echo %PYTHON%
    goto error
)

REM Los spiders de convocatorias leen y escriben JSON en esta carpeta.
cd /d "%~dp0Convocatorias" || goto error

echo.
echo [1/12] FondoInversor...
"%PYTHON%" -m scrapy runspider fondosspyder.py -O FondosInversores.json
if errorlevel 1 goto error

echo.
echo [2/12] SpiderPDF...
"%PYTHON%" -m scrapy runspider SpiderPDF.py -O FondosConDocumentos.json
if errorlevel 1 goto error

echo.
echo [3/12] SpiderDocumentos...
"%PYTHON%" -m scrapy runspider SpiderDocumentos.py -O Fondos.json
if errorlevel 1 goto error

echo.
echo [4/12] embedding.py...
"%PYTHON%" -u "%~dp0..\procesamiento\embedding.py"
if errorlevel 1 goto error

echo.
echo [5/12] extraer_convocatorias.py...
"%PYTHON%" -u "%~dp0..\procesamiento\extraer_convocatorias.py"
if errorlevel 1 goto error

echo.
echo [6/12] completar_convocatorias.py...
"%PYTHON%" -u "%~dp0..\procesamiento\completar_convocatorias.py"
if errorlevel 1 goto error

echo.
echo [7/12] CVUy...
cd /d "%~dp0Investigadores" || goto error
"%PYTHON%" -m scrapy runspider cvuyspider.py -O Investigadores.json
if errorlevel 1 goto error

REM Backend en el PYTHONPATH para el pipeline de proyectos.
cd /d "%~dp0..\..\.." || goto error
set "PYTHONPATH=%CD%"

echo.
echo [8/12] cargar_investigadores.py...
"%PYTHON%" -u worker\scraping\procesamiento\cargar_investigadores.py
if errorlevel 1 goto error

echo.
echo [9/12] cargar_proyectos.py...
"%PYTHON%" -u worker\scraping\procesamiento\cargar_proyectos.py
if errorlevel 1 goto error

echo.
echo [10/12] cargar_fuentes.py...
"%PYTHON%" -u worker\scraping\procesamiento\cargar_fuentes.py
if errorlevel 1 goto error

echo.
echo [11/12] portal_ande.py...
echo Hace falta ANDE_EMAIL y ANDE_PASSWORD en Backend\.env, y Playwright instalado.
"%PYTHON%" -u worker\scraping\portal_ande.py
if errorlevel 1 goto error

echo.
echo [12/12] cargar_formularios.py...
"%PYTHON%" -u worker\scraping\procesamiento\cargar_formularios.py
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
