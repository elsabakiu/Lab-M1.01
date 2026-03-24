from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "KaggleV2-May-2016.csv"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


SPECIALTY_PROVIDER_CODES = {
    "Pediatrics": "PED",
    "Geriatrics": "GER",
    "Chronic Care": "CHR",
    "Rehabilitation": "REH",
    "Women's Health": "WH",
    "Behavioral Health": "BH",
    "Family Medicine": "FM",
}

SPECIALTY_DURATION_BASE = {
    "Pediatrics": 16,
    "Geriatrics": 24,
    "Chronic Care": 20,
    "Rehabilitation": 28,
    "Women's Health": 18,
    "Behavioral Health": 22,
    "Family Medicine": 17,
}

SPECIALTY_CAPACITY_MIN = {
    "Pediatrics": 540,
    "Geriatrics": 480,
    "Chronic Care": 510,
    "Rehabilitation": 450,
    "Women's Health": 540,
    "Behavioral Health": 480,
    "Family Medicine": 540,
}

APPOINTMENT_HOURS = np.array([7, 8, 9, 10, 11, 12, 13, 14, 15, 16])
PROVIDERS_PER_SPECIALTY = 24


def assign_specialty(row: pd.Series) -> str:
    if row["handicap"] > 0:
        return "Rehabilitation"
    if row["age"] < 18:
        return "Pediatrics"
    if row["age"] >= 65:
        return "Geriatrics"
    if row["alcoholism"] == 1:
        return "Behavioral Health"
    if row["diabetes"] == 1 or row["hypertension"] == 1:
        return "Chronic Care"
    if row["gender"] == "F" and 18 <= row["age"] <= 45:
        return "Women's Health"
    return "Family Medicine"


def assign_provider(row: pd.Series) -> str:
    provider_idx = (int(row["appointment_id"]) % PROVIDERS_PER_SPECIALTY) + 1
    provider_code = SPECIALTY_PROVIDER_CODES[row["specialty"]]
    return f"{provider_code}-{provider_idx:02d}"


