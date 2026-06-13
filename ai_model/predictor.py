from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TypedDict

SEQ_LEN    = 30
INPUT_SIZE = 8   # 4 raw + 4 deltas — must match train_model.py

MODEL_PATH  = Path(__file__).parent / "garden_lstm.pt"
SCALER_PATH = Path(__file__).parent / "garden_scaler.pkl"

CLASS_NAMES = ["thriving", "stable", "stressed", "critical"]


class Prediction(TypedDict):
    health_class:     str
    health_class_id:  int
    primary_stressor: str
    stress_vector:    list[float]
    confidence:       float


class Predictor:
    def __init__(self):
        self._model   = None
        self._scaler  = None
        self._ready   = False
        self._window: deque[list[float]] = deque(maxlen=SEQ_LEN)
        self._load()

    def _load(self):
        try:
            import torch
            import joblib
        except ImportError:
            print("[predictor] torch or joblib not installed — model disabled.")
            return

        if not MODEL_PATH.exists() or not SCALER_PATH.exists():
            print("[predictor] model files not found — run: python -m ai_model.train_model")
            return

        try:
            self._model  = torch.jit.load(str(MODEL_PATH), map_location="cpu")
            self._model.eval()
            self._scaler = joblib.load(SCALER_PATH)
            self._ready  = True
            print(f"[predictor] model loaded (warming up — needs {SEQ_LEN} readings / ~{SEQ_LEN * 10 // 60} min)")
        except Exception as exc:
            print(f"[predictor] failed to load model: {exc}")

    @property
    def ready(self) -> bool:
        return self._ready

    @property
    def warmed_up(self) -> bool:
        return self._ready and len(self._window) == SEQ_LEN

    def predict(
        self,
        temp: float,
        humidity: float,
        soil: float,
        light: float,
    ) -> Prediction | None:
        if not self._ready:
            return None

        self._window.append([temp, humidity, soil, light])

        if not self.warmed_up:
            remaining = SEQ_LEN - len(self._window)
            if remaining % 5 == 0:
                print(f"[predictor] warming up — {remaining} more readings needed")
            return None

        import torch
        import numpy as np

        raw    = np.array(list(self._window), dtype=float)   # (SEQ_LEN, 4)
        deltas = np.zeros_like(raw)
        deltas[1:] = raw[1:] - raw[:-1]
        features = np.concatenate([raw, deltas], axis=1)     # (SEQ_LEN, 8)

        scaled = self._scaler.transform(features)
        x      = torch.tensor(scaled, dtype=torch.float32).unsqueeze(0)

        with torch.no_grad():
            logits = self._model(x)
            proba  = torch.softmax(logits, dim=1)[0]

        class_id   = int(proba.argmax().item())
        confidence = float(proba[class_id].item())

        deviations = {
            "temp":     abs(temp     - 72) / 27,
            "humidity": abs(humidity - 45) / 50,
            "soil":     abs(soil     - 75) / 70,
            "light":    abs(light    - 80) / 80,
        }
        primary_stressor = max(deviations, key=deviations.get)

        return Prediction(
            health_class=CLASS_NAMES[class_id],
            health_class_id=class_id,
            primary_stressor=primary_stressor,
            stress_vector=[
                round(deviations["temp"],     3),
                round(deviations["humidity"], 3),
                round(deviations["soil"],     3),
                round(deviations["light"],    3),
            ],
            confidence=round(confidence, 3),
        )


_predictor: Predictor | None = None


def get_predictor() -> Predictor:
    global _predictor
    if _predictor is None:
        _predictor = Predictor()
    return _predictor
