with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

start = content.find('def record_execution_outcome')
end = content.find('\n    def ', start + 1)
if end == -1:
    end = len(content)

func_code = content[start:end]
lines = func_code.split('\n')

# Print lines 1-35 with line numbers
for i, line in enumerate(lines[:35], 1):
    print('{:3}: {}'.format(i, repr(line)))