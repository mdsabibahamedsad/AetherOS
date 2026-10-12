import re

with open('aetheros_capability\capability_router.py', 'r') as f:
    content = f.read()

# Normalize line endings
content = content.replace('\r\n', '\n').replace('\r', '\n')

# Find the _estimate_cost method and everything up to _estimate_latency
pattern = r'(    def _estimate_cost\(self, spec: CapabilitySpec, tool: Optional\[ToolReference\], model: Optional\[ModelReference\]\) -> float:.*?)(?=    def _estimate_latency)'
match = re.search(pattern, content, re.DOTALL)

if match:
    # Clean replacement
    new_method = '''    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:
        """Estimate execution cost in arbitrary units."""
        cost = 0.0
        if model:
            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}
            cost += cost_map.get(model.cost_class, 0.1)
        if tool and tool.risk_level >= RiskLevel.HIGH:
            cost += 0.05  # Premium for high-risk tools
        return cost

'''
    # Replace using regex
    new_content = re.sub(
        r'    def _estimate_cost\(self, spec: CapabilitySpec, tool: Optional\[ToolReference\], model: Optional\[ModelReference\]\) -> float:.*?(?=    def _estimate_latency)',
        '    def _estimate_cost(self, spec: CapabilitySpec, tool: Optional[ToolReference], model: Optional[ModelReference]) -> float:\n        """Estimate execution cost in arbitrary units."""\n        cost = 0.0\n        if model:\n            cost_map = {"free": 0, "low": 0.01, "standard": 0.1, "high": 1.0}\n            cost += cost_map.get(model.cost_class, 0.1)\n        if tool and tool.risk_level >= RiskLevel.HIGH:\n            cost += 0.05  # Premium for high-risk tools\n        return cost\n',
        content,
        flags=re.DOTALL
    )
    
    with open('aetheros_capability\capability_router.py', 'w', newline='\n') as f:
        f.write(content)
    print('Fixed _estimate_cost method')