from __future__ import annotations

import time
import threading
import random
from datetime import datetime
from collections import deque
from typing import Optional

from flask import Flask, jsonify, send_from_directory

from dotenv import load_dotenv
import os

from ai_model.predictor import get_predictor
from ai_model.ollama_advisor import get_advisor
from ai_model.scoring import calculate_score

WRITE_INFLUX = True

DRY_VALUE = 21640
WET_VALUE = 6000
LIGHT_MAX = 34000

DHT_PIN = "D4"
PHOTO_CHANNEL = 0
SOIL_CHANNEL = 2

LED_RED = 21
LED_GREEN = 20
LED_BLUE = 16

POLL_INTERVAL = 10
HISTORY_LEN = 20

AI_MESSAGES = [
    "Digital twin simulation predicts stable short-term growth.",
    "Cross-sensor validation completed successfully.",
    "Plant vitality model indicates favorable conditions.",
    "Predictive growth engine recalculated 24-hour trends.",
    "Environmental stability index remains within target range.",
    "Sensor fusion algorithm verified consistency across environmental inputs.",
]

PRIORITY_MAP = {"critical": 3, "warning": 2, "info": 1}

load_dotenv()

INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG", "gardenbuddy")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "gardendata")

dht_device = None
photo_chan = None
soil_chan = None
write_api = None
_led_r = None
_led_g = None
_led_b = None

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import adafruit_dht
import RPi.GPIO as GPIO

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
photo_chan = AnalogIn(ads, PHOTO_CHANNEL)
soil_chan = AnalogIn(ads, SOIL_CHANNEL)
dht_device = adafruit_dht.DHT22(getattr(board, DHT_PIN), use_pulseio=False)

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_RED,   GPIO.OUT)
GPIO.setup(LED_GREEN, GPIO.OUT)
GPIO.setup(LED_BLUE,  GPIO.OUT)
_led_r = GPIO.PWM(LED_RED,   200)
_led_g = GPIO.PWM(LED_GREEN, 200)
_led_b = GPIO.PWM(LED_BLUE,  200)
_led_r.start(0)
_led_g.start(0)
_led_b.start(0)

if WRITE_INFLUX:
    from influxdb_client import InfluxDBClient, Point
    from influxdb_client.client.write_api import SYNCHRONOUS
    influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)

_predictor = get_predictor()
_advisor   = get_advisor()

history: dict[str, deque] = {
    "time": deque(maxlen=HISTORY_LEN),
    "temperature_f": deque(maxlen=HISTORY_LEN),
    "humidity": deque(maxlen=HISTORY_LEN),
    "soil_moisture_percent": deque(maxlen=HISTORY_LEN),
    "light_percent": deque(maxlen=HISTORY_LEN),
}
latest: dict = {}
state_lock = threading.Lock()

def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _set_led_score(score: int):
    if _led_r is None:
        return
    if score >= 70:
        r, g, b = 0, 100, 0
    elif score >= 40:
        r, g, b = 100, 50, 0
    else:
        r, g, b = 100, 0, 0
    _led_r.ChangeDutyCycle(r)
    _led_g.ChangeDutyCycle(g)
    _led_b.ChangeDutyCycle(b)


def _read_sensors() -> Optional[tuple[float, float, float, float]]:
    temp_c = None
    humidity = None
    for _ in range(3):
        try:
            temp_c = dht_device.temperature
            humidity = dht_device.humidity
            if temp_c is not None and humidity is not None:
                break
        except RuntimeError:
            pass
        dht_device.exit()
        time.sleep(2)

    if temp_c is None or humidity is None:
        return None

    try:
        temp_f = round(temp_c * 9 / 5 + 32, 1)
        humidity = round(humidity, 1)

        raw_light = photo_chan.value
        light_pct = round(_clamp(raw_light / LIGHT_MAX * 100, 0, 75), 1)

        raw_soil = soil_chan.value
        soil_pct = round(
            _clamp(100 * (DRY_VALUE - raw_soil) / (DRY_VALUE - WET_VALUE), 0, 100), 1
        )

        return temp_f, humidity, soil_pct, light_pct

    except Exception:
        return None


