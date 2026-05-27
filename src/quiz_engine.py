from datetime import datetime
from pathlib import Path


class QuizSession:
    def __init__(self, questions: list[dict], max_questions: int = 20):
        self.max_questions = max_questions
        self.questions = sorted(
            questions, key=lambda q: (q.get("tree_id", 0), q.get("q_id", 0))
        )
        self.question_by_id = {
            f"{q.get("tree_id")}_{q.get("q_id")}": q
            for q in self.questions
            if q.get("q_id") is not None and q.get("tree_id") is not None
        }
        self.categories = self._discover_categories()
        self.scores = {c: 50 for c in self.categories}
        self.recommendations: list[str] = []
        self.asked_count = 0
        self.current_index = 0
        self.current_question = self.questions[0] if self.questions else None
        self.category_game_over = False

    def _discover_categories(self) -> list[str]:
        cats = set()
        for q in self.questions:
            for a in q.get("answers", []):
                for k in a.get("score", {}).keys():
                    cats.add(k)
        return sorted(cats)

    def _apply_score_delta(self, answer: dict) -> None:
        for cat, val in answer.get("score", {}).items():
            score_value: int = 0
            try:
                score_value = int(str(val).replace("+", ""))
            except Exception:
                pass
            new_val = self.scores.get(cat, 50) + score_value
            new_val = max(0, min(100, new_val))
            self.scores[cat] = new_val
        for cat_val in self.scores.values():
            if cat_val <= 0:
                self.category_game_over = True

    def _advance_to_next_unasked(self, current_tree_id: int | None) -> None:
        # Advance to the next question tree
        for i in range(self.current_index + 1, len(self.questions)):
            q = self.questions[i]
            # Find the next question tree
            tree_id = q.get("tree_id")
            if tree_id != current_tree_id:
                self.current_index = i
                self.current_question = q
                return
        self.current_question = None

    def _set_current_by_id(self, current_tree_id: int | None, q_id: int | None) -> bool:
        if q_id is None or current_tree_id is None:
            return False
        q = self.question_by_id.get(f"{current_tree_id}_{q_id}")
        if not q:
            return False
        self.current_question = q
        try:
            self.current_index = self.questions.index(q)
        except ValueError:
            pass
        return True

    def apply_answer(self, answer: dict) -> None:
        if not self.current_question:
            return
        self.asked_count += 1

        # Apply score change and recommendations
        self._apply_score_delta(answer)
        rec = answer.get("recommendations")
        if rec:
            self.recommendations.append(rec)

        # Check if max questions reached
        if self.asked_count >= self.max_questions:
            self.current_question = None
            return

        # Determine next question
        current_tree_id = self.current_question.get("tree_id")
        follow_up_id = answer.get("follow_up_question_id", None)
        if not self._set_current_by_id(current_tree_id, follow_up_id):
            self._advance_to_next_unasked(current_tree_id)

    def is_finished(self) -> bool:
        return (
            self.current_question is None
            or self.asked_count >= self.max_questions
            or self.category_game_over
        )

    def generate_report(self, report_dir: Path) -> Path:
        report_file = (
            report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        )
        with report_file.open("w", encoding="utf-8") as f:
            f.write(
                f"# Quiz report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            )
            f.write("## Scores\n\n")
            for k, v in sorted(self.scores.items(), key=lambda x: -x[1]):
                f.write(f"- **{k}**: {v}\n")
            if self.recommendations:
                f.write("\n## Recommendations\n\n")
                for r in self.recommendations:
                    f.write(f"- {r}\n")
        return report_file
