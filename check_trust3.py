with open('aetheros_mesh/trust.py', 'r') as f:
    content = f.read()

# Find all positions where parentheses depth increases
open_paren = 0
positions = []
for i, ch in enumerate(content):
    if ch == '(':
        open_paren += 1
        positions.append((i, open_paren))
    elif ch == ')':
        open_paren -= 1
        positions.append((i, open_paren))

# Find positions where depth is highest
max_depth = max(p[1] for p in positions)
print(f'Max depth: {max_depth}')

# Show positions with depth > 5
for pos, depth in positions:
    if depth > 5:
        print(f'Depth {depth} at {pos}: ...{content[max(0,pos-60):pos+20]}...')