def build_clean_appointments(raw_df: pd.DataFrame) -> pd.DataFrame:
    df = raw_df.rename(
        columns={
            "PatientId": "patient_id",
            "AppointmentID": "appointment_id",
            "Gender": "gender",
            "ScheduledDay": "scheduled_datetime",
            "AppointmentDay": "appointment_datetime",
            "Age": "age",
            "Neighbourhood": "neighborhood",
            "Scholarship": "scholarship",
            "Hipertension": "hypertension",
            "Diabetes": "diabetes",
            "Alcoholism": "alcoholism",
            "Handcap": "handicap",
            "SMS_received": "reminder_sent",
            "No-show": "no_show_label",
        }
    ).copy()

    df["patient_id"] = df["patient_id"].astype(str)
    df["appointment_id"] = df["appointment_id"].astype("int64")
    df["scheduled_datetime"] = pd.to_datetime(df["scheduled_datetime"], utc=True)
    df["appointment_datetime"] = pd.to_datetime(df["appointment_datetime"], utc=True)

    df = df.drop_duplicates(subset=["appointment_id"]).copy()
    df["age"] = df["age"].clip(lower=0, upper=115)
    df["gender"] = df["gender"].str.upper().fillna("U")
    df["no_show"] = (df["no_show_label"].str.lower() == "yes").astype(int)
    df["attended"] = 1 - df["no_show"]
    df["date"] = df["appointment_datetime"].dt.date
    df["weekday"] = df["appointment_datetime"].dt.day_name()
    df["month"] = df["appointment_datetime"].dt.strftime("%Y-%m")
    df["lead_time_days"] = (
        df["appointment_datetime"].dt.normalize() - df["scheduled_datetime"].dt.normalize()
    ).dt.days.clip(lower=0)

    hour_index = df["appointment_id"] % len(APPOINTMENT_HOURS)
    df["hour"] = APPOINTMENT_HOURS[hour_index]

    df["specialty"] = df.apply(assign_specialty, axis=1)
    df["provider"] = df.apply(assign_provider, axis=1)

    chronic_burden = (
        df["hypertension"] + df["diabetes"] + df["alcoholism"] + (df["handicap"] > 0).astype(int)
    )
    age_adjustment = np.where(df["age"] >= 65, 5, np.where(df["age"] < 18, -2, 0))
    base_duration = df["specialty"].map(SPECIALTY_DURATION_BASE).astype(int)
    df["visit_duration_min"] = (
        base_duration
        + chronic_burden * 4
        + df["scholarship"] * 2
        + age_adjustment
        + (df["lead_time_days"] >= 30).astype(int) * 2
    ).clip(lower=15, upper=60)

    provider_day_load = (
        df.groupby(["date", "provider"])["appointment_id"].transform("count").astype(int)
    )
    provider_capacity_min = df["specialty"].map(SPECIALTY_CAPACITY_MIN).astype(int)
    capacity_appointments = (provider_capacity_min / df["visit_duration_min"]).clip(lower=6)
    overload_factor = np.maximum(provider_day_load - capacity_appointments.round().astype(int), 0)

    df["wait_time_min"] = (
        8
        + chronic_burden * 3
        + overload_factor * 4
        + (df["hour"] >= 14).astype(int) * 5
        + (df["reminder_sent"] == 0).astype(int) * 2
        + (df["lead_time_days"] <= 1).astype(int) * 3
    ).clip(lower=5, upper=95)

    df["provider_daily_capacity_min"] = provider_capacity_min
    df["estimated_provider_capacity_appointments"] = capacity_appointments.round(1)
    df["age_band"] = pd.cut(
        df["age"],
        bins=[-1, 17, 34, 49, 64, 120],
        labels=["0-17", "18-34", "35-49", "50-64", "65+"],
    ).astype(str)

    clean_columns = [
        "appointment_id",
        "patient_id",
        "scheduled_datetime",
        "appointment_datetime",
        "date",
        "month",
        "weekday",
        "hour",
        "lead_time_days",
        "gender",
        "age",
        "age_band",
        "neighborhood",
        "specialty",
        "provider",
        "scholarship",
        "hypertension",
        "diabetes",
        "alcoholism",
        "handicap",
        "reminder_sent",
        "attended",
        "no_show",
        "wait_time_min",
        "visit_duration_min",
        "provider_daily_capacity_min",
        "estimated_provider_capacity_appointments",
    ]
    return df[clean_columns].sort_values(["date", "provider", "hour", "appointment_id"])


def build_daily_kpis(clean_df: pd.DataFrame) -> pd.DataFrame:
    provider_day_capacity = (
        clean_df.groupby(["date", "provider"], as_index=False)
        .agg(capacity_minutes=("provider_daily_capacity_min", "first"))
    )
    daily = (
        clean_df.groupby("date", as_index=False)
        .agg(
            total_appointments=("appointment_id", "count"),
            attended_appointments=("attended", "sum"),
            no_show_appointments=("no_show", "sum"),
            avg_wait_time_min=("wait_time_min", "mean"),
            avg_visit_duration_min=("visit_duration_min", "mean"),
            reminder_coverage_rate=("reminder_sent", "mean"),
            avg_lead_time_days=("lead_time_days", "mean"),
            unique_providers=("provider", "nunique"),
            total_scheduled_minutes=("visit_duration_min", "sum"),
        )
        .round(2)
    )
    daily_capacity = (
        provider_day_capacity.groupby("date", as_index=False)
        .agg(total_capacity_minutes=("capacity_minutes", "sum"))
    )
    daily = daily.merge(daily_capacity, on="date", how="left")
    daily["no_show_rate"] = (daily["no_show_appointments"] / daily["total_appointments"]).round(4)
    daily["attendance_rate"] = (daily["attended_appointments"] / daily["total_appointments"]).round(4)
    daily["estimated_utilization_rate"] = (
        daily["total_scheduled_minutes"] / daily["total_capacity_minutes"]
    ).round(4)
    return daily


