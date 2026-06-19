"""Method 3 — multi-model classification inside the walk-forward (Phase A3).

Identifies which features, in combination, best discriminate setups from controls
(primary target). All models run through the purged/embargoed expanding walk-forward
(gws.common.walkforward): the scaler is fit on the training fold only, predictions
are collected out-of-sample, and discrimination (ROC-AUC) + calibration (Brier) are
reported per fold and overall. Feature importance is permutation-based and computed
out-of-sample (never impurity). Class imbalance is handled via class weights.
"""
from __future__ import annotations

import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, brier_score_loss, precision_recall_fscore_support,
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.inspection import permutation_importance
from xgboost import XGBClassifier
from lightgbm import LGBMClassifier

from gws.common.walkforward import expanding_splits


def build_estimators(seed: int = 0, class_weight="balanced") -> dict:
    """The bake-off roster. Each value is a zero-arg builder returning a fresh,
    unfitted sklearn-compatible classifier with predict_proba."""
    return {
        "random_forest": lambda: RandomForestClassifier(
            n_estimators=200, class_weight=class_weight, random_state=seed, n_jobs=-1),
        "xgboost": lambda: XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
            eval_metric="logloss", random_state=seed, n_jobs=-1),
        "lightgbm": lambda: LGBMClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8,
            class_weight=class_weight, random_state=seed, n_jobs=-1, verbose=-1),
        "elastic_net_logistic": lambda: LogisticRegression(
            solver="saga", l1_ratio=0.5,            # l1_ratio implies elastic-net (sklearn >= 1.8 API)
            class_weight=class_weight, max_iter=5000, random_state=seed),
        "svm": lambda: SVC(probability=True, class_weight=class_weight, random_state=seed),
    }


def run_walk_forward(X, y, t, test_boundaries, label_horizon, build_estimator, *,
                     scale: bool = True, threshold: float = 0.5, embargo: int = 0) -> dict:
    """Train/evaluate one estimator across the expanding walk-forward.

    Returns out-of-sample probabilities + true labels, overall ROC-AUC / Brier /
    precision / recall / F1, and per-fold metrics."""
    X = np.asarray(X, float)
    y = np.asarray(y, int)
    t = np.asarray(t)
    oos_p, oos_y, per_fold = [], [], []

    for train_idx, test_idx in expanding_splits(t, test_boundaries, label_horizon, embargo=embargo):
        ytr = y[train_idx]
        if len(np.unique(ytr)) < 2 or len(test_idx) == 0:
            continue
        Xtr, Xte = X[train_idx], X[test_idx]
        if scale:
            sc = StandardScaler().fit(Xtr)               # fit on train fold ONLY
            Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
        model = build_estimator()
        model.fit(Xtr, ytr)
        p = model.predict_proba(Xte)[:, 1]
        oos_p.append(p)
        oos_y.append(y[test_idx])
        if len(np.unique(y[test_idx])) > 1:
            per_fold.append({"auc": float(roc_auc_score(y[test_idx], p)),
                             "brier": float(brier_score_loss(y[test_idx], p)),
                             "n": int(len(test_idx))})

    p = np.concatenate(oos_p)
    yv = np.concatenate(oos_y)
    pred = (p >= threshold).astype(int)
    prec, rec, f1, _ = precision_recall_fscore_support(yv, pred, average="binary", zero_division=0)
    return {
        "oos_proba": p, "oos_y": yv,
        "auc": float(roc_auc_score(yv, p)),
        "brier": float(brier_score_loss(yv, p)),
        "precision": float(prec), "recall": float(rec), "f1": float(f1),
        "per_fold": per_fold,
    }


def compare_models(X, y, t, test_boundaries, label_horizon, estimators, **kw) -> dict:
    """Run the whole roster; returns {model_name: run_walk_forward result}."""
    return {name: run_walk_forward(X, y, t, test_boundaries, label_horizon, fn, **kw)
            for name, fn in estimators.items()}


def permutation_importance_oos(model, X_test, y_test, *, n_repeats: int = 10, seed: int = 0):
    """Out-of-sample permutation importance (AUC drop), never impurity-based."""
    r = permutation_importance(model, X_test, y_test, n_repeats=n_repeats,
                               random_state=seed, scoring="roc_auc")
    return r.importances_mean
