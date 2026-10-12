"""CLI commands — aetheros knowledge, memory, rag."""

from __future__ import annotations

import json
import logging
import os
import sys
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.web.api import KnowledgeAPI
from aetheros_knowledge.models import SourceType

logger = logging.getLogger(__name__)


def build_knowledge_parser(subparsers):
    p = subparsers.add_parser("knowledge", help="Knowledge Center")
    subs = p.add_subparsers(dest="knowledge_command")

    subs.add_parser("status", help="Knowledge Center status")

    p_list = subs.add_parser("list", help="List documents")
    p_list.add_argument("--collection", "-c", default="", help="Collection ID")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--json", action="store_true", help="JSON output")

    p_search = subs.add_parser("search", help="Search documents")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--mode", choices=["fulltext", "semantic", "hybrid"],
                          default="hybrid")
    p_search.add_argument("--collection", "-c", default="")
    p_search.add_argument("--limit", type=int, default=10)

    p_add = subs.add_parser("add", help="Add a document")
    p_add.add_argument("path", help="File or folder path")
    p_add.add_argument("--collection", "-c", default="documents")
    p_add.add_argument("--recursive", "-r", action="store_true")
    p_add.add_argument("--index", action="store_true", help="Index immediately")

    p_import_cmd = subs.add_parser("import", help="Import documents")
    p_import_cmd.add_argument("path", help="File, folder, or URL")
    p_import_cmd.add_argument("--collection", "-c", default="documents")
    p_import_cmd.add_argument("--recursive", "-r", action="store_true")

    p_export = subs.add_parser("export", help="Export collection")
    p_export.add_argument("collection_id", help="Collection ID")
    p_export.add_argument("--output", "-o", default="", help="Output file")

    p_index = subs.add_parser("index", help="Index documents")
    p_index.add_argument("--doc", default="", help="Document ID")
    p_index.add_argument("--all", action="store_true", help="Index all pending")

    p_delete = subs.add_parser("delete", help="Delete a document")
    p_delete.add_argument("document_id", help="Document ID")

    p_trash = subs.add_parser("trash", help="Trash a document")
    p_trash.add_argument("document_id", help="Document ID")

    clist = subs.add_parser("collections", help="List collections")
    clist.add_argument("--json", action="store_true", help="JSON output")

    p_cc = subs.add_parser("collection-create", help="Create collection")
    p_cc.add_argument("name", help="Collection name")
    p_cc.add_argument("--description", "-d", default="")
    p_cc.add_argument("--icon", default="folder")
    p_cc.add_argument("--color", default="#6366f1")

    p_cd = subs.add_parser("collection-delete", help="Delete collection")
    p_cd.add_argument("collection_id", help="Collection ID")


def build_memory_parser(subparsers):
    p = subparsers.add_parser("memory", help="Memory Engine")
    subs = p.add_subparsers(dest="memory_command")

    subs.add_parser("status", help="Memory status")

    p_list = subs.add_parser("list", help="List memories")
    p_list.add_argument("--type", choices=["personal", "workspace", "agent",
                                           "project", "temporary", "long_term"],
                        default="")
    p_list.add_argument("--json", action="store_true")

    p_set = subs.add_parser("set", help="Store a memory")
    p_set.add_argument("key", help="Memory key")
    p_set.add_argument("value", help="Memory value")
    p_set.add_argument("--type", choices=["personal", "workspace", "agent",
                                          "project", "temporary", "long_term"],
                       default="personal")
    p_set.add_argument("--importance", type=float, default=0.5)

    p_get = subs.add_parser("get", help="Get a memory")
    p_get.add_argument("key", help="Memory key")
    p_get.add_argument("--type", default="")

    p_del = subs.add_parser("delete", help="Delete a memory")
    p_del.add_argument("key", help="Memory key")
    p_del.add_argument("--type", default="")

    p_clear = subs.add_parser("clear", help="Clear memories")
    p_clear.add_argument("--type", choices=["personal", "workspace", "agent",
                                            "project", "temporary", "long_term"],
                        default="")

    subs.add_parser("export", help="Export all memories")
    p_import_mem = subs.add_parser("import", help="Import memories")
    p_import_mem.add_argument("file", help="JSON file")
    subs.add_parser("backup", help="Backup memories")
    p_restore = subs.add_parser("restore", help="Restore memories")
    p_restore.add_argument("file", help="Backup file")
    subs.add_parser("reset", help="Reset all memories")


