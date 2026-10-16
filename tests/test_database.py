"""Tests for persistence, against an in-memory SQLite database."""

import pytest


QUESTIONS = [
    {"question": "What is the GIL?", "category": "programming",
     "difficulty": "advanced", "source": "llm"},
    {"question": "Design a rate limiter.", "category": "system_design",
     "difficulty": "intermediate", "source": "llm"},
    {"question": "How do you debug a leak?", "category": "problem_solving",
     "difficulty": "intermediate", "source": "llm"},
]

GOOD_EVALUATION = {"score": 8, "feedback": "Clear and correct.", "degraded": False}


@pytest.fixture
def assessment_id(memory_db, candidate):
    return memory_db.create_assessment(candidate, QUESTIONS)


class TestCreateAssessment:
    def test_stores_the_candidate_and_the_questions(self, memory_db, candidate, assessment_id):
        detail = memory_db.get_assessment(assessment_id)

        assert detail["candidate_data"]["email"] == candidate["email"]
        assert detail["candidate_data"]["tech_stack"] == candidate["tech_stack"]
        assert detail["questions_total"] == len(QUESTIONS)
        assert detail["final_report"] is None

    def test_a_repeat_candidate_is_not_duplicated(self, memory_db, candidate, assessment_id):
        """Candidates are keyed on email, so a second sitting reuses the row."""
        second = memory_db.create_assessment(candidate, QUESTIONS)

        assert second != assessment_id
        with memory_db.session_scope() as session:
            assert session.query(memory_db.Candidate).count() == 1
            assert session.query(memory_db.Assessment).count() == 2

    def test_updated_details_overwrite_the_stored_ones(self, memory_db, candidate, assessment_id):
        candidate["location"] = "Berlin, Germany"
        second = memory_db.create_assessment(candidate, QUESTIONS)

        assert memory_db.get_assessment(second)["candidate_data"]["location"] == "Berlin, Germany"

    def test_fallback_questions_mark_the_assessment_degraded(self, memory_db, candidate):
        degraded_questions = [dict(q, source="fallback", degraded=True) for q in QUESTIONS]
        memory_db.create_assessment(candidate, degraded_questions)

        assert memory_db.list_assessments()[0]["degraded"] is True


class TestRecordAnswer:
    def test_stores_an_answer_with_its_evaluation(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 0, "The GIL is a mutex.", GOOD_EVALUATION)

        detail = memory_db.get_assessment(assessment_id)
        assert detail["answers"][0]["answer"] == "The GIL is a mutex."
        assert detail["evaluations"][0]["score"] == 8
        assert detail["evaluations"][0]["degraded"] is False

    def test_unanswered_questions_are_reported_as_skipped(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 1, "Token bucket.", GOOD_EVALUATION)

        detail = memory_db.get_assessment(assessment_id)
        assert len(detail["answers"]) == 1
        assert len(detail["skipped_questions"]) == 2

    def test_reanswering_replaces_rather_than_duplicates(self, memory_db, assessment_id):
        """The candidate can navigate back; a duplicate row would be double-counted."""
        memory_db.record_answer(assessment_id, 0, "First attempt.", {"score": 4, "feedback": "thin"})
        memory_db.record_answer(assessment_id, 0, "Second attempt.", {"score": 9, "feedback": "much better"})

        detail = memory_db.get_assessment(assessment_id)
        assert len(detail["answers"]) == 1
        assert detail["answers"][0]["answer"] == "Second attempt."
        assert detail["evaluations"][0]["score"] == 9

    def test_keeps_the_degraded_flag_and_reason(self, memory_db, assessment_id):
        memory_db.record_answer(
            assessment_id, 0, "an answer",
            {"score": 5, "feedback": "placeholder", "degraded": True,
             "degraded_reason": "timed out"},
        )

        evaluation = memory_db.get_assessment(assessment_id)["evaluations"][0]
        assert evaluation["degraded"] is True
        assert evaluation["degraded_reason"] == "timed out"

    def test_an_unknown_position_is_ignored_not_fatal(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 99, "nowhere", GOOD_EVALUATION)

        assert memory_db.get_assessment(assessment_id)["answers"] == []


