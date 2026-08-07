from __future__ import annotations

from datetime import date
from functools import lru_cache

import joblib
import pandas as pd

from cardarb.config import MODELS_DIR
from cardarb.db.database import connection
from cardarb.ml.dataset import FEATURE_COLUMNS
from cardarb.ml.train import MODEL_VERSION


class ModelNotTrainedError(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load_model():
    model_path = MODELS_DIR / f"{MODEL_VERSION}.joblib"
    if not model_path.exists():
        raise ModelNotTrainedError(f"No trained model found at {model_path}. Run `cardarb train` first.")
    return joblib.load(model_path)


def predict(features_df: pd.DataFrame) -> pd.DataFrame:
    model = load_model()
    X = features_df[FEATURE_COLUMNS].fillna(0)
    probs = model.predict_proba(X)[:, 1]

    result = features_df[["card_id", "as_of_date"]].copy()
    result["prob_price_rise"] = probs
    result["predicted_label"] = (probs >= 0.5).astype(int)
    result["model_version"] = MODEL_VERSION
    return result


def run_predictions(as_of_date: date) -> pd.DataFrame:
    with connection() as conn:
        features_df = pd.read_sql_query(
            "SELECT * FROM features WHERE as_of_date = ?", conn, params=(as_of_date.isoformat(),)
        )
        if features_df.empty:
            return features_df

        predictions_df = predict(features_df)

        for _, row in predictions_df.iterrows():
            conn.execute(
                """
                INSERT INTO ml_predictions (card_id, as_of_date, model_version, prob_price_rise, predicted_label)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(card_id, as_of_date) DO UPDATE SET
                    model_version=excluded.model_version,
                    prob_price_rise=excluded.prob_price_rise,
                    predicted_label=excluded.predicted_label
                """,
                (
                    int(row["card_id"]),
                    row["as_of_date"],
                    row["model_version"],
                    float(row["prob_price_rise"]),
                    int(row["predicted_label"]),
                ),
            )

    return predictions_df
