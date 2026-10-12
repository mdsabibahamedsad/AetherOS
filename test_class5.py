import ast

# Test with direct call
code = """
class TrustSignal:
    pass

class Test:
    def method(self):
        x = TrustSignal(
            node_id=node_id,
        )
"""

try:
    ast.parse(code)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')