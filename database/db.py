"""
Blood Bank Management Database Module
SQLite Database Manager for Donors, Inventory, Donations, and Requests
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from config import DB_PATH, BLOOD_GROUPS

def get_connection():
    """Returns a SQLite database connection with row factory enabled."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database schema and default inventory."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Donors Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            national_id TEXT UNIQUE,
            full_name TEXT NOT NULL,
            country TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT,
            gender TEXT,
            age INTEGER NOT NULL,
            weight_kg REAL NOT NULL,
            blood_group TEXT NOT NULL,
            hemoglobin REAL,
            systolic_bp INTEGER,
            diastolic_bp INTEGER,
            fingerprint_pattern TEXT,
            fingerprint_ridge_count INTEGER,
            eligibility_status TEXT NOT NULL,
            eligibility_score REAL,
            deferral_reason TEXT,
            last_donation_date TEXT,
            total_donations INTEGER DEFAULT 0,
            registration_date TEXT NOT NULL,
            notes TEXT
        )
    """)

    # 2. Blood Inventory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blood_inventory (
            blood_group TEXT PRIMARY KEY,
            units_available INTEGER DEFAULT 0,
            reserved_units INTEGER DEFAULT 0,
            minimum_threshold INTEGER DEFAULT 10,
            last_updated TEXT NOT NULL
        )
    """)

    # 3. Blood Donations Log Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blood_donations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            donor_id INTEGER NOT NULL,
            donor_name TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units_donated INTEGER DEFAULT 1,
            donation_date TEXT NOT NULL,
            hemoglobin REAL,
            blood_pressure TEXT,
            phlebotomist TEXT,
            notes TEXT,
            FOREIGN KEY (donor_id) REFERENCES donors (id)
        )
    """)

    # 4. Emergency Blood Requests Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS blood_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_name TEXT NOT NULL,
            hospital_name TEXT NOT NULL,
            contact_phone TEXT NOT NULL,
            blood_group TEXT NOT NULL,
            units_requested INTEGER NOT NULL,
            urgency TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            request_date TEXT NOT NULL,
            fulfilled_date TEXT,
            notes TEXT
        )
    """)

    # Populate initial inventory if empty
    cursor.execute("SELECT COUNT(*) FROM blood_inventory")
    if cursor.fetchone()[0] == 0:
        default_stock = {
            "O+": 35,
            "O-": 12,
            "A+": 28,
            "A-": 8,
            "B+": 24,
            "B-": 6,
            "AB+": 15,
            "AB-": 4
        }
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for bg in BLOOD_GROUPS:
            units = default_stock.get(bg, 10)
            cursor.execute("""
                INSERT INTO blood_inventory (blood_group, units_available, reserved_units, minimum_threshold, last_updated)
                VALUES (?, ?, ?, ?, ?)
            """, (bg, units, 0, 10, now_str))

    # Populate sample donors if empty
    cursor.execute("SELECT COUNT(*) FROM donors")
    if cursor.fetchone()[0] == 0:
        sample_donors = [
            ("SO-109283", "Axmed Cali Faarax", "Somalia", "+252 61 555 1234", "axmed.ali@example.com", "Male", 28, 72.5, "O+", 14.8, 120, 80, "Loop", 142, "Eligible", 0.96, "Healthy and ready for donation", "2026-05-10", 3, "2026-10-15", "Frequent donor"),
            ("SO-109284", "Faadumo Maxamed Cumar", "Somalia", "+252 61 777 4321", "faadumo.m@example.com", "Female", 24, 58.0, "A+", 13.2, 115, 75, "Whorl", 168, "Eligible", 0.94, "Healthy and ready for donation", "2026-06-20", 2, "2026-10-18", "Volunteer donor"),
            ("KE-493820", "John Mwangi Gitau", "Kenya", "+254 712 345 678", "j.mwangi@example.com", "Male", 34, 80.0, "B+", 15.1, 125, 82, "Loop", 135, "Eligible", 0.95, "Healthy and ready for donation", "2026-04-12", 5, "2026-10-20", "Golden donor badge"),
            ("SO-109285", "Khadra Xasan Yuusuf", "Somalia", "+252 61 888 9012", "khadra.y@example.com", "Female", 21, 46.5, "AB-", 11.2, 105, 68, "Arch", 98, "Ineligible", 0.12, "Miisaanka oo ka yar 50kg & Hemoglobin hooseysa (<12.5 g/dL)", None, 0, "2026-10-22", "Needs nutrition counseling"),
            ("DJ-993821", "Ibraahim Cismaan Geedi", "Djibouti", "+253 77 123 456", "ibra.geedi@example.com", "Male", 45, 85.0, "A-", 14.5, 130, 85, "Whorl", 175, "Eligible", 0.91, "Healthy and ready for donation", "2026-02-14", 8, "2026-10-24", "Universal plasma provider"),
            ("ET-882910", "Zahra Cabdi Warsame", "Ethiopia", "+251 911 234 567", "zahra.abdi@example.com", "Female", 29, 64.0, "O-", 13.5, 118, 76, "Loop", 140, "Eligible", 0.98, "Universal donor (O-). High priority inventory.", "2026-03-30", 4, "2026-10-25", "Universal Red Cell Donor"),
        ]
        for d in sample_donors:
            cursor.execute("""
                INSERT INTO donors (
                    national_id, full_name, country, phone, email, gender, age, weight_kg, blood_group,
                    hemoglobin, systolic_bp, diastolic_bp, fingerprint_pattern, fingerprint_ridge_count,
                    eligibility_status, eligibility_score, deferral_reason, last_donation_date,
                    total_donations, registration_date, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, d)

    conn.commit()
    conn.close()

def get_all_donors(search_query=None):
    """Fetches all registered donors, optionally filtered by name/phone/blood group."""
    conn = get_connection()
    cursor = conn.cursor()
    if search_query:
        param = f"%{search_query}%"
        cursor.execute("""
            SELECT * FROM donors
            WHERE full_name LIKE ? OR phone LIKE ? OR blood_group LIKE ? OR country LIKE ?
            ORDER BY id DESC
        """, (param, param, param, param))
    else:
        cursor.execute("SELECT * FROM donors ORDER BY id DESC")
    donors = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return donors

def get_donor_by_id(donor_id):
    """Retrieves a single donor record by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM donors WHERE id = ?", (donor_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def register_donor(data):
    """Registers a new donor and updates blood inventory if a donation is logged."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO donors (
            national_id, full_name, country, phone, email, gender, age, weight_kg, blood_group,
            hemoglobin, systolic_bp, diastolic_bp, fingerprint_pattern, fingerprint_ridge_count,
            eligibility_status, eligibility_score, deferral_reason, last_donation_date,
            total_donations, registration_date, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("national_id"),
        data.get("full_name"),
        data.get("country"),
        data.get("phone"),
        data.get("email", ""),
        data.get("gender", "Other"),
        int(data.get("age", 25)),
        float(data.get("weight_kg", 60.0)),
        data.get("blood_group"),
        float(data.get("hemoglobin", 14.0)),
        int(data.get("systolic_bp", 120)),
        int(data.get("diastolic_bp", 80)),
        data.get("fingerprint_pattern", "Unknown"),
        int(data.get("fingerprint_ridge_count", 130)),
        data.get("eligibility_status", "Eligible"),
        float(data.get("eligibility_score", 0.9)),
        data.get("deferral_reason", ""),
        data.get("last_donation_date"),
        int(data.get("total_donations", 0)),
        now_str,
        data.get("notes", "")
    ))
    new_donor_id = cursor.lastrowid

    # If eligible and donation selected, record donation and increment inventory
    if data.get("record_donation_now", False) and data.get("eligibility_status") == "Eligible":
        cursor.execute("""
            INSERT INTO blood_donations (donor_id, donor_name, blood_group, units_donated, donation_date, hemoglobin, blood_pressure, phlebotomist)
            VALUES (?, ?, ?, 1, ?, ?, ?, ?)
        """, (
            new_donor_id,
            data.get("full_name"),
            data.get("blood_group"),
            now_str,
            float(data.get("hemoglobin", 14.0)),
            f"{data.get('systolic_bp', 120)}/{data.get('diastolic_bp', 80)}",
            data.get("phlebotomist", "Blood Bank Staff")
        ))
        # Update donor total donations
        cursor.execute("UPDATE donors SET total_donations = total_donations + 1, last_donation_date = ? WHERE id = ?", (now_str, new_donor_id))
        # Update inventory
        cursor.execute("UPDATE blood_inventory SET units_available = units_available + 1, last_updated = ? WHERE blood_group = ?", (now_str, data.get("blood_group")))

    conn.commit()
    conn.close()
    return new_donor_id

def get_inventory():
    """Returns current blood stock per blood group."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blood_inventory ORDER BY blood_group ASC")
    inv = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return inv

