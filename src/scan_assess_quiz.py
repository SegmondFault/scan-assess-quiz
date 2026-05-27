from datetime import UTC, datetime
from pathlib import Path
import argparse
import json
from nicegui import ui

from src.quiz_engine import QuizSession
from src.runners.run_modules import run_modules

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULES_ROOT = PROJECT_ROOT / "modules"
OUTPUTS_ROOT = PROJECT_ROOT / "outputs"
REPORTS_ROOT = PROJECT_ROOT / "reports"

COLOR_ICON_MAP = {
    "employee_management": ("person", "#3b82f6"),
    "logical_access": ("settings", "#10b981"),
    "awareness_and_compliance": ("notifications", "#f59e0b"),
    "information_system": ("phone_android", "#8b5cf6"),
    "local_area_network": ("router", "#06b6d4"),
    "third_party_management": ("search", "#ec4899"),
}


def create_run_dirs(ts: datetime) -> tuple[Path, Path]:
    """Create output and report directories for the current run based on the timestamp."""
    date_path = Path(ts.strftime("%Y-%m-%dT%H:%M:%SZ").replace(":", "-"))

    output_dir = OUTPUTS_ROOT / date_path
    report_dir = REPORTS_ROOT

    output_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    return output_dir, report_dir


def build_app(max_questions: int) -> None:
    ts = datetime.now(UTC)
    output_dir, report_dir = create_run_dirs(ts)  # Create output and report directories

    # Generate questions by running modules
    generated_json_files, runner_info, runner_errors = run_modules(MODULES_ROOT, output_dir)
    if runner_errors:
        print("\nModule Runner Errors:")
        for error in runner_errors:
            print(f"- {error}")
        print("Stopping execution due to module runner errors.")
        return

    # Load questions from generated JSON files
    questions = []
    for f in sorted(generated_json_files):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                item.setdefault("source_file", f.name)
                questions.append(item)
    if not questions:
        ui.label("No questions found in generated module outputs.")
        return

    @ui.page("/")
    def index():
        session = QuizSession(questions, max_questions=max_questions)

        with ui.column().classes("items-center w-full"):
            ui.label("Scan Assess Quiz").classes("text-h4")

            score_bars = {}
            with ui.column().classes("items-center w-full").style("max-width: 720px;"):
                for cat in session.categories:
                    icon_name, color = COLOR_ICON_MAP.get(cat, (cat, "#64748b"))
                    with ui.row().classes("items-center w-full"):
                        ui.label(cat.replace("_", " ").title()).style(
                            "width: 240px; text-align: right;"
                        )
                        ui.icon(icon_name).style(f"color: {color};")
                        bar = ui.linear_progress(session.scores[cat] / 100.0)
                        bar.style("width: 250px; height: 12px;")
                        bar.classes("rounded")
                        bar.props(f"color={color}")
                        score_bars[cat] = bar

            question_section = ui.column().classes("items-center w-full")
            report_section = ui.column().classes("items-center w-full")
            report_section.set_visibility(False)

            with question_section:
                count_label = ui.label("").classes("text-subtitle2")
                question_label = ui.label("").classes("text-h6")
                answers_container = ui.row().classes("justify-center gap-4 w-full")

            with report_section:
                ui.label("Quiz report").classes("text-h5")
                scores_table = (
                    ui.table(
                        columns=[
                            {
                                "name": "category",
                                "label": "Category",
                                "field": "category",
                            },
                            {"name": "score", "label": "Score", "field": "score"},
                        ],
                        rows=[],
                        row_key="category",
                    )
                    .classes("w-full")
                    .style("max-width: 520px;")
                )
                report_path_label = ui.label("")
                recommendations_label = ui.markdown("")

            game_over_dialog = ui.dialog()
            with game_over_dialog:
                ui.label("Game over!").classes("text-h6")

            def refresh_scores() -> None:
                for cat, bar in score_bars.items():
                    bar.value = session.scores[cat] / 100.0

            def show_report() -> None:
                report_path = session.generate_report(report_dir)
                scores_table.rows = [
                    {"category": k, "score": v}
                    for k, v in session.scores.items()
                ]
                if session.recommendations:
                    rec_lines = "\n".join(f"- {r}" for r in session.recommendations)
                    recommendations_label.content = f"## Recommendations\n{rec_lines}"
                else:
                    recommendations_label.content = ""
                report_path_label.text = f"Report saved to: {report_path}"
                question_section.set_visibility(False)
                report_section.set_visibility(True)

            def on_answer(answer: dict) -> None:
                session.apply_answer(answer)
                refresh_scores()
                if session.category_game_over:
                    game_over_dialog.open()
                show_question()

            def show_question() -> None:
                if session.is_finished():
                    show_report()
                    return
                q = session.current_question
                if q is None:
                    show_report()
                    return
                count_label.text = (
                    f"Question {session.asked_count + 1} / {session.max_questions}"
                )
                question_label.text = q.get("label", "")
                answers_container.clear()
                for answer in q.get("answers", []):
                    with answers_container:
                        with ui.card().classes(
                            "w-64 h-40 items-center justify-between"
                        ):
                            ui.label(answer.get("label", "")).classes("text-center")
                            ui.button(
                                "Select",
                                on_click=lambda _event, a=answer: on_answer(a),
                            ).props("color=primary")

            show_question()


def main():
    parser = argparse.ArgumentParser(description="Run the scan-assess quiz")
    parser.add_argument(
        "--max-questions",
        type=int,
        default=20,
        help="Maximum number of questions to ask (default: 20)",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()

    build_app(max_questions=args.max_questions)
    ui.run(host=args.host, port=args.port, reload=False)
