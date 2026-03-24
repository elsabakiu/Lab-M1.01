"""One-time training script for the no-show prediction model.

Run from the project root:
    python agent/train_model.py
"""
from __future__ import annotations

from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

from agent.no_show_predictor import load_training_data, save_model, train, MODEL_PATH


def main() -> None:
    print("Loading training data...")
    X, y = load_training_data()
    print(f"  {len(X):,} appointments | {y.mean():.1%} no-show rate")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  Train: {len(X_train):,} | Test: {len(X_test):,}")

    print("Training XGBoost model...")
    model = train(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_prob)

    print(f"\nTest AUC-ROC: {auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Attended", "No-Show"]))

    save_model(model)
    print(f"\nModel saved to {MODEL_PATH}")


if __name__ == "__main__":
    main()