def get_dashboard_stats():
    """Calculates summary KPIs for the blood bank."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM donors")
    total_donors = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM donors WHERE eligibility_status = 'Eligible'")
    eligible_donors = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(units_available) FROM blood_inventory")
    total_units = cursor.fetchone()[0] or 0

    cursor.execute("SELECT COUNT(*) FROM blood_requests WHERE status = 'Pending'")
    pending_requests = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM blood_donations")
    total_donations_count = cursor.fetchone()[0]

    cursor.execute("SELECT blood_group, units_available, minimum_threshold FROM blood_inventory")
    inventory_items = [dict(r) for r in cursor.fetchall()]
    critical_groups = [r["blood_group"] for r in inventory_items if r["units_available"] <= r["minimum_threshold"]]

    conn.close()
    return {
        "total_donors": total_donors,
        "eligible_donors": eligible_donors,
        "ineligible_donors": total_donors - eligible_donors,
        "total_units": total_units,
        "pending_requests": pending_requests,
        "total_donations_count": total_donations_count,
        "critical_groups": critical_groups,
        "inventory": inventory_items
    }

def record_donation(donor_id, phlebotomist="Staff", notes=""):
    """Records a new donation for an existing donor."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("SELECT full_name, blood_group, hemoglobin, systolic_bp, diastolic_bp FROM donors WHERE id = ?", (donor_id,))
    donor = cursor.fetchone()
    if not donor:
        conn.close()
        return False, "Donor not found"

    cursor.execute("""
        INSERT INTO blood_donations (donor_id, donor_name, blood_group, units_donated, donation_date, hemoglobin, blood_pressure, phlebotomist, notes)
        VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
    """, (
        donor_id,
        donor["full_name"],
        donor["blood_group"],
        now_str,
        donor["hemoglobin"],
        f"{donor['systolic_bp']}/{donor['diastolic_bp']}",
        phlebotomist,
        notes
    ))
    cursor.execute("UPDATE donors SET total_donations = total_donations + 1, last_donation_date = ? WHERE id = ?", (now_str, donor_id))
    cursor.execute("UPDATE blood_inventory SET units_available = units_available + 1, last_updated = ? WHERE blood_group = ?", (now_str, donor["blood_group"]))
    conn.commit()
    conn.close()
    return True, "Donation recorded successfully"

