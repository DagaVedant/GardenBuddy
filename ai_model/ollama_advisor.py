from __future__ import annotations

import json
import threading
import time
import urllib.request
import urllib.error
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_model.predictor import Prediction

OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.2:3b"
TIMEOUT_S    = 20
REFRESH_S    = 30

_CLASS_DESCRIPTIONS = {
    "thriving": "thriving — all conditions are excellent",
    "stable":   "stable — minor deviations but generally healthy",
    "stressed": "stressed — one or more conditions need attention",
    "critical": "critical — immediate intervention likely required",
}

_STRESSOR_DESCRIPTIONS = {
    "temp":     "temperature",
    "humidity": "relative humidity",
    "soil":     "soil moisture",
    "light":    "light level",
}


def _build_prompt(
    temp: float,
    humidity: float,
    soil: float,
    light: float,
    prediction: "Prediction",
) -> str:
    stressor = _STRESSOR_DESCRIPTIONS.get(prediction["primary_stressor"], prediction["primary_stressor"])
    health   = _CLASS_DESCRIPTIONS.get(prediction["health_class"], prediction["health_class"])
    conf_pct = round(prediction["confidence"] * 100)

    return (
        f"You are a concise plant care expert. "
        f"Current garden sensor readings: "
        f"temperature {temp}°F, humidity {humidity}%, "
        f"soil moisture {soil}%, light level {light}%. "
        f"A machine learning model classified the plant as {health} "
        f"(confidence {conf_pct}%) with {stressor} as the primary stressor. "
        f"Give exactly 2 sentences of specific, actionable advice for the gardener right now. "
        f"Do not repeat the sensor numbers. Do not use bullet points or headers. "
        f"Plain prose only."
    )


def _call_ollama(prompt: str) -> str | None:
    payload = json.dumps({
        "model":  OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            body = json.loads(resp.read())
            return body.get("response", "").strip()
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        return None


class OllamaAdvisor:
    def __init__(self):
        self._lock    = threading.Lock()
        self._advice  = None
        self._pending = threading.Event()
        self._latest_input: dict | None = None

        t = threading.Thread(target=self._loop, daemon=True)
        t.start()
        print(f"[ollama] advisor started (model={OLLAMA_MODEL}, refresh={REFRESH_S}s)")

    def update_input(
        self,
        temp: float,
        humidity: float,
        soil: float,
        light: float,
        prediction: "Prediction",
    ):
        with self._lock:
            self._latest_input = {
                "temp": temp, "humidity": humidity,
                "soil": soil, "light": light,
                "prediction": prediction,
            }
        self._pending.set()

    def get_advice(self) -> str | None:
        with self._lock:
            return self._advice

    def _loop(self):
        while True:
            self._pending.wait()
            self._pending.clear()

            with self._lock:
                inp = self._latest_input

            if inp and inp.get("prediction"):
                prompt = _build_prompt(
                    inp["temp"], inp["humidity"],
                    inp["soil"], inp["light"],
                    inp["prediction"],
                )
                result = _call_ollama(prompt)
                if result:
                    with self._lock:
                        self._advice = result
                    print(f"[ollama] new advice: {result[:80]}…")
                else:
                    print("[ollama] no response — will retry next cycle")

            self._pending.wait(timeout=REFRESH_S)
            self._pending.clear()


_advisor: OllamaAdvisor | None = None


def get_advisor() -> OllamaAdvisor:
    global _advisor
    if _advisor is None:
        _advisor = OllamaAdvisor()
    return _advisor
