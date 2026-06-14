import subprocess, sys, os, math
from pathlib import Path

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "scikit-learn", "joblib"], check=True)

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset, WeightedRandomSampler
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

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
EPOCHS       = 100

CLASS_NAMES      = ["thriving", "stable", "stressed", "critical"]
LABEL_THRESHOLDS = [80, 60, 40]

MODEL_PATH  = Path("/content/garden_lstm.pt")
SCALER_PATH = Path("/content/garden_scaler.pkl")


def calculate_score(temp, humidity, soil, light):
    score = 100.0
    def stress(value, ideal, scale, power):
        return (abs(value - ideal) / scale) ** power
    score -= stress(temp,     72, 18, 1.4) * 22
    score -= stress(humidity, 45, 25, 1.2) * 18
    score -= stress(soil,     75, 20, 1.5) * 35
    score -= stress(light,    80, 30, 1.1) * 15
    if temp > 85 and soil < 30:        score -= 12
    if soil > 75 and humidity > 80:    score -= 10
    if light < 20 and humidity > 70:   score -= 8
    if temp < 45 or temp > 95:         score -= 10
    if humidity < 15 or humidity > 90: score -= 8
    if soil < 10:                      score -= 12
    if light < 10:                     score -= 10
    return max(0, min(100, round(score)))


def score_to_class(score):
    if score >= LABEL_THRESHOLDS[0]: return 0
    if score >= LABEL_THRESHOLDS[1]: return 1
    if score >= LABEL_THRESHOLDS[2]: return 2
    return 3


class TemporalAttention(nn.Module):
    def __init__(self, hidden):
        super().__init__()
        self.attn = nn.Linear(hidden, 1)

    def forward(self, lstm_out):
        scores  = self.attn(lstm_out).squeeze(-1)
        weights = torch.softmax(scores, dim=1).unsqueeze(-1)
        return (lstm_out * weights).sum(dim=1)


class GardenLSTM(nn.Module):
    def __init__(self):
        super().__init__()
        self.input_proj = nn.Linear(INPUT_SIZE, HIDDEN)
        self.lstm = nn.LSTM(
            input_size=HIDDEN, hidden_size=HIDDEN,
            num_layers=N_LAYERS, batch_first=True, dropout=DROPOUT,
        )
        self.attention  = TemporalAttention(HIDDEN)
        self.layer_norm = nn.LayerNorm(HIDDEN)
        self.classifier = nn.Sequential(
            nn.Linear(HIDDEN, 128), nn.GELU(), nn.Dropout(0.2),
            nn.Linear(128, 64),    nn.GELU(),
            nn.Linear(64, N_CLASSES),
        )
        self.aux_head = nn.Sequential(
            nn.Linear(HIDDEN, 64), nn.GELU(),
            nn.Linear(64, 4),
        )

    def _encode(self, x):
        projected   = self.input_proj(x)
        lstm_out, _ = self.lstm(projected)
        context     = self.attention(lstm_out)
        return self.layer_norm(context)

    def forward(self, x):
        return self.classifier(self._encode(x))

    def forward_train(self, x):
        context = self._encode(x)
        return self.classifier(context), self.aux_head(context)


_CLASS_STARTS = [
    {"temp": (66, 78), "humidity": (38, 58), "soil": (65, 88), "light": (65, 88)},
    {"temp": (58, 84), "humidity": (28, 70), "soil": (42, 65), "light": (42, 72)},
    {"temp": (52, 88), "humidity": (22, 82), "soil": (22, 42), "light": (22, 55)},
    {"temp": (45, 55), "humidity": (10, 20), "soil": (5,  18), "light": (0,  18)},
]


def generate_synthetic_sequences(n=20000):
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
                seq.append({"temp": round(t,2), "humidity": round(h,2),
                            "soil": round(s,2), "light":    round(l,2)})
                t = float(np.clip(t + rng.normal(0, 0.4), 45, 100))
                h = float(np.clip(h + rng.normal(0, 0.8), 10,  95))
                s = float(np.clip(s + rng.normal(0, 0.5),  5, 100))
                l = float(np.clip(l + rng.normal(0, 1.0),  0, 100))
            sequences.append(seq)
    rng.shuffle(sequences)
    return sequences


