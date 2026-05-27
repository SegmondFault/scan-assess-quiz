"""Example runner implementation showing how to implement a BaseRunner."""

import json
from pathlib import Path

from src.runners.base_runner import BaseRunner


class Runner(BaseRunner):
    """Example runner that demonstrates the BaseRunner interface."""

    def run(self, output_dir: Path, module_dir: Path) -> tuple[bool, list[Path]]:
        """Example implementation: generate a simple status JSON file."""

        # Generate example data
        example_data = json.load((module_dir / "example_questions.json").open(encoding="utf-8"))

        # Write to output file
        output_path = output_dir / "example_questions.json"
        output_path.write_text(json.dumps(example_data, indent=2), encoding="utf-8")

        # Generate example data 2
        example_data_2 = json.load((module_dir / "example_questions_2.json").open(encoding="utf-8"))

        # Write to output file
        output_path_2 = output_dir / "example_questions_2.json"
        output_path_2.write_text(json.dumps(example_data_2, indent=2), encoding="utf-8")

        return True, [output_path, output_path_2]
