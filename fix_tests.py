import re

with open('tests/agent_economy/test_core.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the mock flow objects to include optimizer
# Pattern 1: Simple flow mock
content = content.replace(
    'flow = type("Flow", (), {"flags": type("Flags", (), {"is_enabled": lambda self, name: True})()})',
    'flow = type("Flow", (), {"flags": type("Flags", (), {"is_enabled": lambda self, name: True})(), "optimizer": type("Opt", (), {"recommend": lambda self, task: {"candidates": []}})()})'
)

# Pattern 2: Flow with more attributes
content = re.sub(
    r'flow = type\("Flow", \(\), \{"flags": type\("Flags", \(\), \{"is_enabled": lambda self, name: True\}\)\(\}\)\}\)',
    'flow = type("Flow", (), {"flags": type("Flags", (), {"is_enabled": lambda self, name: True})(), "optimizer": type("Opt", (), {"recommend": lambda self, task: {"candidates": []}})()})',
    content
)

# Pattern 3: Flow in test_milestone_dependency
content = re.sub(
    r'flow = type\("Flow", \(\), \{"flags": type\("Flags", \(\), \{"is_enabled": lambda self, name: True\}\)\(\)\}\)\)',
    'flow = type("Flow", (), {"flags": type("Flags", (), {"is_enabled": lambda self, name: True})(), "optimizer": type("Opt", (), {"recommend": lambda self, task: {"candidates": []}})()})',
    content
)

with open('tests/agent_economy/test_core.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Fixed test_core.py')