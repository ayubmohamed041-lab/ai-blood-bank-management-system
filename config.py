"""
Blood Bank Management System Configuration
AI Engineer: 10+ Years Experience Production Design
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Paths
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"
DATABASE_DIR = BASE_DIR / "database"
STATIC_DIR = BASE_DIR / "static"
FINGERPRINTS_DIR = BASE_DIR / "sample_fingerprints"

DB_PATH = DATABASE_DIR / "blood_bank.db"

# Server Configuration
HOST = "127.0.0.1"
PORT = 8501

# Blood Groups
BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

# Donor Eligibility WHO / Red Cross Clinical Guidelines
ELIGIBILITY_CRITERIA = {
    "min_age": 18,
    "max_age": 65,
    "min_weight_kg": 50.0,
    "min_hemoglobin_female": 12.5,
    "min_hemoglobin_male": 13.0,
    "min_donation_interval_days": 84,  # ~12 weeks (3 months)
    "min_systolic_bp": 90,
    "max_systolic_bp": 160,
    "min_diastolic_bp": 60,
    "max_diastolic_bp": 100,
}

# XGBoost Model Configuration
XGB_PARAMS = {
    "n_estimators": 150,
    "max_depth": 5,
    "learning_rate": 0.08,
    "subsample": 0.85,
    "colsample_bytree": 0.85,
    "random_state": 42,
    "eval_metric": "logloss",
}
