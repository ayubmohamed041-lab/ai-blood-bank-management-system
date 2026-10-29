"""
Comprehensive Unit and Integration Tests for Blood Bank Management System
Tests:
- Database Schema & Transactions
- Biometric Fingerprint Feature Extraction
- XGBoost ML Inference Engine (Blood Group & Eligibility)
- REST API Endpoints
"""

import unittest
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from database.db import get_connection, init_db, get_dashboard_stats, get_inventory
from fingerprint.scanner import processor
from models.train_models import ml_engine

class TestBloodBankSystem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_db()
        ml_engine.load_models()
        cls.client = app.test_client()

    def test_database_inventory_and_stats(self):
        """Verify database returns valid inventory and donor metrics."""
        stats = get_dashboard_stats()
        self.assertIn("total_donors", stats)
        self.assertIn("total_units", stats)
        self.assertGreater(stats["total_units"], 0)

        inv = get_inventory()
        self.assertEqual(len(inv), 8, "Expected all 8 blood groups in inventory")

    def test_fingerprint_biometric_feature_extraction(self):
        """Verify fingerprint scanner extracts minutiae and patterns correctly."""
        samples = processor.generate_all_sample_fingerprints()
        self.assertIn("O+", samples)

        features = processor.extract_features_from_image(samples["O+"])
        self.assertIn("pattern_name", features)
        self.assertIn("total_ridge_count", features)
        self.assertIn("minutiae_endings", features)
        self.assertIn("ridge_density", features)
        self.assertGreater(features["total_ridge_count"], 50)
        self.assertGreater(features["total_minutiae"], 10)

    def test_ml_blood_group_prediction(self):
        """Verify ML engine classifies blood group and returns probability distribution."""
        sample_features = {
            "pattern_code": 1,
            "total_ridge_count": 140,
            "ridge_density": 13.5,
            "minutiae_endings": 32,
            "minutiae_bifurcations": 22,
            "total_minutiae": 54,
            "pattern_intensity_index": 1,
            "orientation_entropy": 0.62,
            "core_delta_distance": 70.0
        }
        res = ml_engine.predict_blood_group_from_features(sample_features)
        self.assertIn("predicted_blood_group", res)
        self.assertIn("confidence_score", res)
        self.assertIn("class_probabilities", res)
        self.assertEqual(len(res["class_probabilities"]), 8)

    def test_ml_donor_eligibility_engine(self):
        """Verify XGBoost eligibility engine accurately approves healthy donor and flags deferred donor."""
        # 1. Healthy eligible donor
        eligible_donor = {
            "gender": "Male",
            "age": 28,
            "weight_kg": 72.0,
            "hemoglobin": 14.5,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "recency_months": 6,
            "frequency_donations": 2,
            "medical_flag": 0
        }
        res_elig = ml_engine.predict_eligibility(eligible_donor)
        self.assertEqual(res_elig["eligibility_status"], "Eligible")
        self.assertTrue(res_elig["can_donate"])

        # 2. Ineligible donor (underweight & low hemoglobin)
        ineligible_donor = {
            "gender": "Female",
            "age": 22,
            "weight_kg": 44.0,  # Below 50kg limit
            "hemoglobin": 10.5, # Below 12.5 g/dL
            "systolic_bp": 115,
            "diastolic_bp": 75,
            "recency_months": 12,
            "frequency_donations": 0,
            "medical_flag": 0
        }
        res_inelig = ml_engine.predict_eligibility(ineligible_donor)
        self.assertEqual(res_inelig["eligibility_status"], "Ineligible")
        self.assertFalse(res_inelig["can_donate"])
        self.assertGreater(len(res_inelig["deferral_reasons"]), 0)

    def test_api_scan_fingerprint_endpoint(self):
        """Verify /api/scan_fingerprint returns 200 with extracted minutiae and prediction."""
        response = self.client.post("/api/scan_fingerprint", json={"blood_group": "A+"})
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("prediction", data)
        self.assertIn("features", data)

    def test_api_register_donor_endpoint(self):
        """Verify registering a donor persists and updates inventory."""
        new_donor_payload = {
            "full_name": "Test Caafi Jaamac",
            "country": "Somalia",
            "phone": "+252 61 999 0000",
            "email": "caafi@example.com",
            "blood_group": "B+",
            "gender": "Male",
            "age": 30,
            "weight_kg": 75.0,
            "hemoglobin": 15.0,
            "systolic_bp": 120,
            "diastolic_bp": 80,
            "recency_months": 8,
            "record_donation_now": True
        }
        response = self.client.post("/api/register_donor", json=new_donor_payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("donor_id", data)

if __name__ == "__main__":
    unittest.main()