def build_rag_parser(subparsers):
    p = subparsers.add_parser("rag", help="RAG Studio")
    subs = p.add_subparsers(dest="rag_command")

    subs.add_parser("status", help="RAG Studio status")

    p_list = subs.add_parser("list", help="List pipelines")

    p_create = subs.add_parser("create", help="Create a pipeline")
    p_create.add_argument("name", help="Pipeline name")
    p_create.add_argument("--description", "-d", default="")
    p_create.add_argument("--embedder", choices=["openai", "cohere", "jina",
                                                  "voyage", "ollama",
                                                  "sentence-transformers",
                                                  "local"],
                          default="sentence-transformers")
    p_create.add_argument("--vector-store", choices=["chroma", "faiss", "qdrant",
                                                      "milvus", "sqlite"],
                          default="sqlite")
    p_create.add_argument("--chunk-size", type=int, default=512)
    p_create.add_argument("--chunk-overlap", type=int, default=64)
    p_create.add_argument("--top-k", type=int, default=5)
    p_create.add_argument("--no-hybrid", action="store_true")

    p_ret = subs.add_parser("retrieve", help="Retrieve with a pipeline")
    p_ret.add_argument("pipeline_id", help="Pipeline ID")
    p_ret.add_argument("query", help="Search query")
    p_ret.add_argument("--top-k", type=int, default=5)

    p_eval = subs.add_parser("evaluate", help="Evaluate a pipeline")
    p_eval.add_argument("pipeline_id", help="Pipeline ID")
    p_eval.add_argument("--queries", nargs="+", help="Query,expected_id pairs")

    p_del = subs.add_parser("delete", help="Delete a pipeline")
    p_del.add_argument("pipeline_id", help="Pipeline ID")


def handle_knowledge_command(args):
    api = KnowledgeAPI()
    cmd = args.knowledge_command if hasattr(args, "knowledge_command") else None
    if not cmd:
        _show_knowledge_status(api)
        return
    if cmd == "status":
        _show_knowledge_status(api)
    elif cmd == "list":
        _list_documents(api, args)
    elif cmd == "search":
        _search_documents(api, args)
    elif cmd == "add":
        _add_document(api, args)
    elif cmd == "import":
        _import_document(api, args)
    elif cmd == "export":
        _export_collection(api, args)
    elif cmd == "index":
        _index_documents(api, args)
    elif cmd == "delete":
        _delete_document(api, args)
    elif cmd == "trash":
        _trash_document(api, args)
    elif cmd == "collections":
        _list_collections(api, args)
    elif cmd == "collection-create":
        _create_collection(api, args)
    elif cmd == "collection-delete":
        _delete_collection(api, args)
    else:
        print(f"Unknown knowledge command: {cmd}")


def handle_memory_command(args):
    from aetheros_knowledge.models import MemoryType
    api = KnowledgeAPI()
    cmd = args.memory_command if hasattr(args, "memory_command") else None
    if not cmd:
        _show_memory_status(api)
        return
    if cmd == "status":
        _show_memory_status(api)
    elif cmd == "list":
        mt = MemoryType(args.type) if args.type else None
        entries = api.memory.store.list_memory(mt)
        for e in entries:
            val = str(e.value)[:80]
            print(f"  {e.key:30s} {val}")
    elif cmd == "set":
        api.memory._store_memory(MemoryType(args.type), args.key, args.value,
                                  importance=args.importance)
        print(f"Stored memory: {args.key}")
    elif cmd == "get":
        if args.type:
            e = api.store.get_memory(args.key, MemoryType(args.type))
        else:
            e = api.store.get_memory(args.key)
        if e:
            print(f"  Key: {e.key}")
            print(f"  Value: {e.value}")
            print(f"  Type: {e.memory_type.value}")
            print(f"  Importance: {e.importance}")
        else:
            print("Memory not found")
    elif cmd == "delete":
        if args.type:
            api.store.delete_memory(args.key, MemoryType(args.type))
        else:
            api.store.delete_memory(args.key)
        print(f"Deleted memory: {args.key}")
    elif cmd == "clear":
        if args.type:
            api.memory.clear_type(MemoryType(args.type))
            print(f"Cleared {args.type} memories")
        else:
            api.memory.clear_all()
            print("Cleared all memories")
    elif cmd == "export":
        data = api.memory.export_memory()
        print(data)
    elif cmd == "import":
        with open(args.file, "r", encoding="utf-8") as f:
            count = api.memory.import_memory(f.read())
        print(f"Imported {count} memories")
    elif cmd == "backup":
        data = api.memory.backup()
        print(data)
    elif cmd == "restore":
        with open(args.file, "r", encoding="utf-8") as f:
            count = api.memory.restore(f.read())
        print(f"Restored {count} memories")
    elif cmd == "reset":
        api.memory.reset()
        print("Memories reset")


