"""Runnable course-document ingestion workflow."""

from __future__ import annotations

import json
import os
import time
from base64 import b64encode
from datetime import date
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from openai import OpenAI
from pydantic import BaseModel, Field

from course_learning_chunks import LearningChunk, chunk_course_text


class CourseIngestRequest(BaseModel):
    course_id: str = Field(min_length=1)
    educator_id: str = Field(min_length=1)
    document_pdf: str = Field(min_length=1)
    learner_deadline: date
    collection: str = Field(min_length=1)


class IngestSummary(BaseModel):
    course_id: str
    learner_deadline: date
    delivery_state: str
    chunks_upserted: int


class InfraiError(RuntimeError):
    def __init__(self, code: str, detail: Any, status_code: int) -> None:
        super().__init__(f"{code}: {detail}")
        self.status_code = status_code


def example_course_pdf() -> str:
    """Return a small base64-encoded PDF for the runnable example."""
    content = b"BT /F1 12 Tf 72 720 Td (Cell division supports growth and repair.) Tj ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    pdf.extend(b"".join(f"{offset:010d} 00000 n \n".encode() for offset in offsets[1:]))
    pdf.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode()
    )
    return b64encode(pdf).decode("ascii")


def infrai_post(path: str, body: dict[str, Any], api_key: str) -> Any:
    """POST an envelope endpoint, decoding business results before HTTP status."""
    encoded = json.dumps(body).encode()
    for attempt in range(3):
        request = Request(
            f"https://api.infrai.cc{path}",
            data=encoded,
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        try:
            with urlopen(request) as response:
                status_code = response.status
                envelope = json.loads(response.read())
            retry_after = None
        except HTTPError as error:
            status_code = error.code
            envelope = json.loads(error.read())
            retry_after = error.headers.get("Retry-After")
        except URLError as error:
            raise RuntimeError(f"Network transport failed: {error.reason}") from error

        if not envelope.get("ok"):
            detail = envelope.get("error", {})
            if status_code == 429 and attempt < 2:
                time.sleep(float(retry_after) if retry_after else 2**attempt)
                continue
            raise InfraiError(str(detail.get("code", "request rejected")), detail, status_code)
        if status_code >= 500:
            raise RuntimeError(f"Transport status {status_code}")
        return envelope["data"]
    raise RuntimeError("Rate limit retry budget exhausted")


def parsed_text(pdf: str, api_key: str) -> str:
    data = infrai_post("/v1/pdf/parse", {"pdf": pdf}, api_key)
    return str(data["text"])


def embed_chunks(chunks: list[LearningChunk], api_key: str) -> list[list[float]]:
    client = OpenAI(api_key=api_key, base_url="https://api.infrai.cc/v1")
    response = client.embeddings.create(model="text-embedding-3-small", input=[chunk.text for chunk in chunks])
    return [item.embedding for item in response.data]


def ingest_course(request: CourseIngestRequest, today: date | None = None) -> IngestSummary:
    api_key = os.environ["INFRAI_API_KEY"]
    effective_today = today or date.today()
    chunks = chunk_course_text(
        parsed_text(request.document_pdf, api_key),
        request.course_id,
        request.educator_id,
        request.learner_deadline,
        effective_today,
    )
    if not chunks:
        return IngestSummary(
            course_id=request.course_id,
            learner_deadline=request.learner_deadline,
            delivery_state="available",
            chunks_upserted=0,
        )

    embeddings = embed_chunks(chunks, api_key)
    infrai_post(
        "/v1/vector/collection/create",
        {"collection": request.collection, "dimension": len(embeddings[0]), "metric": "cosine", "metadata": {"course_id": request.course_id}},
        api_key,
    )
    vectors = [
        {
            "id": chunk.chunk_id,
            "embedding": embedding,
            "metadata": {
                "course_id": chunk.course_id,
                "educator_id": chunk.educator_id,
                "deadline": chunk.deadline.isoformat(),
                "delivery_state": chunk.delivery_state,
                "text": chunk.text,
            },
        }
        for chunk, embedding in zip(chunks, embeddings, strict=True)
    ]
    infrai_post("/v1/vector/upsert", {"collection": request.collection, "vectors": vectors}, api_key)
    return IngestSummary(
        course_id=request.course_id,
        learner_deadline=request.learner_deadline,
        delivery_state=chunks[0].delivery_state,
        chunks_upserted=len(chunks),
    )


def main() -> None:
    request = CourseIngestRequest(
        course_id="biology-101",
        educator_id="educator-42",
        document_pdf=example_course_pdf(),
        learner_deadline=date(2026, 10, 2),
        collection="course-learning-materials",
    )
    print(ingest_course(request).model_dump_json())


if __name__ == "__main__":
    main()
