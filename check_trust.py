import ast
with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

# Check the exact characters around line 251
idx = content.find('provenance={"task_class": task_class, "verified": verified},')
print(f'Found at: {idx}')
print(repr(content[idx:idx+100]))

# Also check the parentheses balance
open_paren = 0
for i, ch in enumerate(content[:10000]):
    if ch == '(':
        open_paren += 1
    elif ch == ')':
        open_paren -= 1
    if open_paren < 0:
        print(f'Unbalanced at position {i}: {content[max(0,i-20):i+20]}')
        break
if open_paren != 0:
    print(f'Final open_paren count: {open_paren}')
else:
    print('Parentheses balanced in first 10000 chars')