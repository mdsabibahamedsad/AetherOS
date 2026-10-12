import ast

with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

start = content.find('def record_execution_outcome')
end = content.find('\n    def ', start + 1)
if end == -1:
    end = len(content)

func_code = content[start:end]

# Try parsing just the first part (up to the first if statement)
lines = func_code.split('\n')
# Find the line with "if latency_ms is not None:"
for i, line in enumerate(lines):
    if 'if latency_ms is not None:' in line:
        print(f'Found at line {i}: {line}')
        break

# Parse up to that line
partial = '\n'.join(lines[:i])
test_code = f"""
class TrustSignal:
    pass

class TrustDimension:
    EXECUTION = "execution"

class Test:
    def record_signal(self, sig):
        pass
    
{partial}
"""

try:
    ast.parse(test_code)
    print('OK up to first if')
except SyntaxError as e:
    print(f'Error: {e.msg} at line {e.lineno}')
    print(f'Text: {e.text}')