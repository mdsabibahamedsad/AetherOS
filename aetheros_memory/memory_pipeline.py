"""Memory Pipeline — processes user events through stages to produce memories.

Extracts facts from text, categorizes, embeds, stores in memory manager,
indexes in vector DB, and adds to knowledge graph.
"""

from __future__ import annotations

import enum
import logging
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from aetheros_memory.embedding_engine import EmbeddingEngine, EmbeddingConfig
from aetheros_memory.knowledge_graph import (
    EntityType,
    GraphEntity,
    GraphRelationship,
    KnowledgeGraph,
    RelationshipType,
)
from aetheros_memory.memory_manager import MemoryCategory, MemoryManager, MemoryRecord

logger = logging.getLogger("aetheros_memory.pipeline")


class Category(str, enum.Enum):
    CONVERSATION = "conversation"
    PROJECT = "project"
    CODE = "code"
    RESEARCH = "research"
    DECISION = "decision"
    PREFERENCE = "preference"
    TASK = "task"
    IDEA = "idea"
    CONCEPT = "concept"
    INSIGHT = "insight"
    QUESTION = "question"
    COMMAND = "command"
    ERROR = "error"
    PATTERN = "pattern"
    ARCHITECTURE = "architecture"


@dataclass
class Fact:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    category: Category = Category.CONCEPT
    confidence: float = 0.5
    source: str = ""
    entities: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExtractedFact:
    text: str = ""
    facts: List[Fact] = field(default_factory=list)
    original_text: str = ""


@dataclass
class PipelineConfig:
    auto_embed: bool = True
    auto_categorize: bool = True
    auto_graph: bool = True
    extract_enabled: bool = True
    max_facts_per_event: int = 50
    min_confidence: float = 0.3


_DECISION_PATTERNS = [
    re.compile(r"\bwe\s+(?:have\s+)?decided\s+(?:to|that|on)\b", re.IGNORECASE),
    re.compile(r"\bthe\s+decision\s+(?:was|is)\b", re.IGNORECASE),
    re.compile(r"\b(?:was|were|are)\s+approved?\b", re.IGNORECASE),
    re.compile(r"\bit\s+was\s+(?:agreed|resolved|determined)\b", re.IGNORECASE),
    re.compile(r"\b(?:chose|selected|opted)\s+(?:to|for)\b", re.IGNORECASE),
    re.compile(r"\b(?:concluded|decided|resolved)\s+that\b", re.IGNORECASE),
    re.compile(r"\b(?:finalized|locked\s+in|settled\s+on)\b", re.IGNORECASE),
    re.compile(r"\b(?:consensus|agreement)\s+(?:was|is|reached)\b", re.IGNORECASE),
]

_PREFERENCE_PATTERNS = [
    re.compile(r"\bI\s+(?:would\s+)?prefer\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:really\s+)?like\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:would\s+)?want\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:would\s+)?love\b", re.IGNORECASE),
    re.compile(r"\bmy\s+(?:favorite|preferred)\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:am|'m)\s+(?:not\s+)?(?:a\s+)?fan\s+of\b", re.IGNORECASE),
    re.compile(r"\bI\s+(?:don't|do\s+not)\s+(?:like|want)\b", re.IGNORECASE),
    re.compile(r"\bI'd\s+(?:rather|prefer)\b", re.IGNORECASE),
    re.compile(r"\bI'm\s+(?:more\s+)?interested\s+in\b", re.IGNORECASE),
]

_TASK_PATTERNS = [
    re.compile(r"\b(?:TODO|todo|to-do|action\s+item|follow[- ]?up)\s*[:.:]", re.IGNORECASE),
    re.compile(r"\b(?:need|needs|required|requires)\s+to\b", re.IGNORECASE),
    re.compile(r"\bshould\s+(?:we|you|I)\b", re.IGNORECASE),
    re.compile(r"\b(?:don't|do\s+not)\s+forget\s+to\b", re.IGNORECASE),
    re.compile(r"\b(?:must|mustn't)\s+(?:be|have|do|check|ensure|make)\b", re.IGNORECASE),
    re.compile(r"\b(?:next\s+step|next\s+action)\s*(?::|is)\b", re.IGNORECASE),
    re.compile(r"\b(?:assign|assigned)\s+(?:to|by)\b", re.IGNORECASE),
    re.compile(r"\b(?:deadline|due\s+date)\s*(?::|is)\b", re.IGNORECASE),
    re.compile(r"\b(?:track|monitor|watch)\s+for\b", re.IGNORECASE),
]

