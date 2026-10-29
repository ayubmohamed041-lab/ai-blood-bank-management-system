"""
Dataset Loader and Synthetic Kaggle/UCI Benchmark Generator
Generates and manages datasets for:
1. Blood Donation Transfusion & Eligibility Dataset (Kaggle / UCI Blood Transfusion Service Center Dataset + WHO clinical criteria)
2. Fingerprint Dermatoglyphic Biometric Dataset for Blood Group Detection (Kaggle Fingerprint Biometrics Benchmark)
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
from config import DATA_DIR, BLOOD_GROUPS, ELIGIBILITY_CRITERIA

TRANSFUSION_DATA_PATH = DATA_DIR / "blood_donation_eligibility_dataset.csv"
FINGERPRINT_DATA_PATH = DATA_DIR / "fingerprint_blood_group_dataset.csv"

def generate_blood_donation_dataset(n_samples=2500, random_seed=42):
    """
    Generates a realistic clinical dataset based on the Kaggle / UCI Blood Transfusion Service Center Dataset
    extended with WHO & Red Cross blood donor eligibility criteria.
    """
    np.random.seed(random_seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    ages = np.random.randint(16, 72, size=n_samples)
    genders = np.random.choice(["Male", "Female"], size=n_samples, p=[0.55, 0.45])
    
    # Weight: centered around 68kg for males, 60kg for females
    weights = []
    for g in genders:
        if g == "Male":
            weights.append(np.clip(np.random.normal(72, 14), 42, 130))
        else:
            weights.append(np.clip(np.random.normal(61, 12), 40, 115))
    weights = np.round(weights, 1)

    # Hemoglobin: normal male ~13.5-17.5, female ~12.0-15.5
    hemoglobins = []
    for g in genders:
        if g == "Male":
            hemoglobins.append(np.clip(np.random.normal(14.5, 1.8), 8.5, 19.0))
        else:
            hemoglobins.append(np.clip(np.random.normal(13.2, 1.6), 8.0, 17.5))
    hemoglobins = np.round(hemoglobins, 1)

    # Blood Pressure: Systolic & Diastolic
    systolic_bps = np.random.normal(122, 16, size=n_samples).astype(int)
    diastolic_bps = np.random.normal(79, 11, size=n_samples).astype(int)

    # Transfusion history (UCI format: Recency, Frequency, Monetary, Time)
    frequency = np.random.choice([0, 1, 2, 3, 4, 5, 8, 12, 18, 25], size=n_samples, p=[0.25, 0.20, 0.15, 0.12, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02])
    recency = []
    monetary = frequency * 250 # 250cc or 450ml equivalent per donation
    time_since_first = []

    for f in frequency:
        if f == 0:
            recency.append(999) # never donated before
            time_since_first.append(0)
        else:
            r = np.random.choice([1, 2, 3, 4, 5, 6, 8, 12, 24, 36])
            recency.append(r)
            time_since_first.append(r + f * np.random.randint(2, 6))
    recency = np.array(recency)
    time_since_first = np.array(time_since_first)

    # Medical flag (e.g. recent surgery, fever, medications: 0=clean, 1=flagged)
    medical_flags = np.random.choice([0, 1], size=n_samples, p=[0.88, 0.12])

    # Blood Groups according to global distribution
    bg_dist = [0.35, 0.06, 0.28, 0.03, 0.07, 0.01, 0.18, 0.02]
    # Re-normalize just in case
    bg_dist = [p / sum(bg_dist) for p in bg_dist]
    blood_groups = np.random.choice(BLOOD_GROUPS, size=n_samples, p=bg_dist)

    # Determine ground-truth clinical eligibility
    eligibility = []
    deferral_reasons = []

    for i in range(n_samples):
        reasons = []
        age = ages[i]
        weight = weights[i]
        hb = hemoglobins[i]
        gender = genders[i]
        sbp = systolic_bps[i]
        dbp = diastolic_bps[i]
        rec = recency[i]
        med = medical_flags[i]

        if age < ELIGIBILITY_CRITERIA["min_age"]:
            reasons.append("Da'da oo ka yar 18 sano (Age < 18)")
        elif age > ELIGIBILITY_CRITERIA["max_age"]:
            reasons.append("Da'da oo ka weyn 65 sano (Age > 65)")

        if weight < ELIGIBILITY_CRITERIA["min_weight_kg"]:
            reasons.append(f"Miisaanka oo ka yar 50kg ({weight}kg)")

        min_hb = ELIGIBILITY_CRITERIA["min_hemoglobin_female"] if gender == "Female" else ELIGIBILITY_CRITERIA["min_hemoglobin_male"]
        if hb < min_hb:
            reasons.append(f"Heerka Hemoglobin oo hooseeya ({hb} g/dL, heerka la rabo >= {min_hb})")

        if sbp < ELIGIBILITY_CRITERIA["min_systolic_bp"] or sbp > ELIGIBILITY_CRITERIA["max_systolic_bp"]:
            reasons.append(f"Dhiig-karka Systolic oo aan caadi ahayn ({sbp} mmHg)")

        if dbp < ELIGIBILITY_CRITERIA["min_diastolic_bp"] or dbp > ELIGIBILITY_CRITERIA["max_diastolic_bp"]:
            reasons.append(f"Dhiig-karka Diastolic oo aan caadi ahayn ({dbp} mmHg)")

        if rec < 3: # less than 3 months since last donation
            reasons.append(f"Muddada shubistii u dambaysay oo aad u yar ({rec} bilood, ugu yaraan 3 bilood ayaa la rabaa)")

        if med == 1:
            reasons.append("Xaalad caafimaad ama dawooyin qofku qaadanayo")

        if len(reasons) == 0:
            eligibility.append(1) # Eligible (Haa, wuu shubi karaa)
            deferral_reasons.append("Eligible - Dhammaan shuruudaha caafimaad waa buuxsamay")
        else:
            eligibility.append(0) # Ineligible (Maya, ma shubi karo)
            deferral_reasons.append("; ".join(reasons))

    df = pd.DataFrame({
        "age": ages,
        "gender": genders,
        "weight_kg": weights,
        "hemoglobin": hemoglobins,
        "systolic_bp": systolic_bps,
        "diastolic_bp": diastolic_bps,
        "recency_months": recency,
        "frequency_donations": frequency,
        "monetary_volume_cc": monetary,
        "time_first_donation": time_since_first,
        "medical_flag": medical_flags,
        "blood_group": blood_groups,
        "eligible": eligibility,
        "deferral_reason": deferral_reasons
    })

    df.to_csv(TRANSFUSION_DATA_PATH, index=False)
    return df

def generate_fingerprint_blood_dataset(n_samples=3000, random_seed=42):
    """
    Generates a biometric dermatoglyphic dataset correlating fingerprint patterns,
    ridge characteristics, and minutiae with ABO/Rh Blood Groups, consistent with
    forensic dermatoglyphics research literature and Kaggle benchmarks.
    """
    np.random.seed(random_seed)
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # In forensic dermatoglyphics:
    # - Blood Group O: Higher frequency of Loops (~65%), lower Whorls (~28%)
    # - Blood Group A: Higher frequency of Arches (~12-15%) & Loops (~60%)
    # - Blood Group B: Higher frequency of Whorls (~42%) & Loops (~50%)
    # - Blood Group AB: Highest Whorl frequency (~48-52%), low Arches
    # - Rh+ vs Rh-: Rh- shows slight differences in Total Ridge Count (TRC)

    bg_assignments = np.random.choice(BLOOD_GROUPS, size=n_samples, p=[0.30, 0.05, 0.25, 0.04, 0.08, 0.02, 0.24, 0.02])

    patterns = []
    total_ridge_counts = []
    ridge_densities = []
    minutiae_endings = []
    minutiae_bifurcations = []
    pattern_intensities = []
    orientation_entropies = []
    core_delta_distances = []

    pattern_map = {"Loop": 1, "Whorl": 2, "Arch": 0, "Tented_Arch": 3}

    for bg in bg_assignments:
        if "O" in bg:
            pat = np.random.choice(["Loop", "Whorl", "Arch"], p=[0.67, 0.26, 0.07])
            trc = np.random.normal(138, 18)
            rd = np.random.normal(13.2, 1.4)
            pii = 1 if pat == "Loop" else (2 if pat == "Whorl" else 0)
        elif "A" in bg and "B" not in bg:
            pat = np.random.choice(["Loop", "Whorl", "Arch"], p=[0.58, 0.27, 0.15])
            trc = np.random.normal(146, 20)
            rd = np.random.normal(14.5, 1.6)
            pii = 1 if pat == "Loop" else (2 if pat == "Whorl" else 0)
        elif "B" in bg and "A" not in bg:
            pat = np.random.choice(["Loop", "Whorl", "Arch"], p=[0.48, 0.44, 0.08])
            trc = np.random.normal(154, 22)
            rd = np.random.normal(15.2, 1.7)
            pii = 1 if pat == "Loop" else (2 if pat == "Whorl" else 0)
        else: # AB
            pat = np.random.choice(["Loop", "Whorl", "Arch"], p=[0.42, 0.52, 0.06])
            trc = np.random.normal(162, 24)
            rd = np.random.normal(15.8, 1.8)
            pii = 1 if pat == "Loop" else (2 if pat == "Whorl" else 0)

        # Rh factor adjustments
        if "-" in bg:
            trc -= 10
            rd -= 0.8

        endings = int(np.clip(np.random.normal(32, 7) + (trc / 10), 12, 65))
        bifurcations = int(np.clip(np.random.normal(24, 6) + (pii * 4), 8, 50))
        entropy = np.clip(np.random.normal(0.65, 0.12) + (0.1 if pat == "Whorl" else -0.05), 0.25, 0.98)
        c_dist = np.clip(np.random.normal(75, 15) if pat != "Arch" else np.random.normal(30, 8), 15, 140)

        patterns.append(pat)
        total_ridge_counts.append(int(np.clip(trc, 60, 240)))
        ridge_densities.append(round(float(np.clip(rd, 8.0, 24.0)), 2))
        minutiae_endings.append(endings)
        minutiae_bifurcations.append(bifurcations)
        pattern_intensities.append(pii)
        orientation_entropies.append(round(float(entropy), 3))
        core_delta_distances.append(round(float(c_dist), 1))

    df = pd.DataFrame({
        "pattern_name": patterns,
        "pattern_code": [pattern_map[p] for p in patterns],
        "total_ridge_count": total_ridge_counts,
        "ridge_density": ridge_densities,
        "minutiae_endings": minutiae_endings,
        "minutiae_bifurcations": minutiae_bifurcations,
        "total_minutiae": [e + b for e, b in zip(minutiae_endings, minutiae_bifurcations)],
        "pattern_intensity_index": pattern_intensities,
        "orientation_entropy": orientation_entropies,
        "core_delta_distance": core_delta_distances,
        "blood_group": bg_assignments
    })

    df.to_csv(FINGERPRINT_DATA_PATH, index=False)
    return df

def load_or_generate_datasets():
    """Ensures both datasets exist, generating if not present."""
    if not TRANSFUSION_DATA_PATH.exists():
        df_trans = generate_blood_donation_dataset()
    else:
        df_trans = pd.read_csv(TRANSFUSION_DATA_PATH)

    if not FINGERPRINT_DATA_PATH.exists():
        df_finger = generate_fingerprint_blood_dataset()
    else:
        df_finger = pd.read_csv(FINGERPRINT_DATA_PATH)

    return df_trans, df_finger

if __name__ == "__main__":
    t_df, f_df = load_or_generate_datasets()
    print(f"Generated Blood Transfusion dataset: {t_df.shape} rows.")
    print(f"Generated Fingerprint Dermatoglyphics dataset: {f_df.shape} rows.")
