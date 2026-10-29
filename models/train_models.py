"""
XGBoost Machine Learning Training Engine
Trains and serializes:
1. Fingerprint Biometric -> Blood Group Predictor (XGBoost Multi-Class Classifier)
2. Clinical Donor Metrics -> Blood Donation Eligibility Predictor (XGBoost Binary Classifier)
"""

import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
from sklearn.preprocessing import LabelEncoder

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import MODELS_DIR, BLOOD_GROUPS, XGB_PARAMS
from data.dataset_loader import load_or_generate_datasets

# Try importing XGBoost; fall back to GradientBoostingClassifier if wheel is pending
try:
    import xgboost as xgb
    HAS_XGBOOST = True
    print("[AI Engine] Native XGBoost library detected.")
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier
    HAS_XGBOOST = False
    print("[AI Engine] Using Scikit-Learn Gradient Boosting as high-compatibility engine.")

BLOOD_GROUP_MODEL_PATH = MODELS_DIR / "blood_group_xgb.joblib"
BLOOD_GROUP_ENCODER_PATH = MODELS_DIR / "blood_group_encoder.joblib"
ELIGIBILITY_MODEL_PATH = MODELS_DIR / "donor_eligibility_xgb.joblib"
METRICS_REPORT_PATH = MODELS_DIR / "model_metrics.json"

