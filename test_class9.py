import ast

# Test with many kwargs like the real code
code = """
class TrustSignal:
    pass

class TrustDimension:
    EXECUTION = "execution"

class Test:
    def record_signal(self, sig):
        pass
    
    def method(self):
        signals = []
        signals.append(self.record_signal(TrustSignal(
            node_id=node_id,
            dimension=TrustDimension.EXECUTION,
            source=source,
            kind="task_success" if success else "task_failure",
            value=0.5 if success else -0.5,
            confidence=0.8 if verified else 0.6,
            evidence_ref=evidence_ref,
            provenance={"task_class": task_class, "verified": verified},
        )))
"""

try:
    ast.parse(code)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')