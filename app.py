"""
AI Blood Bank Management System - Server Application
Production-grade Flask server integrating Biometric Scanner,
XGBoost Machine Learning Classifier, and SQLite Blood Bank Database.
"""

import os
import sys
import json
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import HOST, PORT, FINGERPRINTS_DIR, MODELS_DIR
from database.db import (
    init_db,
    get_all_donors,
    get_donor_by_id,
    register_donor,
    get_inventory,
    get_dashboard_stats,
    record_donation,
    add_blood_request,
    get_blood_requests,
    fulfill_blood_request
)
from fingerprint.scanner import processor
from models.train_models import ml_engine

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["UPLOAD_FOLDER"] = str(FINGERPRINTS_DIR)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB max

# Ensure sample fingerprints and models are ready on startup
processor.generate_all_sample_fingerprints()
ml_engine.load_models()

@app.route("/")
def index():
    """Renders the main Blood Bank Management System dashboard."""
    return render_template("index.html")

@app.route("/sample_fingerprints/<filename>")
def serve_fingerprint_image(filename):
    """Serves sample fingerprint images."""
    return send_from_directory(str(FINGERPRINTS_DIR), filename)

@app.route("/api/scan_fingerprint", methods=["POST"])
def api_scan_fingerprint():
    """
    Simulates optical biometric thumb scanning.
    Extracts dermatoglyphic minutiae and runs XGBoost Blood Group classification.
    """
    data = request.get_json() or {}
    bg_key = data.get("blood_group", "O+")

    safe_name = bg_key.replace("+", "_pos").replace("-", "_neg")
    img_filename = f"sample_{safe_name}.png"
    img_path = FINGERPRINTS_DIR / img_filename

    if not img_path.exists():
        processor.generate_synthetic_fingerprint_image(blood_group=bg_key, save_path=img_path)

    # Extract biometric features
    features = processor.extract_features_from_image(img_path)

    # Predict with XGBoost model
    prediction = ml_engine.predict_blood_group_from_features(features)

    return jsonify({
        "success": True,
        "image_url": f"/sample_fingerprints/{img_filename}",
        "features": features,
        "prediction": prediction
    })

@app.route("/api/upload_fingerprint", methods=["POST"])
def api_upload_fingerprint():
    """
    Accepts an uploaded fingerprint image (PNG, JPG, BMP),
    extracts biometric features, and runs the XGBoost Classifier.
    """
    if "file" not in request.files:
        return jsonify({"success": False, "message": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"success": False, "message": "No selected file"}), 400

    filename = secure_filename(f"upload_{file.filename}")
    save_path = FINGERPRINTS_DIR / filename
    file.save(str(save_path))

    # Extract biometric minutiae & patterns
    features = processor.extract_features_from_image(save_path)

    # Predict Blood Group via XGBoost
    prediction = ml_engine.predict_blood_group_from_features(features)

    return jsonify({
        "success": True,
        "image_url": f"/sample_fingerprints/{filename}",
        "features": features,
        "prediction": prediction
    })

@app.route("/api/check_eligibility", methods=["POST"])
def api_check_eligibility():
    """
    Evaluates donor blood donation eligibility using XGBoost model
    and WHO/Red Cross clinical criteria.
    """
    donor_info = request.get_json() or {}
    result = ml_engine.predict_eligibility(donor_info)
    return jsonify(result)

@app.route("/api/register_donor", methods=["POST"])
def api_register_donor():
    """
    Registers a new blood donor into SQLite database.
    Evaluates eligibility and optionally logs initial donation.
    """
    data = request.get_json() or {}
    
    # Run eligibility model
    eligibility_res = ml_engine.predict_eligibility(data)
    data["eligibility_status"] = eligibility_res["eligibility_status"]
    data["eligibility_score"] = eligibility_res["eligibility_score"]
    data["deferral_reason"] = eligibility_res["explanation"]

    # Generate national ID if not given
    if not data.get("national_id"):
        import random
        data["national_id"] = f"SO-{random.randint(100000, 999999)}"

    new_id = register_donor(data)
    return jsonify({
        "success": True,
        "donor_id": new_id,
        "eligibility": eligibility_res
    })

@app.route("/api/donors", methods=["GET"])
def api_get_donors():
    """Fetches all registered donors, with optional search query."""
    search_query = request.args.get("search")
    donors = get_all_donors(search_query)
    return jsonify(donors)

@app.route("/api/inventory", methods=["GET"])
def api_get_inventory():
    """Returns current blood bank inventory stock."""
    inv = get_inventory()
    return jsonify(inv)

@app.route("/api/stats", methods=["GET"])
def api_get_stats():
    """Returns blood bank summary metrics and KPIs."""
    stats = get_dashboard_stats()
    return jsonify(stats)

@app.route("/api/record_donation", methods=["POST"])
def api_record_donation():
    """Records a new donation for an existing registered donor."""
    data = request.get_json() or {}
    donor_id = data.get("donor_id")
    if not donor_id:
        return jsonify({"success": False, "message": "donor_id is required"}), 400

    success, msg = record_donation(donor_id)
    return jsonify({"success": success, "message": msg})

@app.route("/api/blood_requests", methods=["GET", "POST"])
def api_blood_requests():
    """Handles emergency blood transfusion requests."""
    if request.method == "POST":
        data = request.get_json() or {}
        patient_name = data.get("patient_name")
        hospital_name = data.get("hospital_name")
        contact_phone = data.get("contact_phone")
        blood_group = data.get("blood_group")
        units = int(data.get("units_requested", 1))
        urgency = data.get("urgency", "Normal")
        notes = data.get("notes", "")

        add_blood_request(patient_name, hospital_name, contact_phone, blood_group, units, urgency, notes)
        return jsonify({"success": True, "message": "Emergency request logged"})
    else:
        reqs = get_blood_requests()
        return jsonify(reqs)

@app.route("/api/fulfill_request/<int:request_id>", methods=["POST"])
def api_fulfill_request(request_id):
    """Fulfills an emergency blood request and updates inventory."""
    success, msg = fulfill_blood_request(request_id)
    return jsonify({"success": success, "message": msg})

@app.route("/api/ai_metrics", methods=["GET"])
def api_ai_metrics():
    """Returns the XGBoost training evaluation metrics and feature importances."""
    metrics_path = MODELS_DIR / "model_metrics.json"
    if metrics_path.exists():
        with open(metrics_path, "r") as f:
            metrics = json.load(f)
        return jsonify(metrics)
    return jsonify({})

if __name__ == "__main__":
    init_db()
    print(f"\n=======================================================")
    print(f"🩸 AI BLOOD BANK MANAGEMENT SYSTEM - PRODUCTION READY")
    print(f"🔬 Biometric Scanner + XGBoost ML Classifier")
    print(f"🌐 Server running at: http://{HOST}:{PORT}")
    print(f"=======================================================\n")
    app.run(host=HOST, port=PORT, debug=False)
