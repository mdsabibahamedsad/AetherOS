#!/usr/bin/env python3
"""Recursive import audit for the AetherOS Python backend.

Scans every .py file in the repo, extracts all import statements,
resolves each against the filesystem, and reports every module
reference that cannot be satisfied.
"""

import ast
import os
import sys
import importlib.util
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, ROOT)

SKIP_DIRS = {
    '__pycache__', 'node_modules', '.git', '.venv', 'build', 'dist', 'release',
    '__snapshots__', '.pytest_cache', '.ruff_cache', 'venv', '.egg-info',
}

THIRD_PARTY = {
    'anthropic', 'anyio', 'bs4', 'certifi', 'charset_normalizer', 'click',
    'cryptography', 'diskcache', 'dotenv', 'fastapi', 'flask', 'google',
    'groq', 'h11', 'httpcore', 'httpx', 'idna', 'jinja2', 'json5', 'litellm',
    'markdown', 'mistralai', 'openai', 'packaging', 'pillow', 'platformdirs',
    'psutil', 'pydantic', 'pydantic_core', 'pygments', 'pymongo', 'pynacl',
    'python_dotenv', 'pytz', 'pyyaml', 'regex', 'requests', 'rich', 'setuptools',
    'six', 'sniffio', 'soupselect', 'starlette', 'tiktoken', 'tokenizers',
    'tqdm', 'typing_extensions', 'tzlocal', 'urllib3', 'uvicorn', 'watchfiles',
    'websockets', 'yarl', 'youtube_transcript_api', 'zstandard',
    'asyncio', 'multipart', 'parse', 'sse_starlette', 'textwrap',
    'abc', 'atexit', 'base64', 'binascii', 'calendar', 'collections',
    'concurrent', 'configparser', 'contextlib', 'contextvars', 'copy', 'csv',
    'dataclasses', 'datetime', 'decimal', 'difflib', 'dis', 'email', 'enum',
    'functools', 'getpass', 'glob', 'gzip', 'hashlib', 'html', 'http',
    'importlib', 'inspect', 'io', 'ipaddress', 'itertools', 'json', 'logging',
    'math', 'mimetypes', 'multiprocessing', 'operator', 'os', 'pathlib',
    'pickle', 'platform', 'pprint', 'queue', 'random', 're', 'reprlib',
    'selectors', 'shlex', 'shutil', 'signal', 'site', 'socket', 'sqlite3',
    'stat', 'statistics', 'string', 'struct', 'subprocess', 'sys', 'tarfile',
    'tempfile', 'textwrap', 'threading', 'time', 'traceback', 'types',
    'typing', 'unicodedata', 'urllib', 'uuid', 'warnings', 'weakref', 'xml',
    'xmlrpc', 'zipfile', 'zoneinfo',
    '__future__', '__main__',
}

REPO_PACKAGES = {
    'agent', 'agents', 'providers', 'tools', 'gateway', 'cron',
    'plugins', 'aetheros_cli', 'aetheros_actions', 'aetheros_automation',
    'aetheros_cloud', 'aetheros_developer_platform', 'aetheros_intelligence',
    'aetheros_knowledge', 'aetheros_ocr', 'aetheros_orchestrator',
    'aetheros_platform', 'aetheros_production', 'aetheros_security',
    'aetheros_voice', 'cluster', 'connect', 'extensions', 'hub',
    'kernel', 'marketplace', 'memory', 'workflows', 'tui_gateway',
    'skills', 'optional_skills', 'acp_adapter', 'ui_tui',
    'tests', 'scripts',
}


def is_known(name):
    top = name.split('.')[0]
    return top in THIRD_PARTY or top in REPO_PACKAGES


def find_python_files():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith('.py'):
                yield os.path.join(dirpath, fn)


def extract_imports(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        try:
            tree = ast.parse(f.read())
        except SyntaxError:
            return [], [f'SyntaxError']

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports, []


def module_path(module_name):
    """Convert a dotted module name to a filesystem path."""
    return os.path.join(ROOT, module_name.replace('.', os.sep) + '.py')


def package_path(module_name):
    """Convert a dotted package name to a directory __init__.py path."""
    return os.path.join(ROOT, module_name.replace('.', os.sep), '__init__.py')


def module_or_package_exists(module_name):
    """Check if a module or package exists on disk without importing."""
    if os.path.isfile(module_path(module_name)):
        return True
    if os.path.isfile(package_path(module_name)):
        return True
    return False


def main():
    all_imports = defaultdict(list)
    import_errors = []
    processed = 0

    for fp in find_python_files():
        rel = os.path.relpath(fp, ROOT)
        processed += 1
        imports, errors = extract_imports(fp)
        for err in errors:
            import_errors.append((rel, err))
        for imp in imports:
            all_imports[imp].append(rel)

    print(f'Processed {processed} Python files')
    print(f'Found {len(all_imports)} unique imported module paths')

    missing = []
    for imp, sources in sorted(all_imports.items()):
        if imp.startswith('__future__'):
            continue
        if imp.startswith('.'):
            continue
        top = imp.split('.')[0]
        if not is_known(imp):
            continue
        if top in REPO_PACKAGES:
            if not module_or_package_exists(imp):
                missing.append((imp, sources))

    print()
    print('=' * 70)
    print('  MISSING / BROKEN MODULE IMPORTS')
    print('=' * 70)
    if not missing:
        print('  (none found — all imports resolve)')
    else:
        for imp, sources in sorted(missing):
            print(f'\n  [BROKEN] {imp}')
            print(f'    Imported by:')
            for s in sorted(set(sources)):
                print(f'      - {s}')

    if import_errors:
        print(f'\n  Syntax errors ({len(import_errors)}):')
        for fp, err in import_errors[:20]:
            print(f'    {fp}: {err}')

    print()
    print(f'  Result: {len(missing)} broken imports')
    return len(missing)


if __name__ == '__main__':
    sys.exit(main())
