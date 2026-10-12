with open('aetheros_mesh/trust.py', 'rb') as f:
    content = f.read()

start = content.find(b'def record_execution_outcome')
end = content.find(b'\n    def ', start + 1)
if end == -1:
    end = len(content)

func_bytes = content[start:end]
print(func_bytes[:2000].decode('utf-8'))