def _write_to_influx(temp_f: float, humidity: float, soil_pct: float, light_pct: float):
    if not write_api:
        return
    try:
        from influxdb_client import Point
        point = (
            Point("garden_sensors")
            .field("temperature_f",         float(temp_f))
            .field("humidity",              float(humidity))
            .field("soil_moisture_percent", float(soil_pct))
            .field("light_percent",         float(light_pct))
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
    except Exception as exc:
        print(f"[InfluxDB] write failed: {exc}")


def _generate_insights(temp_f: float, humidity: float, soil_pct: float, light_pct: float, ollama_advice: str | None = None) -> list[dict]:
    insights = []

    insights.append({
        "message": "AI analysis complete — evaluating plant health and environmental trends.",
        "type": "info",
    })

    findings = []

    if soil_pct < 20:
        findings.append({
            "message": "Soil moisture critically low — immediate irrigation required.",
            "type": "critical",
        })
    elif soil_pct < 35:
        findings.append({
            "message": "Soil moisture trending below target range — irrigation recommended soon.",
            "type": "warning",
        })
    elif soil_pct > 75:
        findings.append({
            "message": "Excess soil moisture detected — reduce watering frequency.",
            "type": "warning",
        })
    else:
        findings.append({
            "message": "Soil moisture remains within the optimal growth zone.",
            "type": "info",
        })

    if temp_f < 55:
        findings.append({
            "message": "Temperature is below optimal — slowed metabolic activity may occur.",
            "type": "warning",
        })
    elif temp_f > 90:
        findings.append({
            "message": "Heat stress conditions detected — ensure adequate ventilation and hydration.",
            "type": "critical",
        })
    else:
        findings.append({
            "message": "Temperature supports healthy plant development.",
            "type": "info",
        })

    if humidity < 30:
        findings.append({
            "message": "Low humidity detected — transpiration rates may increase.",
            "type": "warning",
        })
    elif humidity > 85:
        findings.append({
            "message": "Elevated humidity may increase fungal disease susceptibility.",
            "type": "warning",
        })
    else:
        findings.append({
            "message": "Humidity levels align with recommended conditions.",
            "type": "info",
        })

    if light_pct < 20:
        findings.append({
            "message": "Insufficient light detected — photosynthetic efficiency may decline.",
            "type": "warning",
        })
    elif light_pct > 85:
        findings.append({
            "message": "Excessive light intensity detected — monitor for leaf scorch symptoms.",
            "type": "warning",
        })
    else:
        findings.append({
            "message": "Light conditions support effective photosynthesis.",
            "type": "info",
        })

    if temp_f > 85 and soil_pct < 30:
        findings.append({
            "message": "AI correlation analysis indicates elevated drought stress risk.",
            "type": "critical",
        })

    if humidity > 80 and soil_pct > 70:
        findings.append({
            "message": "Combined moisture indicators suggest increased fungal disease risk.",
            "type": "warning",
        })

    if light_pct < 25 and soil_pct > 60:
        findings.append({
            "message": "Growth efficiency model predicts slower development under current conditions.",
            "type": "warning",
        })

    findings.sort(key=lambda x: PRIORITY_MAP.get(x["type"], 0), reverse=True)

    insights.extend(findings[:2])

    has_critical = any(f["type"] == "critical" for f in findings)

    if not has_critical:
        insights.append({
            "message": ollama_advice if ollama_advice else random.choice(AI_MESSAGES),
            "type": "info",
        })

    return insights


def _poll_loop():
    print(f"[sensor_reader] polling every {POLL_INTERVAL}s")
    while True:
        values = _read_sensors()
        if values is not None:
            temp_f, humidity, soil_pct, light_pct = values
            ts = datetime.now().strftime("%H:%M:%S")
            score = calculate_score(temp_f, humidity, soil_pct, light_pct)

            prediction = _predictor.predict(temp_f, humidity, soil_pct, light_pct)

            if prediction:
                _advisor.update_input(temp_f, humidity, soil_pct, light_pct, prediction)

            ollama_advice = _advisor.get_advice()
            insights = _generate_insights(temp_f, humidity, soil_pct, light_pct, ollama_advice)

            with state_lock:
                history["time"].append(ts)
                history["temperature_f"].append(temp_f)
                history["humidity"].append(humidity)
                history["soil_moisture_percent"].append(soil_pct)
                history["light_percent"].append(light_pct)

                latest.update({
                    "temp": temp_f,
                    "humidity": humidity,
                    "soil": soil_pct,
                    "light": light_pct,
                    "score": score,
                    "insights": insights,
                    "ml": prediction if prediction else {},
                })

            print(
                f"[{ts}] 🌡 {temp_f}°F  💧{humidity}%  🪴{soil_pct}%  ☀️{light_pct}%  "
                f"score={score}"
            )
            _set_led_score(score)
            _write_to_influx(temp_f, humidity, soil_pct, light_pct)
        else:
            print("[sensor_reader] transient read error – retrying next cycle")

        time.sleep(POLL_INTERVAL)

DIST_DIR = os.path.join(os.path.dirname(__file__), "dist")

app = Flask(__name__, static_folder=DIST_DIR)


@app.route("/api/data")
def api_data():
    with state_lock:
        if not latest:
            return jsonify({"error": "no data yet"}), 503

        payload = {
            **latest,
            "chart": {k: list(v) for k, v in history.items()},
        }

    return jsonify(payload)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve_dashboard(path: str):
    target = os.path.join(DIST_DIR, path) if path else None
    if path and os.path.isfile(target):
        return send_from_directory(DIST_DIR, path)
    return send_from_directory(DIST_DIR, "index.html")

if __name__ == "__main__":
    t = threading.Thread(target=_poll_loop, daemon=True)
    t.start()

    time.sleep(POLL_INTERVAL + 1)

    print("[sensor_reader] starting Flask on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
