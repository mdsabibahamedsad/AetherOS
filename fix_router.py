import re

with open('aetheros_capability\capability_router.py', 'r') as f:
    content = f.read()

# Find and replace the _estimate_cost method
old = """    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:
        \"\"\"Estimate execution cost in arbitrary units.\"\"\"
        cost = 0.0
        if model:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            cost += cost_map.get(model.cost_class, 0.1)
        if tool and tool.risk_level >= RiskLevel.HIGH:
            cost += 0.05  # Premium for high-risk tools
        return cost"""

new = """    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:
        \"\"\"Estimate execution cost in arbitrary units.\"\"\"
        cost = 0.0
        if model:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            cost += cost_map.get(model.cost_class, 0.1)
        if tool and tool.risk_level >= RiskLevel.HIGH:
            cost += 0.05  # Premium for high-risk tools
        return cost"""

if old in content:
    content = content.replace(old, new)
    with open('aetheros_capability\capability_router.py', 'w') as f:
        f.write(content)
    print('Replaced successfully')
else:
    print('Pattern not found exactly, trying regex...')
    pattern = r'(    def _estimate_cost\(self, spec: CapabilitySpec, tool: Optional\[ToolReference\], model: Optional\[ModelReference\]\) -> float:\n        \"\"\".*?\"\"\"\n        cost = 0\.0\n        if model:\n            cost_map = \{"free": 0, "low": 0\.01, "standard": 0\.1, "high": 1\.0\}\n            cost \+= cost_map\.get\(model\.cost_class, 0\.1\)\n        if tool and tool\.risk_level >= RiskLevel\.HIGH:\n            cost \+= 0\.05  # Premium for high-risk tools\n        return cost)'
    new_method = '''    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:
        \"\"\"Estimate execution cost in arbitrary units.\"\"\"
        cost = 0.0
        if model:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            cost += cost_map.get(model.cost_class, 0.1)
        if tool and tool.risk_level >= RiskLevel.HIGH:
            cost += 0.05  # Premium for high-risk tools
        return cost'''
    content = re.sub(pattern, new_method, content)
    with open('aetheros_capability\capability_router.py', 'w') as f:
        f.write(content)
    print('Replaced via regex')