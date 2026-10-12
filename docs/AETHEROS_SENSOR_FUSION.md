# AetherOS Sensor Fusion

## Pipeline (§94)

```
Sensor
  ↓
Validation (stale/missing/corrupt/outlier/drifting/inconsistent)
  ↓
Normalization
  ↓
Timestamp alignment (clock model; negative latency flagged)
  ↓
Fusion
  ↓
World State
  ↓
Decision
```

## Fusion Math

### Inverse-Variance Weighting
```
w = confidence / (accuracy² + noise²)
fused = Σ(w × value) / Σ(w)
reported_uncertainty = √(Σ(1/w)) / N
```

### Conflict Handling
- Disagreement > tolerance → `STATE_UNCERTAIN` with all values
- Empty usable set → `UNAVAILABLE` (never fabricated, §203)
- Confidence-weighted mean with uncertainty propagation

## Calibration (§13)

### Profile
```python
CalibrationProfile:
    sensor_id: str
    version: str
    calibrated_at: float
    reference_standard: str
    error: float
    valid_until: float  # 0 = no expiry
```

### Gates
```python
calibration_ok(sensor_id, required=True) → bool
# required=True blocks execution if calibration missing/expired
```

## Sensor Quality (§12)

### Quality Flags
```
ok | stale | missing | corrupt | outlier | drifting | inconsistent
```

### Validation
```python
check_quality(reading, max_age_s=2.0, expected_range=None)
→ updates reading.quality
```

## Privacy (§95-97)

### Redaction
```python
_human_re = re.compile(r"(face|person|voice|license_plate)", re.I)
# Redacts before storage/transmission
```

### Zones
- Camera restricted zones
- Audio restricted zones
- Data retention limits
- Access control

## Fusion Engine

```python
class SensorFusionEngine:
    def __init__(self, disagreement_tol: float = 0.5):
        self.adapters = {}
        self.calibrations = {}
        self.disagreement_tol = disagreement_tol
    
    def attach(self, adapter: SensorAdapter)
    def calibrate(self, profile: CalibrationProfile)
    def calibration_ok(self, sensor_id: str, required: bool) -> bool
    def fuse_numeric(self, readings: List[SensorReading]) -> Dict:
        # Returns: FUSED | STATE_UNCERTAIN | UNAVAILABLE
```

### Quality Gates
```python
check_quality(r, max_age_s=2.0, expected_range=None)
→ reading with updated quality flag
```

## Adapters

### Base
```python
class SensorAdapter:
    def read(self) → SensorReading:
    def health() -> Dict
```

### Concrete
- `ReplaySensorAdapter` - Mode=REPLAY, from recorded data
- `LambdaSensorAdapter` - Wraps callable (tests, file readers)
- Hardware drivers implement `SensorAdapter` interface

## Network Time

### Clock Model
```python
class ClockModel:
    precision_ms = 1.0
    drift_ppm = 0.0
    
    def align(sensor_ts, received_ts):
        return {"latency_s": received_ts - sensor_ts}
```

### Ordering
```python
bus.ordered() → sorted by (at, seq)
# Reports gaps, duplicates, out-of-order
```

## Privacy (§95-97)

### Scrubbing
```python
_privacy_re = re.compile(r"(face|person|voice|license_plate)", re.I)
clean = {k: "[REDACTED]" if _human_re.search(k) else v for k,v in payload.items()}
```

### Zones
- Camera restricted zones
- Audio restricted zones
- Retention limits
- Access control

## Confidence Model (§84)

```
OBSERVED > INFERRED > PREDICTED > SIMULATED > REPLAYED > UNKNOWN > CONTRADICTED
```

Every event tagged with `EventConfidence` enum.

## Failure Modes

| Failure | Detection | Response |
|---------|-----------|----------|
| Stale | timestamp age > max_age | Mark stale, request refresh |
| Missing | No reading in window | Mark missing, use fallback |
| Corrupt | Schema/CRC failure | Mark corrupt, request resend |
| Outlier | Beyond expected range | Mark outlier, flag for review |
| Drifting | Gradual calibration shift | Flag drifting, schedule cal |
| Inconsistent | Cross-sensor disagreement | STATE_UNCERTAIN |

## Safety Integration

- Fusion disagreement → `STATE_UNCERTAIN` → planner reduces confidence
- Calibration expired + required → action blocked
- Sensor failure → `UNAVAILABLE` → planner uses alternatives
- Human in workspace → `COLLABORATIVE_ZONE` speed limits enforced