def handle_rag_command(args):
    api = KnowledgeAPI()
    cmd = args.rag_command if hasattr(args, "rag_command") else None
    if not cmd:
        print("RAG Studio")
        print(f"  Pipelines: {len(api.rag.list_pipelines())}")
        return
    if cmd == "status":
        print("RAG Studio: available")
        print(f"  Pipelines: {len(api.rag.list_pipelines())}")
        print(f"  Embedders: {len(api.rag.get_embedder_info())}")
    elif cmd == "list":
        pipelines = api.rag.list_pipelines()
        for p in pipelines:
            print(f"  {p.id:12s} {p.name:20s} {p.embedder:20s} {p.vector_store:10s}")
    elif cmd == "create":
        p = api.rag.create_pipeline(
            name=args.name, description=args.description or "",
            embedder=args.embedder, vector_store=args.vector_store,
            chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap,
            top_k=args.top_k, hybrid_search=not args.no_hybrid)
        print(f"Created pipeline: {p.id}")
    elif cmd == "retrieve":
        results = api.rag.retrieve(
            api.rag.get_pipeline(args.pipeline_id), args.query, args.top_k)
        for r in results:
            print(f"  [{r['score']:.4f}] {r.get('content', '')[:120]}")
    elif cmd == "evaluate":
        print("Evaluation: run via API with test queries")
    elif cmd == "delete":
        api.rag.delete_pipeline(args.pipeline_id)
        print("Pipeline deleted")


def _show_knowledge_status(api: KnowledgeAPI):
    stats = api.store.get_stats()
    print("Knowledge Center")
    print(f"  Documents: {stats['documents']}")
    print(f"  Indexed:   {stats['indexed']}")
    print(f"  Chunks:    {stats['chunks']}")
    print(f"  Collections: {stats['collections']}")
    print(f"  Memory entries: {stats['memory_entries']}")
    print(f"  Vector backend: {api.get_config()['auto_detected']}")


def _list_documents(api, args):
    docs = api.center.list_documents(
        collection_id=args.collection or None, limit=args.limit)
    if args.json:
        print(json.dumps([api._doc_to_dict(d) for d in docs], indent=2))
        return
    for d in docs:
        print(f"  {d.id:12s} {d.title:40s} {d.source_type.value:10s} {d.status.value:10s}")


def _search_documents(api, args):
    if args.mode == "fulltext":
        results = api.search.fulltext_search(args.query, args.collection or None, args.limit)
    elif args.mode == "semantic":
        results = api.search.semantic_search(args.query, args.limit)
    else:
        results = api.search.hybrid_search(args.query, args.limit, args.collection or None)
    for r in results:
        score = r.get("score", r.get("semantic_score", 0))
        content = r.get("content", r.get("title", ""))[:120]
        print(f"  [{score:.4f}] {content}")


def _add_document(api, args):
    import os
    path = args.path
    if os.path.isdir(path):
        docs = api.center.import_folder(path, args.collection, args.recursive)
        print(f"Imported {len(docs)} documents from folder")
    else:
        doc = api.center.import_file(path, args.collection)
        if doc:
            print(f"Added document: {doc.id}")
            if args.index:
                api.pipeline.index_document(doc)
                print("Indexed")
        else:
            print("Failed to import file")


def _import_document(api, args):
    _add_document(api, args)


def _export_collection(api, args):
    result = api.sharing.export_collection(args.collection_id, args.output or None)
    if result:
        print(f"Exported: {result}")
    else:
        print("Export failed")


def _index_documents(api, args):
    if args.doc:
        doc = api.center.get_document(args.doc)
        if doc:
            api.pipeline.index_document(doc)
            print(f"Indexed: {doc.id}")
        else:
            print("Document not found")
    elif args.all:
        count = api.pipeline.index_all_pending()
        print(f"Indexed {len(count)} documents")
    else:
        print("Specify --doc or --all")


def _delete_document(api, args):
    api.center.delete_document(args.document_id)
    print("Deleted")


def _trash_document(api, args):
    api.center.trash_document(args.document_id)
    print("Trashed")


def _list_collections(api, args):
    cols = api.center.list_collections()
    if args.json:
        print(json.dumps([api._col_to_dict(c) for c in cols], indent=2))
        return
    for c in cols:
        print(f"  {c.id:20s} {c.name:20s} docs={c.document_count}")


def _create_collection(api, args):
    col = api.center.create_collection(
        args.name, args.description, args.icon, args.color)
    print(f"Created: {col.id}")


def _delete_collection(api, args):
    api.center.delete_collection(args.collection_id)
    print("Deleted")


def _show_memory_status(api: KnowledgeAPI):
    stats = api.memory.get_stats()
    print("Memory Engine")
    print(f"  Total entries: {stats['total']}")
    for mt, count in stats["by_type"].items():
        print(f"  {mt:20s}: {count}")
