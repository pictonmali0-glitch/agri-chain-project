@echo off
REM AgriChain Backend Setup – Windows
echo.
echo  AgriChain Backend Setup (Windows)
echo ====================================
echo.

REM Create virtual environment
python -m venv venv
echo [OK] Virtual environment created

REM Activate
call venv\Scripts\activate.bat

REM Install
pip install -r requirements.txt
echo [OK] Dependencies installed

REM Create .env
if not exist .env (
  copy .env.example .env
  echo [OK] .env created from template - please edit it!
)

REM Create upload dirs
if not exist uploads\qrcodes mkdir uploads\qrcodes
if not exist uploads\products mkdir uploads\products
if not exist uploads\profiles mkdir uploads\profiles
echo [OK] Upload directories created

echo.
echo  Starting AgriChain...
echo  Admin login: admin@agrichain.app / Admin@123
echo.
python app.py
pause
