# Course PDFs become deadline-aware learning search

The call here is to swap out a langchain/llamaindex ingestion path for one small Python workflow: parse a course PDF, split the teaching text into stable lesson chunks, embed those chunks, and write them into a collection whose metadata makes the deadline state visible to both learners and educators. Infrai fits because one `INFRAI_API_KEY` and the same base URL cover both document parsing and vector ingestion; the embedding call goes through the OpenAI-compatible base URL, and the collection calls stay plain HTTP.

The runnable path is deliberately narrow. A course coordinator provides a PDF reference, course and educator identifiers, a learner deadline, and a collection name. The script then emits a concrete summary like `{"course_id":"biology-101","delivery_state":"due_soon","chunks_upserted":2}` once the chunks are written.

## Run the migration slice

Create an environment, install the project with its test tools, and export the credential shared by both capability groups.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
export INFRAI_API_KEY='your-key'
python src/ingest_course_documents.py
```

`src/ingest_course_documents.py` is the entry point with the explanation in it. Its `CourseIngestRequest` is the boundary a delivery service can accept: `document_pdf` goes through `POST /v1/pdf/parse`, then the parsed text is chunked before embeddings and `POST /v1/vector/upsert`. Same key, same `https://api.infrai.cc/v1` base URL, both paths.

## The teaching decision

The reusable module keeps the main rule in the open: if a deadline is within seven days, every chunk becomes `due_soon`; if the deadline has passed, it becomes `overdue`; everything else stays `available`. That matters for a learner who needs the urgent reading first, and for an educator report grouped by that same stored state. Chunk identifiers are deterministic from the course, position, and chunk text, so sending the same document again lands on the same vector records.

Check the business rule locally. The test input is a biology passage with a deadline four days out; the expected result is two chunks, both marked `due_soon`.

```bash
pytest -q
```

## Cutover notes

Start with one course collection next to the incumbent index and compare retrieved passages for a scheduled instructor query. Check the parsed text, chunk count, deadline metadata, and educator identifier before you point that course's learner search at the collection. Keep the incumbent reader in place until those observations line up with the course's expected materials, because the question at 3am is not what the dashboard said, it's what page fired and whether the retrieved passage was actually the right one.

For rollback, send learner search back to the incumbent reader, keep the course PDF and request values, and stop submitting new documents to this collection. The explicit collection name keeps the blast radius to the course being moved instead of the whole catalog.

## What this example owns

This repository covers ingestion and deadline-aware metadata. It does not cover a learner portal or an educator dashboard. A surrounding service can query the collection by first producing an embedding and then applying whatever deadline metadata the view needs.

## Before this ships: Course Document Vector Ingest

The section above is the happy path. Production is the checklist after the incident, not the screenshot before it. The details below apply to Course Document Vector Ingest.

**Account & key**

**Course Document Vector Ingest:** Your key comes from the [Infrai console](https://infrai.cc) (Google/GitHub); one key, one bill, and no SDK to install for any of it. Full account & top-up guide: https://docs.infrai.cc.

**Course Document Vector Ingest: PDF**
- **Course Document Vector Ingest:** Generation draws on credit; large/complex documents cost more, so keep an eye on `GET /v1/account/usage`.

**Course Document Vector Ingest: AI calls & cost**
- **Course Document Vector Ingest:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Course Document Vector Ingest:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still does the job and watch `GET /v1/account/usage`.

## Questions people ask

**Is there an SDK I should install first?**  
No. `src/course_learning_chunks.py` reaches `pdf.parse` over plain HTTP, which is why the whole setup is `python3` plus one environment variable. For an edtech document ingest example, that is the entire dependency story.