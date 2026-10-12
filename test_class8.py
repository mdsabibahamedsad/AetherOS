import ast

# Test with multiple kwargs
code = """
class TrustSignal:
    pass

class Test:
    def record_signal(self, sig):
        pass
    
    def method(self):
        signals = []
        signals.append(self.record_signal(TrustSignal(
            node_id=node_id,
            dimension="EXECUTION",
            source=source,
        )))
"""

try:
    ast.parse(code)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')