import ast
code = """
class Test:
    def record_execution_outcome(
        self,
        node_id: str,
        success: bool,
        task_class: str = "",
        latency_ms: float = None,
        cost_usd: float = None,
        sla_met: bool = None,
        verified: bool = False,
        evidence_ref: str = ""
    ):
        signals = []
        source = "outcome"
        signals.append(1)
        if latency_ms is not None:
            attain = max(0.0, min(1.0, 1.0 - latency_ms / 60000.0))
            signals.append(2)
        return signals
"""
ast.parse(code)
print('OK')