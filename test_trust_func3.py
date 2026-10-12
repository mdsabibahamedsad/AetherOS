import ast
code = """
class TrustSignal:
    pass

class TrustDimension:
    EXECUTION = "execution"

class Test:
    def record_signal(self, sig):
        pass
    
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
    ) -> list:
        signals = []
        source = "outcome" if not verified else "verification"
        
        # Execution dimension
        signals.append(self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.EXECUTION,
            source=source,
            kind="task_success" if success else "task_failure",
            value=0.5 if success else -0.5,
            confidence=0.8 if verified else 0.6,
            evidence_ref=evidence_ref,
            provenance={"task_class": task_class, "verified": verified}
        ))
        return signals
"""
try:
    ast.parse(code)
    print('Isolated function OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')