"""ScientificIntelligenceEngine facade: task lifecycle, autonomy
LEVEL 0-5, stop conditions, decision engine, campaigns, budgets,
checkpoints, audit. Physical lab always needs separate authorization.
Operates under Master 50 control plane; feeds Master 51 lessons;
uses Master 52 simulation."""
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .discovery import DiscoverySynthesizer, RedTeamScientist
from .evidence import (BayesianUpdater, EvidenceEngine, NegativeResultMemory,
                       ReproducibilityEngine)
from .experiments import (ActiveExperimentSelector, ComputationalRuntime,
                          ExperimentDesigner, ExperimentSimulator)
from .hypotheses import (ExplorationController, FalsificationEngine,
                         HypothesisCritic, HypothesisDiversifier,
                         HypothesisEngine, NoveltyAnalyzer)
from .knowledge import ScientificKnowledgeGraph, ScientificMemory
from .models import (Experiment, ExperimentResult, ExperimentStatus,
                     Hypothesis, ResearchTraceEvent, ScientificDiscovery,
                     ScientificTask, TaskStatus, new_id)
from .research import (ContradictionEngine, KnowledgeGapDetector,
                       ResearchLandscapeBuilder, SourceIndependenceAnalyzer,
                       decompose_question)
from .safety import LabConnector, ScientificSafetyPolicy
from .statistics import Statistics

logger = logging.getLogger(__name__)


class ScienceDenied(Exception):
    pass


