"""
GridGuard AI — Risk Model Training Script
Generates 2000 synthetic samples and trains XGBClassifier for 5 premium tiers.

Usage:
    cd backend
    python scripts/train_risk_model.py
"""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
from xgboost import XGBClassifier
import joblib

# Seed for reproducibility
np.random.seed(42)

NUM_SAMPLES = 2000

# City risk profiles (higher = riskier weather)
CITY_RISK = {
    "bengaluru": 0.3,
    "mumbai": 0.7,    # Heavy rain
    "chennai": 0.6,    # Cyclone-prone
    "delhi": 0.8,      # AQI + heat
    "hyderabad": 0.4,
    "pune": 0.35,
    "kolkata": 0.5,
}

CITIES = list(CITY_RISK.keys())


def generate_synthetic_data(n: int = NUM_SAMPLES) -> pd.DataFrame:
    """Generate synthetic training data with Indian city risk distributions."""
    records = []

    for _ in range(n):
        city = np.random.choice(CITIES)
        base_risk = CITY_RISK[city]

        # Feature generation with city-specific variance
        avg_workability_7d = max(0, min(1, np.random.normal(1 - base_risk * 0.5, 0.15)))
        online_hours_7d = max(0, np.random.normal(30, 10))
        zone_event_freq_30d = max(0, int(np.random.exponential(base_risk * 15)))
        city_risk_index = max(0, min(1, np.random.normal(base_risk, 0.1)))
        partner_tenure_days = max(7, int(np.random.exponential(120)))
        payout_rate_30d = max(0, np.random.exponential(base_risk * 0.3))

        # Calculate risk score (rule-based) for labeling
        risk_score = (
            0.3 * (1 - avg_workability_7d)
            + 0.3 * min(zone_event_freq_30d / 20.0, 1.0)
            + 0.2 * (1 - min(partner_tenure_days / 365.0, 1.0))
            + 0.2 * city_risk_index
        )
        risk_score = max(0, min(1, risk_score))

        # Map to premium tier (class 0-4)
        if risk_score < 0.2:
            tier = 0
        elif risk_score < 0.4:
            tier = 1
        elif risk_score < 0.6:
            tier = 2
        elif risk_score < 0.8:
            tier = 3
        else:
            tier = 4

        records.append({
            "avg_workability_7d": round(avg_workability_7d, 4),
            "online_hours_7d": round(online_hours_7d, 2),
            "zone_event_freq_30d": zone_event_freq_30d,
            "city_risk_index": round(city_risk_index, 4),
            "partner_tenure_days": partner_tenure_days,
            "payout_rate_30d": round(payout_rate_30d, 4),
            "premium_tier": tier,
        })

    return pd.DataFrame(records)


def main():
    print("=" * 60)
    print("GridGuard AI — Risk Model Training")
    print("=" * 60)

    # Generate data
    print(f"\n📊 Generating {NUM_SAMPLES} synthetic samples...")
    df = generate_synthetic_data()

    print(f"\nClass distribution:")
    tier_labels = {0: "Tier 1 (₹12)", 1: "Tier 2 (₹18)", 2: "Tier 3 (₹24)", 3: "Tier 4 (₹36)", 4: "Tier 5 (₹48)"}
    for tier, label in tier_labels.items():
        count = (df["premium_tier"] == tier).sum()
        print(f"  {label}: {count} ({count/len(df)*100:.1f}%)")

    # Split features and labels
    feature_cols = [
        "avg_workability_7d",
        "online_hours_7d",
        "zone_event_freq_30d",
        "city_risk_index",
        "partner_tenure_days",
        "payout_rate_30d",
    ]
    X = df[feature_cols].values
    y = df["premium_tier"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Train XGBoost
    print("\n🧠 Training XGBClassifier...")
    model = XGBClassifier(
        n_estimators=100,
        max_depth=4,
        learning_rate=0.1,
        n_jobs=-1,
        objective="multi:softmax",
        num_class=5,
        random_state=42,
        eval_metric="mlogloss",
    )
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n✅ Accuracy: {accuracy:.4f}")
    print(f"\n📋 Classification Report:")
    print(classification_report(y_test, y_pred, target_names=[f"Tier {i+1}" for i in range(5)]))

    print(f"\n🔀 Confusion Matrix:")
    print(confusion_matrix(y_test, y_pred))

    # Feature importances
    print(f"\n📊 Feature Importances:")
    for name, imp in sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {name}: {imp:.4f}")

    # Save model
    os.makedirs("models", exist_ok=True)
    model_path = "models/risk_model.pkl"
    joblib.dump(model, model_path)
    print(f"\n💾 Model saved to {model_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
