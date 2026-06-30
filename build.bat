@echo off
setlocal
echo === Building BinMind.exe ===
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 ( echo. & echo [!] pip install failed & exit /b 1 )
pyinstaller --noconfirm --clean BinMind.spec
if errorlevel 1 ( echo. & echo [!] PyInstaller failed & exit /b 1 )
echo.
echo === Done. Your app: dist\BinMind.exe ===
endlocal