class BloodBankMLEngine:
    def __init__(self):
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        self.blood_group_model = None
        self.bg_encoder = None
        self.eligibility_model = None
        self.metrics = {}

    def train_blood_group_model(self, df_fingerprint):
        """
        Trains XGBoost classifier to predict Blood Group from fingerprint dermatoglyphics.
        """
        feature_cols = [
            "pattern_code",
            "total_ridge_count",
            "ridge_density",
            "minutiae_endings",
            "minutiae_bifurcations",
            "total_minutiae",
            "pattern_intensity_index",
            "orientation_entropy",
            "core_delta_distance"
        ]
        X = df_fingerprint[feature_cols]
        y_raw = df_fingerprint["blood_group"]

        self.bg_encoder = LabelEncoder()
        y = self.bg_encoder.fit_transform(y_raw)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        if HAS_XGBOOST:
            model = xgb.XGBClassifier(
                n_estimators=160,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                eval_metric="mlogloss"
            )
        else:
            model = GradientBoostingClassifier(
                n_estimators=160,
                max_depth=5,
                learning_rate=0.08,
                subsample=0.85,
                random_state=42
            )

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)

        acc = float(accuracy_score(y_test, y_pred))
        report = classification_report(y_test, y_pred, target_names=self.bg_encoder.classes_, output_dict=True)
        conf_mat = confusion_matrix(y_test, y_pred).tolist()

        # Feature importances
        importances = {feat: round(float(imp), 4) for feat, imp in zip(feature_cols, model.feature_importances_)}

        self.blood_group_model = model
        joblib.dump(model, BLOOD_GROUP_MODEL_PATH)
        joblib.dump(self.bg_encoder, BLOOD_GROUP_ENCODER_PATH)

        self.metrics["blood_group_model"] = {
            "algorithm": "XGBoost Classifier" if HAS_XGBOOST else "Gradient Boosting (XGBoost-equivalent)",
            "accuracy": round(acc, 4),
            "feature_importance": importances,
            "classes": list(self.bg_encoder.classes_),
            "confusion_matrix": conf_mat,
            "classification_report": report
        }
        print(f"[XGBoost Blood Group Model] Accuracy: {acc * 100:.2f}%")
        return model, acc

    def train_eligibility_model(self, df_transfusion):
        """
        Trains XGBoost classifier to predict Blood Donation Eligibility from clinical metrics.
        """
        # Encode gender
        df = df_transfusion.copy()
        df["gender_code"] = df["gender"].map({"Male": 1, "Female": 0})

        feature_cols = [
            "age",
            "gender_code",
            "weight_kg",
            "hemoglobin",
            "systolic_bp",
            "diastolic_bp",
            "recency_months",
            "frequency_donations",
            "monetary_volume_cc",
            "medical_flag"
        ]
        X = df[feature_cols]
        y = df["eligible"]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )

        if HAS_XGBOOST:
            model = xgb.XGBClassifier(
                n_estimators=180,
                max_depth=4,
                learning_rate=0.06,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                eval_metric="logloss"
            )
        else:
            model = GradientBoostingClassifier(
                n_estimators=180,
                max_depth=4,
                learning_rate=0.06,
                subsample=0.85,
                random_state=42
            )

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]

        acc = float(accuracy_score(y_test, y_pred))
        roc_auc = float(roc_auc_score(y_test, y_proba))
        report = classification_report(y_test, y_pred, target_names=["Ineligible", "Eligible"], output_dict=True)
        conf_mat = confusion_matrix(y_test, y_pred).tolist()

        importances = {feat: round(float(imp), 4) for feat, imp in zip(feature_cols, model.feature_importances_)}

        self.eligibility_model = model
        joblib.dump(model, ELIGIBILITY_MODEL_PATH)

        self.metrics["eligibility_model"] = {
            "algorithm": "XGBoost Classifier" if HAS_XGBOOST else "Gradient Boosting (XGBoost-equivalent)",
            "accuracy": round(acc, 4),
            "roc_auc": round(roc_auc, 4),
            "feature_importance": importances,
            "confusion_matrix": conf_mat,
            "classification_report": report
        }
        print(f"[XGBoost Eligibility Model] Accuracy: {acc * 100:.2f}%, ROC-AUC: {roc_auc * 100:.2f}%")
        return model, acc

    def train_all(self):
        """Loads Kaggle/UCI datasets and trains both XGBoost models."""
        t_df, f_df = load_or_generate_datasets()
        print("\n--> Training Blood Group Dermatoglyphic XGBoost Model...")
        self.train_blood_group_model(f_df)
        print("\n--> Training Blood Donation Eligibility XGBoost Model...")
        self.train_eligibility_model(t_df)

        with open(METRICS_REPORT_PATH, "w") as f:
            json.dump(self.metrics, f, indent=4)
        print(f"\n[OK] Models and metrics saved successfully in {MODELS_DIR}")

    def load_models(self):
        """Loads serialized models from disk."""
        if BLOOD_GROUP_MODEL_PATH.exists() and BLOOD_GROUP_ENCODER_PATH.exists():
            self.blood_group_model = joblib.load(BLOOD_GROUP_MODEL_PATH)
            self.bg_encoder = joblib.load(BLOOD_GROUP_ENCODER_PATH)

        if ELIGIBILITY_MODEL_PATH.exists():
            self.eligibility_model = joblib.load(ELIGIBILITY_MODEL_PATH)

        if METRICS_REPORT_PATH.exists():
            with open(METRICS_REPORT_PATH, "r") as f:
                self.metrics = json.load(f)

        return self.blood_group_model is not None and self.eligibility_model is not None

    def predict_blood_group_from_features(self, feat_dict):
        """Predicts blood group and confidence probability distribution from extracted features."""
        if not self.blood_group_model:
            self.load_models()

        cols = [
            "pattern_code",
            "total_ridge_count",
            "ridge_density",
            "minutiae_endings",
            "minutiae_bifurcations",
            "total_minutiae",
            "pattern_intensity_index",
            "orientation_entropy",
            "core_delta_distance"
        ]
        row = [
            feat_dict["pattern_code"],
            feat_dict["total_ridge_count"],
            feat_dict["ridge_density"],
            feat_dict["minutiae_endings"],
            feat_dict["minutiae_bifurcations"],
            feat_dict["total_minutiae"],
            feat_dict["pattern_intensity_index"],
            feat_dict["orientation_entropy"],
            feat_dict["core_delta_distance"]
        ]
        X = pd.DataFrame([row], columns=cols)
        pred_idx = self.blood_group_model.predict(X)[0]
        probas = self.blood_group_model.predict_proba(X)[0]

        predicted_group = self.bg_encoder.inverse_transform([pred_idx])[0]
        confidence = float(probas[pred_idx])

        # Full probability breakdown for all blood groups
        breakdown = {cls: round(float(p), 4) for cls, p in zip(self.bg_encoder.classes_, probas)}

        return {
            "predicted_blood_group": predicted_group,
            "confidence_score": round(confidence, 4),
            "confidence_percent": round(confidence * 100, 1),
            "class_probabilities": breakdown
        }

    def predict_eligibility(self, donor_info):
        """Predicts whether the donor can donate blood right now."""
        if not self.eligibility_model:
            self.load_models()

        gender_code = 1 if donor_info.get("gender") == "Male" else 0
        age = int(donor_info.get("age", 25))
        weight = float(donor_info.get("weight_kg", 60.0))
        hb = float(donor_info.get("hemoglobin", 14.0))
        sbp = int(donor_info.get("systolic_bp", 120))
        dbp = int(donor_info.get("diastolic_bp", 80))
        recency = int(donor_info.get("recency_months", 12))
        freq = int(donor_info.get("frequency_donations", 1))
        monetary = freq * 250
        med_flag = int(donor_info.get("medical_flag", 0))

        cols = [
            "age",
            "gender_code",
            "weight_kg",
            "hemoglobin",
            "systolic_bp",
            "diastolic_bp",
            "recency_months",
            "frequency_donations",
            "monetary_volume_cc",
            "medical_flag"
        ]
        row = [age, gender_code, weight, hb, sbp, dbp, recency, freq, monetary, med_flag]
        X = pd.DataFrame([row], columns=cols)

        pred = int(self.eligibility_model.predict(X)[0])
        probas = self.eligibility_model.predict_proba(X)[0]
        elig_score = float(probas[1])

        # Clinical explainability check
        reasons = []
        if age < 18:
            reasons.append("Da'da oo ka yar 18 sano (Age under 18 years)")
        elif age > 65:
            reasons.append("Da'da oo ka weyn 65 sano (Age over 65 years)")

        if weight < 50.0:
            reasons.append(f"Miisaanka oo ka yar 50kg ({weight}kg)")

        min_hb = 12.5 if donor_info.get("gender") == "Female" else 13.0
        if hb < min_hb:
            reasons.append(f"Heerka dhiigga/Hemoglobin oo hooseeya ({hb} g/dL, heerka ugu yar waa {min_hb} g/dL)")

        if sbp < 90 or sbp > 160 or dbp < 60 or dbp > 100:
            reasons.append(f"Dhiig-karka oo aan caadi ahayn ({sbp}/{dbp} mmHg)")

        if recency < 3:
            reasons.append(f"Waxaa dhiig lagaa shubay {recency} bilood kahor (Ugu yaraan 3 bilood sug)")

        if med_flag == 1:
            reasons.append("Xaalad caafimaad ama dawooyin gaar ah")

        status = "Eligible" if (pred == 1 and len(reasons) == 0) else "Ineligible"
        status_somali = "HAA, Dhiig wuu shubi karaa" if status == "Eligible" else "MAYA, Dhiig ma shubi karo"

        deferral_text = "Qofku wuu caafimaad qabaa, dhiig shubistu waa badbaado." if status == "Eligible" else "; ".join(reasons)

        return {
            "eligibility_status": status,
            "eligibility_somali": status_somali,
            "eligibility_score": round(elig_score, 4),
            "eligibility_percent": round(elig_score * 100, 1),
            "can_donate": (status == "Eligible"),
            "deferral_reasons": reasons,
            "explanation": deferral_text
        }

ml_engine = BloodBankMLEngine()

if __name__ == "__main__":
    ml_engine.train_all()
