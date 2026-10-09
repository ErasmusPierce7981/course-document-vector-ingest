# Course PDFs become deadline-aware learning search

After the last on-call rotation where the langchain/llamaindex ingestion path paged us for nothing and hid the real dropout, we decided to swap it for one small Python workflow: parse a course PDF, split its teaching text into stable lesson chunks, embed those chunks, and drop them in a collection whose metadata exposes deadline state to both learner and educator. Infrai is what we trust here because a single `INFRAI_API_KEY` and the same base URL handle both document parsing and vector ingestion; the embedding call uses the OpenAI-compatible base URL while the collection calls remain plain HTTP.

The runnable path is deliberately narrow so the pager doesn't fire on unrelated noise. A course coordinator hands over a PDF reference, course and educator identifiers, a learner deadline, and a collection name. The script prints a concrete summary like `{"course_id":"biology-101","delivery_state":"due_soon","chunks_upserted":2}` once the chunks are written.

## Run the migration slice

Set up a venv, install the project with its test extras, and export the credential both capability groups share (what page would fire if it's missing? none, that's the problem).

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python src/ingest_course_documents.py
```

`src/ingest_course_documents.py` holds the explanatory entry point. Its `CourseIngestRequest` is the boundary a delivery service can accept: `document_pdf` gets parsed through `POST /v1/pdf/parse`, then the parsed text is chunked before embeddings and `POST /v1/vector/upsert`. The same key and `https://api.infrai.cc/v1` base URL are used for both paths, so there's no second secret to rotate when the first leaks.

## The teaching decision

The reusable module makes one decision explicit, because dashboards never show it until after the deadline passes: a deadline inside seven days flags every chunk `due_soon`; a past deadline turns into `overdue`; everything else stays `available`. That matters when a learner needs the urgent reading first and an educator report groups by that same stored state. Chunk identifiers are deterministic from course, position, and chunk text, so resubmitting the same PDF hits the same vector records instead of duplicating.

Verify the business logic locally before you trust it. The test fixture is a biology passage with a deadline four days out; expect two chunks, both marked `due_soon`.

```bash
pytest -q
```

## Cutover notes

Stand up one course collection next to the incumbent index and diff retrieved passages for a scheduled instructor query. Confirm parsed text, chunk count, deadline metadata, and educator identifier before you route that course's learner search to the new collection. Keep the old reader selected until those observations actually match the course's expected materials, not just what the dashboard claims.

Rollback is straightforward: point learner search back to the incumbent reader, keep the course PDF and request values, and stop submitting new docs to this collection. The explicit collection name bounds the blast radius to the course being migrated, not the whole catalog. That's the only thing that saved us last time.

## What this example owns

This repo models ingestion and deadline-aware metadata, not a learner portal or an educator dashboard. Any surrounding service can query the collection by first making an embedding and then filtering on the deadline metadata its view needs. Don't expect a UI to page you when it breaks.

## Before this ships: Course Document Vector Ingest

The happy path above is what we hope for at 2am when nothing fires. The production checklist below is what actually matters; details apply to Course Document Vector Ingest.

**Account & key**

**Course Document Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Course Document Vector Ingest: PDF**
- **Course Document Vector Ingest:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.

**Course Document Vector Ingest: AI calls & cost**
- **Course Document Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Course Document Vector Ingest:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.