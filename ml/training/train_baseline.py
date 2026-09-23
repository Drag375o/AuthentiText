"""
Train the baseline AI-associated-text classifier.

Input: a JSONL file, one object per line:

    {"text": "...", "label": "human"}
    {"text": "...", "label": "ai"}

Usage:

    python manage.py train_detector data/labelled.jsonl

The script extracts the same features the application computes (so training and
inference can never drift apart), trains logistic regression on standardised
features, measures it on a held-out split AND with cross-validation, and saves
a bundle containing the model, the exact feature order and the measured metrics.

Nothing here invents performance. If the data is small or unbalanced, the
metrics will say so, and the interface reports whatever they are.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

LABELS = {"human": 0, "ai": 1}
MIN_EXAMPLES = 20
RANDOM_STATE = 0


@dataclass
class TrainingReport:
    version: str
    examples: int
    features: int
    metrics: dict
    path: Path

    def summary(self) -> str:
        m = self.metrics
        return (f"Saved {self.path}\n"
                f"  examples      {self.examples}\n"
                f"  features      {self.features}\n"
                f"  accuracy      {m['accuracy']:.3f} (held-out split)\n"
                f"  precision     {m['precision']:.3f}\n"
                f"  recall        {m['recall']:.3f}\n"
                f"  roc_auc       {m['roc_auc']:.3f}\n"
                f"  cv_accuracy   {m['cv_accuracy_mean']:.3f} +/- {m['cv_accuracy_std']:.3f}")


def load_examples(path: Path) -> list[tuple[str, int]]:
    examples = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        row = json.loads(line)
        label = str(row.get("label", "")).lower()
        if label not in LABELS:
            raise ValueError(f"{path}:{line_number}: label must be 'human' or 'ai', got {label!r}")
        if not row.get("text", "").strip():
            raise ValueError(f"{path}:{line_number}: empty text")
        examples.append((row["text"], LABELS[label]))
    return examples


def extract_rows(texts: list[str]) -> tuple[list[list[float]], list[str]]:
    """Run the application's own pipeline, so training uses production features."""
    from analyzer.services.pipeline import run_pipeline

    feature_sets = [run_pipeline(text).features for text in texts]
    usable = sorted({name for features in feature_sets for name, value in features.items() if value is not None})
    # Keep only features present in every example: no imputation, no invented values.
    names = [name for name in usable if all(features.get(name) is not None for features in feature_sets)]
    rows = [[float(features[name]) for name in names] for features in feature_sets]
    return rows, names


def train(path: Path, output: Path, version: str = "baseline-0.1") -> TrainingReport:
    import numpy as np
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
    from sklearn.model_selection import cross_val_score, train_test_split
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    import joblib

    examples = load_examples(path)
    if len(examples) < MIN_EXAMPLES:
        raise ValueError(f"Only {len(examples)} examples; at least {MIN_EXAMPLES} are needed for a meaningful model.")
    counts = {name: sum(1 for _, y in examples if y == value) for name, value in LABELS.items()}
    if min(counts.values()) < MIN_EXAMPLES // 4:
        raise ValueError(f"Unbalanced data: {counts}. Both classes need a reasonable number of examples.")

    texts, labels = zip(*examples)
    rows, names = extract_rows(list(texts))
    X, y = np.array(rows), np.array(labels)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=RANDOM_STATE, stratify=y)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=RANDOM_STATE))
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    probabilities = model.predict_proba(X_test)[:, 1]
    precision, recall, _, _ = precision_recall_fscore_support(y_test, predictions, average="binary", zero_division=0)
    cv = cross_val_score(model, X, y, cv=min(5, min(counts.values())), scoring="accuracy")
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "precision": float(precision),
        "recall": float(recall),
        "roc_auc": float(roc_auc_score(y_test, probabilities)) if len(set(y_test)) > 1 else float("nan"),
        "cv_accuracy_mean": float(cv.mean()),
        "cv_accuracy_std": float(cv.std()),
        "test_size": int(len(y_test)),
    }

    model.fit(X, y)   # refit on everything for the shipped model
    output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": model, "feature_names": names, "metrics": metrics, "version": version,
                 "trained_on": f"{len(examples)} labelled documents ({counts['human']} human, {counts['ai']} ai)"}, output)
    return TrainingReport(version, len(examples), len(names), metrics, output)
