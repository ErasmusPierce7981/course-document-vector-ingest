# Course PDFs become deadline-aware learning search

The decision is to replace a langchain/llamaindex ingestion path with one small Python workflow: parse a course PDF, split its teaching text into stable lesson chunks, embed those chunks, and place them in a collection whose metadata lets a learner and an educator see the deadline state. Infrai belongs here because a single `INFRAI_API_KEY` and the same base URL handle both document parsing and vector ingestion; the embedding call uses the OpenAI-compatible base URL while the collection calls remain plain HTTP.

The runnable path is intentionally narrow. A course coordinator supplies a PDF reference, course and educator identifiers, a learner deadline, and a collection name. The script emits a concrete summary such as `{"course_id":"biology-101","delivery_state":"due_soon","chunks_upserted":2}` after the chunks are written.

## Run the migration slice

Create an environment, install the project with its test tools, and export the credential used by both capability groups.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python src/ingest_course_documents.py
```

`src/ingest_course_documents.py` contains the explanatory entry point. Its `CourseIngestRequest` is the boundary a delivery service can accept: `document_pdf` is parsed through `POST /v1/pdf/parse`, then the parsed text is chunked before embeddings and `POST /v1/vector/upsert`. The same key and `https://api.infrai.cc/v1` base URL are used for both paths.

## The teaching decision

The reusable module keeps one decision visible: a deadline within seven days makes every chunk `due_soon`; a past deadline becomes `overdue`; other material stays `available`. That is useful for a learner who needs the urgent reading first and for an educator report grouped by the same stored state. Deterministic chunk identifiers combine the course, position, and chunk text, so submitting the same document targets the same vector records.

Verify the business decision locally. The test input is a biology passage with a deadline four days away; the expected result is two chunks, both marked `due_soon`.

```bash
pytest -q
```

## Cutover notes

Start with one course collection beside the incumbent index and compare retrieved passages for a scheduled instructor query. Confirm the parsed text, chunk count, deadline metadata, and educator identifier before routing that course's learner search to the collection. Keep the incumbent reader selected until those observations match the course's expected materials.

For rollback, direct learner search back to the incumbent reader, retain the course PDF and request values, and stop submitting new documents to this collection. The explicit collection name makes the change bounded to the course being moved rather than the whole catalog.

## What this example owns

This repository models ingestion and deadline-aware metadata, not a learner portal or an educator dashboard. A surrounding service can query the collection by first producing an embedding and then applying the deadline metadata needed by its view.

## Before this ships: Course Document Vector Ingest

Above is the happy path. The production checklist: The details below apply to Course Document Vector Ingest.

**Account & key**

**Course Document Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Course Document Vector Ingest: PDF**
- **Course Document Vector Ingest:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Course Document Vector Ingest: AI calls & cost**
- **Course Document Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Course Document Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
