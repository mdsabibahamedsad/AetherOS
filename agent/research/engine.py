"""Research execution engine.

Composes the EXISTING infrastructure — ``agent/web_search_registry``
providers for search/extract, ``tools.url_safety`` for SSRF gating,
``tools.website_policy`` for domain policy, ``tools.threat_patterns`` (via
``agent.research.injection``) for untrusted-content scanning — into an
evidence-backed pipeline with observable states, budgets, idempotent
re-runs, checkpoint/resume, and validated citations.

No new model tools are registered here; the surface is library + CLI +
skill (Footprint Ladder rung 2).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from agent.research.injection import safe_excerpt, scan_content
from agent.research.models import (
    Claim,
    ClaimKind,
    ClaimStatus,
    Contradiction,
    Evidence,
    ResearchDepth,
    ResearchSource,
    ResearchTask,
    SourceVisibility,
    TaskStatus,
    ToolFailureKind,
    compute_content_hash,
    detect_contradiction,
    score_source_quality,
)
from agent.research.planner import ResearchPlan, SubQuestion, build_plan
from agent.research.state import (
    TERMINAL_STATES,
    IllegalTransition,
    ResearchStateMachine,
)
from agent.research.store import ResearchStore
from agent.research.urlnorm import (
    SourceDeduplicator,
    dedup_key,
    normalize_url,
    registrable_domain,
)


def dedup_key_of(url: str) -> str:
    return dedup_key(url)
from agent.research.privacy import (
    ExfilBlocked,
    PrivateBoundary,
    evaluate_outbound,
    guard_outbound_query,
)
from agent.research.webops import (
    FetchPipeline,
    PolitenessLimiter,
    RobotsGate,
    detect_live_intent,
)
from agent.research.adversarial import (
    absorb_disprove_result,
    build_disprove_tasks,
    detect_bias,
    diversify_candidates,
)

logger = logging.getLogger(__name__)

EventSink = Callable[[Dict[str, Any]], None]
UrlGate = Callable[[str], Tuple[bool, str]]
ClaimExtractor = Callable[[str, ResearchSource, Dict[str, Any]], List[Claim]]

_CITATION_RE = re.compile(r"\[S(\d+)\]")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")

_FAILURE_HINTS: Tuple[Tuple[str, ToolFailureKind], ...] = (
    ("timeout", ToolFailureKind.TIMEOUT),
    ("timed out", ToolFailureKind.TIMEOUT),
    ("rate limit", ToolFailureKind.RATE_LIMIT),
    ("429", ToolFailureKind.RATE_LIMIT),
    ("401", ToolFailureKind.AUTHENTICATION),
    ("403", ToolFailureKind.AUTHENTICATION),
    ("auth", ToolFailureKind.AUTHENTICATION),
)


class ResearchCancelled(Exception):
    pass


class ResearchPaused(Exception):
    pass


def classify_tool_failure(error: Any) -> ToolFailureKind:
    text = str(error).lower()
    for hint, kind in _FAILURE_HINTS:
        if hint in text:
            return kind
    return ToolFailureKind.PROVIDER_FAILURE


@dataclass
class EngineConfig:
    max_sentences_per_source: int = 4
    excerpt_chars: int = 240
    low_yield_stop: int = 2
    sufficient_verified_ratio: float = 0.55
    confirm_independent_domains: int = 3
    politeness_delay: float = 0.0
    respect_robots: bool = True
    enable_adversarial_pass: bool = True
    disprove_top_k_by_depth: Optional[Dict[str, int]] = None

    def __post_init__(self):
        if self.disprove_top_k_by_depth is None:
            self.disprove_top_k_by_depth = {
                "quick": 0, "standard": 2, "deep": 3, "exhaustive": 4,
            }


def _default_search_provider():
    from agent.web_search_registry import get_active_search_provider

    return get_active_search_provider()


def resolve_search_chain(preferred=None):
    """P93 fallback: injected → active-configured → FanOutSearch wrapper."""
    if preferred is not None:
        return [preferred]
    chain = []
    try:
        active = _default_search_provider()
    except Exception:
        active = None
    if active is not None:
        chain.append(active)
    from agent.research.multiprovider import FanOutSearch

    try:
        fanout = FanOutSearch.from_registry()
    except Exception:
        fanout = None
    if fanout:
        chain.append(fanout)
    return chain


def _default_extract_provider():
    from agent.web_search_registry import get_active_extract_provider

    return get_active_extract_provider()


def _gate_url(url: str) -> Tuple[bool, str]:
    from tools.url_safety import is_safe_url
    from tools.website_policy import check_website_access

    if not is_safe_url(url):
        return False, "ssrf_or_unsafe_destination"
    block = check_website_access(url)
    if block:
        return False, f"domain_policy:{block.get('rule', 'blocked')}"
    return True, ""


class ResearchEngine:
    def __init__(
        self,
        store: Optional[ResearchStore] = None,
        search_provider: Any = None,
        extract_provider: Any = None,
        claim_extractor: Optional[ClaimExtractor] = None,
        url_gate: UrlGate = _gate_url,
        on_event: Optional[EventSink] = None,
        config: Optional[EngineConfig] = None,
        page_cache=None,
        boundary: Optional[PrivateBoundary] = None,
    ):
        self.store = store or ResearchStore()
        self._search = search_provider
        self._extract = extract_provider
        self._claim_extractor = claim_extractor
        self._url_gate = url_gate
        self._on_event = on_event or (lambda event: None)
        self.config = config or EngineConfig()
        self._cancel_requested: set = set()
        self._pause_requested: set = set()
        self.boundary = boundary or PrivateBoundary()
        self.page_cache = page_cache
        self._robots_gate = RobotsGate() if self.config.respect_robots else None
        if self.config.politeness_delay > 0:
            self.fetch_pipeline = FetchPipeline(
                cache=page_cache,
                robots=RobotsGate() if self.config.respect_robots else None,
                limiter=PolitenessLimiter(self.config.politeness_delay),
            )
        else:
            self.fetch_pipeline = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        query: str,
        depth: ResearchDepth = ResearchDepth.STANDARD,
        owner: str = "",
        constraints: Optional[List[str]] = None,
        sources_allowed: Optional[List[str]] = None,
        sources_blocked: Optional[List[str]] = None,
        deadline_seconds: Optional[float] = None,
        parent_task: str = "",
    ) -> ResearchTask:
        task = ResearchTask(
            user_query=" ".join(query.split()),
            depth=depth,
            owner=owner,
            constraints=list(constraints or []),
            sources_allowed=list(sources_allowed or []),
            sources_blocked=list(sources_blocked or []),
            deadline=(time.time() + deadline_seconds) if deadline_seconds else None,
            parent_task=parent_task,
        )
        machine = ResearchStateMachine(task.research_id)
        self.store.create_task(task)
        machine.observe(self._transition_recorder(task))
        machine.transition(TaskStatus.PLANNING, detail="plan requested")
        plan = build_plan(task)
        task.objective = plan.objective
        task.plan = [sq.to_dict() for sq in plan.subquestions]
        self.store.save_task(task)
        return task

    def cancel(self, research_id: str) -> bool:
        """Request cooperative cancel; also cancels stored paused tasks."""
        task = self.store.get_task(research_id)
        if not task:
            return False
        if task.status in TERMINAL_STATES:
            return False
        self._cancel_requested.add(research_id)
        if task.status != TaskStatus.SEARCHING:
            machine = ResearchStateMachine(research_id, initial=task.status)
            try:
                machine.transition(TaskStatus.CANCELLED, detail="user cancel")
            except IllegalTransition:
                self._cancel_requested.discard(research_id)
                return False
            task.status = machine.status
            self.store.save_task(task)
            self.store.log_event(research_id, "cancelled", "user requested")
            self._cancel_requested.discard(research_id)
        return True

    def pause(self, research_id: str) -> bool:
        """Request cooperative pause; takes effect between pipeline steps."""
        task = self.store.get_task(research_id)
        if not task or task.status in TERMINAL_STATES:
            return False
        self._pause_requested.add(research_id)
        if task.status == TaskStatus.PAUSED:
            self._pause_requested.discard(research_id)
            return True
        if task.status not in (TaskStatus.CREATED, TaskStatus.PLANNING,
                               TaskStatus.SEARCHING):
            machine = ResearchStateMachine(research_id, initial=task.status)
            try:
                machine.transition(TaskStatus.PAUSED, detail="user pause")
            except IllegalTransition:
                self._pause_requested.discard(research_id)
                return False
            task.status = machine.status
            self.store.save_task(task)
            self.store.log_event(research_id, "paused", "user requested")
            self._pause_requested.discard(research_id)
        return True

    def run(
        self,
        research_id: str,
        report_format: str = "deep",
        remember: bool = False,
        comparison_subjects: Optional[List[str]] = None,
    ) -> ResearchTask:
        task = self.store.get_task(research_id)
        if not task:
            raise ValueError(f"unknown research task: {research_id}")
        if task.status in TERMINAL_STATES:
            return task
        machine = ResearchStateMachine(research_id, initial=task.status)
        machine.observe(self._transition_recorder(task))
        started = time.time()
        budget = task.budget_for_depth()
        dedup = SourceDeduplicator()
        try:
            self._hydrate_existing(task, dedup)
            plan = self._load_plan(task)
            self._search_phase(machine, task, plan, dedup, budget, started)
            claims = self._read_extract_phase(machine, task, dedup, budget, started)
            claims = self._verify_phase(machine, task, claims)
            self._adversarial_phase(machine, task, dedup, budget)
            try:
                self._build_graph(task)
            except Exception:
                logger.exception("knowledge graph build failed; continuing")
            if machine.status not in (TaskStatus.VERIFYING, TaskStatus.SEARCHING):
                # Early exits (quarantines, blocks, failures) can strand the
                # machine in a reading/extraction state; verification is the
                # legitimate funnel into synthesis.
                self._safe_transition(machine, TaskStatus.VERIFYING,
                                      detail="pre-synthesis normalization")
            machine.transition(TaskStatus.SYNTHESIZING, detail="rendering report")
            report, warnings = self.render_report(
                task, fmt=report_format, subjects=comparison_subjects
            )
            report = self._validate_citations(report, task)
            task.final_report = report
            if warnings:
                task.constraints = list(
                    dict.fromkeys(list(task.constraints) + warnings[:3])
                )
            machine.transition(TaskStatus.REVIEWING, detail="citation validation")
            machine.transition(TaskStatus.COMPLETED, detail="done")
            task.status = machine.status
            self.store.save_task(task)
            if remember:
                from agent.research.memory_bridge import remember_research

                outcomes = remember_research(task, self.store.list_claims(research_id))
                self.store.log_event(
                    research_id, "memory_write",
                    f"{sum(1 for o in outcomes if o.get('written'))}/{len(outcomes)}",
                )
            return task
        except ResearchCancelled:
            self._cancel_requested.discard(research_id)
            self._safe_transition(machine, TaskStatus.CANCELLED, detail="cancelled")
            task.status = machine.status
            self.store.save_task(task)
            return task
        except ResearchPaused:
            self._pause_requested.discard(research_id)
            self._safe_transition(machine, TaskStatus.PAUSED, detail="user pause")
            task.status = machine.status
            self.store.save_task(task)
            self.store.log_event(research_id, "paused", "cooperative checkpoint")
            return task
        except Exception as exc:
            logger.exception("research run failed")
            task.error = str(exc)[:500]
            self._safe_transition(machine, TaskStatus.FAILED, detail=task.error)
            task.status = machine.status
            self.store.save_task(task)
            return task

    def render_report(
        self,
        task: ResearchTask,
        fmt: str = "deep",
        subjects: Optional[List[str]] = None,
    ) -> Tuple[str, List[str]]:
        from agent.research.reports import (
            ReportContext,
            quality_metric,
            render as render_report_fmt,
            render_traceability,
        )

        ctx = ReportContext(
            task=task,
            sources=self.store.list_sources(task.research_id),
            claims=self.store.list_claims(task.research_id),
            contradictions=self.store.list_contradictions(task.research_id),
            queries_run=list(task.queries_run),
            usage=self.store.usage(task.research_id),
        )
        body, warnings = render_report_fmt(ctx, fmt, subjects)
        if fmt == "deep":
            bias = detect_bias(ctx.sources, ctx.claims)
            quality = quality_metric(ctx)
            extra = [
                "",
                "## Quality & Bias (disclosed heuristics)",
                f"- Bias: {bias.summary()}",
                *(f"- Bias note: {n}" for n in bias.notes),
                f"- Quality: {quality['total']:.2f} — {quality['disclaimer']}",
                "",
            ]
            extra.append(render_traceability(ctx))
            body = body + "\n" + "\n".join(extra)
        return body, warnings

    # ------------------------------------------------------------------
    # Pipeline phases
    # ------------------------------------------------------------------

    def _hydrate_existing(self, task: ResearchTask, dedup: SourceDeduplicator) -> None:
        for src in self.store.list_sources(task.research_id):
            dedup.register_url(src.url)
            # Private/user documents are independent of the public web:
            # their hashes must not mark later public pages as mirrors.
            if src.content_hash and src.visibility == SourceVisibility.PUBLIC:
                dedup.register_content(src.content_hash, src.url)

    def _load_plan(self, task: ResearchTask) -> ResearchPlan:
        from agent.research.planner import SearchStrategy

        if task.plan:
            subs = [
                SubQuestion(
                    text=sq["text"],
                    purpose=sq.get("purpose", ""),
                    strategies=[
                        SearchStrategy(kind=st["kind"], query=st["query"])
                        for st in sq.get("strategies", [])
                    ],
                )
                for sq in task.plan
            ]
            return ResearchPlan(objective=task.objective, subquestions=subs)
        plan = build_plan(task)
        task.plan = [sq.to_dict() for sq in plan.subquestions]
        return plan

    def _search_phase(
        self,
        machine: ResearchStateMachine,
        task: ResearchTask,
        plan: ResearchPlan,
        dedup: SourceDeduplicator,
        budget: Dict[str, int],
        started: float,
    ) -> None:
        if machine.status == TaskStatus.CREATED:
            machine.transition(TaskStatus.PLANNING)
        if machine.status == TaskStatus.PLANNING:
            machine.transition(TaskStatus.SEARCHING, detail="starting searches")
        elif machine.status == TaskStatus.PAUSED:
            machine.transition(TaskStatus.SEARCHING, detail="resumed")

        if not self._search:
            chain = resolve_search_chain()
            self._search = chain[0] if chain else None
        if not self._search:
            raise RuntimeError(
                "no web search backend available; configure one via `aetheros tools` "
                "or pass search_provider to ResearchEngine"
            )
        provider_name = getattr(self._search, "name", "unknown")

        low_yield = 0
        for subquestion in plan.subquestions:
            if self._stop_searching(machine, task, budget, started, low_yield):
                break
            for strategy in subquestion.strategies:
                if self._stop_searching(machine, task, budget, started, low_yield):
                    break
                query = strategy.query
                if query in task.queries_run:
                    continue
                self._check_cancel(task.research_id)
                self._check_pause(task.research_id)
                verdict = evaluate_outbound(query, self.boundary)
                if not verdict.outbound_ok:
                    self.store.log_event(
                        task.research_id, "security_rejection",
                        f"outbound_query_blocked:{verdict.reason}"[:300],
                    )
                    self._on_event({"kind": "warning",
                                    "detail": f"query blocked: {verdict.reason}"})
                    continue
                task.queries_run.append(query)
                self.store.log_event(task.research_id, "query", query)
                self._on_event({"kind": "search", "detail": safe_excerpt(query, 80)})
                before = dedup.unique_pages
                try:
                    results = self._execute_search(query, budget["max_sources"])
                except Exception as exc:
                    kind = classify_tool_failure(exc)
                    self.store.log_event(
                        task.research_id, "failure", f"{kind.value}: {exc}"[:300]
                    )
                    continue
                candidates = [
                    (str(r.get("url") or ""), str(r.get("title") or ""))
                    for r in results
                ]
                diversified = diversify_candidates(candidates)
                allowed_urls = {u for u, _ in diversified}
                results = [r for r in results if str(r.get("url") or "") in allowed_urls]
                new_pages = 0
                for raw in results:
                    if dedup.unique_pages >= budget["max_sources"]:
                        break
                    admitted, reason = self._admit_result(raw, task)
                    if not admitted:
                        self.store.log_event(
                            task.research_id, "skipped", reason
                        )
                        continue
                    if not dedup.register_url(admitted.url):
                        continue
                    admitted.provider = provider_name
                    admitted.quality_score = score_source_quality(admitted)["total"]
                    self.store.upsert_source(task.research_id, admitted)
                    new_pages += 1
                yield_delta = dedup.unique_pages - before
                low_yield = low_yield + 1 if yield_delta < 2 else 0

    def _stop_searching(
        self,
        machine: ResearchStateMachine,
        task: ResearchTask,
        budget: Dict[str, int],
        started: float,
        low_yield: int,
    ) -> bool:
        if machine.status != TaskStatus.SEARCHING:
            return True
        if task.deadline and time.time() > task.deadline:
            return True
        if len(task.queries_run) >= budget["max_queries"]:
            return True
        usage = self.store.usage(task.research_id)
        if usage["pages"] >= budget["max_sources"]:
            return True
        if low_yield >= self.config.low_yield_stop:
            self.store.log_event(
                task.research_id, "marginal_value_stop", "queries stopped yielding new pages"
            )
            return True
        return False

    def _execute_search(self, query: str, max_sources: int) -> List[Dict[str, Any]]:
        response = self._search.search(query=query, limit=min(8, max(3, max_sources // 2)))
        if not isinstance(response, dict) or not response.get("success"):
            raise RuntimeError(str(response.get("error", "malformed search envelope")))
        web = ((response.get("data") or {}).get("web")) or []
        if not isinstance(web, list):
            raise RuntimeError("malformed search results payload")
        return web

    def _admit_result(self, raw: Dict[str, Any], task: ResearchTask) -> Tuple[Optional[ResearchSource], str]:
        url = str(raw.get("url") or "").strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            return None, "non_http_url"
        canonical = normalize_url(url)
        if not canonical:
            return None, "unparseable_url"
        allowed_domains, blocked_domains = task.sources_allowed, task.sources_blocked
        reg = registrable_domain(url)
        if blocked_domains and any(reg == registrable_domain(d) for d in blocked_domains):
            return None, "user_blocked_domain"
        if allowed_domains and not any(reg == registrable_domain(d) for d in allowed_domains):
            return None, "outside_user_allowlist"
        ok, reason = self._url_gate(canonical)
        if not ok:
            return None, reason
        from agent.research.lookalike import assess_domain, risk_bump

        verdict = assess_domain(canonical)
        history_risk = self.store.domain_risk_factor(registrable_domain(canonical))
        title = str(raw.get("title") or "")[:200]
        snippet = safe_excerpt(str(raw.get("description") or ""), self.config.excerpt_chars)

        from agent.research.models import classify_source_type

        source = ResearchSource(
            url=url,
            canonical_url=canonical,
            domain=(canonical.split("//", 1)[-1].split("/", 1)[0]),
            title=title,
            snippet=snippet,
            source_type=classify_source_type(canonical, title),
            trust_signals=_initial_trust_signals(canonical),
            publication_date=str(raw.get("published_date") or "") or None,
            access_status="discovered",
            risk=min(1.0, history_risk * 0.5 + risk_bump(verdict)),
            metadata={
                **({"lookalike_of": verdict.lookalike_of,
                    "lookalike_kind": verdict.kind}
                   if verdict.kind != "none" else {}),
                **({"domain_history_risk": round(history_risk, 2)}
                   if history_risk > 0 else {}),
            },
        )
        return source, ""

    def _read_extract_phase(
        self,
        machine: ResearchStateMachine,
        task: ResearchTask,
        dedup: SourceDeduplicator,
        budget: Dict[str, int],
        started: float,
    ) -> List[Claim]:
        pending = [s for s in self.store.list_sources(task.research_id) if not s.content_hash]
        if pending:
            self._safe_transition(machine, TaskStatus.COLLECTING, detail=f"{len(pending)} pages queued")
            if not self._extract:
                self._extract = _default_extract_provider()
                if not self._extract:
                    raise RuntimeError(
                        "no web extract backend available; configure one via `aetheros tools`"
                    )
            for source in pending:
                self._check_cancel(task.research_id)
                self._check_pause(task.research_id)
                if task.deadline and time.time() > task.deadline:
                    break
                self._safe_transition(machine, TaskStatus.READING, detail=source.canonical_url)
                self._on_event({"kind": "reading", "detail": source.domain})
                force_refresh = detect_live_intent(task.user_query)
                cached = (
                    self.page_cache.get_fresh(
                        dedup_key_of(source.url), source.source_type,
                        force_refresh=force_refresh,
                    )
                    if self.page_cache is not None
                    else None
                )
                if cached is not None:
                    content, title = cached["content"], cached["title"]
                    self.store.log_event(task.research_id, "cache_hit", source.domain)
                    self._bump_domain(source.url, "fetches")
                else:
                    if self._robots_gate is not None:
                        robots_ok, robots_detail = self._robots_gate.allowed(source.url)
                        if not robots_ok:
                            source.access_status = f"robots_blocked:{robots_detail}"
                            self.store.upsert_source(task.research_id, source)
                            self.store.log_event(
                                task.research_id, "skipped",
                                f"robots:{source.domain}"[:200],
                            )
                            continue
                    if (
                        self.fetch_pipeline is not None
                        and self.fetch_pipeline.limiter is not None
                    ):
                        from urllib.parse import urlparse

                        host = urlparse(source.canonical_url).hostname or ""
                        self.fetch_pipeline.limiter.wait(host)
                    try:
                        content, title, meta = self._fetch_one(source)
                    except Exception as exc:
                        kind = classify_tool_failure(exc)
                        source.access_status = f"fetch_failed:{kind.value}"
                        self.store.upsert_source(task.research_id, source)
                        self.store.log_event(
                            task.research_id, "failure",
                            f"{kind.value}:{source.domain}:{str(exc)[:120]}",
                        )
                        continue
                    final_url = str(
                        (meta or {}).get("final_url")
                        or (meta or {}).get("sourceURL")
                        or ""
                    )
                    if final_url and registrable_domain(final_url) != registrable_domain(source.url):
                        source.redirect_chain = [source.url, final_url]
                        ok_final, reason_final = self._url_gate(final_url)
                        if not ok_final:
                            source.access_status = f"redirect_blocked:{reason_final}"
                            source.risk = min(1.0, source.risk + 0.5)
                            self.store.upsert_source(task.research_id, source)
                            self.store.log_event(
                                task.research_id, "security_rejection",
                                f"redirect_to_unsafe:{source.domain}->{reason_final}",
                            )
                            continue
                        source.risk = min(1.0, source.risk + 0.2)
                    if self.page_cache is not None:
                        self.page_cache.put(
                            dedup_key_of(source.url), source.url, title,
                            content, compute_content_hash(content),
                            source.source_type,
                        )
                    self._bump_domain(source.url, "fetches")
                self._safe_transition(machine, TaskStatus.EXTRACTING, detail=source.domain)
                scan = scan_content(content)
                if scan.quarantined:
                    source.injection_flags = list(scan.threats)
                    source.risk = min(1.0, source.risk + 0.6)
                    source.access_status = "quarantined:injection_patterns"
                    source.content_hash = compute_content_hash(content)
                    self.store.upsert_source(task.research_id, source)
                    self._bump_domain(source.url, "quarantined")
                    self.store.log_event(
                        task.research_id, "security_rejection",
                        f"{source.domain}:{scan.summary()}"[:300],
                    )
                    self._on_event({"kind": "warning", "detail": f"injection patterns quarantined ({source.domain})"})
                    continue
                source.content_hash = compute_content_hash(content)
                is_new, copies = dedup.register_content(source.content_hash, source.url)
                if not is_new:
                    mirrors = dedup.mirrors_of(source.content_hash)
                    mirrors = [m for m in mirrors if m != source.url]
                    source.metadata["mirror_of"] = mirrors[0] if mirrors else ""
                    source.access_status = "duplicate_content"
                    source.trust_signals.corroboration_domains = 0
                    self.store.upsert_source(task.research_id, source)
                    self._bump_domain(source.url, "duplicates")
                    self.store.log_event(
                        task.research_id, "duplicate", f"{source.domain} mirrors {mirrors[0] if mirrors else '?'}"
                    )
                    continue
                source.access_status = "ok"
                source.snippet = safe_excerpt(content, self.config.excerpt_chars) or source.snippet
                if title and not source.title:
                    source.title = title[:200]
                self.store.upsert_source(task.research_id, source)
                claims = self._make_claims(task, source, content)
                self.store.log_event(
                    task.research_id, "claims", f"{source.domain}:{len(claims)}"
                )
        return self.store.list_claims(task.research_id)

    def _fetch_one(self, source: ResearchSource) -> Tuple[str, str, Dict[str, Any]]:
        results = self._extract.extract([source.url])
        if inspect.iscoroutine(results):
            results = asyncio.run(results)
        if not isinstance(results, list) or not results:
            raise RuntimeError("empty extract payload")
        entry = next(
            (r for r in results if str(r.get("url", "")).rstrip("/") == source.url.rstrip("/")),
            results[0],
        )
        if entry.get("error"):
            raise RuntimeError(str(entry["error"]))
        if entry.get("blocked_by_policy"):
            raise RuntimeError("blocked_by_policy")
        content = str(entry.get("content") or "")
        if not content.strip():
            raise RuntimeError("empty page content")
        meta = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
        return content, str(entry.get("title") or ""), meta

    def _make_claims(
        self, task: ResearchTask, source: ResearchSource, content: str
    ) -> List[Claim]:
        if self._claim_extractor:
            claims = self._claim_extractor(content, source, {})
        else:
            claims = self._sentence_claims(content, source)
        kept: List[Claim] = []
        for claim in claims[: self.config.max_sentences_per_source * 2]:
            claim.task_id = task.research_id
            if self.store.add_claim(task.research_id, claim):
                for ev in claim.evidence:
                    self.store.add_evidence(task.research_id, ev)
                kept.append(claim)
                continue
            existing = next(
                (
                    c
                    for c in self.store.list_claims(task.research_id)
                    if c.claim_id == claim.claim_id
                ),
                None,
            )
            if existing is not None:
                existing.source_ids = list(
                    dict.fromkeys(list(existing.source_ids) + list(claim.source_ids))
                )
                for ev in claim.evidence:
                    ev.claim_id = existing.claim_id
                    if self.store.add_evidence(task.research_id, ev):
                        existing.evidence.append(ev)
                existing.updated_at = time.time()
                self.store.update_claim(task.research_id, existing)
                kept.append(existing)
        return kept

    def _sentence_claims(self, content: str, source: ResearchSource) -> List[Claim]:
        window = _prep_for_sentences(content)
        sentences = [s.strip() for s in _SENTENCE_RE.split(window)]
        scored = []
        for idx, sent in enumerate(sentences):
            if not (40 <= len(sent) <= 400):
                continue
            letters = sum(ch.isalpha() for ch in sent)
            if letters < 30 or "@" in sent or sent.count("|") > 2:
                continue
            scored.append((idx, sent))
        selected = scored[: self.config.max_sentences_per_source]
        claims = []
        from agent.research.targets import classify_news_language

        for idx, sent in selected:
            ev = Evidence(
                claim_id="",
                source_id=source.source_id,
                location=f"sentence:{idx}",
                excerpt_reference=safe_excerpt(sent, self.config.excerpt_chars),
                content_hash=compute_content_hash(sent),
                retrieved_at=time.time(),
                strength=0.45,
            )
            marker = classify_news_language(sent)
            claim = Claim(
                text=sent,
                kind=ClaimKind.SOURCE_CLAIM,
                status=ClaimStatus.UNVERIFIED,
                source_ids=[source.source_id],
                evidence=[ev],
                confidence=0.3,
                language_marker=marker if source.source_type.value == "NEWS" else "",
                location_hint=f"{source.source_type.value.lower()} page 1",
            )
            ev.claim_id = claim.claim_id
            claims.append(claim)
        return claims

    def _verify_phase(
        self, machine: ResearchStateMachine, task: ResearchTask, claims: List[Claim]
    ) -> List[Claim]:
        self._safe_transition(machine, TaskStatus.VERIFYING, detail="corroboration pass")
        sources = {s.source_id: s for s in self.store.list_sources(task.research_id)}
        self._assign_statuses(task, claims, sources)
        self._detect_contradictions(task, claims)
        claims = self.store.list_claims(task.research_id)
        total = len(claims)
        strong = sum(
            1
            for c in claims
            if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED, ClaimStatus.SUPPORTED)
        )
        task.confidence = round(min(1.0, (strong / total) if total else 0.0), 3)
        self.store.log_event(
            task.research_id, "verified", f"{strong}/{total} supported claims"
        )
        return claims

    def _assign_statuses(
        self,
        task: ResearchTask,
        claims: List[Claim],
        sources: Dict[str, ResearchSource],
    ) -> bool:
        groups: List[List[Claim]] = []
        remaining = list(claims)
        while remaining:
            head = remaining.pop(0)
            group = [head]
            for other in list(remaining):
                if _same_assertion(head.text, other.text):
                    group.append(other)
                    remaining.remove(other)
            groups.append(group)
        for group in groups:
            domains = {
                registrable_domain(sources[sid].url)
                for c in group
                for sid in c.source_ids
                if sid in sources
            }
            primary = any(
                sources[sid].is_primary
                for c in group
                for sid in c.source_ids
                if sid in sources
            )
            n = len(domains)
            if n >= self.config.confirm_independent_domains:
                status = ClaimStatus.CONFIRMED
            elif n >= 2:
                status = ClaimStatus.STRONGLY_SUPPORTED
            elif n == 1 and primary:
                status = ClaimStatus.SUPPORTED
            else:
                status = ClaimStatus.UNVERIFIED
            for claim in group:
                claim.status = status
                conf = {"CONFIRMED": 0.95, "STRONGLY_SUPPORTED": 0.8, "SUPPORTED": 0.65}.get(status.value, 0.3)
                strengths = [e.strength for e in claim.evidence] or [0.0]
                claim.confidence = round(conf * (sum(strengths) / len(strengths)) / 0.5, 3)
                if claim.confidence > 1:
                    claim.confidence = 1.0
                claim.updated_at = time.time()
                self.store.update_claim(task.research_id, claim)
        return True

    def _detect_contradictions(self, task: ResearchTask, claims: List[Claim]) -> None:
        capped = claims[:60]
        for i in range(len(capped)):
            for j in range(i + 1, len(capped)):
                a, b = capped[i], capped[j]
                if a.source_ids and set(a.source_ids) & set(b.source_ids):
                    continue
                signal = detect_contradiction(a.text, b.text) or detect_contradiction(b.text, a.text)
                if signal:
                    con = Contradiction(
                        claim_a_id=a.claim_id,
                        claim_b_id=b.claim_id,
                        reason=f"conflict signal ({signal})",
                    )
                    self.store.add_contradiction(task.research_id, con)
                    a.status = ClaimStatus.CONTRADICTED
                    b.status = ClaimStatus.CONTRADICTED
                    self.store.update_claim(task.research_id, a)
                    self.store.update_claim(task.research_id, b)
                    self.store.log_event(
                        task.research_id, "contradiction", signal[:200]
                    )

    # ------------------------------------------------------------------
    # Adversarial pass (P74) + knowledge graph (P50-52)
    # ------------------------------------------------------------------

    def _adversarial_phase(
        self,
        machine: ResearchStateMachine,
        task: ResearchTask,
        dedup: SourceDeduplicator,
        budget: Dict[str, int],
    ) -> None:
        top_k = self.config.disprove_top_k_by_depth.get(task.depth.value, 0)
        if not self.config.enable_adversarial_pass or top_k <= 0:
            return
        if not self._search:
            return
        claims = [
            c for c in self.store.list_claims(task.research_id)
            if c.status in (ClaimStatus.CONFIRMED, ClaimStatus.STRONGLY_SUPPORTED)
        ]
        disprove_tasks = build_disprove_tasks(claims, top_k=top_k)
        if not disprove_tasks:
            return
        self.store.log_event(
            task.research_id, "adversarial",
            f"{len(disprove_tasks)} disprove targets",
        )
        sources = {s.source_id: s for s in self.store.list_sources(task.research_id)}
        for dtask in disprove_tasks:
            for query in dtask.queries[:2]:
                if len(task.queries_run) >= budget["max_queries"] + 4:
                    return
                verdict = evaluate_outbound(query, self.boundary)
                if not verdict.outbound_ok:
                    continue
                task.queries_run.append(query)
                self.store.log_event(task.research_id, "query", query)
                try:
                    results = self._execute_search(query, 4)
                except Exception as exc:
                    self.store.log_event(
                        task.research_id, "failure",
                        f"{classify_tool_failure(exc).value}:{str(exc)[:120]}",
                    )
                    continue
                claim = next(
                    (c for c in claims if c.claim_id == dtask.claim_id), None
                )
                if claim is None:
                    continue
                for raw in results:
                    snippet = safe_excerpt(str(raw.get("description") or ""), 240)
                    title = str(raw.get("title") or "")
                    combined = f"{title}. {snippet}".strip(". ")
                    if absorb_disprove_result(claim, combined, source_id=""):
                        counter = Claim(
                            text=combined.rstrip("."),
                            status=ClaimStatus.CONTRADICTED,
                            confidence=0.35,
                            task_id=task.research_id,
                        )
                        if self.store.add_claim(task.research_id, counter):
                            self.store.update_claim(task.research_id, counter)
                        self.store.update_claim(task.research_id, claim)
                        self.store.add_contradiction(
                            task.research_id,
                            Contradiction(
                                claim_a_id=claim.claim_id,
                                claim_b_id=counter.claim_id,
                                reason=f"adversarial:{signal_short(combined)}",
                            ),
                        )
                        self.store.log_event(
                            task.research_id, "contradiction",
                            f"adversarial hit on {dtask.claim_id}"[:200],
                        )
                        break

    def _build_graph(self, task: ResearchTask):
        from agent.research.knowledge_graph import ResearchKnowledgeGraph

        graph = self.store.load_graph(task.research_id)
        sources = {s.source_id: s for s in self.store.list_sources(task.research_id)}
        domain_entities: Dict[str, str] = {}

        def entity_for_domain(domain: str) -> Optional[str]:
            key = registrable_domain(domain)
            if key not in domain_entities:
                eid, _created = graph.add_entity(
                    key, "source", confidence=0.5, source_ids=[]
                )
                domain_entities[key] = eid
            return domain_entities[key]

        for src in sources.values():
            entity_for_domain(src.url or src.domain)

        known_names = set()
        for src in sources.values():
            known_names.update(re.findall(r"[A-Z][A-Za-z0-9]{2,}", src.title))
        for claim in self.store.list_claims(task.research_id):
            candidates = ResearchKnowledgeGraph.extract_candidate_entities(
                claim.text, known_names
            )
            for name in candidates:
                eid, created = graph.add_entity(
                    name, "technology", confidence=0.3,
                    source_ids=list(claim.source_ids),
                )
                for sid in claim.source_ids:
                    src = sources.get(sid)
                    if src is None:
                        continue
                    src_eid = entity_for_domain(src.url)
                    relation = (
                        "contradicts"
                        if claim.status == ClaimStatus.CONTRADICTED and created is False
                        else "mentions" if claim.has_evidence else "related_to"
                    )
                    graph.link(
                        src_eid, relation, eid,
                        confidence=claim.confidence or 0.3,
                        evidence_refs=[ev.evidence_id for ev in claim.evidence][:2],
                        source_ids=[sid],
                    )
        self.store.save_graph(task.research_id, graph)
        self.store.log_event(
            task.research_id, "knowledge_graph",
            f"{len(graph.entities)} nodes/{len(graph.edges)} edges",
        )
        return graph

    # ------------------------------------------------------------------
    # Local documents (P31-35, P65-66) and MCP evidence (P90-91)
    # ------------------------------------------------------------------

    def add_local_document(self, research_id: str, path: str) -> Dict[str, Any]:
        """Ingest an authorized local/user document as a private source."""
        from agent.research.documents import DocumentIngestion

        task = self.store.get_task(research_id)
        if not task:
            raise ValueError(f"unknown research task: {research_id}")
        doc = DocumentIngestion().ingest(path)
        text = doc.full_text
        doc_scan = scan_content(text)
        self.boundary.register_private_text(text)
        tables_md = "\n\n".join(t.to_markdown() for t in doc.tables[:5])
        source = ResearchSource(
            url=f"file://{doc.path}",
            canonical_url=f"file://{doc.path}",
            domain="local",
            title=doc.title,
            content_hash=compute_content_hash(text),
            visibility=SourceVisibility.USER_PROVIDED,
            access_status=(
                "quarantined:injection_patterns" if doc_scan.quarantined
                else "local_document"
            ),
            snippet=safe_excerpt(text, self.config.excerpt_chars),
            injection_flags=list(doc_scan.threats),
            metadata={
                "kind": doc.kind,
                "pages": str(len(doc.pages)),
                **({"ocr": doc.metadata["ocr"]} if doc.metadata.get("ocr") else {}),
                **({"tables_md": tables_md} if tables_md else {}),
                **{f"pdf_{k}": v for k, v in doc.metadata.items() if k != "ocr"},
            },
        )
        inserted = self.store.upsert_source(research_id, source)
        claims_added = 0
        if doc_scan.quarantined:
            self.store.log_event(
                research_id, "security_rejection",
                f"local_doc_quarantined:{doc_scan.summary()}"[:300],
            )
        if inserted and not doc_scan.quarantined:
            window = _prep_for_sentences(text)
            sentences = [s.strip() for s in _SENTENCE_RE.split(window)]
            kept = 0
            offset = 0
            for idx, sent in enumerate(sentences):
                if kept >= self.config.max_sentences_per_source:
                    break
                if not (40 <= len(sent) <= 400):
                    offset += len(sent) + 1
                    continue
                letters = sum(ch.isalpha() for ch in sent)
                if letters < 30 or "@" in sent or sent.count("|") > 2:
                    offset += len(sent) + 1
                    continue
                page_no = doc.page_of_offset(offset)
                is_ocr_page = any(
                    p.number == page_no and p.ocr for p in doc.pages
                )
                ev = Evidence(
                    claim_id="",
                    source_id=source.source_id,
                    location=f"{doc.kind} page {page_no}" + (" (OCR)" if is_ocr_page else ""),
                    excerpt_reference=safe_excerpt(sent, self.config.excerpt_chars),
                    content_hash=compute_content_hash(sent),
                    retrieved_at=time.time(),
                    strength=0.4,
                )
                claim = Claim(
                    text=sent,
                    kind=ClaimKind.SOURCE_CLAIM,
                    status=ClaimStatus.UNVERIFIED,
                    source_ids=[source.source_id],
                    evidence=[ev],
                    confidence=0.25,
                )
                ev.claim_id = claim.claim_id
                if self.store.add_claim(research_id, claim):
                    self.store.add_evidence(research_id, ev)
                    claims_added += 1
                kept += 1
                offset += len(sent) + 1
        self.store.log_event(
            research_id, "document_ingested",
            f"{doc.kind}:{len(doc.pages)}p:{claims_added} claims",
        )
        return {
            "source_id": source.source_id,
            "pages": len(doc.pages),
            "tables": len(doc.tables),
            "ocr_pages": doc.ocr_pages,
            "claims_added": claims_added,
            "warnings": list(doc.warnings),
            "inserted": inserted,
        }

    def add_mcp_evidence(
        self, research_id: str, server: str, tool: str, output_text: str
    ) -> Dict[str, Any]:
        """P90-91: MCP tool output is UNTRUSTED external data — it gets the
        same injection screening and provenance treatment as web content."""
        task = self.store.get_task(research_id)
        if not task:
            raise ValueError(f"unknown research task: {research_id}")
        url = f"mcp://{server}/{tool}"
        scan = scan_content(output_text or "")
        source = ResearchSource(
            url=url,
            canonical_url=url,
            domain=f"mcp:{server}",
            title=f"{server}:{tool}",
            provider=f"mcp:{server}",
            visibility=SourceVisibility.SYSTEM,
            content_hash=compute_content_hash(output_text or ""),
            access_status=(
                "quarantined:injection_patterns" if scan.quarantined else "ok"
            ),
            snippet=safe_excerpt(output_text or "", self.config.excerpt_chars),
            injection_flags=list(scan.threats),
        )
        if scan.quarantined:
            source.risk = 0.6
        inserted = self.store.upsert_source(research_id, source)
        claims_added = 0
        if inserted and not scan.quarantined and output_text:
            claims = self._sentence_claims(output_text, source)
            for claim in claims[: self.config.max_sentences_per_source]:
                claim.task_id = research_id
                if self.store.add_claim(research_id, claim):
                    for ev in claim.evidence:
                        self.store.add_evidence(research_id, ev)
                    claims_added += 1
        self.store.log_event(
            research_id,
            "mcp_evidence" if not scan.quarantined else "security_rejection",
            f"{server}/{tool}:{scan.summary()}"[:300],
        )
        return {
            "source_id": source.source_id,
            "quarantined": scan.quarantined,
            "claims_added": claims_added,
            "inserted": inserted,
        }

    def _validate_citations(self, report: str, task: ResearchTask) -> str:
        sources = {s.source_id: i + 1 for i, s in enumerate(self.store.list_sources(task.research_id))}
        evidence_by_source = {}
        for ev in self.store.list_evidence(task.research_id):
            evidence_by_source.setdefault(ev.source_id, []).append(ev)
        problems: List[str] = []

        def check(match: re.Match) -> str:
            n = int(match.group(1))
            source = next((s for s, k in sources.items() if k == n), None)
            if source is None:
                problems.append(f"citation S{n} references no retrieved source")
                return ""
            if not evidence_by_source.get(source):
                problems.append(f"citation S{n} has no linked evidence")
                return match.group(0)
            return match.group(0)

        validated = _CITATION_RE.sub(check, report)
        if problems:
            note = "\n".join(f"- DROPPED: {p}" for p in problems)
            validated += "\n\n## Citation Validation\n" + note + "\n"
            self.store.log_event(
                task.research_id, "citation_validation", "; ".join(problems)[:300]
            )
        return validated

    # ------------------------------------------------------------------
    # Plumbing
    # ------------------------------------------------------------------

    def _check_cancel(self, research_id: str) -> None:
        if research_id in self._cancel_requested:
            raise ResearchCancelled(research_id)

    def _check_pause(self, research_id: str) -> None:
        if research_id in self._pause_requested:
            raise ResearchPaused(research_id)

    def _bump_domain(self, url: str, field: str) -> None:
        try:
            self.store.bump_domain(registrable_domain(url), field)
        except Exception:
            logger.debug("domain stat bump failed", exc_info=True)

    def _transition_recorder(self, task: ResearchTask) -> EventSink:
        def recorder(event) -> None:
            self.store.record_transition(event)
            task.status = TaskStatus(event.to_status)
            task.touch()
            self.store.save_task(task)
            self._on_event(
                {"kind": "phase", "state": event.to_status, "detail": event.detail}
            )
        return recorder

    def _safe_transition(
        self, machine: ResearchStateMachine, target: TaskStatus, detail: str
    ) -> None:
        try:
            machine.transition(target, detail=detail)
        except IllegalTransition:
            pass


def _prep_for_sentences(text: str) -> str:
    """Drop markdown table rows (tables are captured separately) and turn
    paragraph breaks into explicit sentence boundaries before splitting."""
    lines = [
        ln for ln in (text or "")[:20000].splitlines()
        if not ln.lstrip().startswith("|")
    ]
    paragraphs = [seg.strip() for seg in "\n".join(lines).split("\n\n") if seg.strip()]
    return ". ".join(paragraphs)


def _initial_trust_signals(canonical_url: str):
    from agent.research.models import TrustSignals

    return TrustSignals(https=canonical_url.lower().startswith("https://"))


def _normalize_for_compare(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def signal_short(text: str) -> str:
    words = re.findall(r"[A-Za-z]{4,}", text or "")
    return " ".join(words[:4])[:48]


def _same_assertion(a: str, b: str) -> bool:
    na, nb = _normalize_for_compare(a), _normalize_for_compare(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    shorter, longer = (na, nb) if len(na) <= len(nb) else (nb, na)
    if len(shorter) < 25:
        return False
    containment = len(set(shorter.split()) & set(longer.split())) / len(shorter.split())
    return containment >= 0.85
