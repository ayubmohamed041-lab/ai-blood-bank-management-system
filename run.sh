#!/usr/bin/env bash
# AI Biometric Blood Bank Management System Launcher

echo "======================================================================"
echo "          AI BIOMETRIC BLOOD BANK MANAGEMENT SYSTEM"
echo "      Fingerprint Scanner + XGBoost ML Classifier + Inventory"
echo "======================================================================"
echo ""

if ! command -v python3 &> /dev/null
then
    echo "[ERROR] Python3 could not be found. Please install Python 3.10+."
    exit 1
fi

echo "[1/2] Verifying Datasets and ML Models..."
python3 -c "from data.dataset_loader import load_or_generate_datasets; from models.train_models import ml_engine; load_or_generate_datasets(); ml_engine.load_models(); print('[OK] ML Engine Ready!')"

echo ""
echo "[2/2] Starting Blood Bank Server..."
echo "Web Dashboard: http://127.0.0.1:8501"
echo ""
python3 app.py
