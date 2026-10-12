"""AetherOS Self-Evolving Intelligence Fabric (Master 51)."""

from .models import *  # noqa
from .engine import SelfImprovementEngine, GovernanceDenied  # noqa
from .traces import TraceStore, RedactionEngine  # noqa
from .graders_eval import (EvaluationEngine, EvalDataset, ensemble,  # noqa
                           GraderUnavailable)
from .failures import (FailureAnalyzer, RootCauseAnalyzer,  # noqa
                       classify_severity)
from .lessons import LessonEngine  # noqa
from .experiments import ExperimentRunner, BudgetExceeded  # noqa
from .improvements import ImprovementPlanner, CandidateRegistry  # noqa
from .deploy import DeploymentController, LADDER  # noqa
from .monitoring import DriftDetector, Scorecards, eval_health  # noqa

__version__ = "1.0.0"
__all__ = ["SelfImprovementEngine", "GovernanceDenied", "__version__"]
