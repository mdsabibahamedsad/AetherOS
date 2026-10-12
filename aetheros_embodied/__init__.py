"""Master 54: Embodied Intelligence 1.0.

PLEDGE: a model of the world is not the world. Every physical-world
event carries an execution mode: HARDWARE_UNAVAILABLE | SIMULATION |
REPLAY | LIVE_HARDWARE. Nothing is invented: no sensor readings, no
movement, no measurements without a real source behind them.
"""

from .models import *  # noqa
from .engine import EmbodiedIntelligenceEngine, EmbodiedDenied  # noqa
from .registries import (PhysicalDeviceRegistry, RobotRegistry,  # noqa
                         ActuatorRegistry, CapabilityRegistry,
                         CredentialBroker)
from .sensors import (SensorFusionEngine, SensorReading,  # noqa
                      CalibrationProfile, ReplaySensorAdapter)
from .spatial import (SpatialWorldModel, MappingEngine,  # noqa
                      LocalizationEngine, CollisionChecker, OccupancyMap)
from .frames import Frame, Transform, transform_point  # noqa
from .planning import (PhysicalTaskPlanner, MotionPlanner,  # noqa
                       ManipulationPlanner, NavigationPlanner)
from .twins import PhysicalDigitalTwin, RobotTwin, RoomTwin  # noqa
from .simulation import KinematicSimulator, SimToRealTracker  # noqa
from .safety import SafetyController  # noqa
from .execution import (ActionExecutor, SimulatedRobotAdapter,  # noqa
                        CommandAuthenticator, RateLimiter, LoopDetector)
from .verification import ExpectationEngine, ActionVerifier  # noqa
from .telemetry import TelemetryEngine, EventBus  # noqa
from .security import DeviceSecurityController  # noqa
from .memory import PhysicalMemory, EmbodiedSkill  # noqa
from .lab import (LabAutomationEngine, LabInstrument, LabProtocol,  # noqa
                  BayesianOptimizer, pareto_frontier)
from .benchmarks import EmbodiedBenchmarkEngine  # noqa

__version__ = "1.0.0"
__all__ = ["EmbodiedIntelligenceEngine", "EmbodiedDenied", "__version__"]
