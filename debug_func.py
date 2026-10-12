with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

start = content.find('def record_execution_outcome')
end = content.find('\n    def ', start + 1)
if end == -1:
    end = len(content)

func_code = content[start:end]
print(func_code[:2000])