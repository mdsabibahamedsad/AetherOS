"""
Ratings and Reviews
===================

Manages ratings and reviews for marketplace extensions.
Supports:

- Star ratings (1-5)
- Written reviews
- Verified purchase badges
- Review moderation
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class Rating:
    """A numerical rating for an extension."""
    extension_id: str
    score: float        # 1.0 to 5.0
    user: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
        self.score = max(1.0, min(5.0, self.score))


@dataclass
class Review:
    """A written review for an extension."""
    extension_id: str
    rating: float
    title: str = ""
    body: str = ""
    user: str = ""
    version: str = ""
    timestamp: str = ""
    verified_purchase: bool = False
    helpful_count: int = 0


class RatingsManager:
    """Manages ratings and reviews locally."""

    def __init__(self, storage_path: Optional[Path] = None) -> None:
        self._storage_path = storage_path or Path.home() / ".aetheros" / "reviews.json"
        self._ratings: Dict[str, List[Rating]] = {}
        self._reviews: Dict[str, List[Review]] = {}
        self._load()

    def add_rating(self, rating: Rating) -> None:
        self._ratings.setdefault(rating.extension_id, []).append(rating)
        self._save()

    def add_review(self, review: Review) -> None:
        self._reviews.setdefault(review.extension_id, []).append(review)
        self._save()

    def get_average_rating(self, extension_id: str) -> float:
        ratings = self._ratings.get(extension_id, [])
        if not ratings:
            return 0.0
        return sum(r.score for r in ratings) / len(ratings)

    def get_rating_count(self, extension_id: str) -> int:
        return len(self._ratings.get(extension_id, []))

    def get_reviews(self, extension_id: str) -> List[Review]:
        return list(self._reviews.get(extension_id, []))

    def get_user_review(self, extension_id: str, user: str) -> Optional[Review]:
        for review in self._reviews.get(extension_id, []):
            if review.user == user:
                return review
        return None

    def delete_review(self, extension_id: str, user: str) -> bool:
        reviews = self._reviews.get(extension_id, [])
        for i, review in enumerate(reviews):
            if review.user == user:
                reviews.pop(i)
                self._save()
                return True
        return False

    def _load(self) -> None:
        try:
            if self._storage_path.exists():
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                for ext_id, ratings_data in data.get("ratings", {}).items():
                    self._ratings[ext_id] = [Rating(**r) for r in ratings_data]
                for ext_id, reviews_data in data.get("reviews", {}).items():
                    self._reviews[ext_id] = [Review(**r) for r in reviews_data]
        except Exception as exc:
            logger.debug("Failed to load reviews: %s", exc)

    def _save(self) -> None:
        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "ratings": {
                    ext_id: [{"extension_id": r.extension_id, "score": r.score,
                               "user": r.user, "timestamp": r.timestamp}
                              for r in ratings]
                    for ext_id, ratings in self._ratings.items()
                },
                "reviews": {
                    ext_id: [{"extension_id": r.extension_id, "rating": r.rating,
                               "title": r.title, "body": r.body, "user": r.user,
                               "version": r.version, "timestamp": r.timestamp,
                               "verified_purchase": r.verified_purchase,
                               "helpful_count": r.helpful_count}
                              for r in reviews]
                    for ext_id, reviews in self._reviews.items()
                },
            }
            self._storage_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Failed to save reviews: %s", exc)
