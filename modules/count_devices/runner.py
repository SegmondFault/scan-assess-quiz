"""Runner for the count_devices module that scans for devices and generates questions."""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from pathlib import Path

from src.runners.base_runner import BaseRunner


class Device:
    ip: str
    name: str | None

    def __init__(self, ip: str, name: str | None = None) -> None:
        self.ip = ip
        self.name = name


class Runner(BaseRunner):
    """Scan for devices and generate quiz questions about device count."""

    DEFAULT_TARGET = "192.168.1.0/24"
    TREE_ID = 3

    def run(self, output_dir: Path, module_dir: Path) -> tuple[bool, list[Path]]:
        """
        Run network scan and generate device count questions.

        Args:
            output_dir: Directory where output files should be written
            module_dir: Directory containing the module (unused for this module)

        Returns:
            Tuple of (success, list of generated JSON files)
        """
        try:
            # Get the target network to scan
            target = self._get_target_network()

            # Run the nmap scan
            output = self._run_nmap_ping_scan(target)
            devices = self._parse_devices_from_grepable_output(output)

            # Generate questions based on scan results
            questions = self._generate_questions(devices)

            # Write to output file
            output_path = output_dir / "count_devices_questions.json"
            output_path.write_text(json.dumps(questions, indent=2), encoding="utf-8")

            return True, [output_path]

        except Exception as error:
            print(f"count_devices module error: {error}", file=sys.stderr)
            return False, []

    def _get_local_ipv4(self) -> str | None:
        """Attempts to determine the local IPv4 address."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.connect(("8.8.8.8", 80))
                candidate = sock.getsockname()[0]
                if candidate and candidate.count(".") == 3 and not candidate.startswith("127."):
                    return candidate
        except OSError:
            pass

        try:
            candidate = socket.gethostbyname(socket.gethostname())
            if candidate and candidate.count(".") == 3 and not candidate.startswith("127."):
                return candidate
        except OSError:
            pass

        return None

    def _get_target_network(self) -> str:
        """Determine the target network for scanning."""
        local_ip = self._get_local_ipv4()
        if not local_ip:
            return self.DEFAULT_TARGET

        # Assume a /24 subnet and replace the last octet with 0/24
        octets = local_ip.split(".")
        if len(octets) != 4:
            return self.DEFAULT_TARGET
        return f"{octets[0]}.{octets[1]}.{octets[2]}.0/24"

    def _run_nmap_ping_scan(self, target: str) -> str:
        """Runs an nmap ping scan and returns the grepable output."""
        command = ["nmap", "-sn", "-oG", "-", target]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "nmap is not installed or not on PATH. Please install nmap first."
            ) from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "No stderr output."
            raise RuntimeError(f"nmap scan failed: {stderr}") from exc

        return result.stdout

    def _parse_devices_from_grepable_output(self, output: str) -> list[Device]:
        """Parses nmap grepable output to extract discovered devices."""
        devices: dict[str, Device] = {}
        # Extract address and hostname for only Status: Up
        line_pattern = re.compile(r"^Host:\s+(\d+\.\d+\.\d+\.\d+)\s+\((.*?)\)\s+Status:\s+Up")

        for line in output.splitlines():
            line = line.strip()
            match = line_pattern.match(line)
            if not match:
                continue

            ip = match.group(1).strip()
            raw_name = match.group(2).strip()
            name = raw_name if raw_name else None
            devices[ip] = Device(ip=ip, name=name)

        return sorted(
            devices.values(),
            key=lambda device: tuple(int(part) for part in device.ip.split(".")),
        )

    def _generate_questions(self, devices: list[Device]) -> list[dict]:
        """Generate quiz questions based on discovered devices."""
        device_count = len(devices)

        # Create multiple choice options around the actual count
        options: list[int] = []
        if device_count > 1:
            options.append(max(1, device_count - 1))
        options.append(device_count)
        options.append(device_count + 1)
        options.append(device_count + 3)

        questions = [
            {
                "q_id": 1,
                "tree_id": self.TREE_ID,
                "label": "How many devices do you think are on the network?",
                "answers": [
                    {
                        "a_id": i + 1,
                        "label": f"{option} devices",
                        "score": self._calculate_score(option, device_count),
                        "recommendations": f"You guessed there are {option} devices on the network. There are {device_count} devices.\n"
                            + self._get_recommendations(
                            option, device_count
                        ),
                        "follow_up_question_id": 2,
                    }
                    for i, option in enumerate(options)
                ],
            },
            {
                "q_id": 2,
                "tree_id": self.TREE_ID,
                "label": "Device discovery is important for security awareness. Do you monitor your network regularly?",
                "answers": [
                    {
                        "a_id": 1,
                        "label": "Yes, regularly",
                        "score": {
                            "local_area_network": "+5",
                            "awareness_and_compliance": "+5",
                        },
                    },
                    {
                        "a_id": 2,
                        "label": "Occasionally",
                        "score": {
                            "local_area_network": "+5",
                            "awareness_and_compliance": "+3",
                        },
                    },
                    {
                        "a_id": 3,
                        "label": "Never",
                        "score": {
                            "local_area_network": "-10",
                            "awareness_and_compliance": "-5",
                        },
                        "recommendations": "You should implement regular network monitoring to detect unauthorized devices.",
                    },
                ],
            },
        ]

        return questions

    def _calculate_score(self, guess: int, actual: int) -> dict[str, str]:
        """Calculate score adjustment based on guess accuracy."""
        if guess == actual:
            return {
                "local_area_network": "+10",
                "awareness_and_compliance": "+10",
            }
        elif abs(guess - actual) <= 1:
            return {
                "local_area_network": "+10",
                "awareness_and_compliance": "+5",
            }
        else:
            return {
                "local_area_network": "-5",
                "awareness_and_compliance": "-2",
            }

    def _get_recommendations(self, guess: int, actual: int) -> str:
        """Get recommendations based on answer accuracy."""
        if guess == actual:
            return "Excellent awareness of your network devices!"
        elif abs(guess - actual) == 1:
            return "Good estimate. Keep monitoring your network for better accuracy."
        else:
            return "Consider implementing network monitoring tools to track your devices accurately."
