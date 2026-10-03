from datetime import date

from course_learning_chunks import chunk_course_text


def test_a_near_deadline_marks_every_lesson_chunk_for_attention() -> None:
    chunks = chunk_course_text(
        text="cell division prepares organisms for growth and repair",
        course_id="biology-101",
        educator_id="educator-42",
        deadline=date(2026, 10, 2),
        today=date(2026, 9, 28),
        words_per_chunk=4,
    )

    assert len(chunks) == 2
    assert {chunk.delivery_state for chunk in chunks} == {"due_soon"}
    assert all(chunk.chunk_id.startswith("biology-101-lesson-") for chunk in chunks)