def add_blood_request(patient_name, hospital_name, contact_phone, blood_group, units_requested, urgency="Normal", notes=""):
    """Adds a blood transfusion emergency/routine request."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT INTO blood_requests (patient_name, hospital_name, contact_phone, blood_group, units_requested, urgency, status, request_date, notes)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
    """, (patient_name, hospital_name, contact_phone, blood_group, units_requested, urgency, now_str, notes))
    conn.commit()
    conn.close()
    return True

def get_blood_requests():
    """Fetches all blood requests."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM blood_requests ORDER BY id DESC")
    requests = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return requests

def fulfill_blood_request(request_id):
    """Fulfills a request and deducts stock from inventory."""
    conn = get_connection()
    cursor = conn.cursor()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("SELECT blood_group, units_requested, status FROM blood_requests WHERE id = ?", (request_id,))
    req = cursor.fetchone()
    if not req or req["status"] != "Pending":
        conn.close()
        return False, "Request not pending or not found"

    bg = req["blood_group"]
    units = req["units_requested"]

    cursor.execute("SELECT units_available FROM blood_inventory WHERE blood_group = ?", (bg,))
    inv = cursor.fetchone()
    if not inv or inv["units_available"] < units:
        conn.close()
        return False, f"Not enough units available for {bg}! In stock: {inv['units_available'] if inv else 0}"

    cursor.execute("UPDATE blood_inventory SET units_available = units_available - ?, last_updated = ? WHERE blood_group = ?", (units, now_str, bg))
    cursor.execute("UPDATE blood_requests SET status = 'Fulfilled', fulfilled_date = ? WHERE id = ?", (now_str, request_id))
    conn.commit()
    conn.close()
    return True, "Request fulfilled successfully"

# Initialize tables when imported
init_db()