_QUESTION_PATTERNS = [
    re.compile(r"^((?:what|when|where|why|how|who|whose|whom)\b.*)\?$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"^((?:are|is|was|were|do|does|did|have|has|had|can|could|will|would|shall|should|may|might)\b.*)\?$", re.MULTILINE | re.IGNORECASE),
    re.compile(r"\b(?:question|query|wonder(?:ed)?)\s*(?::|is|about)\b", re.IGNORECASE),
    re.compile(r"\b(?:unclear|not\s+sure|uncertain)\s+(?:about|whether|what|how)\b", re.IGNORECASE),
    re.compile(r"\b(?:any\s+idea|any\s+thoughts|any\s+suggestions)\s*\?", re.IGNORECASE),
]

_CONCEPT_PATTERNS = [
    re.compile(r"\b(?:concept|idea|notion)\s+(?:of|is|called)\b", re.IGNORECASE),
    re.compile(r"\b(?:introducing|introduces|introduced)\s+(?:a\s+)?(?:new\s+)?(?:concept|approach|method|technique|paradigm)\b", re.IGNORECASE),
    re.compile(r"\b(?:refers?\s+to|defined?\s+as)\b", re.IGNORECASE),
]

_CODE_PATTERNS = [
    re.compile(r"\b(?:function|class|method|def)\s+\w+\s*\([^)]*\)", re.IGNORECASE),
    re.compile(r"\b(?:import|from)\s+[\w.]+(?:\s+import\s+[\w.*]+)?", re.IGNORECASE),
    re.compile(r"\b(?:API|endpoint|route|middleware|callback|decorator)\b", re.IGNORECASE),
    re.compile(r"\b(?:refactor|refactored|refactoring)\b", re.IGNORECASE),
    re.compile(r"\b(?:bug|bugfix|hotfix|patch)\s*(?::|#)\s*\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:type\s+hint|annotation|generic|protocol|ABC)\b", re.IGNORECASE),
    re.compile(r"\backquote.*?`[^`]+`", re.IGNORECASE),
]

_PEOPLE_PATTERNS = [
    re.compile(r"\b(?:@\w+|u\/\w+|user\s+\w+)\b"),
    re.compile(r"\b(?:said|asked|mentioned|suggested|reported)\s+(?:that\s+)?\b", re.IGNORECASE),
]

_PROJECT_PATTERNS = [
    re.compile(r"\bproj(?:ect)?\s*[#:;]\s*[\w-]+\b", re.IGNORECASE),
    re.compile(r"\b(?:repo|repository|package|module|library)\s*[:;]\s*[\w./-]+\b", re.IGNORECASE),
    re.compile(r"\b(?:workspace|workspace_id)\s*[:;=]\s*\S+\b", re.IGNORECASE),
]

_NUMBER_PATTERNS = [
    re.compile(r"\bversion\s+(\d+[.]\d+(?:[.]\d+)?(?:[ab]\d+)?(?:[-.]\w+)?)\b", re.IGNORECASE),
    re.compile(r"\bv(\d+[.]\d+(?:[.]\d+)?)\b", re.IGNORECASE),
    re.compile(r"\b\d+[.]\d+[.]\d+\b"),
]

_RELATIONSHIP_PATTERNS = [
    re.compile(r"\b(?:depends?\s+on|rel(?:ie)?s?\s+on|requires?)\b", re.IGNORECASE),
    re.compile(r"\b(?:related\s+to|connected\s+(?:with|to)|linked\s+to)\b", re.IGNORECASE),
    re.compile(r"\b(?:part\s+of|member\s+of|belongs?\s+to)\b", re.IGNORECASE),
    re.compile(r"\b(?:leads?\s+to|causes?|triggers?|results?\s+in)\b", re.IGNORECASE),
    re.compile(r"\b(?:consists?\s+of|composed\s+of|includes?)\b", re.IGNORECASE),
    re.compile(r"\b(?:implements?|extends?|inherits?\s+from)\b", re.IGNORECASE),
    re.compile(r"\b(?:collaborates?\s+with|works?\s+with|paired\s+with)\b", re.IGNORECASE),
]

_ERROR_PATTERNS = [
    re.compile(r"\b(?:error|exception|fail(?:ed|ure)?|crash(?:ed)?|stack\s+trace)\s*(?::|is|was)\b", re.IGNORECASE),
    re.compile(r"\b(?:traceback|Traceback|raise|raised|threw|thrown)\b"),
    re.compile(r"\b(?:unhandled|unexpected|uncaught)\s+(?:error|exception)\b", re.IGNORECASE),
    re.compile(r"\b(?:HTTP|status)\s+\d{3}\b"),
]

_ARCHITECTURE_PATTERNS = [
    re.compile(r"\b(?:architecture|design\s+pattern|system\s+design|structure)\s*(?::|is|of)\b", re.IGNORECASE),
    re.compile(r"\b(?:layer|tier|component|module|service|microservice)\b", re.IGNORECASE),
    re.compile(r"\b(?:singleton|factory|observer|strategy|adapter|facade|builder|decorator|proxy|composite)\b", re.IGNORECASE),
    re.compile(r"\b(?:diagram|flowchart|UML)\b", re.IGNORECASE),
    re.compile(r"\b(?:client-server|peer-to-peer|pub-sub|publish-subscribe|event-driven|request-response|CQRS|event\s+sourcing)\b", re.IGNORECASE),
    re.compile(r"\b(?:database|schema|table|index|query|ORM|migration)\s*(?::|is|for)\b", re.IGNORECASE),
]

_INSIGHT_PATTERNS = [
    re.compile(r"\b(?:realized|realize|noticed|notice)\s+that\b", re.IGNORECASE),
    re.compile(r"\b(?:insight|takeaway|key\s+learning|lesson\s+learned)\s*(?::|is)\b", re.IGNORECASE),
    re.compile(r"\b(?:turns?\s+out|it\s+seems|apparently|interestingly)\b", re.IGNORECASE),
    re.compile(r"\b(?:important\s+to\s+note|worth\s+noting|crucial\s+point)\b", re.IGNORECASE),
    re.compile(r"\b(?:this\s+(?:means|implies|suggests)\s+that)\b", re.IGNORECASE),
]

_PATTERN_PATTERNS = [
    re.compile(r"\b(?:pattern|anti-pattern|code\s+smell|idiom)\s*(?::|is|of)\b", re.IGNORECASE),
    re.compile(r"\b(?:always|never|whenever|every\s+time)\s+(?:use|avoid|check|ensure|do|call)\b", re.IGNORECASE),
    re.compile(r"\b(?:common\s+(?:mistake|error|pitfall|gotcha))\b", re.IGNORECASE),
    re.compile(r"\b(?:best\s+practice|recommended|standard\s+way)\b", re.IGNORECASE),
]

_CAPITALIZED_TERM = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b")

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")

_ENTITY_EXTRACT = re.compile(
    r"\b(?:"
    r"(?:function|class|method|module|package|library|framework|tool|app|service|API|database|table|schema|endpoint|route|config|setting|variable|constant|type|interface|protocol|format|algorithm) "
    r"['\"]?(\w+(?:\s+\w+)*)['\"]?"
    r")\b",
    re.IGNORECASE,
)


class MemoryPipeline:
    def __init__(
        self,
        memory_manager: Optional[MemoryManager] = None,
        embedding_engine: Optional[EmbeddingEngine] = None,
        knowledge_graph: Optional[KnowledgeGraph] = None,
        config: Optional[PipelineConfig] = None,
    ) -> None:
        self._memory_manager = memory_manager
        self._embedding_engine = embedding_engine or (memory_manager.embedding_engine if memory_manager else EmbeddingEngine())
        self._knowledge_graph = knowledge_graph or (memory_manager.knowledge_graph if memory_manager else None)
        self._config = config or PipelineConfig()
        self._lock = threading.RLock()
        self._total_processed = 0
        self._total_facts_extracted = 0
        self._total_errors = 0
        self._processing_times: List[float] = []

    def process(
        self,
        text: str,
        source: str = "",
        workspace_id: str = "",
        project_id: str = "",
        conversation_id: str = "",
    ) -> ExtractedFact:
        start = time.monotonic()
        if not text or not text.strip():
            raise ValueError("text must be a non-empty string")

        with self._lock:
            self._total_processed += 1

        facts: List[Fact] = []
        if self._config.extract_enabled:
            try:
                facts = self.extract_facts(text)
            except Exception as exc:
                with self._lock:
                    self._total_errors += 1
                logger.warning("Fact extraction failed: %s", exc)

        if self._config.auto_categorize:
            for fact in facts:
                try:
                    fact.category = self.categorize(fact)
                except Exception as exc:
                    logger.warning("Categorization failed for fact %s: %s", fact.id, exc)

        if self._config.auto_embed:
            for fact in facts:
                try:
                    embedding = self.embed(fact)
                    fact.metadata["embedding"] = embedding
                except Exception as exc:
                    logger.warning("Embedding failed for fact %s: %s", fact.id, exc)

        if facts:
            try:
                self.store(facts, source, workspace_id, project_id, conversation_id)
            except Exception as exc:
                with self._lock:
                    self._total_errors += 1
                logger.warning("Store failed for facts: %s", exc)

            if self._config.auto_graph:
                try:
                    self.index_in_graph(facts, source)
                except Exception as exc:
                    logger.warning("Graph indexing failed: %s", exc)

        elapsed = (time.monotonic() - start) * 1000
        with self._lock:
            self._total_facts_extracted += len(facts)
            self._processing_times.append(elapsed)
            if len(self._processing_times) > 1000:
                self._processing_times = self._processing_times[-1000:]

        return ExtractedFact(text=text[:500], facts=facts, original_text=text)

    def extract_facts(self, text: str) -> List[Fact]:
        if not text:
            return []

        facts: List[Fact] = []
        seen_contents: set = set()
        max_facts = self._config.max_facts_per_event

        def _add_fact(content: str, category: Category, confidence: float, extra_entities: Optional[List[str]] = None) -> None:
            if len(facts) >= max_facts:
                return
            content = content.strip()
            if not content or len(content) < 10:
                return
            key = content[:200].lower()
            if key in seen_contents:
                return
            seen_contents.add(key)
            entities: List[str] = extra_entities or []
            entities.extend(_ENTITY_EXTRACT.findall(content))
            facts.append(Fact(
                content=content,
                category=category,
                confidence=min(confidence, 1.0),
                entities=list(set(entities)),
            ))

        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            sentence_lower = sentence.lower()

            for pattern in _DECISION_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.DECISION, 0.85 + 0.1 * (len(m.group()) / len(sentence)))
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _PREFERENCE_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.PREFERENCE, 0.8)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _ERROR_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.ERROR, 0.9)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _QUESTION_PATTERNS:
                m = pattern.match(sentence)
                if m:
                    _add_fact(m.group(1) if pattern.groups >= 1 else sentence, Category.QUESTION, 0.75)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _TASK_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.TASK, 0.8)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _ARCHITECTURE_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.ARCHITECTURE, 0.75)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _INSIGHT_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.INSIGHT, 0.7)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _PATTERN_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.PATTERN, 0.65)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _CONCEPT_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.CONCEPT, 0.6)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _CODE_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.CODE, 0.7)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _RELATIONSHIP_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.INSIGHT, 0.55)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _PROJECT_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.PROJECT, 0.6)
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _NUMBER_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.CONCEPT, 0.5, extra_entities=[m.group(0)])
                    break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            matches = _CAPITALIZED_TERM.findall(sentence)
            for term in matches:
                if len(term) >= 4 and term.lower() not in ("This", "That", "What", "When", "Where", "Which"):
                    _add_fact(f"{term} is mentioned: {sentence[:200]}", Category.CONCEPT, 0.4, extra_entities=[term])
                    if len(facts) >= max_facts:
                        break

        for sentence in sentences:
            if len(facts) >= max_facts:
                break
            for pattern in _PEOPLE_PATTERNS:
                m = pattern.search(sentence)
                if m:
                    _add_fact(sentence, Category.CONVERSATION, 0.5, extra_entities=[m.group(0)])
                    break

        filtered = [f for f in facts if f.confidence >= self._config.min_confidence]
        return filtered[:max_facts]

    def categorize(self, fact: Fact) -> Category:
        if fact.category != Category.CONCEPT:
            return fact.category

        content = fact.content.lower()

        if re.search(r"\berror\b|\bexception\b|\bfail(?:ed|ure)?\b|\bcrash\b|\bstack\s+trace\b", content):
            return Category.ERROR
        if re.search(r"\bprefer\b|\blike\b|\bwant\b|\bfavorite\b|\blove\b|\bhate\b|\bdislike\b", content):
            return Category.PREFERENCE
        if re.search(r"\bdecided\b|\bdecision\b|\bagreed\b|\bapproved\b|\bchose\b|\bselected\b|\bconcluded\b|\bfinalized\b", content):
            return Category.DECISION
        if re.search(r"\btodo\b|\bto[- ]do\b|\baction\s+item\b|\bneed\s+to\b|\bshould\b|\bmust\b|\bassign\b|\bdeadline\b|\bnext\s+step\b", content):
            return Category.TASK
        if re.search(r"\?$", content) or re.search(r"\bquestion\b|\bwonder\b|\bunclear\b|\bnot\s+sure\b", content):
            return Category.QUESTION
        if re.search(r"\barchitecture\b|\bdesign\s+pattern\b|\blayer\b|\btier\b|\bcomponent\b|\bmodule\b|\bservice\b|\bmicroservice\b", content):
            return Category.ARCHITECTURE
        if re.search(r"\bpattern\b|\banti-pattern\b|\bcode\s+smell\b|\bbest\s+practice\b|\bidiom\b", content):
            return Category.PATTERN
        if re.search(r"\binsight\b|\brealized\b|\bnoticed\b|\btakeaway\b|\bturns?\s+out\b|\bthis\s+means\b|\bimplies\b", content):
            return Category.INSIGHT
        if re.search(r"\bconcept\b|\bidea\b|\bnotion\b|\bintroduce\b|\brefers?\s+to\b|\bdefined?\s+as\b|\bis\s+a\s+new\b", content):
            return Category.CONCEPT
        if re.search(r"\bfunction\b|\bclass\b|\bmethod\b|\bimport\b|\bAPI\b|\bendpoint\b|\broute\b|\brefactor\b|\bbug\b|\bgit\b|\bcommit\b|\bPR\b|\bpull\s+request\b", content):
            return Category.CODE
        if re.search(r"\bresearch\b|\bstudy\b|\bsurvey\b|\banalysis\b|\banalyze\b|\binvestigat\b|\blearn(?:ed|ing)?\s+about\b", content):
            return Category.RESEARCH
        if re.search(r"\bproject\b|\brepo\b|\brepository\b|\bworkspace\b", content):
            return Category.PROJECT

        return fact.category

    def embed(self, fact: Fact) -> List[float]:
        try:
            result = self._embedding_engine.embed(fact.content)
            return result.vector
        except Exception as exc:
            logger.warning("Embedding failed for fact %s: %s", fact.id, exc)
            raise

    def store(
        self,
        facts: List[Fact],
        source: str = "",
        workspace_id: str = "",
        project_id: str = "",
        conversation_id: str = "",
    ) -> List[MemoryRecord]:
        if self._memory_manager is None:
            logger.warning("No MemoryManager set; cannot store facts")
            return []
        records: List[MemoryRecord] = []
        for fact in facts:
            mc = self._category_to_memory_category(fact.category)
            metadata = dict(fact.metadata)
            embedding = metadata.pop("embedding", [])
            record = self._memory_manager.store(
                content=fact.content,
                category=mc,
                tags=list(set(fact.entities)),
                importance=fact.confidence,
                source=fact.source or source,
                workspace_id=workspace_id,
                project_id=project_id,
                conversation_id=conversation_id,
                metadata={
                    "fact_id": fact.id,
                    "fact_category": fact.category.value,
                    "fact_confidence": fact.confidence,
                    "fact_timestamp": fact.timestamp,
                },
            )
            if embedding:
                with self._lock:
                    record.embedding = embedding
            records.append(record)
        return records

    def index_in_graph(self, facts: List[Fact], source: str = "") -> int:
        if self._knowledge_graph is None:
            return 0
        count = 0
        for fact in facts:
            try:
                entity = GraphEntity(
                    name=fact.content[:120],
                    description=fact.content[:500],
                    type=self._fact_to_entity_type(fact.category),
                    importance=fact.confidence,
                    properties={
                        "fact_id": fact.id,
                        "category": fact.category.value,
                        "source": fact.source or source,
                        "confidence": fact.confidence,
                        "timestamp": fact.timestamp,
                        "entities": ",".join(fact.entities),
                    },
                )
                self._knowledge_graph.add_entity(entity)
                count += 1
            except Exception as exc:
                logger.warning("Failed to index fact %s in graph: %s", fact.id, exc)
        return count

    def process_batch(self, texts: List[str]) -> List[ExtractedFact]:
        results: List[ExtractedFact] = []
        for text in texts:
            try:
                result = self.process(text)
                results.append(result)
            except Exception as exc:
                logger.warning("Batch processing failed for text: %s", exc)
                results.append(ExtractedFact(text=str(exc), facts=[], original_text=text))
        return results

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            avg_time = 0.0
            if self._processing_times:
                avg_time = sum(self._processing_times) / len(self._processing_times)
            p95 = 0.0
            if len(self._processing_times) > 1:
                sorted_times = sorted(self._processing_times)
                idx = int(len(sorted_times) * 0.95)
                p95 = sorted_times[idx]
            return {
                "total_processed": self._total_processed,
                "total_facts_extracted": self._total_facts_extracted,
                "total_errors": self._total_errors,
                "avg_processing_time_ms": round(avg_time, 2),
                "p95_processing_time_ms": round(p95, 2),
                "config": {
                    "auto_embed": self._config.auto_embed,
                    "auto_categorize": self._config.auto_categorize,
                    "auto_graph": self._config.auto_graph,
                    "extract_enabled": self._config.extract_enabled,
                    "max_facts_per_event": self._config.max_facts_per_event,
                    "min_confidence": self._config.min_confidence,
                },
            }

    @property
    def memory_manager(self) -> MemoryManager:
        return self._memory_manager

    @property
    def embedding_engine(self) -> EmbeddingEngine:
        return self._embedding_engine

    @property
    def knowledge_graph(self) -> Optional[KnowledgeGraph]:
        return self._knowledge_graph

    @property
    def config(self) -> PipelineConfig:
        return self._config

    @staticmethod
    def _category_to_memory_category(category: Category) -> MemoryCategory:
        mapping = {
            Category.CONVERSATION: MemoryCategory.CONVERSATION,
            Category.PROJECT: MemoryCategory.PROJECT,
            Category.CODE: MemoryCategory.CODE,
            Category.RESEARCH: MemoryCategory.RESEARCH,
            Category.DECISION: MemoryCategory.LONG_TERM,
            Category.PREFERENCE: MemoryCategory.USER_PREFERENCES,
            Category.TASK: MemoryCategory.TASK,
            Category.IDEA: MemoryCategory.LONG_TERM,
            Category.CONCEPT: MemoryCategory.LONG_TERM,
            Category.INSIGHT: MemoryCategory.LONG_TERM,
            Category.QUESTION: MemoryCategory.CONVERSATION,
            Category.COMMAND: MemoryCategory.TOOL,
            Category.ERROR: MemoryCategory.TEMPORARY,
            Category.PATTERN: MemoryCategory.LONG_TERM,
            Category.ARCHITECTURE: MemoryCategory.LONG_TERM,
        }
        return mapping.get(category, MemoryCategory.CONVERSATION)

    @staticmethod
    def _fact_to_entity_type(category: Category) -> EntityType:
        mapping = {
            Category.CONVERSATION: EntityType.CONVERSATION,
            Category.PROJECT: EntityType.PROJECT,
            Category.CODE: EntityType.CODE_SNIPPET,
            Category.RESEARCH: EntityType.RESEARCH_SESSION,
            Category.DECISION: EntityType.DECISION,
            Category.PREFERENCE: EntityType.KNOWLEDGE,
            Category.TASK: EntityType.TASK,
            Category.IDEA: EntityType.IDEA,
            Category.CONCEPT: EntityType.CONCEPT,
            Category.INSIGHT: EntityType.KNOWLEDGE,
            Category.QUESTION: EntityType.KNOWLEDGE,
            Category.COMMAND: EntityType.TOOL,
            Category.ERROR: EntityType.KNOWLEDGE,
            Category.PATTERN: EntityType.KNOWLEDGE,
            Category.ARCHITECTURE: EntityType.CONCEPT,
        }
        return mapping.get(category, EntityType.KNOWLEDGE)
