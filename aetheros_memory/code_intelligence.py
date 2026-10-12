"""Code Intelligence Memory module.

Remembers repositories, architecture, functions, classes, patterns,
coding style, and previous fixes across projects.
"""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("aetheros_memory.code_intelligence")


class CodeEntityType(str, Enum):
    REPOSITORY = "repository"
    MODULE = "module"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    METHOD = "method"
    VARIABLE = "variable"
    INTERFACE = "interface"
    ENUM = "enum"
    TYPE_ALIAS = "type_alias"
    DECORATOR = "decorator"
    TEST = "test"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    ARCHITECTURE_DECISION = "architecture_decision"


@dataclass
class CodeEntity:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: CodeEntityType = CodeEntityType.FILE
    name: str = ""
    file_path: str = ""
    line_start: int = 0
    line_end: int = 0
    signature: str = ""
    docstring: str = ""
    source_code: str = ""
    dependencies: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "file_path": self.file_path,
            "line_start": self.line_start,
            "line_end": self.line_end,
            "signature": self.signature,
            "docstring": self.docstring,
            "source_code": self.source_code,
            "dependencies": self.dependencies,
            "imports": self.imports,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeEntity":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=CodeEntityType(data.get("type", "file")),
            name=data.get("name", ""),
            file_path=data.get("file_path", ""),
            line_start=data.get("line_start", 0),
            line_end=data.get("line_end", 0),
            signature=data.get("signature", ""),
            docstring=data.get("docstring", ""),
            source_code=data.get("source_code", ""),
            dependencies=data.get("dependencies", []),
            imports=data.get("imports", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class CodeRelationship:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_id: str = ""
    target_id: str = ""
    relationship: str = ""
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "weight": self.weight,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeRelationship":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_id=data.get("source_id", ""),
            target_id=data.get("target_id", ""),
            relationship=data.get("relationship", ""),
            weight=data.get("weight", 1.0),
        )


@dataclass
class ArchitecturePattern:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    entities: List[str] = field(default_factory=list)
    pattern_type: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "entities": self.entities,
            "pattern_type": self.pattern_type,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArchitecturePattern":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            entities=data.get("entities", []),
            pattern_type=data.get("pattern_type", ""),
            confidence=data.get("confidence", 0.0),
        )