class TestFinalReport:
    REPORT = {
        "overall_score": 6.4,
        "performance_score": 8.0,
        "completion_penalty_factor": 0.8,
        "questions_answered": 1,
        "completion_status": "Partial Assessment (1/5 questions)",
        "recommendation": "Maybe",
        "detailed_feedback": "Promising but thin evidence.",
        "degraded": False,
    }

    def test_round_trips_the_whole_report(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 0, "an answer", GOOD_EVALUATION)
        memory_db.save_final_report(assessment_id, self.REPORT, ended_early=True)

        detail = memory_db.get_assessment(assessment_id)
        assert detail["final_report"]["overall_score"] == 6.4
        assert detail["final_report"]["performance_score"] == 8.0
        assert detail["final_report"]["completion_penalty_factor"] == 0.8
        assert detail["final_report"]["recommendation"] == "Maybe"
        assert detail["ended_early"] is True
        assert detail["completed_at"] is not None

    def test_regenerating_replaces_the_previous_report(self, memory_db, assessment_id):
        memory_db.save_final_report(assessment_id, self.REPORT)
        memory_db.save_final_report(assessment_id, dict(self.REPORT, overall_score=9.1))

        assert memory_db.get_assessment(assessment_id)["final_report"]["overall_score"] == 9.1
        with memory_db.session_scope() as session:
            assert session.query(memory_db.Report).count() == 1

    def test_a_missing_assessment_is_ignored_not_fatal(self, memory_db):
        memory_db.save_final_report(999, self.REPORT)  # must not raise

    def test_report_defaults_fill_in_missing_keys(self, memory_db, assessment_id):
        memory_db.save_final_report(assessment_id, {"overall_score": 7.0})

        report = memory_db.get_assessment(assessment_id)["final_report"]
        assert report["performance_score"] == 7.0
        assert report["completion_penalty_factor"] == 1.0
        assert report["recommendation"] == "Maybe"


class TestListAssessments:
    def test_summarises_each_assessment(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 0, "an answer", GOOD_EVALUATION)
        memory_db.save_final_report(
            assessment_id, {"overall_score": 7.0, "recommendation": "Hire"}
        )

        row = memory_db.list_assessments()[0]
        assert row["assessment_id"] == assessment_id
        assert row["name"] == "Ada Lovelace"
        assert row["questions_answered"] == 1
        assert row["questions_total"] == len(QUESTIONS)
        assert row["overall_score"] == 7.0
        assert row["recommendation"] == "Hire"
        assert row["is_complete"] is True

    def test_an_unfinished_assessment_is_listed_as_incomplete(self, memory_db, assessment_id):
        row = memory_db.list_assessments()[0]
        assert row["is_complete"] is False
        assert row["overall_score"] is None

    def test_most_recent_first(self, memory_db, candidate):
        first = memory_db.create_assessment(candidate, QUESTIONS)
        second = memory_db.create_assessment(dict(candidate, email="b@example.org"), QUESTIONS)

        ids = [r["assessment_id"] for r in memory_db.list_assessments()]
        assert ids.index(second) < ids.index(first)

    def test_limit_is_respected(self, memory_db, candidate):
        for i in range(4):
            memory_db.create_assessment(dict(candidate, email=f"c{i}@example.org"), QUESTIONS)

        assert len(memory_db.list_assessments(limit=2)) == 2

    def test_empty_database_lists_nothing(self, memory_db):
        assert memory_db.list_assessments() == []


class TestDelete:
    def test_removes_the_assessment_and_its_children(self, memory_db, assessment_id):
        memory_db.record_answer(assessment_id, 0, "an answer", GOOD_EVALUATION)
        memory_db.save_final_report(assessment_id, {"overall_score": 7.0})

        assert memory_db.delete_assessment(assessment_id) is True
        assert memory_db.get_assessment(assessment_id) is None

        with memory_db.session_scope() as session:
            assert session.query(memory_db.Question).count() == 0
            assert session.query(memory_db.Answer).count() == 0
            assert session.query(memory_db.Evaluation).count() == 0
            assert session.query(memory_db.Report).count() == 0
            # The candidate outlives the assessment.
            assert session.query(memory_db.Candidate).count() == 1

    def test_deleting_an_unknown_assessment_reports_false(self, memory_db):
        assert memory_db.delete_assessment(999) is False


class TestGetAssessment:
    def test_unknown_id_returns_none(self, memory_db):
        assert memory_db.get_assessment(999) is None

    def test_answers_and_evaluations_stay_aligned(self, memory_db, assessment_id):
        """render_report zips these two lists, so their order has to match."""
        memory_db.record_answer(assessment_id, 2, "Third.", {"score": 3, "feedback": "c"})
        memory_db.record_answer(assessment_id, 0, "First.", {"score": 1, "feedback": "a"})

        detail = memory_db.get_assessment(assessment_id)
        assert [a["answer"] for a in detail["answers"]] == ["First.", "Third."]
        assert [e["score"] for e in detail["evaluations"]] == [1, 3]


class TestSessionScope:
    def test_rolls_back_on_error(self, memory_db, candidate):
        with pytest.raises(RuntimeError):
            with memory_db.session_scope() as session:
                memory_db.upsert_candidate(session, candidate)
                raise RuntimeError("boom")

        with memory_db.session_scope() as session:
            assert session.query(memory_db.Candidate).count() == 0