def build_no_show_patterns(clean_df: pd.DataFrame) -> pd.DataFrame:
    patterns = (
        clean_df.groupby(["weekday", "hour", "specialty"], as_index=False)
        .agg(
            total_appointments=("appointment_id", "count"),
            no_show_count=("no_show", "sum"),
            attended_count=("attended", "sum"),
            avg_lead_time_days=("lead_time_days", "mean"),
            reminder_coverage_rate=("reminder_sent", "mean"),
        )
        .round(2)
    )
    patterns["no_show_rate"] = (patterns["no_show_count"] / patterns["total_appointments"]).round(4)
    return patterns.sort_values(["weekday", "hour", "specialty"])


def build_provider_utilization(clean_df: pd.DataFrame) -> pd.DataFrame:
    provider = (
        clean_df.groupby(["date", "provider", "specialty"], as_index=False)
        .agg(
            total_appointments=("appointment_id", "count"),
            attended_appointments=("attended", "sum"),
            no_show_appointments=("no_show", "sum"),
            avg_wait_time_min=("wait_time_min", "mean"),
            avg_visit_duration_min=("visit_duration_min", "mean"),
            total_scheduled_minutes=("visit_duration_min", "sum"),
            capacity_minutes=("provider_daily_capacity_min", "first"),
        )
        .round(2)
    )
    provider["utilization_rate"] = (
        provider["total_scheduled_minutes"] / provider["capacity_minutes"]
    ).round(4)
    provider["no_show_rate"] = (
        provider["no_show_appointments"] / provider["total_appointments"]
    ).round(4)
    provider["capacity_gap_minutes"] = (
        provider["total_scheduled_minutes"] - provider["capacity_minutes"]
    ).round(2)
    provider["utilization_status"] = np.where(
        provider["utilization_rate"] >= 0.9,
        "Overloaded",
        np.where(provider["utilization_rate"] <= 0.6, "Underused", "Balanced"),
    )
    return provider.sort_values(["date", "specialty", "provider"])


def build_reminder_effectiveness(clean_df: pd.DataFrame) -> pd.DataFrame:
    reminder = (
        clean_df.groupby(["reminder_sent", "weekday", "specialty"], as_index=False)
        .agg(
            total_appointments=("appointment_id", "count"),
            attended_appointments=("attended", "sum"),
            no_show_appointments=("no_show", "sum"),
            avg_lead_time_days=("lead_time_days", "mean"),
            avg_wait_time_min=("wait_time_min", "mean"),
        )
        .round(2)
    )
    reminder["attendance_rate"] = (
        reminder["attended_appointments"] / reminder["total_appointments"]
    ).round(4)
    reminder["no_show_rate"] = (
        reminder["no_show_appointments"] / reminder["total_appointments"]
    ).round(4)
    reminder["reminder_status"] = np.where(reminder["reminder_sent"] == 1, "Reminder Sent", "No Reminder")
    return reminder.sort_values(["reminder_sent", "weekday", "specialty"])


def main() -> None:
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Raw dataset not found at {RAW_PATH}")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(
        RAW_PATH,
        dtype={
            "PatientId": "string",
            "AppointmentID": "int64",
        },
    )
    clean_df = build_clean_appointments(raw_df)

    clean_df.to_csv(PROCESSED_DIR / "appointments_clean.csv", index=False)
    build_daily_kpis(clean_df).to_csv(PROCESSED_DIR / "daily_kpis.csv", index=False)
    build_no_show_patterns(clean_df).to_csv(PROCESSED_DIR / "no_show_patterns.csv", index=False)
    build_provider_utilization(clean_df).to_csv(
        PROCESSED_DIR / "provider_utilization.csv", index=False
    )
    build_reminder_effectiveness(clean_df).to_csv(
        PROCESSED_DIR / "reminder_effectiveness.csv", index=False
    )

    print(f"Wrote processed outputs to {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
