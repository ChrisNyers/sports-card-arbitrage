from __future__ import annotations

import json
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from cardarb.config import MODELS_DIR
from cardarb.ml.dataset import FEATURE_COLUMNS, LABEL_COLUMN, build_training_dataset

MODEL_VERSION = "price_rise_classifier_v1"


def train_model(df: pd.DataFrame | None = None) -> dict:
    """Trains a logistic regression baseline and saves the model + metrics.

    Kept to logistic regression deliberately (not a more complex model) so the
    coefficients stay inspectable, matching the Phase 1 spec's "60-65%
    baseline accuracy" target rather than chasing a higher but opaque score.
    """
    if df is None:
        df = build_training_dataset()

    X = df[FEATURE_COLUMNS]
    y = df[LABEL_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    pipeline = Pipeline(
        [
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000)),
        ]
    )
    pipeline.fit(X_train, y_train)
    y_pred = pipeline.predict(X_test)

    metrics = {
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "accuracy": round(float(accuracy_score(y_test, y_pred)), 4),
        "precision": round(float(precision_score(y_test, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, y_pred, zero_division=0)), 4),
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
        "feature_columns": FEATURE_COLUMNS,
    }

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, MODELS_DIR / f"{MODEL_VERSION}.joblib")
    (MODELS_DIR / f"{MODEL_VERSION}_metadata.json").write_text(json.dumps(metrics, indent=2))

    return metrics
