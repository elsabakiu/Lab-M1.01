"""No-show prediction model for ClinicIQ.

Trains an XGBoost classifier on historical appointment data and generates
a daily ranked list of appointments by predicted no-show probability.
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
MODEL_PATH = PROJECT_ROOT / "agent" / "no_show_model.pkl"

FEATURE_COLUMNS = [
    "age",
    "lead_time_days",
    "hour",
    "reminder_sent",
    "scholarship",
    "hypertension",
    "diabetes",
    "alcoholism",
    "handicap",
    "gender_encoded",
    "specialty_encoded",
    "day_of_week",
]

SPECIALTY_MAP = {
    "Pediatrics": 0,
    "Geriatrics": 1,
    "Chronic Care": 2,
    "Rehabilitation": 3,
    "Women's Health": 4,
    "Behavioral Health": 5,
    "Family Medicine": 6,
}

WEEKDAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}

# Human-readable feature labels for explainability
FEATURE_LABELS = {
    "lead_time_days": "booking lead time",
    "reminder_sent": "no SMS reminder sent",
    "age": "patient age",
    "hour": "appointment hour",
    "scholarship": "welfare recipient",
    "hypertension": "hypertension",
    "diabetes": "diabetes",
    "alcoholism": "alcoholism",
    "handicap": "disability flag",
    "gender_encoded": "gender",
    "specialty_encoded": "specialty",
    "day_of_week": "day of week",
}


def _encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add encoded columns needed for model features."""
    out = df.copy()
    out["gender_encoded"] = (out["gender"].str.upper() == "M").astype(int)
    out["specialty_encoded"] = out["specialty"].map(SPECIALTY_MAP).fillna(6).astype(int)
    out["day_of_week"] = out["weekday"].map(WEEKDAY_MAP).fillna(0).astype(int)
    return out


def load_training_data() -> tuple[pd.DataFrame, pd.Series]:
    """Load and prepare training features and labels."""
    df = pd.read_csv(PROCESSED_DIR / "appointments_clean.csv")
    df = _encode_features(df)
    X = df[FEATURE_COLUMNS].fillna(0).astype(float)
    y = df["no_show"].astype(int)
    return X, y


def train(X: pd.DataFrame, y: pd.Series) -> Any:
    """Train XGBoost classifier and return fitted model."""
    from xgboost import XGBClassifier

    # class imbalance: ~20% no-show → scale_pos_weight ≈ 4
    no_show_count = int(y.sum())
    show_count = int((y == 0).sum())
    scale = round(show_count / max(no_show_count, 1), 1)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=scale,
        eval_metric="logloss",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X, y)
    return model


def save_model(model: Any) -> None:
    with open(MODEL_PATH, "wb") as f:
        pickle.dump(model, f)


def load_model() -> Any:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Model not found at {MODEL_PATH}. Run `python agent/train_model.py` first."
        )
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


def _top_features(model: Any, row: pd.Series, n: int = 3) -> list[str]:
    """Return human-readable top-n contributing feature names for a single row."""
    importances = model.feature_importances_
    # Weight importances by the row's feature values (normalised)
    row_vals = row[FEATURE_COLUMNS].values.astype(float)
    # Use feature importance * |feature value| as a simple contribution proxy
    contributions = importances * np.abs(row_vals)
    top_idx = contributions.argsort()[::-1][:n]
    labels = []
    for idx in top_idx:
        feat = FEATURE_COLUMNS[idx]
        label = FEATURE_LABELS.get(feat, feat)
        val = row_vals[idx]
        # Add context for binary flags
        if feat == "reminder_sent" and val == 0:
            labels.append("no SMS reminder sent")
        elif feat == "lead_time_days":
            labels.append(f"booked {int(val)}d in advance")
        elif feat == "age":
            labels.append(f"patient age {int(val)}")
        elif feat == "hour":
            labels.append(f"slot at {int(val):02d}:00")
        elif feat == "day_of_week":
            day_name = [k for k, v in WEEKDAY_MAP.items() if v == int(val)]
            labels.append(day_name[0] if day_name else label)
        else:
            labels.append(label)
    return labels


def _simulate_todays_appointments(n: int = 60) -> pd.DataFrame:
    """
    Sample n appointments from historical data to simulate today + tomorrow.
    Adds synthetic appointment_time strings for display purposes.
    """
    df = pd.read_csv(PROCESSED_DIR / "appointments_clean.csv")
    sample = df.sample(n=n, random_state=42).copy()
    # Half today, half tomorrow
    today = pd.Timestamp.now().normalize()
    tomorrow = today + pd.Timedelta(days=1)
    half = n // 2
    dates = [today] * half + [tomorrow] * (n - half)
    sample["appointment_date"] = [d.strftime("%Y-%m-%d") for d in dates]
    sample["appointment_time_str"] = sample["hour"].apply(
        lambda h: f"{int(h):02d}:00"
    )
    return sample


def generate_daily_risk_report(n_appointments: int = 60) -> pd.DataFrame:
    """
    Generate a ranked daily risk report from the trained model.
    Returns a DataFrame ready to display in the Streamlit No-Show Risk Board.
    """
    model = load_model()
    raw = _simulate_todays_appointments(n_appointments)
    raw = _encode_features(raw)

    X = raw[FEATURE_COLUMNS].fillna(0).astype(float)
    raw["no_show_probability"] = model.predict_proba(X)[:, 1]

    # Risk tiers
    raw["risk_tier"] = pd.cut(
        raw["no_show_probability"],
        bins=[-0.001, 0.35, 0.60, 1.001],
        labels=["Low", "Medium", "High"],
    )

    # Top-3 contributing features per row
    raw["top_3_features"] = [
        " | ".join(_top_features(model, row))
        for _, row in raw[FEATURE_COLUMNS].iterrows()
    ]

    report = raw[
        [
            "appointment_date",
            "appointment_time_str",
            "patient_id",
            "specialty",
            "provider",
            "age",
            "reminder_sent",
            "lead_time_days",
            "no_show_probability",
            "risk_tier",
            "top_3_features",
        ]
    ].rename(
        columns={
            "appointment_date": "Date",
            "appointment_time_str": "Time",
            "patient_id": "Patient ID",
            "specialty": "Specialty",
            "provider": "Provider",
            "age": "Age",
            "reminder_sent": "Reminder Sent",
            "lead_time_days": "Lead Time (days)",
            "no_show_probability": "No-Show Risk",
            "risk_tier": "Risk Tier",
            "top_3_features": "Key Risk Factors",
        }
    )

    report = report.sort_values("No-Show Risk", ascending=False).reset_index(drop=True)
    report["No-Show Risk"] = report["No-Show Risk"].round(3)
    report["Reminder Sent"] = report["Reminder Sent"].map({1: "Yes", 0: "No"})
    return report
