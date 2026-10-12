# AetherOS Hardware Adapters

## Overview

Hardware adapters provide a uniform interface between AetherOS and physical devices. The core AetherOS logic never depends on specific vendors, protocols, or hardware implementations.

## Adapter Interface

```python
class PhysicalAdapter:
    """Base adapter interface (§236-242)."""
    
    def discover(self) -> List[str]:
        """Return list of discoverable device IDs."""
    
    def connect(self, device_id: str) -> Dict[str, Any]:
        """Establish connection to device."""
    
    def capabilities(self, device_id: str) -> List[str]:
        """Return list of capability strings."""
    
    def state(self, device_id: str) -> Dict[str, Any]:
        """Get current device state."""
    
    def observe(self, device_id: str) -> Dict[str, Any]:
        """Get sensor observation."""
    
    def plan(self, *args, **kwargs) -> Dict[str, Any]:
        """Generate execution plan."""
    
    def execute(self, action: PhysicalAction) -> Dict[str, Any]:
        """Execute physical action."""
    
    def stop(self, device_id: str) -> Dict[str, Any]:
        """Emergency stop."""
    
    def health(self, device_id: str) -> Dict[str, Any]:
        """Device health status."""
    
    def disconnect(self, device_id: str) -> None:
        """Clean disconnect."""
```

## Adapter Types

### SensorAdapter
```python
class SensorAdapter:
    def read(self) -> SensorReading:
        """Single reading with quality metadata."""
    def stream(self) -> AsyncIterator[SensorReading]:
        """Continuous stream."""
    def calibrate(self, profile: CalibrationProfile) -> bool:
    def health(self) -> Dict[str, Any]:
```

### ActuatorAdapter
```python
class ActuatorAdapter:
    def capabilities(self) -> List[str]:
    def execute(self, action: PhysicalAction) -> Dict[str, Any]:
    def stop(self) -> Dict[str, Any]:
    def state(self) -> Dict[str, Any]:
```

### RobotAdapter
```python
class RobotAdapter:
    def getState(self) -> Dict[str, Any]:
    def getCapabilities(self) -> List[str]:
    def planMotion(self, target: Pose) -> Trajectory:
    def executeMotion(self, trajectory: Trajectory) -> MotionResult:
    def stop(self) -> Dict[str, Any]:
    def home(self) -> Dict[str, Any]:
    def calibrate(self) -> CalibrationResult:
```

### LabAdapter
```python
class LabAdapter:
    def getCapabilities(self) -> List[str]:
    def validateProtocol(self, proto: LabProtocol) -> ValidationResult:
    def simulate(self, proto: LabProtocol) -> SimulationResult:
    def execute(self, protocol: LabProtocol) -> RunResult:
    def measure(self, step: Step) -> MeasurementResult:
    def stop(self) -> Dict[str, Any]:
```

### SimulatorAdapter
```python
class SimulatorAdapter:
    def reset(self) -> State:
    def observe(self) -> Observation:
    def step(self, action: Action) -> Tuple[State, Reward, Done, Info]:
    def simulate(self, policy: Policy) -> Trajectory:
    def compare(self, other: SimulatorAdapter) -> ComparisonReport:
```

## Pairing & Trust (§47-48)

```
discover → authenticate → verify identity → authorize capabilities → register
```

- **Paired ≠ Trusted**: New devices are `UNTRUSTED_DEVICE` + `OBSERVE_ONLY`
- **Attestation**: Requires firmware + identity verification
- **Authorization**: Explicit capability grants per device
- **Revocation**: Immediate permission removal
- **Human Lock**: `LOCKED_BY_HUMAN` prevents AI control

## Device Capabilities

### Standard Capabilities (§7)
```
READ_TEMPERATURE, READ_POSITION, CAPTURE_IMAGE,
MOVE, ROTATE, GRIP, RELEASE, PUSH, PULL,
PRESS, PICK, PLACE, WELD, PRINT, DRILL,
DISPENSE, HEAT, COOL, MIX, MEASURE
```

### Risk Levels
| Capability | Risk | Required Permission |
|------------|------|---------------------|
| READ_TEMPERATURE | LOW | OBSERVE |
| CAPTURE_IMAGE | LOW | OBSERVE |
| MOVE | MEDIUM | CONTROLLED_ACTION |
| GRIP | HIGH | CONTROLLED_ACTION |
| WELD | HIGH | PHYSICAL_EXPERIMENT |
| DISPENSE | HIGH | PHYSICAL_EXPERIMENT |

## Pairing Flow

```
1. DISCOVER
   ├── USB/Bluetooth/mDNS/vendor API
   ├── Device advertises capabilities
   └── User reviews device info

2. PAIR
   ├── Credential exchange (OS keychain)
   ├── Identity verification
   └── Device registered as UNTRUSTED_DEVICE

3. ATTEST
   ├── Firmware hash verification
   ├── Identity certificate validation
   └── TRUSTED if both pass

4. AUTHORIZE
   ├── Explicit capability grants
   ├── Scope definition (resource patterns)
   └── Audit log entry

5. OPERATE
   ├── Capability token per action
   ├── Continuous health monitoring
   └── Revocation on anomaly
```

## Simulated Adapters (Development)

When hardware unavailable:

```python
SimulatedRobotAdapter:
    - Kinematic simulator (differential drive + 2-link arm)
    - SIMULATION mode labeled
    - MOVE, ROTATE, READ_POSITION
    - No hardware side effects

MockSensorAdapter:
    - Replay recorded sensor data
    - REPLAY mode labeled
    - Configurable noise/drift

LambdaSensorAdapter:
    - Wraps any callable
    - For testing, CI, replay
```

## Vendor Adapters (Future)

| Vendor | Type | Status |
|--------|------|--------|
| Intel RealSense | Camera/Depth | Planned |
| Azure Kinect | Camera/Depth | Planned |
| Leap Motion | Hand Tracking | Planned |
| Meta Quest | XR Headset | Planned |
| Apple Vision Pro | XR Headset | Planned |
| Universal Robots | Robot Arm | Planned |
| Franka Emika | Robot Arm | Planned |
| Boston Dynamics | Quadruped | Planned |
| ROS2 Bridge | Robot Middleware | Planned |

## Security

- Private keys never leave custody layer
- CredentialBroker holds secrets, issues scoped tokens
- mTLS for device communication
- Command HMAC with nonce/replay protection
- Emergency stop bypasses all layers

## Testing

```bash
# Run adapter tests
pytest tests/hardware/test_adapters.py -v

# Test with simulated hardware
pytest tests/hardware/ -k "simulated"

# Test with real hardware (requires hardware)
pytest tests/hardware/ -k "hardware" --hardware
```