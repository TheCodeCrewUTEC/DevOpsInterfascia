@echo off

REM Ir a la carpeta donde está este archivo .bat
cd /d "%~dp0"

echo ==========================================
echo INICIO SCRAPING - %date% %time%
echo ==========================================

echo.
echo [1/5] Ejecutando FondoInversor...
scrapy crawl FondoInversor -o FondosInversores.json

IF ERRORLEVEL 1 (
    echo ERROR en FondoInversor
    exit /b 1
)

echo.
echo [2/5] Ejecutando SpiderPDF...
scrapy crawl SpiderPDF -o FondosConDocumentos.json

IF ERRORLEVEL 1 (
    echo ERROR en SpiderPDF
    exit /b 1
)

echo.
echo [3/5] Ejecutando SpiderDocumentos...
scrapy crawl SpiderDocumentos -o Fondos.json

IF ERRORLEVEL 1 (
    echo ERROR en SpiderDocumentos
    exit /b 1
)

echo.
echo [4/5] Ejecutando embedding.py...
python spiders/embedding.py

IF ERRORLEVEL 1 (
    echo ERROR en embedding.py
    exit /b 1
)

echo.
echo [5/5] Ejecutando extraer_convocatorias.py...
python spiders/extraer_convocatorias.py

IF ERRORLEVEL 1 (
    echo ERROR en extraer_convocatorias.py
    exit /b 1
)

echo.
echo ==========================================
echo SCRAPING FINALIZADO CORRECTAMENTE
echo %date% %time%
echo ==========================================

exit /b 0