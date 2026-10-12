from __future__ import annotations
import ast, json, logging, os, re, time, uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

class IndexEntry:
    def __init__(self, file_path: str, symbols: list[dict[str, Any]] = None, dependencies: list[str] = None, last_indexed: float = 0.0):
        self.file_path = file_path
        self.symbols = symbols or []
        self.dependencies = dependencies or []
        self.last_indexed = last_indexed

class CodeIndexer:
    def __init__(self, index_dir: str | None = None):
        self._index_dir = index_dir or os.path.expanduser("~/.aetheros/developer/index")
        os.makedirs(self._index_dir, exist_ok=True)
        self._indexes: dict[str, dict[str, IndexEntry]] = {}

    def index_project(self, project_path: str, project_id: str) -> dict[str, Any]:
        project_path = os.path.abspath(project_path)
        index: dict[str, IndexEntry] = {}
        stats = {"files_indexed": 0, "total_symbols": 0, "errors": []}
        for root, dirs, files in os.walk(project_path):
            dirs[:] = [d for d in dirs if not d.startswith((".", "node_modules", "__pycache__", "venv", ".venv", "target", "build", "dist", ".git"))]
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, project_path)
                try:
                    entry = self._index_file(file_path, rel_path)
                    if entry:
                        index[rel_path] = entry
                        stats["files_indexed"] += 1
                        stats["total_symbols"] += len(entry.symbols)
                except Exception as e:
                    stats["errors"].append(str(rel_path))
                    logger.debug("Failed to index %s: %s", rel_path, e)
        self._indexes[project_id] = index
        self._persist_index(project_id, index)
        return stats

    def _index_file(self, file_path: str, rel_path: str) -> IndexEntry | None:
        ext = os.path.splitext(file_path)[1].lower()
        try:
            with open(file_path, encoding="utf-8", errors="replace") as f:
                content = f.read()
        except Exception:
            return None
        symbols: list[dict[str, Any]] = []
        deps: list[str] = self._extract_dependencies(content, ext)
        if ext == ".py":
            symbols = self._index_python(content, file_path)
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            symbols = self._index_jsts(content, file_path)
        elif ext in (".rs",):
            symbols = self._index_rust(content, file_path)
        elif ext in (".go",):
            symbols = self._index_go(content, file_path)
        elif ext in (".java",):
            symbols = self._index_java(content, file_path)
        else:
            lines = content.split("\n")
            for i, line in enumerate(lines):
                line_s = line.strip()
                if line_s.startswith(("function ", "def ", "class ", "fn ", "func ", "export function", "export class", "export default")):
                    symbols.append({"name": line_s.split()[1] if len(line_s.split()) > 1 else line_s, "kind": "function" if "function" in line_s or "def " in line_s else "class", "line": i + 1})
        if not symbols:
            symbols = [{"name": os.path.basename(file_path), "kind": "file", "line": 1}]
        return IndexEntry(file_path=rel_path, symbols=symbols, dependencies=deps, last_indexed=time.time())

    def _extract_dependencies(self, content: str, ext: str) -> list[str]:
        deps: list[str] = []
        if ext == ".py":
            for m in re.finditer(r'^(?:from\s+(\S+)\s+import|import\s+(\S+))', content, re.MULTILINE):
                deps.append(m.group(1) or m.group(2))
        elif ext in (".js", ".jsx", ".ts", ".tsx"):
            for m in re.finditer(r'(?:import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+[\'"]([^\'"]+)[\'"]|require\([\'"]([^\'"]+)[\'"]\))', content):
                deps.append(m.group(1) or m.group(2))
        return deps

    def _index_python(self, content: str, file_path: str) -> list[dict[str, Any]]:
        symbols = []
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append({"name": node.name, "kind": "function", "line": node.lineno, "end_line": node.end_lineno})
                elif isinstance(node, ast.ClassDef):
                    methods = [{"name": m.name, "kind": "method", "line": m.lineno} for m in node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
                    symbols.append({"name": node.name, "kind": "class", "line": node.lineno, "methods": methods})
        except SyntaxError:
            pass
        return symbols

    def _index_jsts(self, content: str, file_path: str) -> list[dict[str, Any]]:
        symbols = []
        patterns = [
            (r'(?:export\s+)?(?:async\s+)?function\s+(\w+)', "function"),
            (r'(?:export\s+)?class\s+(\w+)', "class"),
            (r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\([^)]*\)\s*=>)', "function"),
            (r'(?:export\s+)?interface\s+(\w+)', "interface"),
            (r'(?:export\s+)?type\s+(\w+)', "type"),
            (r'(?:export\s+)?enum\s+(\w+)', "enum"),
            (r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)', "class"),
        ]
        for i, line in enumerate(content.split("\n"), 1):
            for pat, kind in patterns:
                m = re.search(pat, line)
                if m:
                    symbols.append({"name": m.group(1), "kind": kind, "line": i})
                    break
        return symbols

    def _index_rust(self, content: str, file_path: str) -> list[dict[str, Any]]:
        symbols = []
        for i, line in enumerate(content.split("\n"), 1):
            m = re.search(r'(?:pub\s+)?fn\s+(\w+)', line)
            if m:
                symbols.append({"name": m.group(1), "kind": "function", "line": i})
            m = re.search(r'(?:pub\s+)?(?:struct|enum|trait|impl)\s+(\w+)', line)
            if m:
                symbols.append({"name": m.group(1), "kind": "struct" if "struct" in line else "enum" if "enum" in line else "trait" if "trait" in line else "impl", "line": i})
        return symbols

    def _index_go(self, content: str, file_path: str) -> list[dict[str, Any]]:
        symbols = []
        for i, line in enumerate(content.split("\n"), 1):
            m = re.search(r'func\s+(\w+)', line)
            if m:
                symbols.append({"name": m.group(1), "kind": "function", "line": i})
            m = re.search(r'type\s+(\w+)\s+(?:struct|interface)', line)
            if m:
                symbols.append({"name": m.group(1), "kind": "type", "line": i})
        return symbols

    def _index_java(self, content: str, file_path: str) -> list[dict[str, Any]]:
        symbols = []
        for i, line in enumerate(content.split("\n"), 1):
            m = re.search(r'(?:public|private|protected)\s+(?:static\s+)?(?:class|interface|enum)\s+(\w+)', line)
            if m:
                symbols.append({"name": m.group(1), "kind": "class", "line": i})
            m = re.search(r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+\s+)*(\w+)\s*\(', line)
            if m and not re.search(r'(?:if|while|for|switch|catch)\s*\(', line):
                symbols.append({"name": m.group(1), "kind": "method", "line": i})
        return symbols

    def search(self, query: str, project_id: str, search_type: str = "text") -> list[dict[str, Any]]:
        query_lower = query.lower()
        results = []
        index = self._indexes.get(project_id) or self._load_index(project_id)
        if not index:
            return results
        for rel_path, entry in index.items():
            if search_type == "text":
                if query_lower in rel_path.lower():
                    results.append({"type": "file", "file": rel_path, "match": rel_path})
            elif search_type == "symbol":
                for sym in entry.symbols:
                    if query_lower in sym.get("name", "").lower():
                        results.append({"type": "symbol", "file": rel_path, "symbol": sym["name"], "kind": sym.get("kind", ""), "line": sym.get("line", 0)})
            elif search_type == "dependency":
                for dep in entry.dependencies:
                    if query_lower in dep.lower():
                        results.append({"type": "dependency", "file": rel_path, "dependency": dep})
            elif search_type == "all":
                if query_lower in rel_path.lower():
                    results.append({"type": "file", "file": rel_path, "match": rel_path})
                for sym in entry.symbols:
                    if query_lower in sym.get("name", "").lower():
                        results.append({"type": "symbol", "file": rel_path, "symbol": sym["name"], "kind": sym.get("kind", ""), "line": sym.get("line", 0)})
        results = results[:100]
        return results

    def semantic_search(self, query: str, project_id: str, max_results: int = 20) -> list[dict[str, Any]]:
        results = self.search(query, project_id, "all")
        scored = []
        query_words = set(query.lower().split())
        for r in results:
            score = 0
            name = r.get("symbol", r.get("file", "")).lower()
            for qw in query_words:
                if qw in name:
                    score += 10
                if name.startswith(qw) or name.endswith(qw):
                    score += 5
            if "authentication" in query.lower() and any(w in name for w in ["auth", "login", "token", "session", "password", "credential"]):
                score += 15
            if r.get("kind") == "class":
                score += 3
            scored.append((score, r))
        scored.sort(key=lambda x: -x[0])
        return [r for _, r in scored[:max_results]]

    def get_file_symbols(self, rel_path: str, project_id: str) -> list[dict[str, Any]]:
        index = self._indexes.get(project_id) or self._load_index(project_id)
        if index and rel_path in index:
            return index[rel_path].symbols
        return []

    def get_project_summary(self, project_id: str) -> dict[str, Any]:
        index = self._indexes.get(project_id) or self._load_index(project_id)
        if not index:
            return {"files": 0, "symbols": 0, "languages": {}}
        total_symbols = 0
        file_types: dict[str, int] = {}
        for rel_path, entry in index.items():
            ext = os.path.splitext(rel_path)[1].lower()
            file_types[ext] = file_types.get(ext, 0) + 1
            total_symbols += len(entry.symbols)
        return {"files": len(index), "symbols": total_symbols, "languages": file_types, "last_indexed": time.time()}

    def _persist_index(self, project_id: str, index: dict[str, IndexEntry]):
        data = {}
        for rel_path, entry in index.items():
            data[rel_path] = {"file_path": entry.file_path, "symbols": entry.symbols, "dependencies": entry.dependencies, "last_indexed": entry.last_indexed}
        path = os.path.join(self._index_dir, f"{project_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_index(self, project_id: str) -> dict[str, IndexEntry] | None:
        path = os.path.join(self._index_dir, f"{project_id}.json")
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            index = {}
            for rel_path, d in data.items():
                entry = IndexEntry(file_path=d["file_path"], symbols=d.get("symbols", []), dependencies=d.get("dependencies", []), last_indexed=d.get("last_indexed", 0))
                index[rel_path] = entry
            self._indexes[project_id] = index
            return index
        except Exception:
            return None

    def clear_index(self, project_id: str):
        self._indexes.pop(project_id, None)
        path = os.path.join(self._index_dir, f"{project_id}.json")
        if os.path.isfile(path):
            os.remove(path)
