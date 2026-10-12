#!/usr/bin/env python3
import re

with open('agent/research/reports.py', 'r') as f:
    content = f.read()

# Find and replace the criteria section in render_decision_memo
old_pattern = r'## Criteria \(explicit assumptions\)"\s*\n\s*for constraint in ctx\.task\.constraints or \[\]:.*?\n\s*if not ctx\.task\.constraints:.*?\n\s*lines \+= \[\s*## Options / Tradeoffs\s*\n'

new_section = '''## Criteria (explicit assumptions, with transparency)')
    # Display explicit criteria/constraints from the user
    for i, constraint in enumerate(ctx.task.constraints or [], 1):
        lines.append(f'{i}. {constraint}')
    if not ctx.task.constraints:
        lines.append('- No explicit criteria supplied; do not treat defaults as user intent.')
    
    # Disclose assumption weights - user-specified constraints are taken as-is
    lines.append('')
    lines.append('*Assumptions are user-specified and taken as-is; no automatic')
    lines.append('weighting is applied. The user may review and modify constraints at')
    lines.append('any time before synthesis begins.")
    lines += ["", "## Options / Tradeoffs']'''

# Try a simpler replace approach - find the specific block
start_marker = '## Criteria (explicit assumptions)"'
if start_marker in content:
    # Find the section to replace
    start_idx = content.find(start_marker)
    # Find the end of this section (before ## Options / Tradeoffs)
    end_marker = '## Options / Tradeoffs'
    end_idx = content.find(end_marker, start_idx)
    if end_idx >= 0:
        # Replace the section
        replacement = '''## Criteria (explicit assumptions, with transparency)')
    # Display explicit criteria/constraints from the user
    for i, constraint in enumerate(ctx.task.constraints or [], 1):
        lines.append(f'{i}. {constraint}')
    if not ctx.task.constraints:
        lines.append('- No explicit criteria supplied; do not treat defaults as user intent.')
    
    # Disclose assumption weights - user-specified constraints are taken as-is
    lines.append('')
    lines.append('*Assumptions are user-specified and taken as-is; no automatic')
    lines.append('weighting is applied. The user may review and modify constraints at')
    lines.append('any time before synthesis begins.")
    lines += ["", "## Options / Tradeoffs']'''
        
        new_content = content[:start_idx] + replacement + content[end_idx:]
        with open('agent/research/reports.py', 'w') as f:
            f.write(new_content)
        print('SUCCESS: Enhanced decision memo criteria section')
    else:
        print('Could not find end marker')
else:
    print('Could not find start marker')