"""Tests for aetheros_comm.reliability — retry, circuit breaker, backpressure."""

from __future__ import annotations

import time

import pytest

from aetheros_comm.reliability import (Backpressure, CircuitBreaker,
                                       FailureClass, FallbackChain,
                                       RetryPolicy, classify_error)


class TestFailureClass:
    def test_classify_timeout(self):
        assert classify_error(TimeoutError()) == FailureClass.TIMEOUT

    def test_classify_invalid(self):
        assert classify_error(ValueError()) == FailureClass.INVALID_REQUEST

    def test_classify_by_type_name(self):
        # classification is by exception type name, not free text.
        assert classify_error(Exception("connection reset")) == FailureClass.TRANSIENT
        assert classify_error(ValueError("authorization failed")) == FailureClass.INVALID_REQUEST
        assert classify_error(Exception("rate limit")) == FailureClass.RATE_LIMIT

    def test_classify_authorization_type(self):
        assert classify_error(PermissionError()) == FailureClass.AUTHORIZATION


class TestRetryPolicy:
    def test_transient_retryable(self):
        policy = RetryPolicy(max_attempts=3)
        assert policy.should_retry(FailureClass.TRANSIENT, attempt=0)
        assert policy.should_retry(FailureClass.TRANSIENT, attempt=1)

    def test_permanent_not_retryable(self):
        policy = RetryPolicy(max_attempts=3)
        assert not policy.should_retry(FailureClass.PERMANENT, attempt=0)

    def test_attempt_cap(self):
        policy = RetryPolicy(max_attempts=2)
        assert policy.should_retry(FailureClass.TRANSIENT, attempt=0)
        assert not policy.should_retry(FailureClass.TRANSIENT, attempt=1)

    def test_delay_bounded(self):
        policy = RetryPolicy(base_delay=0.1, max_delay=0.5, max_attempts=5)
        delays = [policy.delay_for(i) for i in range(5)]
        assert all(0 < d <= 0.55 for d in delays)  # max_delay + jitter margin


class TestCircuitBreaker:
    def test_closed_until_threshold(self):
        breaker = CircuitBreaker(failure_threshold=3, open_timeout=100)
        assert breaker.state == "CLOSED"
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.allow_request()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        assert not breaker.allow_request()

    def test_success_resets(self):
        breaker = CircuitBreaker(failure_threshold=2, open_timeout=100)
        breaker.record_failure()
        breaker.record_success()
        assert breaker.to_dict()["consecutive_failures"] == 0

    def test_half_open_after_timeout(self):
        breaker = CircuitBreaker(failure_threshold=2, open_timeout=0.05)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.state == "OPEN"
        time.sleep(0.06)
        assert breaker.state == "HALF_OPEN"
        assert breaker.allow_request()

    def test_to_dict(self):
        breaker = CircuitBreaker(failure_threshold=2, open_timeout=10)
        data = breaker.to_dict()
        assert data["state"] == "CLOSED"
        assert data["consecutive_failures"] == 0


class TestBackpressure:
    def test_acquire_release(self):
        bp = Backpressure(max_in_flight=2, queue_limit=10)
        assert bp.acquire("agent")
        assert bp.acquire("agent")
        assert bp.acquire("agent")  # queued (not rejected below max_in_flight)
        bp.release("agent")
        assert bp.acquire("agent")

    def test_queue_limit(self):
        bp = Backpressure(max_in_flight=1, queue_limit=2)
        bp.acquire("a")
        assert bp.acquire("a")  # queued
        assert bp.acquire("a")  # queued
        assert not bp.acquire("a")  # queue full

    def test_release_releases_queue(self):
        bp = Backpressure(max_in_flight=1, queue_limit=2)
        bp.acquire("a")
        bp.acquire("a")  # queued
        bp.release("a")  # pops the queued slot first
        snap = bp.snapshot()
        assert snap["in_flight"].get("a") == 1

    def test_snapshot(self):
        bp = Backpressure(max_in_flight=1, queue_limit=2)
        bp.acquire("a")
        snap = bp.snapshot()
        assert snap["in_flight"]["a"] == 1

    def test_snapshot_shape(self):
        bp = Backpressure()
        snap = bp.snapshot()
        assert set(snap) == {"in_flight", "queued"}


class TestFallbackChain:
    def test_next_candidate_in_order(self):
        chain = FallbackChain(candidates=["a", "b", "c"])
        assert chain.next_candidate() == "a"
        assert chain.next_candidate() == "b"
        assert chain.next_candidate() == "c"
        assert chain.next_candidate() is None

    def test_reset(self):
        chain = FallbackChain(candidates=["a", "b"])
        chain.next_candidate()
        chain.reset()
        assert chain.next_candidate() == "a"

    def test_remaining(self):
        chain = FallbackChain(candidates=["a", "b", "c"])
        chain.next_candidate()
        assert chain.remaining() == ["b", "c"]

    def test_to_dict(self):
        chain = FallbackChain(task_description="task", candidates=["a", "b"])
        data = chain.to_dict()
        assert data["candidates"] == ["a", "b"]
        assert data["task_description"] == "task"
        assert data["remaining"] == ["a", "b"]