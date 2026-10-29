@echo off
TITLE AI Blood Bank Management System
COLOR 0C
echo ======================================================================
echo           AI BIOMETRIC BLOOD BANK MANAGEMENT SYSTEM
echo       Fingerprint Scanner + XGBoost ML Classifier + Inventory
echo ======================================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python lama helin. Fadlan hubi in Python uu ku rakiban yahay.
    pause
    exit /b
)

echo [1/2] Xaqiijinta xogta iyo moodalka Machine Learning...
python -c "from data.dataset_loader import load_or_generate_datasets; from models.train_models import ml_engine; load_or_generate_datasets(); ml_engine.load_models(); print('[OK] ML Engine Ready!')"

echo.
echo [2/2] Furitaanka Server-ka Blood Bank...
echo Web Dashboard: http://127.0.0.1:8501
echo.
python app.py

pause
