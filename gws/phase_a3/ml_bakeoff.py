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

# The kernel SVM is O(n^2)-O(n^3) in fit and `probability=True` adds ~5x (internal Platt CV);
# beyond ~1e5 rows it effectively never terminates and would hang a full-universe bake-off
# (review, compute aspect). We keep the nonlinear model but PRE-COMMIT a hard training-subsample
# cap so its cost is bounded and constant; scoring is still on the full fold.
SVM_TRAIN_CAP = 20_000


class _CappedSVC:
    """RBF SVC that trains on at most SVM_TRAIN_CAP rows (deterministic subsample), so the
    bake-off scales. Scores the full test fold. Probabilities via CalibratedClassifierCV (the
    replacement for the deprecated SVC(probability=True)). sklearn-compatible (fit/predict_proba)."""

    def __init__(self, cap: int = SVM_TRAIN_CAP, **kw):
        self.cap = cap
        self.kw = kw
        self._m = None
        self.n_train_ = 0

    def fit(self, X, y):
        from sklearn.calibration import CalibratedClassifierCV
        X = np.asarray(X, float); y = np.asarray(y)
        if len(y) > self.cap:
            idx = np.random.default_rng(0).choice(len(y), self.cap, replace=False)
            X, y = X[idx], y[idx]
        self.n_train_ = len(y)
        self._m = CalibratedClassifierCV(SVC(**self.kw), cv=3, ensemble=False).fit(X, y)
        return self

    def predict_proba(self, X):
        return self._m.predict_proba(X)


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
        "svm": lambda: _CappedSVC(class_weight=class_weight, random_state=seed),
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
    # Headline AUC is the n-weighted mean of PER-FOLD AUCs with a fold-dispersion band (review
    # M-7). A single AUC on probabilities concatenated across folds mixes scores from different
    # training sizes and is a biased estimator under drifting base rates; findings_hierarchy
    # should consume auc_fold_mean, not the pooled auc (kept for reference / diagnostics).
    if per_fold:
        fa = np.array([f["auc"] for f in per_fold]); fn = np.array([f["n"] for f in per_fold])
        auc_fold_mean = float(np.average(fa, weights=fn))
        auc_fold_std = float(np.sqrt(np.average((fa - auc_fold_mean) ** 2, weights=fn))) \
            if len(fa) > 1 else float("nan")
    else:
        auc_fold_mean = auc_fold_std = float("nan")
    return {
        "oos_proba": p, "oos_y": yv,
        "auc_fold_mean": auc_fold_mean, "auc_fold_std": auc_fold_std,
        "auc": float(roc_auc_score(yv, p)),          # pooled-CV AUC (diagnostic, not headline)
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
