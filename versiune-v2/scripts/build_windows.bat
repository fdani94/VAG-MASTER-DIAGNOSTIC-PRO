@echo off
setlocal
cd /d "%~dp0\.."

py -3 -m venv .venv
if errorlevel 1 goto :error

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 goto :error

pip install -r requirements.txt pyinstaller pillow
if errorlevel 1 goto :error

python scripts\build_database.py
if errorlevel 1 goto :error

python scripts\create_icon.py
if errorlevel 1 goto :error

python -m unittest discover -s tests -v
if errorlevel 1 goto :error

pyinstaller --noconfirm --clean --windowed --onedir ^
  --name KID-VAG-MASTER-V2 ^
  --icon assets\kid_vag_v2.ico ^
  --add-data "assets;assets" ^
  main.py
if errorlevel 1 goto :error

echo.
echo BUILD FINALIZAT:
echo dist\KID-VAG-MASTER-V2\KID-VAG-MASTER-V2.exe
pause
exit /b 0

:error
echo.
echo BUILD NEREUSIT. Verifica mesajul de mai sus.
pause
exit /b 1
