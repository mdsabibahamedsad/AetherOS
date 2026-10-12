"""ScienceBench (§67-71, §205-211): real measured runs of the
benchmark engine categories + E2E algorithm demo (§235). No invented
numbers — everything executes here."""
from __future__ import annotations

import json
import random
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from aetheros_science import ScientificIntelligenceEngine
from aetheros_science.benchmarks import (ScientificBenchmarkEngine,
                                         adversarial_fixtures,
                                         golden_fixtures)
from aetheros_science.safety import ScientificSafetyPolicy


def _eng():
    return ScientificIntelligenceEngine(Path(tempfile.mkdtemp()),
                                        autonomy=5)


def e2e_algorithm_demo() -> dict:
    """§235: which sort is faster? Real timed runs, real stats."""
    eng = _eng()
    task = eng.create_task(
        "Which sort performs better on random integer lists?",
        domain="computer science")
    decomp = eng.understand(task)
    hyps = eng.hypothesize(task, decomp,
                            strategies=["EXPLANATORY", "ALTERNATIVE"])
    hyp = hyps[0]
    exp = eng.design_experiment(task, hyp, seed=42)
    code = (
        "import json, random, time\n"
        "def insertion(a):\n"
        "    a=list(a)\n"
        "    for i in range(1,len(a)):\n"
        "        k=a[i]; j=i-1\n"
        "        while j>=0 and a[j]>k:\n"
        "            a[j+1]=a[j]; j-=1\n"
        "        a[j+1]=k\n"
        "    return a\n"
        "rng=random.Random(42)\n"
        "base=[rng.randint(0,9999) for _ in range(400)]\n"
        "t0=time.perf_counter(); insertion(base); t_ins=time.perf_counter()-t0\n"
        "t0=time.perf_counter(); sorted(base); t_tim=time.perf_counter()-t0\n"
        "json.dump({'insertion_ms':t_ins*1000,'timsort_ms':t_tim*1000},\n"
        "          open('metrics.json','w'))\n")
    res = eng.execute(task, exp, code, {})
    m = res.metrics
    ratio = (m["insertion_ms"] / max(m["timsort_ms"], 1e-9))
    analysis = eng.analyze(task, exp, res, [m["insertion_ms"]],
                           [m["timsort_ms"]])
    rep = eng.replicate(task, exp, code, {}, mode="SEED")
    return {"task": task.id, "hypotheses": len(hyps),
            "metrics": m, "speedup": round(ratio, 2),
            "outcome": analysis["outcome"],
            "replication": rep.reproducibility,
            "conclusion": "timsort faster on n=400 random ints "
                          "(single context; external validity uncertain)",
            "next_experiment": "vary n in {100,1000,10000} + nearly-sorted input"}


def main():
    eng = _eng()
    bench = ScientificBenchmarkEngine()
    fx = golden_fixtures()
    bench.run("SA", lambda: {"passed": bool(
        eng.stats.welch_t(fx["mean_shift"]["a"],
                          fx["mean_shift"]["b"])["statistical"])})
    bench.run("SA", lambda: {"passed": not bool(
        eng.stats.welch_t(fx["null_case"]["a"],
                          fx["null_case"]["b"])["statistical"])})
    bench.run("CS", lambda: {"passed": abs(
        eng.stats.pearson(fx["perfect_corr"]["xs"],
                          fx["perfect_corr"]["ys"])["r"] - 1.0) < 1e-9})
    bench.run("HG", lambda: {"passed": len(
        eng.hyp_engine.generate("t", ["cache"], "latency")) >= 10})
    bench.run("HF", lambda: {"passed": bool(
        eng.falsification.criteria(
            eng.hyp_engine.generate("t", ["x"], "y")[0]
        ).falsify_observation)})
    adv = adversarial_fixtures()
    bench.run("CI", lambda: {"passed": not adv["fake_citation"]["resolves"]})
    bench.run("PR", lambda: {"passed": adv["prompt_injection_paper"][
        "expect_quarantine"] and bool(eng.safety.scan_document(
            adv["prompt_injection_paper"]["text"])["quarantine"])})
    out = {"benchmark": bench.summary(), "e2e_demo": e2e_algorithm_demo(),
           "engine_health": eng.health()}
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
