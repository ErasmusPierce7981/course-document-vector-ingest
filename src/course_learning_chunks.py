"""Domain decisions for turning course material into learner-facing chunks."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date
from typing import Literal


DeliveryState = Literal["available", "due_soon", "overdue"]


@dataclass(frozen=True)
class LearningChunk:
    chunk_id: str
    text: str
    course_id: str
    educator_id: str
    deadline: date
    delivery_state: DeliveryState


def delivery_state(deadline: date, today: date) -> DeliveryState:
    """Make deadline visibility explicit for learners and educator reporting."""
    days_remaining = (deadline - today).days
    if days_remaining < 0:
        return "overdue"
    if days_remaining <= 7:
        return "due_soon"
    return "available"


def chunk_course_text(
    text: str,
    course_id: str,
    educator_id: str,
    deadline: date,
    today: date,
    words_per_chunk: int = 120,
) -> list[LearningChunk]:
    """Split parsed course text into stable, reportable retrieval units."""
    words = text.split()
    if not words:
        return []

    state = delivery_state(deadline, today)
    chunks: list[LearningChunk] = []
    for index, start in enumerate(range(0, len(words), words_per_chunk)):
        chunk_text = " ".join(words[start : start + words_per_chunk])
        digest = hashlib.sha256(f"{course_id}:{index}:{chunk_text}".encode()).hexdigest()[:16]
        chunks.append(
            LearningChunk(
                chunk_id=f"{course_id}-lesson-{index}-{digest}",
                text=chunk_text,
                course_id=course_id,
                educator_id=educator_id,
                deadline=deadline,
                delivery_state=state,
            )
        )
    return chunks