_PATTERNS: Dict[str, List[re.Pattern]] = {
    "python": [
        re.compile(r"^\s*(?:async\s+)?def\s+(\w+)\s*\((.+?)\)\s*(?:->\s*(.+?))?\s*:", re.MULTILINE),
        re.compile(r"^\s*class\s+(\w+)\s*(?:\((.+?)\))?\s*:", re.MULTILINE),
        re.compile(r"^\s*@(\w+(?:\.\w+)*)", re.MULTILINE),
        re.compile(r"^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$", re.MULTILINE),
        re.compile(r"^\s*(\w+)\s*=\s*(?:['\"].+?['\"]|True|False|None|\d+|\[\]|\{\}|\(\)|set\(\))", re.MULTILINE),
    ],
    "typescript": [
        re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.+?)\)\s*(?::\s*(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:export\s+)?(?:async\s+)?(\w+)\s*=\s*(?:async\s+)?\((.+?)\)\s*(?::\s*(.+?))?\s*=>", re.MULTILINE),
        re.compile(r"(?:export\s+)?class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:export\s+)?interface\s+(\w+)\s*(?:extends\s+(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:export\s+)?enum\s+(\w+)\s*\{", re.MULTILINE),
        re.compile(r"(?:export\s+)?type\s+(\w+)\s*=", re.MULTILINE),
        re.compile(r"^import\s+(?:.*?\s+from\s+)?['\"](.+?)['\"]", re.MULTILINE),
        re.compile(r"@(\w+)", re.MULTILINE),
    ],
    "javascript": [
        re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.+?)\)\s*(?::\s*(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:export\s+)?(?:async\s+)?(\w+)\s*=\s*(?:async\s+)?\((.+?)\)\s*(?::\s*(.+?))?\s*=>", re.MULTILINE),
        re.compile(r"(?:export\s+)?class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"^import\s+(?:.*?\s+from\s+)?['\"](.+?)['\"]", re.MULTILINE),
    ],
    "rust": [
        re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\((.+?)\)\s*(?:->\s*(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"^\s*(?:pub\s+)?(?:struct|trait|enum|impl)\s+(\w+)(?:<(.*?)>)?", re.MULTILINE),
        re.compile(r"^\s*use\s+(.+?);", re.MULTILINE),
        re.compile(r"^\s*type\s+(\w+)\s*=", re.MULTILINE),
    ],
    "go": [
        re.compile(r"^\s*func\s+(?:\(.+?\)\s+)?(\w+)\s*\((.+?)\)\s*(?:\((.+?)\)|(.+?))\s*\{", re.MULTILINE),
        re.compile(r"^\s*type\s+(\w+)\s+(?:struct|interface)\s*\{", re.MULTILINE),
        re.compile(r"^\s*import\s+\(?(.+?)\)?", re.MULTILINE | re.DOTALL),
    ],
    "java": [
        re.compile(r"(?:public|private|protected|static|\s)*(?:<.+?>)?\s*(?:[\w<>[\],\s]+)\s+(\w+)\s*\((.+?)\)\s*(?:throws\s+\w+)?\s*\{", re.MULTILINE),
        re.compile(r"(?:public|private|protected)?\s*(?:abstract|final|static)?\s*class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:public|private|protected)?\s*interface\s+(\w+)\s*(?:extends\s+(.+?))?\s*\{", re.MULTILINE),
        re.compile(r"(?:public|private|protected)?\s*enum\s+(\w+)\s*\{", re.MULTILINE),
        re.compile(r"^import\s+(.+?);", re.MULTILINE),
        re.compile(r"@(\w+)", re.MULTILINE),
    ],
}


def _detect_language(file_path: str, language: str = "") -> str:
    if language:
        return language.lower()
    ext = Path(file_path).suffix.lower()
    ext_map = {
        ".py": "python", ".pyi": "python", ".pyx": "python",
        ".ts": "typescript", ".tsx": "typescript",
        ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript",
        ".rs": "rust",
        ".go": "go",
        ".java": "java", ".kt": "java", ".kts": "java",
    }
    return ext_map.get(ext, "python")


def _parse_python_file(content: str, file_path: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = content.split("\n")

    imports: List[str] = []
    for m in re.finditer(r"^\s*(?:from\s+(\S+)\s+)?import\s+(.+)$", content, re.MULTILINE):
        if m.group(1):
            imports.append(f"{m.group(1)}.{m.group(2).split()[0]}")
        else:
            imp = m.group(2).split(",")[0].strip()
            imp = imp.split(" as ")[0].strip()
            imports.append(imp)

    entities.append(CodeEntity(
        type=CodeEntityType.FILE,
        name=Path(file_path).name,
        file_path=file_path,
        line_start=1,
        line_end=len(lines),
        source_code=content,
        imports=imports,
    ))

    for m in re.finditer(r"^\s*class\s+(\w+)\s*(?:\((.+?)\))?\s*:", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        name = m.group(1)
        sig = m.group(2) or ""
        entity_type = CodeEntityType.CLASS
        if name.endswith("Error") or name.endswith("Exception"):
            entity_type = CodeEntityType.TYPE_ALIAS
        entities.append(CodeEntity(
            type=entity_type,
            name=name,
            file_path=file_path,
            line_start=start,
            signature=f"class {name}({sig})" if sig else f"class {name}",
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*(?:async\s+)?def\s+(\w+)\s*\((.+?)\)\s*(?:->\s*(.+?))?\s*:", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        name = m.group(1)
        sig = m.group(2) or ""
        ret = m.group(3) or ""
        if name.startswith("test_"):
            entity_type = CodeEntityType.TEST
        else:
            entity_type = CodeEntityType.METHOD if content[:m.start()].rfind("class") > content[:m.start()].rfind("\n\n") else CodeEntityType.FUNCTION
        sig_str = f"def {name}({sig})" + (f" -> {ret}" if ret else "")
        entities.append(CodeEntity(
            type=entity_type,
            name=name,
            file_path=file_path,
            line_start=start,
            signature=sig_str,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*@(\w+(?:\.\w+)*)", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.DECORATOR,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip(),
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*(\w+)\s*=\s*(?:['\"].+?['\"]|True|False|None|\d+|\[\]|\{\}|\(\)|set\(\))", content, re.MULTILINE):
        var_name = m.group(1)
        if var_name.isupper():
            entity_type = CodeEntityType.CONFIG
        else:
            entity_type = CodeEntityType.VARIABLE
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=entity_type,
            name=var_name,
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip(),
            source_code=m.group(0),
            imports=imports,
        ))

    return entities


def _parse_typescript_file(content: str, file_path: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = content.split("\n")

    imports: List[str] = []
    for m in re.finditer(r"""^import\s+(?:.*?\s+from\s+)?['\"](.+?)['\"]""", content, re.MULTILINE):
        imports.append(m.group(1))

    entities.append(CodeEntity(
        type=CodeEntityType.FILE,
        name=Path(file_path).name,
        file_path=file_path,
        line_start=1,
        line_end=len(lines),
        source_code=content,
        imports=imports,
    ))

    for m in re.finditer(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.+?)\)\s*(?::\s*(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.FUNCTION,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:export\s+)?(?:async\s+)?(\w+)\s*=\s*(?:async\s+)?\((.+?)\)\s*(?::\s*(.+?))?\s*=>", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.FUNCTION,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:export\s+)?class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.CLASS,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:export\s+)?interface\s+(\w+)\s*(?:extends\s+(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.INTERFACE,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:export\s+)?enum\s+(\w+)\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.ENUM,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:export\s+)?type\s+(\w+)\s*=", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.TYPE_ALIAS,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"@(\w+)", content):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.DECORATOR,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    return entities


def _parse_rust_file(content: str, file_path: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = content.split("\n")

    imports: List[str] = []
    for m in re.finditer(r"^\s*use\s+(.+?);", content, re.MULTILINE):
        imports.append(m.group(1))

    entities.append(CodeEntity(
        type=CodeEntityType.FILE,
        name=Path(file_path).name,
        file_path=file_path,
        line_start=1,
        line_end=len(lines),
        source_code=content,
        imports=imports,
    ))

    for m in re.finditer(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)\s*\((.+?)\)\s*(?:->\s*(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        name = m.group(1)
        if name.startswith("test_"):
            entity_type = CodeEntityType.TEST
        else:
            entity_type = CodeEntityType.FUNCTION
        entities.append(CodeEntity(
            type=entity_type,
            name=name,
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*(?:pub\s+)?(?:struct|trait|enum)\s+(\w+)", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        kw = m.group(0).strip().split()[1] if m.group(0).strip().startswith("pub") else m.group(0).strip().split()[0]
        type_map = {"struct": CodeEntityType.CLASS, "trait": CodeEntityType.INTERFACE, "enum": CodeEntityType.ENUM}
        entities.append(CodeEntity(
            type=type_map.get(kw, CodeEntityType.CLASS),
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*type\s+(\w+)\s*=", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.TYPE_ALIAS,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    return entities


def _parse_go_file(content: str, file_path: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = content.split("\n")

    imports: List[str] = []
    for m in re.finditer(r"^\s*import\s+\(?(.+?)\)?", content, re.MULTILINE | re.DOTALL):
        block = m.group(1)
        if block:
            for imp in re.findall(r'["](.+?)["]', block):
                imports.append(imp)

    entities.append(CodeEntity(
        type=CodeEntityType.FILE,
        name=Path(file_path).name,
        file_path=file_path,
        line_start=1,
        line_end=len(lines),
        source_code=content,
        imports=imports,
    ))

    for m in re.finditer(r"^\s*func\s+(?:\(.+?\)\s+)?(\w+)\s*\((.+?)\)\s*(?:\((.+?)\)|(\w+))\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.FUNCTION,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"^\s*type\s+(\w+)\s+(?:struct|interface)\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        kw = m.group(0).strip().split()[2]
        type_map = {"struct": CodeEntityType.CLASS, "interface": CodeEntityType.INTERFACE}
        entities.append(CodeEntity(
            type=type_map.get(kw, CodeEntityType.CLASS),
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    return entities


def _parse_java_file(content: str, file_path: str) -> List[CodeEntity]:
    entities: List[CodeEntity] = []
    lines = content.split("\n")

    imports: List[str] = []
    for m in re.finditer(r"^import\s+(.+?);", content, re.MULTILINE):
        imports.append(m.group(1))

    entities.append(CodeEntity(
        type=CodeEntityType.FILE,
        name=Path(file_path).name,
        file_path=file_path,
        line_start=1,
        line_end=len(lines),
        source_code=content,
        imports=imports,
    ))

    for m in re.finditer(r"(?:public|private|protected|static|\s)*(?:<.+?>)?\s*[\w<>[\],\s]+\s+(\w+)\s*\((.+?)\)\s*(?:throws\s+\w+)?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.METHOD if "class" in content[:m.start()] else CodeEntityType.FUNCTION,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:public|private|protected)?\s*(?:abstract|final|static)?\s*class\s+(\w+)\s*(?:extends\s+(\w+))?\s*(?:implements\s+(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.CLASS,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            signature=m.group(0).strip()[:200],
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:public|private|protected)?\s*interface\s+(\w+)\s*(?:extends\s+(.+?))?\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.INTERFACE,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"(?:public|private|protected)?\s*enum\s+(\w+)\s*\{", content, re.MULTILINE):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.ENUM,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    for m in re.finditer(r"@(\w+)", content):
        start = content[:m.start()].count("\n") + 1
        entities.append(CodeEntity(
            type=CodeEntityType.DECORATOR,
            name=m.group(1),
            file_path=file_path,
            line_start=start,
            source_code=m.group(0),
            imports=imports,
        ))

    return entities


_PARSERS = {
    "python": _parse_python_file,
    "typescript": _parse_typescript_file,
    "javascript": _parse_typescript_file,
    "rust": _parse_rust_file,
    "go": _parse_go_file,
    "java": _parse_java_file,
}


class CodeIntelligence:
    """Indexes, stores, and queries code entities and relationships across repositories."""

    def __init__(self, storage_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._entities: Dict[str, CodeEntity] = {}
        self._relationships: Dict[str, CodeRelationship] = {}
        self._patterns: Dict[str, ArchitecturePattern] = {}
        self._entity_by_name: Dict[str, List[str]] = {}
        self._storage_path: Optional[str] = storage_path

    def index_file(self, file_path: str, content: str, language: str = "") -> List[CodeEntity]:
        lang = _detect_language(file_path, language)
        parser = _PARSERS.get(lang)
        if parser is None:
            logger.warning("No parser for language %s, file %s", lang, file_path)
            return []
        entities = parser(content, file_path)
        with self._lock:
            for entity in entities:
                self._entities[entity.id] = entity
                key = f"{entity.name}:{entity.type.value}"
                if key not in self._entity_by_name:
                    self._entity_by_name[key] = []
                self._entity_by_name[key].append(entity.id)
        return entities

    def index_repository(self, repo_path: str, repo_name: str, language: str = "") -> Dict[str, Any]:
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.is_dir():
            return {"error": f"Directory not found: {repo_path}", "indexed": 0, "files": 0}
        repo_entity = CodeEntity(
            type=CodeEntityType.REPOSITORY,
            name=repo_name,
            file_path=repo_path,
            metadata={"language": language, "path": repo_path},
        )
        with self._lock:
            self._entities[repo_entity.id] = repo_entity
        total_entities = 0
        total_files = 0
        extensions = self._language_extensions(language) if language else None
        for file_path in repo_path_obj.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith("."):
                if extensions and file_path.suffix.lower() not in extensions:
                    continue
                try:
                    content = file_path.read_text(encoding="utf-8", errors="replace")
                    entities = self.index_file(str(file_path), content, language)
                    total_entities += len(entities)
                    total_files += 1
                    for ent in entities:
                        self._entities[ent.id] = ent
                except Exception as exc:
                    logger.debug("Skipping file %s: %s", file_path, exc)
        return {"repo": repo_name, "indexed": total_entities, "files": total_files, "path": repo_path}

    def _language_extensions(self, language: str) -> Set[str]:
        mapping = {
            "python": {".py", ".pyi", ".pyx"},
            "typescript": {".ts", ".tsx"},
            "javascript": {".js", ".jsx", ".mjs"},
            "rust": {".rs"},
            "go": {".go"},
            "java": {".java", ".kt", ".kts"},
        }
        return mapping.get(language.lower(), set())

    def add_entity(self, entity: CodeEntity) -> CodeEntity:
        with self._lock:
            self._entities[entity.id] = entity
            key = f"{entity.name}:{entity.type.value}"
            if key not in self._entity_by_name:
                self._entity_by_name[key] = []
            self._entity_by_name[key].append(entity.id)
        return entity

    def get_entity(self, entity_id: str) -> Optional[CodeEntity]:
        with self._lock:
            return self._entities.get(entity_id)

    def find_entity(self, name: str, entity_type: Optional[CodeEntityType] = None) -> List[CodeEntity]:
        with self._lock:
            results: List[CodeEntity] = []
            for entity in self._entities.values():
                if entity.name == name and (entity_type is None or entity.type == entity_type):
                    results.append(entity)
            return results

    def add_relationship(self, source_id: str, target_id: str, relationship: str, weight: float = 1.0) -> Optional[CodeRelationship]:
        with self._lock:
            if source_id not in self._entities or target_id not in self._entities:
                return None
            rel = CodeRelationship(
                source_id=source_id,
                target_id=target_id,
                relationship=relationship,
                weight=weight,
            )
            self._relationships[rel.id] = rel
            return rel

    def get_relationships(self, entity_id: str) -> List[CodeRelationship]:
        with self._lock:
            return [
                rel for rel in self._relationships.values()
                if rel.source_id == entity_id or rel.target_id == entity_id
            ]

    def search_code(self, query: str, entity_type: Optional[CodeEntityType] = None, file_path: Optional[str] = None) -> List[CodeEntity]:
        query_lower = query.lower()
        with self._lock:
            results: List[CodeEntity] = []
            for entity in self._entities.values():
                if entity_type is not None and entity.type != entity_type:
                    continue
                if file_path is not None and entity.file_path != file_path:
                    continue
                if (query_lower in entity.name.lower()
                        or query_lower in entity.signature.lower()
                        or query_lower in entity.docstring.lower()
                        or query_lower in entity.source_code.lower()):
                    results.append(entity)
            return results

    def find_dependencies(self, entity_id: str) -> List[CodeEntity]:
        with self._lock:
            entity = self._entities.get(entity_id)
            if entity is None:
                return []
            dep_entities: List[CodeEntity] = []
            seen: Set[str] = set()
            for dep_name in entity.dependencies + entity.imports:
                for e in self._entities.values():
                    if e.id in seen:
                        continue
                    if e.name == dep_name or dep_name.endswith(f".{e.name}"):
                        dep_entities.append(e)
                        seen.add(e.id)
                        break
            return dep_entities

    def detect_pattern(self, entities: List[CodeEntity]) -> Optional[ArchitecturePattern]:
        names = set(e.name.lower() for e in entities)
        types = set(e.type for e in entities)
        combined = "\n".join(e.source_code for e in entities).lower()

        pattern_defs = [
            ("singleton", 0.7, lambda: "_instance" in combined or "get_instance" in combined),
            ("factory", 0.6, lambda: "factory" in names or any("factory" in e.name.lower() for e in entities)),
            ("mvc", 0.5, lambda: bool({"controller", "model", "view"}.intersection(names))),
            ("microservice", 0.4, lambda: bool(CodeEntityType.INTERFACE in types and len(entities) > 5)),
            ("pipeline", 0.5, lambda: "pipeline" in names or "chain" in names or "handler" in names),
            ("repository", 0.5, lambda: "repository" in names or "repo" in names),
            ("observer", 0.6, lambda: "observer" in combined or "listener" in combined or "subscribe" in combined),
            ("strategy", 0.5, lambda: "strategy" in names or any("strategy" in e.name.lower() for e in entities)),
        ]

        matched = [(name, conf) for name, conf, check in pattern_defs if check()]
        if not matched:
            return None

        matched.sort(key=lambda x: x[1], reverse=True)
        name, confidence = matched[0]
        return ArchitecturePattern(
            name=name.capitalize(),
            description=f"Detected {name} pattern across {len(entities)} entities",
            entities=[e.id for e in entities],
            pattern_type=name,
            confidence=confidence,
        )

    def get_architecture(self, repo_name: str) -> Dict[str, Any]:
        with self._lock:
            repo_entities = [e for e in self._entities.values() if repo_name in e.file_path]
            classes = [e for e in repo_entities if e.type == CodeEntityType.CLASS]
            functions = [e for e in repo_entities if e.type in (CodeEntityType.FUNCTION, CodeEntityType.METHOD)]
            interfaces = [e for e in repo_entities if e.type == CodeEntityType.INTERFACE]
            modules = set(Path(e.file_path).parent.name for e in repo_entities if e.file_path)
            pattern = self.detect_pattern(repo_entities)
            return {
                "repo": repo_name,
                "total_entities": len(repo_entities),
                "classes": [{"name": c.name, "file": c.file_path, "line": c.line_start} for c in classes],
                "functions": [{"name": f.name, "file": f.file_path, "line": f.line_start} for f in functions],
                "interfaces": [{"name": i.name, "file": i.file_path} for i in interfaces],
                "modules": sorted(modules),
                "detected_pattern": pattern.to_dict() if pattern else None,
            }

    def get_entity_graph(self, entity_id: str, depth: int = 1) -> Dict[str, Any]:
        with self._lock:
            center = self._entities.get(entity_id)
            if center is None:
                return {"nodes": [], "edges": []}
            nodes: Dict[str, Any] = {entity_id: center.to_dict()}
            edges: List[Dict[str, Any]] = []
            visited: Set[str] = {entity_id}
            current_level: Set[str] = {entity_id}
            for _ in range(depth):
                next_level: Set[str] = set()
                for eid in current_level:
                    for rel in self._relationships.values():
                        if rel.source_id == eid and rel.target_id not in visited:
                            next_level.add(rel.target_id)
                            if rel.target_id in self._entities:
                                nodes[rel.target_id] = self._entities[rel.target_id].to_dict()
                            edges.append(rel.to_dict())
                            visited.add(rel.target_id)
                        elif rel.target_id == eid and rel.source_id not in visited:
                            next_level.add(rel.source_id)
                            if rel.source_id in self._entities:
                                nodes[rel.source_id] = self._entities[rel.source_id].to_dict()
                            edges.append(rel.to_dict())
                            visited.add(rel.source_id)
                current_level = next_level
            return {"nodes": list(nodes.values()), "edges": edges}

    def export_json(self, filepath: Optional[str] = None) -> str:
        with self._lock:
            data = {
                "entities": [e.to_dict() for e in self._entities.values()],
                "relationships": [r.to_dict() for r in self._relationships.values()],
                "patterns": [p.to_dict() for p in self._patterns.values()],
                "exported_at": time.time(),
            }
        json_str = json.dumps(data, indent=2, default=str)
        if filepath:
            Path(filepath).write_text(json_str, encoding="utf-8")
        return json_str

    def import_json(self, filepath: str) -> int:
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        count = 0
        with self._lock:
            for ed in data.get("entities", []):
                entity = CodeEntity.from_dict(ed)
                self._entities[entity.id] = entity
                key = f"{entity.name}:{entity.type.value}"
                if key not in self._entity_by_name:
                    self._entity_by_name[key] = []
                self._entity_by_name[key].append(entity.id)
                count += 1
            for rd in data.get("relationships", []):
                rel = CodeRelationship.from_dict(rd)
                self._relationships[rel.id] = rel
            for pd in data.get("patterns", []):
                pattern = ArchitecturePattern.from_dict(pd)
                self._patterns[pattern.id] = pattern
        return count

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            type_counts: Dict[str, int] = {}
            for entity in self._entities.values():
                type_counts[entity.type.value] = type_counts.get(entity.type.value, 0) + 1
            return {
                "total_entities": len(self._entities),
                "total_relationships": len(self._relationships),
                "total_patterns": len(self._patterns),
                "entities_by_type": type_counts,
                "storage_path": self._storage_path,
            }

    def persist(self) -> None:
        if self._storage_path:
            self.export_json(self._storage_path)
            logger.info("CodeIntelligence persisted to %s", self._storage_path)