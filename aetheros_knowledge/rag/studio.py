"""
RAG Studio — build retrieval pipelines, choose models, evaluate.

The RAG (Retrieval-Augmented Generation) system is designed for:
1. Storing and processing large documents and text corpora
2. Semantic search to find relevant information based on meaning, not just keywords
3. Chunking documents into manageable pieces for processing
4. Generating vector embeddings for semantic similarity matching
5. Retrieving the most relevant chunks to augment language model generation

This system is optimized for:
- Finding relevant information in large knowledge bases
- Answering questions based on stored documents
- Providing context for language models from relevant sources
- Handling various document formats (PDF, HTML, text, etc.)

This system is NOT designed for:
- Fast key-value lookups
- Storing simple preferences or agent states
- Managing temporary caches with TTL
- Storing small amounts of structured data

For those use cases, use the Memory Engine instead.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.models import RAGPipeline
from aetheros_knowledge.search.engine import SearchEngine
from aetheros_knowledge.vectordb import get_vectordb, VectorDB
from aetheros_knowledge.indexing.embedders import get_embedder, BaseEmbedder
from aetheros_knowledge.indexing.chunkers import chunk_text
from aetheros_knowledge.indexing.pipeline import IndexingPipeline

logger = logging.getLogger(__name__)

EMBEDDER_OPTIONS = ["openai", "cohere", "jina", "voyage", "ollama",
                     "sentence-transformers", "local"]
VECTOR_STORE_OPTIONS = ["chroma", "faiss", "qdrant", "milvus", "sqlite"]
RANKING_OPTIONS = ["cosine", "dot_product", "euclidean", "bm25"]
CHUNK_SIZES = [128, 256, 384, 512, 768, 1024]
CHUNK_OVERLAPS = [0, 16, 32, 64, 128]


class RAGStudio:
    def __init__(self, store: KnowledgeStore):
        self.store = store

    def create_pipeline(self, name: str, description: str = "",
                         embedder: str = "sentence-transformers",
                         vector_store: str = "sqlite",
                         chunk_size: int = 512,
                         chunk_overlap: int = 64,
                         ranking: str = "cosine",
                         reranking: bool = False,
                         hybrid_search: bool = True,
                         top_k: int = 5) -> RAGPipeline:
        p = RAGPipeline(
            id=str(uuid.uuid4()), name=name, description=description,
            embedder=embedder, vector_store=vector_store,
            chunk_size=chunk_size, chunk_overlap=chunk_overlap,
            ranking=ranking, reranking=reranking,
            hybrid_search=hybrid_search, top_k=top_k)
        self.store.save_pipeline(p)
        logger.info("Created RAG pipeline: %s (%s)", name, p.id)
        return p

    def get_pipeline(self, pid: str) -> Optional[RAGPipeline]:
        pipelines = self.store.list_pipelines()
        for p in pipelines:
            if p.id == pid:
                return p
        return None

    def list_pipelines(self) -> list[RAGPipeline]:
        return self.store.list_pipelines()

    def delete_pipeline(self, pid: str):
        self.store.delete_pipeline(pid)

    def build_search_engine(self, pipeline: RAGPipeline) -> SearchEngine:
        embedder = get_embedder(pipeline.embedder)
        vdb = get_vectordb(pipeline.vector_store)
        return SearchEngine(self.store, vdb, embedder, pipeline.reranking)

    def build_index_pipeline(self, pipeline: RAGPipeline) -> IndexingPipeline:
        return IndexingPipeline(
            self.store, pipeline.embedder,
            pipeline.chunk_size, pipeline.chunk_overlap)

    def retrieve(self, pipeline: RAGPipeline, query: str,
                  top_k: int = None) -> list[dict]:
        engine = self.build_search_engine(pipeline)
        k = top_k or pipeline.top_k
        if pipeline.hybrid_search:
            return engine.hybrid_search(query, k)
        else:
            results = engine.semantic_search(query, k)
            return [{"id": r.id, "content": r.content,
                      "score": r.score, "metadata": r.metadata}
                    for r in results]

    def evaluate(self, pipeline: RAGPipeline,
                  test_queries: list[tuple[str, str]]) -> dict:
        engine = self.build_search_engine(pipeline)
        total = len(test_queries)
        hits = 0
        reciprocal_ranks = []
        for query, expected_doc_id in test_queries:
            results = engine.hybrid_search(query, pipeline.top_k)
            for i, r in enumerate(results):
                if r["id"].startswith(expected_doc_id) or \
                   r.get("metadata", {}).get("document_id") == expected_doc_id:
                    hits += 1
                    reciprocal_ranks.append(1.0 / (i + 1))
                    break
            else:
                reciprocal_ranks.append(0.0)
        return {
            "total_queries": total,
            "hits": hits,
            "hit_rate": round(hits / max(total, 1), 4),
            "mrr": round(sum(reciprocal_ranks) / max(total, 1), 4),
            "pipeline": pipeline.name,
            "config": {
                "embedder": pipeline.embedder,
                "vector_store": pipeline.vector_store,
                "chunk_size": pipeline.chunk_size,
                "hybrid": pipeline.hybrid_search,
            },
        }

    def get_embedder_info(self) -> list[dict]:
        return [{"name": name, "available": True}
                for name in EMBEDDER_OPTIONS]

    def get_vector_store_info(self) -> list[dict]:
        from aetheros_knowledge.vectordb import VECTORDB_MAP
        return [{"name": name, "available": name in VECTORDB_MAP}
                for name in VECTOR_STORE_OPTIONS]

    # --- RAG Enhancement Methods ---
    def expand_query(self, query: str, 
                    expansion_terms: int = 3,
                    use_synonyms: bool = True,
                    use_related: bool = True) -> str:
        """
        Expand a query with related terms to improve retrieval performance.
        
        This method enhances the original query with additional terms that might
        help retrieve more relevant documents. It can use synonyms, related terms,
        or other expansion techniques.
        
        Args:
            query: The original search query
            expansion_terms: Maximum number of expansion terms to add
            use_synonyms: Whether to include synonym-based expansion
            use_related: Whether to include related term expansion
            
        Returns:
            Expanded query string
        """
        # Simple implementation - in a production system, this would use
        # WordNet, embeddings, or other NLP techniques
        expanded_parts = [query]
        
        if use_synonyms:
            # Basic synonym expansion (in practice, use a proper synonym library)
            synonym_map = {
                "AI": ["artificial intelligence", "machine learning"],
                "ML": ["machine learning", "deep learning"],
                "NLP": ["natural language processing", "computational linguistics"],
                "DL": ["deep learning", "neural networks"],
                "data": ["information", "facts", "details"],
                "method": ["approach", "technique", "procedure"],
                "result": ["outcome", "finding", "conclusion"],
                "study": ["research", "investigation", "analysis"],
                "show": ["demonstrate", "indicate", "reveal"],
                "use": ["utilize", "employ", "apply"]
            }
            
            words = query.upper().split()
            for word in words:
                if word in synonym_map and len(expanded_parts) <= expansion_terms + 1:
                    expanded_parts.extend(synonym_map[word][:expansion_terms])
                    
        if use_related and len(expanded_parts) < expansion_terms * 2:
            # Add some basic related terms based on common prefixes/suffixes
            related_additions = []
            if "learn" in query.lower():
                related_additions.extend(["training", "education", "instruction"])
            if "network" in query.lower():
                related_additions.extend(["architecture", "structure", "design"])
            if "data" in query.lower():
                related_additions.extend(["dataset", "database", "information"])
                
            for term in related_additions:
                if term not in expanded_parts and len(expanded_parts) < expansion_terms * 2:
                    expanded_parts.append(term)
        
        # Join and limit length
        expanded_query = " ".join(expanded_parts)
        # Avoid excessively long queries
        if len(expanded_query) > 500:
            expanded_query = expanded_query[:500]
            
        return expanded_query

    def tune_hybrid_search(self, alpha: float = 0.5) -> None:
        """
        Tune the balance between keyword and semantic search in hybrid search.
        
        In hybrid search, alpha controls the weight given to semantic (vector) search
        vs. keyword (BM25/text) search. Alpha=0.0 means pure keyword search,
        alpha=1.0 means pure semantic search.
        
        Args:
            alpha: Weight for semantic search (0.0-1.0)
                  0.0 = pure keyword search
                  0.5 = balanced (default)
                  1.0 = pure semantic search
        """
        # This would typically update the search engine configuration
        # For now, we'll log the recommendation
        logger.info(f"Hybrid search tuning: set alpha to {alpha} "
                   f"({alpha*100:.0f}% semantic, {(1-alpha)*100:.0f}% keyword)")
        
        # In a full implementation, this would update the underlying search engine
        # For example: self.search_engine.set_alpha(alpha)

    def diversify_results(self, results: list[dict], 
                         diversity_threshold: float = 0.8,
                         max_results: int = None) -> list[dict]:
        """
        Diversify search results to avoid redundancy.
        
        This method reduces similarity between results to provide a more diverse
        set of answers, preventing the system from returning too many similar
        documents.
        
        Args:
            results: List of search result dictionaries (with 'id', 'score', etc.)
            diversity_threshold: Similarity threshold above which results are
                               considered too similar (0.0-1.0)
            max_results: Maximum number of results to return (None for all)
                           
        Returns:
            Diversified list of results
        """
        if not results or len(results) <= 1:
            return results
            
        # Simple diversification based on result IDs (in practice, would use
        # content similarity or metadata)
        diversified = [results[0]]  # Always include the highest-ranked result
        
        for result in results[1:]:
            # Check if this result is sufficiently different from already selected ones
            is_diverse = True
            for selected in diversified:
                # Simple diversity check based on ID similarity
                # In practice, would use content similarity, metadata, etc.
                if result.get('id') == selected.get('id'):
                    is_diverse = False
                    break
                    
                # Could add more sophisticated checks here
                # For example, check if they're from the same document
                result_doc_id = result.get('metadata', {}).get('document_id')
                selected_doc_id = selected.get('metadata', {}).get('document_id')
                if result_doc_id and selected_doc_id and result_doc_id == selected_doc_id:
                    # Same document - apply diversity threshold
                    if diversity_threshold > 0.9:  # Very strict
                        is_diverse = False
                        break
            
            if is_diverse:
                diversified.append(result)
                
            # Stop if we have enough results
            if max_results and len(diversified) >= max_results:
                break
        
        logger.debug(f"Diversified results from {len(results)} to {len(diversified)}")
        return diversified

    def filter_by_metadata(self, results: list[dict],
                          filters: dict) -> list[dict]:
        """
        Filter search results based on metadata criteria.
        
        Args:
            results: List of search result dictionaries
            filters: Dictionary of metadata filters to apply
                    (e.g., {"source_type": "pdf", "language": "en"})
                           
        Returns:
            Filtered list of results
        """
        if not filters:
            return results
            
        filtered_results = []
        for result in results:
            metadata = result.get('metadata', {})
            matches = True
            
            for key, value in filters.items():
                if key not in metadata or metadata[key] != value:
                    matches = False
                    break
                    
            if matches:
                filtered_results.append(result)
                
        logger.debug(f"Filtered results from {len(results)} to {len(filtered_results)}")
        return filtered_results

    def get_defaults(self) -> dict:
        return {
            "embedder": "sentence-transformers",
            "vector_store": "sqlite",
            "chunk_size": 512,
            "chunk_overlap": 64,
            "ranking": "cosine",
            "reranking": False,
            "hybrid_search": True,
            "top_k": 5,
            "embedder_options": EMBEDDER_OPTIONS,
            "vector_store_options": VECTOR_STORE_OPTIONS,
            "chunk_sizes": CHUNK_SIZES,
            "chunk_overlaps": CHUNK_OVERLAPS,
        }
