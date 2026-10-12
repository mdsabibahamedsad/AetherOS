import ast
with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

# Find all unmatched opening parentheses
open_paren = 0
for i, ch in enumerate(content):
    if ch == '(':
        open_paren += 1
    elif ch == ')':
        open_paren -= 1
    if open_paren < 0:
        print(f'Unbalanced at position {i}: ...{content[max(0,i-40):i+40]}...')
        break
    if open_paren > 10:
        print(f'Deep nesting at position {i}: open_paren={open_paren}')
        # Show context
        print(f'Context: ...{content[max(0,i-80):i+80]}...')

print(f'Final open_paren count: {open_paren}')