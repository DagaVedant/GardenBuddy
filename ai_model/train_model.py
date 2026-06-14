from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

import numpy as np

try:
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
except ImportError:
    sys.exit("PyTorch not installed.  Run: pip install torch")

try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    import joblib
except ImportError:
    sys.exit("scikit-learn not installed.  Run: pip install scikit-learn joblib")

from ai_model.scoring import calculate_score

MODEL_PATH  = Path(__file__).parent / "garden_lstm.pt"
SCALER_PATH = Path(__file__).parent / "garden_scaler.pkl"

SEQ_LEN      = 30
INPUT_SIZE   = 8
HIDDEN       = 256
N_LAYERS     = 3
N_CLASSES    = 4
DROPOUT      = 0.3
BATCH        = 128
LR           = 3e-4
WARMUP_STEPS = 200
AUX_WEIGHT   = 0.3

INFLUX_URL    = os.getenv("INFLUX_URL",    "http://localhost:8086")
INFLUX_TOKEN  = os.getenv("INFLUX_TOKEN")
INFLUX_ORG    = os.getenv("INFLUX_ORG",    "gardenbuddy")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "gardendata")
LOOKBACK_DAYS = 30

CLASS_NAMES      = ["thriving", "stable", "stressed", "critical"]
LABEL_THRESHOLDS = [80, 60, 40]


def score_to_class(score: float) -> int:
    if score >= LABEL_THRESHOLDS[0]: return 0
    if score >= LABEL_THRESHOLDS[1]: return 1
    if score >= LABEL_THRESHOLDS[2]: return 2
    return 3


class TemporalAttention(nn.Module):
    def __init__(self, hidden: int):
        super().__init__()
        self.attn = nn.Linear(hidden, 1)

    def forward(self, lstm_out: torch.Tensor) -> torch.Tensor:
        scores  = self.attn(lstm_out).squeeze(-1)
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        return (lstm_out * weights).sum(dim=1)


class GardenLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.input_proj = nn.Linear(INPUT_SIZE, HIDDEN)
        self.lstm = nn.LSTM(
            input_size=HIDDEN,
            hidden_size=HIDDEN,
            num_layers=N_LAYERS,
            batch_first=True,
            dropout=DROPOUT,
        )
        self.attention  = TemporalAttention(HIDDEN)
        self.layer_norm = nn.LayerNorm(HIDDEN)
        self.classifier = nn.Sequential(
            nn.Linear(HIDDEN, 128),
            nn.GELU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.GELU(),
            nn.Linear(64, N_CLASSES),
        )
        self.aux_head = nn.Sequential(
            nn.Linear(HIDDEN, 64),
            nn.GELU(),
            nn.Linear(64, 4),
        )

    def _encode(self, x: torch.Tensor) -> torch.Tensor:
        projected       = self.input_proj(x)
        lstm_out, _     = self.lstm(projected)
        context         = self.attention(lstm_out)
        return self.layer_norm(context)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self._encode(x))

    def forward_train(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        context = self._encode(x)
        return self.classifier(context), self.aux_head(context)


def fetch_from_influx() -> list[dict]:
    try:
        from influxdb_client import InfluxDBClient
    except ImportError:
        print("[train] influxdb-client not installed — skipping InfluxDB fetch.")
        return []
    if not INFLUX_TOKEN:
        print("[train] INFLUX_TOKEN not set — skipping InfluxDB fetch.")
        return []

    client    = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
    query_api = client.query_api()
    flux = f"""
    from(bucket: "{INFLUX_BUCKET}")
      |> range(start: -{LOOKBACK_DAYS}d)
      |> filter(fn: (r) => r._measurement == "garden_sensors")
      |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"])
    """
    rows = []
    try:
        for table in query_api.query(flux):
            for rec in table.records:
                rows.append({
                    "temp":     float(rec["temperature_f"]        or 70),
                    "humidity": float(rec["humidity"]              or 45),
                    "soil":     float(rec["soil_moisture_percent"] or 50),
                    "light":    float(rec["light_percent"]         or 40),
                })
        print(f"[train] fetched {len(rows)} rows from InfluxDB.")
    except Exception as exc:
        print(f"[train] InfluxDB query failed: {exc}")
    client.close()
    return rows


_CLASS_STARTS = [
    {"temp": (66, 78), "humidity": (38, 58), "soil": (65, 88), "light": (65, 88)},
    {"temp": (58, 84), "humidity": (28, 70), "soil": (42, 65), "light": (42, 72)},
    {"temp": (52, 88), "humidity": (22, 82), "soil": (22, 42), "light": (22, 55)},
    {"temp": (45, 55), "humidity": (10, 20), "soil": (5,  18), "light": (0,  18)},
]

def generate_synthetic_sequences(n: int = 20000) -> list[list[dict]]:
    rng = np.random.default_rng(42)
    sequences = []
    per_class = n // N_CLASSES

    for ranges in _CLASS_STARTS:
        for _ in range(per_class):
            t = float(rng.uniform(*ranges["temp"]))
            h = float(rng.uniform(*ranges["humidity"]))
            s = float(rng.uniform(*ranges["soil"]))
            l = float(rng.uniform(*ranges["light"]))

            seq = []
            for _ in range(SEQ_LEN + 1):
                seq.append({"temp": round(t, 2), "humidity": round(h, 2),
                            "soil": round(s, 2), "light":    round(l, 2)})
                t = float(np.clip(t + rng.normal(0, 0.4), 45, 100))
                h = float(np.clip(h + rng.normal(0, 0.8), 10,  95))
                s = float(np.clip(s + rng.normal(0, 0.5),  5, 100))
                l = float(np.clip(l + rng.normal(0, 1.0),  0, 100))

            sequences.append(seq)

    rng.shuffle(sequences)
    return sequences


def rows_to_sequences(rows: list[dict]) -> list[list[dict]]:
    seqs = []
    for i in range(len(rows) - SEQ_LEN):
        seqs.append(rows[i : i + SEQ_LEN + 1])
    return seqs


def seq_to_features(seq: list[dict]) -> tuple[np.ndarray, np.ndarray, int]:
    raw = np.array([[r["temp"], r["humidity"], r["soil"], r["light"]] for r in seq])

    deltas        = np.zeros_like(raw)
    deltas[1:]    = raw[1:] - raw[:-1]
    features      = np.concatenate([raw, deltas], axis=1)

    x_steps  = features[:SEQ_LEN]
    next_raw = raw[SEQ_LEN]

    last     = seq[SEQ_LEN - 1]
    score    = calculate_score(last["temp"], last["humidity"], last["soil"], last["light"])
    label    = score_to_class(score)

    return x_steps, next_raw, label


def build_tensors(
    sequences: list[list[dict]],
    scaler: StandardScaler | None = None,
    fit_scaler: bool = False,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, StandardScaler]:

    all_X, all_next, all_y = [], [], []
    for seq in sequences:
        x_steps, next_raw, label = seq_to_features(seq)
        all_X.append(x_steps)
        all_next.append(next_raw)
        all_y.append(label)

    arr  = np.array(all_X, dtype=float)
    flat = arr.reshape(-1, INPUT_SIZE)

    if scaler is None:
        scaler = StandardScaler()
    if fit_scaler:
        scaler.fit(flat)

    scaled = scaler.transform(flat).reshape(arr.shape)

    X      = torch.tensor(scaled,                              dtype=torch.float32)
    y_next = torch.tensor(np.array(all_next, dtype=float),    dtype=torch.float32)
    y_cls  = torch.tensor(np.array(all_y,   dtype=np.int64),  dtype=torch.long)
    return X, y_cls, y_next, scaler


class WarmupCosineScheduler(torch.optim.lr_scheduler.LambdaLR):
    def __init__(self, optimizer, warmup_steps: int, total_steps: int):
        def lr_lambda(step: int) -> float:
            if step < warmup_steps:
                return step / max(1, warmup_steps)
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            return 0.5 * (1.0 + np.cos(np.pi * progress))
        super().__init__(optimizer, lr_lambda)


def train(epochs: int = 100):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device: {device}")

    print("[train] collecting data …")
    real_rows  = fetch_from_influx()
    real_seqs  = rows_to_sequences(real_rows)
    synth_seqs = generate_synthetic_sequences(20000)

    all_seqs = real_seqs + synth_seqs
    print(f"[train] total sequences: {len(all_seqs)} ({len(real_seqs)} real, {len(synth_seqs)} synthetic)")

    train_seqs, val_seqs = train_test_split(all_seqs, test_size=0.15, random_state=42)

    X_train, y_cls_train, y_next_train, scaler = build_tensors(train_seqs, fit_scaler=True)
    X_val,   y_cls_val,   y_next_val,   _      = build_tensors(val_seqs,   scaler=scaler)

    unique, counts = np.unique(y_cls_train.numpy(), return_counts=True)
    for cls, cnt in zip(unique, counts):
        print(f"  class {cls} ({CLASS_NAMES[cls]}): {cnt} train sequences")

    class_counts  = np.bincount(y_cls_train.numpy(), minlength=N_CLASSES).astype(float)
    sample_weights = (1.0 / class_counts)[y_cls_train.numpy()]
    sampler   = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
    train_dl  = DataLoader(TensorDataset(X_train, y_cls_train, y_next_train), batch_size=BATCH, sampler=sampler)
    val_dl   = DataLoader(TensorDataset(X_val,   y_cls_val,   y_next_val),   batch_size=BATCH)

    model       = GardenLSTM().to(device)
    optimizer   = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-3)
    total_steps = epochs * len(train_dl)
    scheduler   = WarmupCosineScheduler(optimizer, WARMUP_STEPS, total_steps)
    cls_loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
    aux_loss_fn = nn.MSELoss()

    best_val_acc = 0.0
    best_state   = None

    print(f"\n[train] training for {epochs} epochs …")
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        for xb, yb_cls, yb_next in train_dl:
            xb, yb_cls, yb_next = xb.to(device), yb_cls.to(device), yb_next.to(device)
            optimizer.zero_grad()
            cls_logits, next_pred = model.forward_train(xb)
            loss = cls_loss_fn(cls_logits, yb_cls) + AUX_WEIGHT * aux_loss_fn(next_pred, yb_next)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            total_loss += loss.item()

        model.eval()
        correct = total = 0
        with torch.no_grad():
            for xb, yb_cls, _ in val_dl:
                xb, yb_cls = xb.to(device), yb_cls.to(device)
                preds   = model(xb).argmax(dim=1)
                correct += (preds == yb_cls).sum().item()
                total   += yb_cls.size(0)
        val_acc = correct / total

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            best_state   = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        if epoch % 10 == 0 or epoch == 1:
            print(f"  epoch {epoch:3d}/{epochs}  loss={total_loss/len(train_dl):.4f}  val_acc={val_acc:.3f}")

    print(f"\n[train] best val accuracy: {best_val_acc:.3f}")

    model.load_state_dict(best_state)
    model.eval().cpu()
    scripted = torch.jit.script(model)
    scripted.save(str(MODEL_PATH))
    joblib.dump(scaler, SCALER_PATH)

    print(f"[train] model  saved → {MODEL_PATH}")
    print(f"[train] scaler saved → {SCALER_PATH}")


if __name__ == "__main__":
    train()
