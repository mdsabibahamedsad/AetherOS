import ast

# Test with simpler call
code = """
class TrustSignal:
    pass

class Test:
    def method(self):
        signals.append(self.record_signal(TrustSignal(
            node_id=node_id,
        ))
"""

try:
    ast.parse(code)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')