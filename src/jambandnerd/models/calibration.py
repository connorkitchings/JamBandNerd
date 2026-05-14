"""Hand-rolled Platt scaling for calibrating raw model scores to probabilities."""

from __future__ import annotations

import numpy as np


class PlattScaler:
    """Sigmoid-based probability calibration: P(y=1|x) = sigmoid(a * x + b).

    Fit via gradient descent on binary labels, matching the same approach
    used by DealPredictor's logistic regression.
    """

    def __init__(
        self,
        learning_rate: float = 0.01,
        max_iter: int = 200,
        tol: float = 1e-6,
    ) -> None:
        self.learning_rate = learning_rate
        self.max_iter = max_iter
        self.tol = tol
        self.a: float = 1.0
        self.b: float = 0.0

    def fit(self, raw_scores: np.ndarray, labels: np.ndarray) -> PlattScaler:
        n = len(raw_scores)
        if n == 0:
            return self

        a = 0.0
        b = 0.0
        pos_rate = float(np.clip(labels.mean(), 1e-6, 1 - 1e-6))
        b = float(np.log(pos_rate / (1 - pos_rate)))

        for _ in range(self.max_iter):
            logits = a * raw_scores + b
            clipped = np.clip(logits, -30.0, 30.0)
            probs = 1.0 / (1.0 + np.exp(-clipped))
            errors = probs - labels

            grad_a = float(np.dot(errors, raw_scores)) / n
            grad_b = float(np.mean(errors))

            a -= self.learning_rate * grad_a
            b -= self.learning_rate * grad_b

            if abs(grad_a) < self.tol and abs(grad_b) < self.tol:
                break

        self.a = a
        self.b = b
        return self

    def transform(self, raw_scores: np.ndarray) -> np.ndarray:
        logits = self.a * raw_scores + self.b
        clipped = np.clip(logits, -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-clipped))

    def fit_transform(self, raw_scores: np.ndarray, labels: np.ndarray) -> np.ndarray:
        self.fit(raw_scores, labels)
        return self.transform(raw_scores)
