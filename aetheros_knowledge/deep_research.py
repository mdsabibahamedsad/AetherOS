"""Deep Research Engine for iterative, source-backed investigation."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Callable, Dict, List, Optional

from aetheros_knowledge.store import KnowledgeStore
from aetheros_knowledge.search.engine import SearchEngine
from aetheros_knowledge.models import KnowledgeDocument, DocumentChunk, SourceType
from aetheros_knowledge.indexing.chunkers import chunk_text
from aetheros_knowledge.indexing.embedders import get_embedder, BaseEmbedder
from aetheros_security.runtime import get_security_context

logger = logging.getLogger(__name__)


class DeepResearchEngine:
    """Orchestrates deep research cycles: search, ingest, extract, iterate."""

    def __init__(
        self,
        store: KnowledgeStore,
        search_engine: Optional[SearchEngine] = None,
        search_func: Optional[Callable[[str], List[str]]] = None,
        ingest_func: Optional[Callable[[str], str]] = None,
        max_iterations: int = 5,
        max_sources: int = 20,
        time_budget_seconds: int = 300,
        confidence_threshold: float = 0.7,
        chunk_size: int = 512,
        chunk_overlap: int = 64,
        embedder_name: str = "sentence-transformers",
    ):
        """
        Initialize the deep research engine.

        Args:
            store: KnowledgeStore for persisting documents, chunks, and claim-evidence.
            search_engine: Optional SearchEngine for searching the store.
            search_func: Optional function that takes a query and returns a list of source paths (e.g., URLs) to ingest.
            ingest_func: Optional function that takes a source path and returns the content as a string.
            max_iterations: Maximum number of research cycles.
            max_sources: Maximum number of unique sources to ingest.
            time_budget_seconds: Total time budget for the research process.
            confidence_threshold: Minimum confidence for claim-evidence relationships to consider sufficient.
            chunk_size: Size of chunks for document processing.
            chunk_overlap: Overlap between chunks.
            embedder_name: Name of the embedder to use for vectorization.
        """
        self.store = store
        self.search_engine = search_engine
        self.search_func = search_func
        self.ingest_func = ingest_func
        self.max_iterations = max_iterations
        self.max_sources = max_sources
        self.time_budget_seconds = time_budget_seconds
        self.confidence_threshold = confidence_threshold
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedder_name = embedder_name
        self._start_time: Optional[float] = None
        self._iterations = 0
        self._sources_ingested: set[str] = set()  # source paths we've ingested
        self._processed_doc_ids: set[str] = set()  # document IDs we've processed for claims in the current iteration
        self._claims_extracted: Dict[str, List[Dict[str, Any]]] = {}  # doc_id -> list of claim-evidence relations
        self._embedder: Optional[BaseEmbedder] = None
        if self.embedder_name:
            try:
                self._embedder = get_embedder(self.embedder_name)
            except Exception as e:
                logger.warning(f"Failed to load embedder {self.embedder_name}: {e}")
                self._embedder = None

        # Trusted domains for web source evaluation
        self._trusted_domains = {
            ".gov",
            ".edu",
            ".ac.uk",
            ".gov.uk",
            # Add more trusted TLDs/domains as needed
        }

    def _check_budget(self) -> bool:
        """Check if we have exceeded time or iteration budget."""
        if self._start_time is None:
            return True
        elapsed = time.time() - self._start_time
        if elapsed >= self.time_budget_seconds:
            logger.info(
                "Deep research time budget exceeded: %.2f seconds", elapsed
            )
            return False
        if self._iterations >= self.max_iterations:
            logger.info(
                "Deep research iteration budget exceeded: %d iterations",
                self._iterations,
            )
            return False
        if len(self._sources_ingested) >= self.max_sources:
            logger.info(
                "Deep research source budget exceeded: %d sources",
                len(self._sources_ingested),
            )
            return False
        return True

    def _is_source_trusted(self, source_path: str) -> bool:
        """
        Evaluate trustworthiness of a web source based on domain.
        For non-web sources, assume trusted.
        """
        if not source_path.lower().startswith(("http://", "https://")):
            # Local file or other non-web source
            return True
        # Extract domain from URL
        # Simple regex for demonstration
        match = re.search(r"https?://([^/]+)/", source_path)
        if not match:
            return False
        domain = match.group(1).lower()
        # Check if domain ends with any trusted suffix
        for trusted in self._trusted_domains:
            if domain.endswith(trusted):
                return True
        # Additional heuristics could be added here
        return False

    def _ingest_source(self, source_path: str, content: str) -> Optional[str]:
        """
        Ingest a single source into the knowledge store.
        This includes saving the document, chunking, embedding, and saving chunks.

        Args:
            source_path: Identifier or path of the source (URL, file path, etc.).
            content: The textual content of the source.

        Returns:
            Document ID if successful, None otherwise.
        """
        # Check permission to write
        ctx = get_security_context()
        principal = ctx.principal.strip()
        if principal:
            collection_id = "deep_research"  # TODO: make configurable
            if not self.store._check_knowledge_permission(
                principal=principal,
                action="knowledge:document:write",
                resource=collection_id,
                parameters={"source_path": source_path},
            ):
                logger.warning(
                    "Access denied to ingest source %s for principal %s",
                    source_path,
                    principal,
                )
                return None

        # Check for prompt injection in content
        if self._check_prompt_injection(content):
            logger.warning(f"Prompt injection detected in content from source: {source_path}")
            return None

        # Create document
        doc = KnowledgeDocument(
            title=f"Source: {source_path}",
            source_type=SourceType.WEBSITE if source_path.startswith("http") else SourceType.TXT,
            source_path=source_path,
            collection_id=collection_id,
            content_type="text/plain",
            language="en",
            size_bytes=len(content.encode("utf-8")),
            word_count=len(content.split()),
            chunk_count=0,  # will be set after chunking
            checksum="",  # TODO: compute checksum
            tags=["deep_research"],
            metadata={
                "ingested_at": time.time(),
                "deep_research_iteration": self._iterations,
                "source_trust": self._is_source_trusted(source_path),
            },
        )
        self.store.save_document(doc)

        # Chunk the content
        try:
            text_chunks = chunk_text(content, self.chunk_size, self.chunk_overlap)
        except Exception as e:
            logger.error(f"Failed to chunk content from {source_path}: {e}")
            return doc.id  # Return the doc ID even if chunking failed

        # Prepare DocumentChunk objects
        chunks: List[DocumentChunk] = []
        for i, chunk_text_content in enumerate(text_chunks):
            chunk_id = str(uuid.uuid4())
            chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc.id,
                content=chunk_text_content,
                chunk_index=i,
                token_count=len(chunk_text_content.split()),  # approximate
                embedding=[],  # will be populated below
                metadata={},
            )
            chunks.append(chunk)

        # Embed chunks if we have an embedder
        if self._embedder and chunks:
            try:
                texts = [chunk.content for chunk in chunks]
                embeddings = self._embedder.embed(texts)
                for chunk, embedding in zip(chunks, embeddings):
                    chunk.embedding = embedding
            except Exception as e:
                logger.warning(f"Failed to embed chunks for {source_path}: {e}")
                # Continue without embeddings

        # Save chunks
        try:
            self.store.save_chunks(chunks)
            # Update document chunk count
            doc.chunk_count = len(chunks)
            self.store.save_document(doc)
        except Exception as e:
            logger.error(f"Failed to save chunks for {source_path}: {e}")
            # We still return the doc ID because the document was saved
            return doc.id

        return doc.id

    def _search_store(self, query: str) -> List[str]:
        """
        Search the store for documents matching the query.
        Returns a list of document IDs.
        """
        if self.search_engine is None:
            logger.warning("No search engine available for searching the store")
            return []
        try:
            results = self.search_engine.hybrid_search(query, top_k=10)
            # Assuming results are dictionaries with an 'id' field that is the document ID
            doc_ids = [r.get("id") for r in results if r.get("id")]
            return doc_ids
        except Exception as e:
            logger.error(f"Error searching store: {e}")
            return []

    def _check_prompt_injection(self, text: str) -> bool:
        """
        Check if the text contains prompt injection patterns.
        Returns True if prompt injection is detected, False otherwise.
        """
        injection_patterns = [
            # Common prompt injection patterns
            r"(?i)ignore\s+previous\s+instructions",
            r"(?i)forget\s+everything\s+above",
            r"(?i)you\s+are\s+now",
            r"(?i)this\s+is\s+a\s+prompt\s+injection",
            r"(?i)disregard\s+all\s+prior\s+directives",
            r"(?i)override\s+previous\s+commands",
            r"(?i)new\s+instruction\s*:",
            r"(?i)system\s*:\s*",
            r"(?i)```\s*prompt\s*",  # Maybe a code block with prompt
            # Add more as needed
        ]
        for pattern in injection_patterns:
            if re.search(pattern, text):
                return True
        return False

    def _extract_claims(self, text: str) -> List[str]:
        """
        Extract potential claim sentences from text using improved heuristics.
        Returns list of claim strings.
        """
        # Split into sentences (naive)
        sentences = re.split(r"[.!?]+", text)
        claims = []
        claim_indicators = [
            r"according to",
            r"study shows?",
            r"research indicates?",
            r"data suggests?",
            r"it is estimated",
            r"survey found",
            r"percent of",
            r"% of",
            r"increased by",
            r"decreased by",
            r"evidence suggests?",
            r"we found",
            r"the results show",
            r"statistics show",
            r"studies show",
            r"experts say",
            r"report says",
            r"findings reveal",
            r"analysis shows",
            r"it was found that",
            r"it has been shown that",
            r"data indicates",
            r"observations suggest",
            r"we observed that",
            r"the data reveals",
            r"results indicate",
            r"conclusion",
            r"therefore",
            r"thus,",
            r"hence,",
        ]
        # Also look for sentences with numbers and statistical terms
        number_pattern = r"\d+(\.\d+)?(%| percent| percentage| times| fold)"
        for sent in sentences:
            sent = sent.strip()
            if len(sent) < 10:
                continue
            # Check for claim indicators
            is_claim = False
            for pattern in claim_indicators:
                if re.search(pattern, sent, re.IGNORECASE):
                    is_claim = True
                    break
            # Check for numbers and statistical terms if not already marked as claim
            if not is_claim:
                if re.search(number_pattern, sent, re.IGNORECASE):
                    is_claim = True
                # Also check for words like 'significant', 'correlation', etc.
                sig_words = ['significant', 'correlation', 'p-value', 'confidence interval', 'average', 'mean', 'median', 'std', 'deviation']
                for word in sig_words:
                    if word in sent.lower():
                        is_claim = True
                        break
            if is_claim:
                claims.append(sent)
        return claims

    def _extract_claims_and_evidence(
        self, doc_id: str
    ) -> List[Dict[str, Any]]:
        """
        Extract claims and supporting evidence from a document.

        Args:
            doc_id: Document ID to process.

        Returns:
            List of claim-evidence relationship dicts.
        """
        # Retrieve the document
        doc = self.store.get_document(doc_id)
        if not doc:
            logger.warning("Document %s not found", doc_id)
            return []

        # Retrieve chunks for the document
        chunks = self.store.get_chunks(doc_id)
        if not chunks:
            logger.warning("No chunks found for document %s", doc_id)
            return []

        # Extract claims from each chunk's content
        claim_evidence_relations: List[Dict[str, Any]] = []
        for chunk in chunks:
            claims = self._extract_claims(chunk.content)
            for claim_text in claims:
                # For simplicity, we'll use the chunk itself as evidence
                # In a more sophisticated system, we would search for relevant chunks.
                relation = {
                    "claim_id": f"claim_{doc_id}_{chunk.chunk_index}_{len(claim_evidence_relations)}",
                    "claim_text": claim_text,
                    "evidence_id": chunk.id,
                    "support_type": "supports",
                    "confidence": 0.6,  # Placeholder confidence
                    "context": f"Extracted from chunk {chunk.chunk_index} of document {doc_id}",
                }
                claim_evidence_relations.append(relation)

        return claim_evidence_relations

    def _generate_next_query(self, goal: str, iteration_findings: List[Dict[str, Any]]) -> str:
        """
        Generate a new search query based on the claims and evidence found so far.
        This implementation uses the claim texts from the current iteration to form a new query.
        """
        if not iteration_findings:
            return goal
        # Extract unique claim texts from the findings
        claim_texts = [f.get("claim_text", "") for f in iteration_findings if f.get("claim_text")]
        # Remove duplicates while preserving order
        unique_claims = []
        for ct in claim_texts:
            if ct not in unique_claims:
                unique_claims.append(ct)
        # Combine the goal with the top claims (limit to 5 to avoid too long query)
        combined = goal + " " + " ".join(unique_claims[:5])
        return combined

    def run_research(self, goal: str) -> Dict[str, Any]:
        """
        Execute deep research on a given goal.

        Args:
            goal: The research goal or question.

        Returns:
            A dictionary containing the research report.
        """
        self._start_time = time.time()
        self._iterations = 0
        self._sources_ingested.clear()
        self._processed_doc_ids.clear()
        self._claims_extracted.clear()

        logger.info("Starting deep research on goal: %s", goal)

        query = goal
        all_findings: List[Dict[str, Any]] = []

        while self._check_budget():
            self._iterations += 1
            logger.info(
                "Deep research iteration %d/%d",
                self._iterations,
                self.max_iterations,
            )

            # Reset processed document IDs for this iteration
            self._processed_doc_ids.clear()
            iteration_findings: List[Dict[str, Any]] = []

            # Step 1: Search the store for documents matching the current query
            store_doc_ids = self._search_store(query)
            logger.info(
                "Iteration %d: found %d documents in store",
                self._iterations,
                len(store_doc_ids),
            )

            # Step 2: Process each store document for claims (if not processed in this iteration)
            for doc_id in store_doc_ids:
                if doc_id not in self._processed_doc_ids:
                    self._processed_doc_ids.add(doc_id)
                    claims_evidence = self._extract_claims_and_evidence(doc_id)
                    if claims_evidence:
                        self._claims_extracted[doc_id] = claims_evidence
                        # Persist claim-evidence relationships to store
                        for rel in claims_evidence:
                            self.store.add_claim_evidence_relationship(
                                claim_id=rel.get("claim_id", ""),
                                claim_text=rel.get("claim_text", ""),
                                evidence_id=rel.get("evidence_id", ""),
                                support_type=rel.get("support_type", "supports"),
                                confidence=rel.get("confidence", 0.5),
                                context=rel.get("context", ""),
                                created_by="deep_research_engine",
                            )
                        iteration_findings.extend(claims_evidence)
                        all_findings.extend(claims_evidence)
                        logger.debug(
                            "Extracted %d claim-evidence relations from document %s",
                            len(claims_evidence),
                            doc_id,
                        )

            # Step 3: If we have an external search function, use it to get new sources and ingest them
            if self.search_func:
                try:
                    new_source_paths = self.search_func(query)
                    logger.info(
                        "Iteration %d: external search returned %d new sources",
                        self._iterations,
                        len(new_source_paths),
                    )
                except Exception as e:
                    logger.error(f"Error in external search function: {e}")
                    new_source_paths = []

                for source_path in new_source_paths:
                    if source_path not in self._sources_ingested:
                        self._sources_ingested.add(source_path)
                        content = None
                        if self.ingest_func:
                            try:
                                content = self.ingest_func(source_path)
                            except Exception as e:
                                logger.error(
                                    f"Error ingesting source {source_path}: {e}"
                                )
                        else:
                            logger.warning(
                                "No ingest function provided; skipping source %s",
                                source_path,
                            )

                        if content is not None:
                            doc_id = self._ingest_source(source_path, content)
                            if doc_id:
                                # Process this new document for claims in the current iteration
                                self._processed_doc_ids.add(doc_id)
                                claims_evidence = self._extract_claims_and_evidence(doc_id)
                                if claims_evidence:
                                    self._claims_extracted[doc_id] = claims_evidence
                                    # Persist claim-evidence relationships to store
                                    for rel in claims_evidence:
                                        self.store.add_claim_evidence_relationship(
                                            claim_id=rel.get("claim_id", ""),
                                            claim_text=rel.get("claim_text", ""),
                                            evidence_id=rel.get("evidence_id", ""),
                                            support_type=rel.get("support_type", "supports"),
                                            confidence=rel.get("confidence", 0.5),
                                            context=rel.get("context", ""),
                                            created_by="deep_research_engine",
                                        )
                                    iteration_findings.extend(claims_evidence)
                                    all_findings.extend(claims_evidence)
                                    logger.debug(
                                        "Extracted %d claim-evidence relations from ingested source %s",
                                        len(claims_evidence),
                                        source_path,
                                    )
                            else:
                                logger.warning(
                                    f"Failed to ingest source {source_path}"
                                )

            # Step 4: Generate new query for the next iteration
            query = self._generate_next_query(goal, iteration_findings)

            # Step 5: Check if we have sufficient confidence to stop early
            if iteration_findings:
                avg_confidence = sum(f.get("confidence", 0.0) for f in iteration_findings) / len(iteration_findings)
                logger.info(
                    "Iteration %d: average confidence of claim-evidence relations: %.2f",
                    self._iterations,
                    avg_confidence,
                )
                if avg_confidence >= self.confidence_threshold:
                    logger.info(
                        "Stopping early due to sufficient confidence (threshold: %.2f)",
                        self.confidence_threshold,
                    )
                    break
            else:
                logger.info("No findings in this iteration; continuing if budget allows.")

            # If we have exhausted the budget, the while condition will break on the next iteration.

        duration = time.time() - self._start_time if self._start_time else 0
        logger.info(
            "Deep research completed in %.2f seconds after %d iterations",
            duration,
            self._iterations,
        )

        # Compile report
        report = {
            "goal": goal,
            "findings": all_findings,
            "sources": list(self._sources_ingested),
            "claim_evidence_map": self._claims_extracted,
            "iterations": self._iterations,
            "duration_seconds": duration,
        }
        return report