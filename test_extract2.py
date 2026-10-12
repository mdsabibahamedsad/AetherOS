import ast

# Extract the exact function from trust.py and test it
with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

start = content.find('def record_execution_outcome')
end = content.find('\n    def ', start + 1)
if end == -1:
    end = len(content)

func_code = content[start:end]

# Wrap in minimal class
test_code = f"""
class TrustSignal:
    pass

class TrustDimension:
    EXECUTION = "execution"

class Test:
    def record_signal(self, sig):
        pass
    
{func_code}
"""

try:
    ast.parse(test_code)
    print('OK')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')
    lines = test_code.split('\n')
    if e.lineno <= len(lines):
        print(f'Line {e.lineno}: {lines[e.lineno-1]}')