class ScientificIntelligenceEngine:
    def __init__(self, home: Path, plane: Any = None,
                 improvement: Any = None, cognitive: Any = None,
                 autonomy: int = 1, tenant: str = "default",
                 strict: bool = True):
        self.home = Path(home)
        self.home.mkdir(parents=True, exist_ok=True)
        self.plane = plane
        self.improvement = improvement
        self.cognitive = cognitive
        self.autonomy = autonomy
        self.tenant = tenant
        self.strict = strict  # SCIENCE_STRICT default on
        self.tasks: Dict[str, ScientificTask] = {}
        self.hypotheses: Dict[str, Hypothesis] = {}
        self.experiments: Dict[str, Experiment] = {}
        self.results: Dict[str, ExperimentResult] = {}
        self.discoveries: Dict[str, ScientificDiscovery] = {}
        self.traces: List[ResearchTraceEvent] = []
        # components
        self.landscape_builder = ResearchLandscapeBuilder()
        self.gaps = KnowledgeGapDetector()
        self.independence = SourceIndependenceAnalyzer()
        self.contradictions = ContradictionEngine()
        self.hyp_engine = HypothesisEngine()
        self.diversifier = HypothesisDiversifier()
        self.novelty = NoveltyAnalyzer()
        self.critic = HypothesisCritic()
        self.falsification = FalsificationEngine()
        self.explorer = ExplorationController()
        self.designer = ExperimentDesigner()
        self.runtime = ComputationalRuntime(self.home / "runs")
        self.simulator = ExperimentSimulator(cognitive)
        self.selector = ActiveExperimentSelector()
        self.stats = Statistics()
        self.evidence = EvidenceEngine()
        self.bayes = BayesianUpdater()
        self.repro = ReproducibilityEngine()
        self.negative = NegativeResultMemory()
        self.graph = ScientificKnowledgeGraph()
        self.memory = ScientificMemory()
        self.safety = ScientificSafetyPolicy()
        self.lab = LabConnector()
        self.synth = DiscoverySynthesizer()
        self.redteam = RedTeamScientist()
        self._identity_id: Optional[str] = None
        self._halted = False
        self._ensure_identity()
        self._wire_emergency_stop()

    # ------------------------------------------------------------ governance
    def _audit(self, typ: str, data: Dict[str, Any]) -> None:
        if self.plane is not None:
            try:
                self.plane.audit.emit(typ, {"tenant": self.tenant}, data)
                return
            except Exception as exc:
                logger.warning("audit emit failed: %s", exc)
        logger.info("science audit %s %s", typ, data)

    def _wire_emergency_stop(self) -> None:
        if self.plane is None:
            return
        try:
            self.plane.emergency.on_stop(lambda _s: self.stop_all())
        except Exception:
            pass

    def _gate(self, capability: str,
              resource: str = "scientific-intelligence",
              local_ok: bool = False) -> None:
        """Master-50 gate. Two honest modes:
        - plane bound: provisioned 'science-engine' service identity is
          checked against trust/policy/scopes. Trust is NEVER self-granted.
        - plane None: only sandbox-contained local capabilities
          (local_ok=True) proceed; lab/external/publish deny (fail closed).
        """
        if self.plane is None:
            if local_ok and self.autonomy >= 4:
                return
            raise ScienceDenied(
                "no control plane: privileged action denied")
        try:
            from aetheros_control_plane.models import ActionManifest
            manifest = ActionManifest(
                task_id="science", agent_id="science-engine",
                identity_id=self._identity_id or "science-engine",
                capabilities=[capability],
                scopes=[capability], resources=[resource])
            gate = self.plane.check(manifest)
            if not gate.allowed:
                raise ScienceDenied("; ".join(gate.reasons))
        except ScienceDenied:
            raise
        except Exception as exc:
            raise ScienceDenied(f"control-plane error: {exc}")

    def _ensure_identity(self) -> None:
        """Provision the engine's service identity + declared scopes.
        Install-time provisioning, audited. Trust/policy decisions stay
        with the plane administrator."""
        if self.plane is None or self._identity_id:
            return
        try:
            from aetheros_control_plane.models import IdentityType
            existing = [i for i in self.plane.identities.list()
                        if i.display_name == "science-engine"]
            if existing:
                self._identity_id = existing[0].id
                return
            ident = self.plane.identities.create(
                IdentityType.SERVICE, "science-engine",
                capabilities=["science.experiment.execute",
                              "science.simulate", "science.read"],
                scopes=["science.experiment.execute",
                        "science.simulate", "science.read"])
            self._identity_id = ident.id
            self.plane.audit.emit(
                "science.identity.provisioned", {"tenant": self.tenant},
                {"identity": ident.id,
                 "note": "service identity; trust not self-granted"})
        except Exception as exc:
            logger.warning("identity provisioning failed: %s", exc)

    def _trace(self, kind: str, ref: str, task_id: str = "",
               **detail: Any) -> None:
        self.traces.append(ResearchTraceEvent(
            kind=kind, ref=ref, task_id=task_id, detail=detail))

    def stop_all(self) -> None:
        """STOP ALL SCIENCE: no new experiments/calls; state preserved."""
        self._halted = True
        for exp in self.experiments.values():
            if exp.status in (ExperimentStatus.QUEUED,
                              ExperimentStatus.RUNNING,
                              ExperimentStatus.PAUSED):
                exp.status = ExperimentStatus.CANCELLED
        self._audit("science.stopped_all", {})

    # ---------------------------------------------------------------- tasks
    def create_task(self, question: str, **kwargs: Any) -> ScientificTask:
        task = ScientificTask(question=question, **kwargs)
        task.history.append({"status": task.status, "at": time.time()})
        self.tasks[task.id] = task
        self._trace("task", task.id, task.id, question=question)
        self._audit("science.task.created",
                    {"task": task.id, "question": question})
        return task

    def _set_status(self, task: ScientificTask, status: str) -> None:
        task.status = status
        task.updated_at = time.time()
        task.history.append({"status": status, "at": task.updated_at})
        self._trace("status", task.id, task.id, status=status)

    # --------------------------------------------------------------- pipeline
    def understand(self, task: ScientificTask) -> Dict[str, Any]:
        self._set_status(task, TaskStatus.UNDERSTANDING)
        decomp = decompose_question(task.question, task.known_facts,
                                    task.background)
        self._trace("decomposition", task.id, task.id, **decomp)
        return decomp

    def research(self, task: ScientificTask,
                 sources: Optional[List[Any]] = None) -> Any:
        self._require_level(1, "research")
        self._set_status(task, TaskStatus.RESEARCHING)
        landscape = self.landscape_builder.build(
            task.id, task.question, sources)
        landscape.contradictions = self.contradictions.detect(
            landscape.claims)
        self._trace("research", task.id, task.id,
                    sources=len(landscape.sources),
                    claims=len(landscape.claims))
        return landscape

    def hypothesize(self, task: ScientificTask, decomp: Dict[str, Any],
                    strategies: Optional[List[str]] = None) -> List[Hypothesis]:
        self._require_level(2, "hypothesis generation")
        self._set_status(task, TaskStatus.HYPOTHESIS_GENERATION)
        target = (decomp.get("candidate_causal_factors") or ["phenomenon"])[0]
        hyps = self.hyp_engine.generate(
            task.id, decomp.get("candidate_causal_factors", []),
            decomp.get("phenomenon", ""), strategies)
        for h in hyps:
            self.hypotheses[h.id] = h
            self.graph.add_node("Hypothesis", h.id,
                                {"statement": h.statement})
        self.diversifier.diversify(hyps)
        self._trace("hypotheses", task.id, task.id, count=len(hyps))
        self._set_status(task, TaskStatus.HYPOTHESIS_REVIEW)
        return hyps

    def review(self, hyp: Hypothesis,
               claims: Optional[List[str]] = None) -> Any:
        return self.critic.review(hyp, claims)

    def design_experiment(self, task: ScientificTask, hyp: Hypothesis,
                          experiment_type: str = "COMPUTATIONAL",
                          seed: int = 0) -> Experiment:
        self._require_level(3, "experiment design")
        self._set_status(task, TaskStatus.EXPERIMENT_DESIGN)
        indep = hyp.variables.get("independent", ["x"])
        dep = hyp.variables.get("dependent", ["y"])
        exp = self.designer.design(task.id, hyp.id,
                                   f"test: {hyp.statement[:120]}",
                                   indep, dep, experiment_type, seed)
        exp.safety_class = self.safety.classify(
            experiment_type, exp.protocol, task.domain)
        exp.approval_required = self.safety.approval_required(
            exp.safety_class, task.human_approval_policy)
        # consult negative memory before proposing
        prior = self.negative.matches(hyp.statement, str(indep))
        if prior:
            exp.design += f" [negative-memory hits: {len(prior)}]"
        self.experiments[exp.id] = exp
        self._trace("experiment_designed", exp.id, task.id,
                    type=experiment_type, approval=exp.approval_required)
        return exp

    def simulate(self, task: ScientificTask,
                 exp: Experiment, scenario: Dict[str, Any]) -> ExperimentResult:
        self._set_status(task, TaskStatus.SIMULATING)
        res = self.simulator.simulate(exp, scenario)
        self.results[exp.id + ":sim"] = res
        return res

    def execute(self, task: ScientificTask, exp: Experiment, code: str,
               parameters: Dict[str, Any],
               approved: bool = False) -> ExperimentResult:
        if self._halted:
            raise ScienceDenied("STOP ALL SCIENCE active")
        self._require_level(4, "experiment execution")
        if exp.approval_required and not approved:
            exp.status = ExperimentStatus.AWAITING_APPROVAL
            self._set_status(task, TaskStatus.AWAITING_APPROVAL)
            raise ScienceDenied(
                f"experiment {exp.id} requires human approval")
        if exp.experiment_type == "PHYSICAL_LAB":
            self._gate("science.lab.execute")
            return self._lab_execute(task, exp)
        self._gate("science.experiment.execute", local_ok=True)
        self._check_budget(task)
        self._set_status(task, TaskStatus.EXECUTING)
        exp.status = ExperimentStatus.RUNNING
        res = self.runtime.run(exp, code, parameters)
        exp.status = (ExperimentStatus.COMPLETED if res.exit_code == 0
                      else ExperimentStatus.FAILED)
        self.results[exp.id] = res
        self.memory.record("experiment", exp.id,
                           {"exit": res.exit_code,
                            "type": res.execution_type})
        self._trace("experiment_completed", exp.id, task.id,
                    exit=res.exit_code)
        self._set_status(task, TaskStatus.ANALYZING)
        return res

    def _lab_execute(self, task: ScientificTask,
                     exp: Experiment) -> ExperimentResult:
        out = self.lab.execute(exp.protocol)
        res = ExperimentResult(experiment_id=exp.id,
                               execution_type="REAL",
                               stderr=out.get("note", out["status"]))
        self.results[exp.id] = res
        return res

    def analyze(self, task: ScientificTask, exp: Experiment,
                res: ExperimentResult, group_a: List[float],
                group_b: List[float]) -> Dict[str, Any]:
        comp = self.stats.welch_t(group_a, group_b)
        res.statistical_analysis = comp
        res.interpretation_label = "EXPLORATORY"  # default; preregister to upgrade
        outcome = ("SUPPORTS" if comp.get("statistical") and comp.get("practical")
                   else "WEAKENS" if comp.get("statistical") else "INCONCLUSIVE")
        res.falsification_outcome = outcome
        hyp = self.hypotheses.get(exp.hypothesis_id)
        if hyp:
            from .hypotheses import FalsificationEngine
            hyp.status = FalsificationEngine.judge(hyp, outcome)
            hyp.version += 1
            hyp.prior_history.append({"experiment": exp.id,
                                      "outcome": outcome,
                                      "at": time.time()})
        self._trace("analyzed", exp.id, task.id, outcome=outcome)
        return {"comparison": comp, "outcome": outcome}

    def replicate(self, task: ScientificTask, exp: Experiment,
                  code: str, parameters: Dict[str, Any],
                  mode: str = "SEED", rel_tol: float = 0.25) -> ExperimentResult:
        res = self.runtime.reproduce(exp, code, parameters)
        first = self.results.get(exp.id)
        outcome = "DIVERGED"
        if first is not None:
            # bitwise equality is wrong for measured floats (timings);
            # numeric metrics must match within tolerance, non-numeric
            # metrics must match exactly.
            outcome = ("MATCHED" if self._metrics_match(
                first.metrics, res.metrics, rel_tol) else "DIVERGED")
        self.repro.record(exp.id, exp.id, mode, outcome,
                          {"manifest": res.provenance.get(
                              "manifest_fingerprint")})
        res.reproducibility = ("REPRODUCED" if outcome == "MATCHED"
                               else "DIVERGENCE")
        self.results[exp.id + f":rep:{mode}"] = res
        return res

    def discover(self, task: ScientificTask, claim: str, claim_id: str,
                 evidence_ids: List[str], experiments: List[str],
                 context: Dict[str, Any]) -> ScientificDiscovery:
        disc = self.synth.propose(task.id, claim, claim_id, evidence_ids,
                                  experiments)
        for s in ["HYPOTHESIS", "TESTABLE", "EXPERIMENT_DESIGNED",
                  "EXPERIMENT_EXECUTED", "EVIDENCE_COLLECTED", "ANALYZED"]:
            self.synth.advance(disc, s)
        verdict = self.synth.validate(disc, context)
        self.discoveries[disc.id] = disc
        self._trace("discovery", disc.id, task.id, status=disc.status,
                    gate=verdict["passed"])
        self._audit("science.discovery.proposed",
                    {"discovery": disc.id, "gate": verdict["passed"]})
        if not verdict["passed"] and self.strict:
            raise ScienceDenied(
                f"discovery gate blocked: {verdict['blocking']}")
        return disc

    # --------------------------------------------------------------- control
    def _require_level(self, level: int, action: str) -> None:
        if self.autonomy < level:
            raise ScienceDenied(
                f"autonomy LEVEL {self.autonomy} < {level} for {action}")

    def _check_budget(self, task: ScientificTask) -> None:
        spent = sum(1 for r in self.results.values()
                    if r.execution_type == "REAL")
        limit = task.budget.get("max_experiments", 100)
        if spent >= limit:
            raise ScienceDenied("experiment budget exhausted — stopping")

    def stop_reasons(self, task: ScientificTask,
                     evidence_count: int) -> Optional[str]:
        if task.status in (TaskStatus.DISCOVERED, TaskStatus.FAILED,
                           TaskStatus.CANCELLED):
            return "terminal state"
        spent = sum(1 for r in self.results.values()
                    if r.execution_type == "REAL")
        if spent >= task.budget.get("max_experiments", 100):
            return "budget exhausted"
        if task.deadline and time.time() > task.deadline:
            return "time exhausted"
        if evidence_count >= 3:
            return "evidence saturated"
        return None

    def decide_next(self, uncertainty: float, eig: float, risk: float,
                    cost: float, value: float) -> str:
        if self._halted:
            return "stop"
        if risk > 0.8:
            return "ask human"
        if eig * value / max(cost, 1e-9) < 0.1:
            return "stop"
        if uncertainty > 0.6:
            return "run simulation"
        return "run experiment"

    @staticmethod
    def _metrics_match(a: Dict[str, Any], b: Dict[str, Any],
                       rel_tol: float) -> bool:
        if set(a) != set(b):
            return False
        for k, v in a.items():
            w = b[k]
            if isinstance(v, bool) or isinstance(w, bool):
                if v is not w:
                    return False
            elif isinstance(v, (int, float)) and isinstance(w, (int, float)):
                denom = max(abs(v), abs(w), 1e-9)
                if abs(v - w) / denom > rel_tol:
                    return False
            elif v != w:
                return False
        return True

    def checkpoint(self, task_id: str) -> Dict[str, Any]:
        task = self.tasks[task_id]
        return {"task": task.id, "status": task.status,
                "history": task.history,
                "experiments": [e.id for e in self.experiments.values()
                                if e.task_id == task_id]}

    def health(self) -> Dict[str, Any]:
        return {"tasks": len(self.tasks),
                "hypotheses": len(self.hypotheses),
                "experiments": len(self.experiments),
                "results": len(self.results),
                "discoveries": len(self.discoveries),
                "halted": self._halted,
                "lab": self.lab.status,
                "simulation": self.simulator.status}
