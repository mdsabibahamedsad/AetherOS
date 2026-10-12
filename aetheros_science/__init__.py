"""Master 53: Scientific Intelligence & Autonomous Discovery Engine.

PLEDGE: plausibility is never presented as truth. Every object below
carries explicit status/provenance labels: UNVALIDATED HYPOTHESIS,
SIMULATION vs REAL, INFERRED vs OBSERVED, E0-E6 evidence strength.
Anything that cannot actually execute is marked UNAVAILABLE.
"""

from .models import *  # noqa
from .engine import ScientificIntelligenceEngine, ScienceDenied  # noqa
from .research import (decompose_question, ResearchLandscapeBuilder,  # noqa
                       KnowledgeGapDetector, SourceIndependenceAnalyzer,
                       ContradictionEngine)
from .hypotheses import (HypothesisEngine, HypothesisDiversifier,  # noqa
                         HypothesisCritic, NoveltyAnalyzer,
                         FalsificationEngine, ExplorationController)
from .experiments import (ExperimentDesigner, ComputationalRuntime,  # noqa
                          ExperimentSimulator, ActiveExperimentSelector,
                          fingerprint_experiment)
from .statistics import Statistics  # noqa
from .evidence import (EvidenceEngine, BayesianUpdater,  # noqa
                       ReproducibilityEngine, NegativeResultMemory)
from .knowledge import ScientificKnowledgeGraph, ScientificMemory  # noqa
from .discovery import (DiscoverySynthesizer, ReplicationEngine,  # noqa
                        RedTeamScientist, ReportGenerator, QualityGate,
                        check_causal_language, check_discovery_language,
                        verify_numeric_claims)
from .safety import ScientificSafetyPolicy, LabConnector  # noqa
from .benchmarks import ScientificBenchmarkEngine  # noqa

__version__ = "1.0.0"
__all__ = ["ScientificIntelligenceEngine", "ScienceDenied", "__version__"]
