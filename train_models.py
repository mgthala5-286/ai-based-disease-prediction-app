from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import make_scorer, accuracy_score, balanced_accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


BASE_DIR = Path(__file__).resolve().parent
DATASETS_DIR = BASE_DIR / "datasets"
MODELS_DIR = BASE_DIR / "models"
TARGET_HINTS = ("target", "outcome", "diagnosis", "disease", "class", "label", "result", "status")
RANDOM_STATE = 42


def one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=False)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=False)


def infer_target_column(frame: pd.DataFrame, requested: str | None = None) -> str:
    if requested:
        if requested not in frame.columns:
            raise ValueError(f"Target column '{requested}' was not found.")
        return requested

    lowered = {column.lower().strip(): column for column in frame.columns}
    for hint in TARGET_HINTS:
        if hint in lowered:
            return lowered[hint]

    return frame.columns[-1]


def clean_dataset(path: Path, target_column: str | None) -> tuple[pd.DataFrame, pd.Series, str]:
    frame = pd.read_csv(path)
    frame = frame.dropna(how="all").drop_duplicates()
    frame = frame.loc[:, frame.notna().any()]
    if frame.shape[1] < 2:
        raise ValueError("Dataset must contain at least one feature column and one target column.")

    target = infer_target_column(frame, target_column)
    frame = frame.dropna(subset=[target])
    y = frame[target]
    X = frame.drop(columns=[target])
    if X.empty:
        raise ValueError("No usable feature columns remain after cleaning.")
    if y.nunique(dropna=True) < 2:
        raise ValueError("Target column must contain at least two classes.")
    return X, y, target


def build_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    numeric_features = X.select_dtypes(include=["number", "bool"]).columns.tolist()
    categorical_features = [column for column in X.columns if column not in numeric_features]

    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("encoder", one_hot_encoder()),
        ]
    )
    return ColumnTransformer(
        transformers=[
            ("num", numeric_pipeline, numeric_features),
            ("cat", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )


def candidate_models() -> dict[str, object]:
    return {
        "logistic_regression": LogisticRegression(max_iter=3000, class_weight="balanced"),
        "random_forest": RandomForestClassifier(
            n_estimators=350,
            random_state=RANDOM_STATE,
            class_weight="balanced_subsample",
            min_samples_leaf=2,
            n_jobs=-1,
        ),
        "extra_trees": ExtraTreesClassifier(
            n_estimators=500,
            random_state=RANDOM_STATE,
            class_weight="balanced",
            min_samples_leaf=2,
            n_jobs=-1,
        ),
    }


def make_pipeline(X: pd.DataFrame, model: object) -> Pipeline:
    return Pipeline(
        steps=[
            ("preprocess", build_preprocessor(X)),
            ("model", model),
        ]
    )


def evaluate_models(X: pd.DataFrame, y: pd.Series) -> tuple[str, dict[str, dict[str, float]]]:
    min_class_count = int(y.value_counts().min())
    n_splits = min(5, min_class_count)
    if n_splits < 2:
        raise ValueError("Each class needs at least two rows for stratified validation.")

    scoring = {
        "accuracy": make_scorer(accuracy_score),
        "balanced_accuracy": make_scorer(balanced_accuracy_score),
        "f1_macro": make_scorer(f1_score, average="macro"),
    }
    cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=RANDOM_STATE)
    results: dict[str, dict[str, float]] = {}

    for name, model in candidate_models().items():
        pipeline = make_pipeline(X, model)
        scores = cross_validate(pipeline, X, y, cv=cv, scoring=scoring, n_jobs=-1, error_score="raise")
        results[name] = {
            "accuracy": round(float(scores["test_accuracy"].mean()), 4),
            "balanced_accuracy": round(float(scores["test_balanced_accuracy"].mean()), 4),
            "f1_macro": round(float(scores["test_f1_macro"].mean()), 4),
            "validation_folds": n_splits,
        }

    best_name = max(results, key=lambda name: (results[name]["balanced_accuracy"], results[name]["f1_macro"]))
    return best_name, results


def train_dataset(path: Path, target_column: str | None, dry_run: bool) -> dict[str, object]:
    X, y, target = clean_dataset(path, target_column)
    best_name, metrics = evaluate_models(X, y)
    best_pipeline = make_pipeline(X, candidate_models()[best_name])
    if not dry_run:
        best_pipeline.fit(X, y)
        MODELS_DIR.mkdir(exist_ok=True)
        model_path = MODELS_DIR / f"{path.stem}_model.pkl"
        joblib.dump(
            {
                "pipeline": best_pipeline,
                "target_column": target,
                "feature_columns": X.columns.tolist(),
                "labels": sorted(str(label) for label in y.unique()),
                "best_model": best_name,
                "metrics": metrics[best_name],
                "trained_at": datetime.now().isoformat(timespec="seconds"),
            },
            model_path,
        )

    return {
        "dataset": str(path.relative_to(BASE_DIR)),
        "rows": int(len(X)),
        "features": int(X.shape[1]),
        "target_column": target,
        "best_model": best_name,
        "metrics": metrics,
    }


def dataset_paths(selected: list[str] | None) -> list[Path]:
    if selected:
        return [Path(item).resolve() if Path(item).is_absolute() else (BASE_DIR / item).resolve() for item in selected]
    return sorted(DATASETS_DIR.glob("*.csv"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Train disease prediction models from CSV datasets.")
    parser.add_argument("--dataset", nargs="*", help="Optional dataset path(s). Defaults to every CSV in datasets/.")
    parser.add_argument("--target", help="Target column name. If omitted, common target names are inferred, then the last column is used.")
    parser.add_argument("--dry-run", action="store_true", help="Evaluate models without writing pickle files or metrics.")
    args = parser.parse_args()

    summaries: dict[str, object] = {}
    skipped: dict[str, str] = {}
    for path in dataset_paths(args.dataset):
        try:
            summaries[path.stem] = train_dataset(path, args.target, args.dry_run)
            best = summaries[path.stem]["best_model"]
            score = summaries[path.stem]["metrics"][best]["balanced_accuracy"]
            print(f"[trained] {path.name}: best={best}, balanced_accuracy={score}")
        except Exception as exc:
            skipped[path.name] = str(exc)
            print(f"[skipped] {path.name}: {exc}")

    if summaries and not args.dry_run:
        metrics_path = MODELS_DIR / "model_metrics.json"
        metrics_path.write_text(
            json.dumps(
                {
                    "generated_at": datetime.now().isoformat(timespec="seconds"),
                    "models": summaries,
                    "skipped": skipped,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[saved] {metrics_path.relative_to(BASE_DIR)}")

    if not summaries:
        print("No models were trained. Replace placeholder CSVs with real datasets that include a target column.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
