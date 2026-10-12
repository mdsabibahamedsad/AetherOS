import ast

# Test 1: Simple nested call
code1 = """
def f():
    signals.append(g(h(
        a=1,
        b=2,
    )))
"""
try:
    ast.parse(code1)
    print('Test 1 OK')
except SyntaxError as e:
    print(f'Test 1 Error: {e.msg} at line {e.lineno}')

# Test 2: With dict
code2 = """
def f():
    signals.append(g(h(
        a=1,
        b={"x": 1},
    )))
"""
try:
    ast.parse(code2)
    print('Test 2 OK')
except SyntaxError as e:
    print(f'Test 2 Error: {e.msg} at line {e.lineno}')

# Test 3: With conditional expression
code3 = """
def f():
    signals.append(g(h(
        a=1,
        b="x" if True else "y",
    )))
"""
try:
    ast.parse(code3)
    print('Test 3 OK')
except SyntaxError as e:
    print(f'Test 3 Error: {e.msg} at line {e.lineno}')