def seq_to_features(seq):
    raw        = np.array([[r["temp"], r["humidity"], r["soil"], r["light"]] for r in seq])
    deltas     = np.zeros_like(raw)
    deltas[1:] = raw[1:] - raw[:-1]
    features   = np.concatenate([raw, deltas], axis=1)
    last       = seq[SEQ_LEN - 1]
    label      = score_to_class(calculate_score(last["temp"], last["humidity"], last["soil"], last["light"]))
    return features[:SEQ_LEN], raw[SEQ_LEN], label


def build_tensors(sequences, scaler=None, fit_scaler=False):
    all_X, all_next, all_y = [], [], []
    for seq in sequences:
        x, nxt, lbl = seq_to_features(seq)
        all_X.append(x); all_next.append(nxt); all_y.append(lbl)
    arr  = np.array(all_X, dtype=float)
    flat = arr.reshape(-1, INPUT_SIZE)
    if scaler is None: scaler = StandardScaler()
    if fit_scaler:     scaler.fit(flat)
    scaled = scaler.transform(flat).reshape(arr.shape)
    X      = torch.tensor(scaled,                           dtype=torch.float32)
    y_next = torch.tensor(np.array(all_next, dtype=float), dtype=torch.float32)
    y_cls  = torch.tensor(np.array(all_y, dtype=np.int64), dtype=torch.long)
    return X, y_cls, y_next, scaler


class WarmupCosineScheduler(torch.optim.lr_scheduler.LambdaLR):
    def __init__(self, optimizer, warmup_steps, total_steps):
        def lr_lambda(step):
            if step < warmup_steps:
                return step / max(1, warmup_steps)
            progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
            return 0.5 * (1.0 + math.cos(math.pi * progress))
        super().__init__(optimizer, lr_lambda)


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"device: {device}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")

print("generating data …")
sequences = generate_synthetic_sequences(20000)
train_seqs, val_seqs = train_test_split(sequences, test_size=0.15, random_state=42)

X_train, y_cls_train, y_next_train, scaler = build_tensors(train_seqs, fit_scaler=True)
X_val,   y_cls_val,   y_next_val,   _      = build_tensors(val_seqs,   scaler=scaler)

unique, counts = np.unique(y_cls_train.numpy(), return_counts=True)
for cls, cnt in zip(unique, counts):
    print(f"  class {cls} ({CLASS_NAMES[cls]}): {cnt}")

class_counts   = np.bincount(y_cls_train.numpy(), minlength=N_CLASSES).astype(float)
sample_weights = (1.0 / class_counts)[y_cls_train.numpy()]
sampler  = WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)
train_dl = DataLoader(TensorDataset(X_train, y_cls_train, y_next_train), batch_size=BATCH, sampler=sampler)
val_dl   = DataLoader(TensorDataset(X_val,   y_cls_val,   y_next_val),   batch_size=BATCH)

model       = GardenLSTM().to(device)
optimizer   = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-3)
total_steps = EPOCHS * len(train_dl)
scheduler   = WarmupCosineScheduler(optimizer, WARMUP_STEPS, total_steps)
cls_loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)
aux_loss_fn = nn.MSELoss()

best_val_acc = 0.0
best_state   = None

print(f"\ntraining for {EPOCHS} epochs …")
for epoch in range(1, EPOCHS + 1):
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
            preds    = model(xb).argmax(dim=1)
            correct += (preds == yb_cls).sum().item()
            total   += yb_cls.size(0)
    val_acc = correct / total

    if val_acc > best_val_acc:
        best_val_acc = val_acc
        best_state   = {k: v.cpu().clone() for k, v in model.state_dict().items()}

    if epoch % 10 == 0 or epoch == 1:
        print(f"  epoch {epoch:3d}/{EPOCHS}  loss={total_loss/len(train_dl):.4f}  val_acc={val_acc:.3f}")

print(f"\nbest val accuracy: {best_val_acc:.3f}")

model.load_state_dict(best_state)
model.eval().cpu()
scripted = torch.jit.script(model)
scripted.save(str(MODEL_PATH))
joblib.dump(scaler, SCALER_PATH)
print(f"saved → {MODEL_PATH}")
print(f"saved → {SCALER_PATH}")

from google.colab import files
files.download(str(MODEL_PATH))
files.download(str(SCALER_PATH))
