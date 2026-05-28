from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SUSPICIOUS_DOMAIN_TOKENS = (
    "login",
    "verify",
    "secure",
    "password",
    "invoice",
    "payment",
    "paypal",
    "sharepoint",
    "micros0ft",
    "microsoft-",
    "office365",
)


class Runner:
    """Generate quiz questions from recent scan-assess module telemetry."""

    def run(self, output_dir: Path, module_dir: Path) -> tuple[bool, list[Path]]:
        output_dir.mkdir(parents=True, exist_ok=True)
        scan_root = self._find_scan_assess_root(module_dir)
        latest_run = self._latest_scan_run(scan_root)
        telemetry = self._load_latest_telemetry(latest_run) if latest_run else {}

        questions: list[dict[str, Any]] = []
        self._add_baseline_questions(questions)
        self._add_enumeros_questions(questions, telemetry.get("enumeros"))
        self._add_safesniff_questions(questions, telemetry.get("safesniff"))
        self._add_dnscap_questions(questions, telemetry.get("dnscap"))
        self._add_threatsucker_questions(questions, telemetry.get("threatsucker"))
        self._add_sitechecker_questions(questions, telemetry.get("sitechecker"))

        out_file = output_dir / "ngo_socio_tech_telemetry_questions.json"
        out_file.write_text(json.dumps(questions, indent=2, sort_keys=True), encoding="utf-8")
        return True, [out_file]

    def _find_scan_assess_root(self, module_dir: Path) -> Path:
        env_root = os.environ.get("SCAN_ASSESS_ROOT")
        if env_root:
            root = Path(env_root).expanduser().resolve()
            if root.exists():
                return root
        for parent in module_dir.resolve().parents:
            if (
                (parent / "outputs").exists()
                and (parent / "modules").exists()
                and (
                    (parent / "modules" / "enumeros").exists()
                    or (parent / "modules" / "safesniff").exists()
                    or (parent / "modules" / "dnscap").exists()
                )
            ):
                return parent
        return module_dir.resolve()

    def _latest_scan_run(self, scan_root: Path) -> Path | None:
        outputs_dir = scan_root / "outputs"
        if not outputs_dir.exists():
            return None
        module_files = (
            "enumeros/enumeros.json",
            "safesniff/safesniff.json",
            "dnscap/dnscap_summary.json",
            "threatsucker/threatsucker_correlation.json",
            "sitechecker/sitechecker.json",
        )
        for run_dir in sorted((p for p in outputs_dir.iterdir() if p.is_dir()), reverse=True):
            if any((run_dir / rel_path).exists() for rel_path in module_files):
                return run_dir
        return None

    def _load_latest_telemetry(self, latest_run: Path | None) -> dict[str, dict]:
        if latest_run is None:
            return {}
        targets = {
            "enumeros": latest_run / "enumeros" / "enumeros.json",
            "safesniff": latest_run / "safesniff" / "safesniff.json",
            "dnscap": latest_run / "dnscap" / "dnscap_summary.json",
            "threatsucker": latest_run / "threatsucker" / "threatsucker_correlation.json",
            "sitechecker": latest_run / "sitechecker" / "sitechecker.json",
        }
        return {name: self._read_json(path) for name, path in targets.items() if path.exists()}

    def _read_json(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _add_question(
        self,
        questions: list[dict[str, Any]],
        tree_id: int,
        label: str,
        answers: list[dict[str, Any]],
        *,
        source_module: str = "ngo_socio_tech_telemetry",
        source_file: str = "generated_context",
        observed_item: str = "general",
        context_kind: str = "work_context",
    ) -> None:
        questions.append(
            {
                "tree_id": tree_id,
                "q_id": len([q for q in questions if q.get("tree_id") == tree_id]) + 1,
                "label": label,
                "source_module": source_module,
                "source_file": source_file,
                "observed_item": observed_item,
                "context_kind": context_kind,
                "answers": answers,
            }
        )

    def _recognition_answers(self, item_type: str) -> list[dict[str, Any]]:
        return [
            {
                "a_id": 1,
                "label": f"Yes, I recognise this {item_type} and know who is responsible for it",
                "score": {"system_knowledge": "+8", "asset_ownership": "+8"},
            },
            {
                "a_id": 2,
                "label": f"I recognise this {item_type}, but I am not sure who maintains it",
                "score": {"system_knowledge": "+3", "asset_ownership": "-3"},
                "recommendations": f"Clarify ownership for this {item_type} so findings can be routed quickly.",
            },
            {
                "a_id": 3,
                "label": f"I do not recognise this {item_type}",
                "score": {"system_knowledge": "-8", "incident_routing": "+2"},
                "recommendations": f"Treat unfamiliar {item_type} evidence as something to verify with the team or provider.",
            },
        ]

    def _update_owner_answers(self) -> list[dict[str, Any]]:
        return [
            {
                "a_id": 1,
                "label": "I do this myself or know exactly who does it",
                "score": {"asset_ownership": "+8", "incident_routing": "+4"},
            },
            {
                "a_id": 2,
                "label": "An external provider or colleague handles it",
                "score": {"third_party_coordination": "+8", "asset_ownership": "+4"},
            },
            {
                "a_id": 3,
                "label": "I am not sure who handles updates or fixes",
                "score": {"asset_ownership": "-8", "third_party_coordination": "-4"},
                "recommendations": "Create a simple owner list for devices, websites, accounts, and update responsibilities.",
            },
        ]

    def _add_baseline_questions(self, questions: list[dict[str, Any]]) -> None:
        self._add_question(
            questions,
            100,
            "Which description is closest to your role in the organisation?",
            [
                {"a_id": 1, "label": "Finance, administration, grants, or payments", "score": {"role_context": "+6"}},
                {"a_id": 2, "label": "Programme delivery, casework, donors, or partnerships", "score": {"role_context": "+6"}},
                {"a_id": 3, "label": "Communications, website, social media, or public inboxes", "score": {"role_context": "+6"}},
                {"a_id": 4, "label": "Leadership, operations, or general management", "score": {"role_context": "+6"}},
                {"a_id": 5, "label": "IT support, supplier, volunteer, or another role", "score": {"role_context": "+6"}},
            ],
            observed_item="respondent_role",
        )
        self._add_question(
            questions,
            101,
            "If something suspicious happens, do you know who should be told first?",
            [
                {"a_id": 1, "label": "Yes, I know the internal contact or provider", "score": {"incident_routing": "+10"}},
                {"a_id": 2, "label": "I would ask a colleague but I am not sure who owns it", "score": {"incident_routing": "-2"}},
                {
                    "a_id": 3,
                    "label": "No, I do not know the route",
                    "score": {"incident_routing": "-10"},
                    "recommendations": "Publish one clear first-contact route for suspicious emails, device issues, and account concerns.",
                },
            ],
            observed_item="incident_route",
        )

    def _add_enumeros_questions(self, questions: list[dict[str, Any]], data: dict | None) -> None:
        if not data:
            return
        hostname = data.get("hostname") or "this device"
        os_info = data.get("os") or {}
        os_label = " ".join(str(os_info.get(k, "")).strip() for k in ("product_name", "product_version")).strip()
        self._add_question(
            questions,
            200,
            f"Enumeros saw {hostname}{f' running {os_label}' if os_label else ''}. Is that a device you use or support for NGO work?",
            self._recognition_answers("device"),
            source_module="enumeros",
            source_file="enumeros/enumeros.json",
            observed_item=str(hostname),
            context_kind="local_inventory",
        )
        version_status = data.get("version_status") or {}
        outdated_items = [
            name
            for name, status in version_status.items()
            if isinstance(status, dict)
            and str(status.get("status", "")).lower() in {"outdated", "unsupported", "stale"}
        ]
        if outdated_items or (data.get("summary") or {}).get("outdated_count", 0):
            label = ", ".join(outdated_items[:3]) or "software updates"
            self._add_question(
                questions,
                201,
                f"Enumeros found a possible update gap for {label}. Who would normally update or approve updates for this?",
                self._update_owner_answers(),
                source_module="enumeros",
                source_file="enumeros/enumeros.json",
                observed_item=label,
                context_kind="update_ownership",
            )

    def _add_safesniff_questions(self, questions: list[dict[str, Any]], data: dict | None) -> None:
        if not data:
            return
        devices = []
        inventory = data.get("device_inventory") or {}
        if isinstance(inventory.get("devices"), list):
            devices.extend(inventory["devices"])
        if isinstance(data.get("hosts"), list):
            devices.extend(data["hosts"])
        if isinstance(data.get("tested_hosts"), list):
            devices.extend(data["tested_hosts"])
        if not devices and data.get("target_detection"):
            target_detection = data.get("target_detection") or {}
            local_ip = target_detection.get("local_ip") or data.get("target") or "the detected network"
            prefix = target_detection.get("prefix")
            tested_hosts = data.get("tested_hosts")
            target_label = f"{local_ip}/{prefix}" if prefix else str(local_ip)
            self._add_question(
                questions,
                300,
                f"SafeSniff selected {target_label} for network checking and planned checks across {tested_hosts or 'the discovered'} hosts. Is that the network scope you would expect for NGO devices?",
                [
                    {"a_id": 1, "label": "Yes, that matches the NGO network I expect", "score": {"system_knowledge": "+7", "asset_ownership": "+4"}},
                    {
                        "a_id": 2,
                        "label": "It may be correct, but I would need someone else to confirm",
                        "score": {"system_knowledge": "+2", "third_party_coordination": "+4"},
                        "recommendations": "Keep a simple note of the expected office or home-office network ranges used for NGO work.",
                    },
                    {
                        "a_id": 3,
                        "label": "No, I do not recognise that network scope",
                        "score": {"system_knowledge": "-7", "incident_routing": "+2"},
                        "recommendations": "Ask the network owner or provider to confirm whether this scan scope matches the organisation's environment.",
                    },
                ],
                source_module="safesniff",
                source_file="safesniff/safesniff.json",
                observed_item=target_label,
                context_kind="network_scope",
            )
        for index, device in enumerate(devices[:3], start=1):
            if isinstance(device, dict):
                name = device.get("hostname") or device.get("host") or device.get("ip") or device.get("target") or f"network device {index}"
                services = device.get("services") or device.get("open_ports") or device.get("ports") or []
            else:
                name = str(device)
                services = []
            service_hint = f" with services {services[:3]}" if services else ""
            self._add_question(
                questions,
                300 + index,
                f"SafeSniff observed {name}{service_hint}. Is this expected on the NGO network?",
                self._recognition_answers("network device"),
                source_module="safesniff",
                source_file="safesniff/safesniff.json",
                observed_item=str(name),
                context_kind="network_observation",
            )

    def _add_dnscap_questions(self, questions: list[dict[str, Any]], data: dict | None) -> None:
        if not data:
            return
        candidates: list[str] = []
        for event in data.get("events", [])[:50]:
            if isinstance(event, dict) and event.get("qname"):
                candidates.append(str(event["qname"]))
        top_qnames = ((data.get("summary") or {}).get("top_qnames") or [])
        for item in top_qnames:
            if isinstance(item, dict) and item.get("qname"):
                candidates.append(str(item["qname"]))
        suspicious = [
            domain
            for domain in dict.fromkeys(candidates)
            if any(token in domain.lower() for token in SUSPICIOUS_DOMAIN_TOKENS)
        ]
        chosen = suspicious[:3] or list(dict.fromkeys(candidates))[:2]
        for index, domain in enumerate(chosen, start=1):
            self._add_question(
                questions,
                400 + index,
                f"DNScap recorded DNS activity for {domain}. Do you recognise this domain or the work activity that might have caused it?",
                [
                    {"a_id": 1, "label": "Yes, it is expected for our work", "score": {"system_knowledge": "+6"}},
                    {
                        "a_id": 2,
                        "label": "It looks related to an email, login page, invoice, or file-sharing prompt I saw",
                        "score": {"phishing_readiness": "+4", "incident_routing": "+3"},
                        "recommendations": "If the domain was reached from an email or login prompt, preserve the message and route it for review.",
                    },
                    {
                        "a_id": 3,
                        "label": "I do not recognise it and would report it",
                        "score": {"phishing_readiness": "+8", "incident_routing": "+6"},
                    },
                    {
                        "a_id": 4,
                        "label": "I am not sure what I would do",
                        "score": {"phishing_readiness": "-6", "incident_routing": "-6"},
                        "recommendations": "Agree a simple rule: unfamiliar login, payment, or document domains should be reported before credentials are entered.",
                    },
                ],
                source_module="dnscap",
                source_file="dnscap/dnscap_summary.json",
                observed_item=domain,
                context_kind="dns_history",
            )

    def _add_threatsucker_questions(self, questions: list[dict[str, Any]], data: dict | None) -> None:
        if not data:
            return
        matches = data.get("dns_matches") or data.get("critical_items") or data.get("top_threats") or []
        if isinstance(matches, dict):
            matches = list(matches.values())
        if not matches:
            counts = data.get("counts") or {}
            self._add_question(
                questions,
                500,
                "ThreatSucker did not currently correlate DNS or vulnerability evidence with high-confidence threat intelligence. Would you know what extra business context might still be relevant?",
                [
                    {
                        "a_id": 1,
                        "label": "Yes, I can add recent suspicious emails, invoices, website changes, or account concerns",
                        "score": {"phishing_readiness": "+6", "incident_routing": "+4"},
                    },
                    {
                        "a_id": 2,
                        "label": "I would know who to ask for that context",
                        "score": {"third_party_coordination": "+5", "incident_routing": "+4"},
                    },
                    {
                        "a_id": 3,
                        "label": "No, I would not know what context to add",
                        "score": {"phishing_readiness": "-5", "incident_routing": "-4"},
                        "recommendations": "Create a short incident prompt: recent strange emails, password prompts, invoice requests, website changes, and account warnings.",
                    },
                ],
                source_module="threatsucker",
                source_file="threatsucker/threatsucker_correlation.json",
                observed_item=f"{counts.get('dns_matches', 0)} DNS matches",
                context_kind="threat_correlation",
            )
            return
        for index, match in enumerate(matches[:2], start=1):
            item = match
            if isinstance(match, dict):
                item = match.get("indicator") or match.get("domain") or match.get("name") or match.get("threat_type") or match
            self._add_question(
                questions,
                500 + index,
                f"ThreatSucker correlated telemetry with {item}. Have you seen related emails, login prompts, payment requests, or website warnings?",
                [
                    {
                        "a_id": 1,
                        "label": "Yes, I saw something related and can describe where",
                        "score": {"phishing_readiness": "+8", "incident_routing": "+6"},
                        "recommendations": "Capture the related message, domain, or screenshot and link it to the technical finding.",
                    },
                    {"a_id": 2, "label": "No, I have not seen anything related", "score": {"phishing_readiness": "+2"}},
                    {
                        "a_id": 3,
                        "label": "I am not sure what would count as related",
                        "score": {"phishing_readiness": "-5"},
                        "recommendations": "Give users concrete examples of related phishing lures: invoices, password resets, file shares, donation/payment notices.",
                    },
                ],
                source_module="threatsucker",
                source_file="threatsucker/threatsucker_correlation.json",
                observed_item=str(item),
                context_kind="threat_correlation",
            )

    def _add_sitechecker_questions(self, questions: list[dict[str, Any]], data: dict | None) -> None:
        if not data:
            return
        target = data.get("target_url") or data.get("final_url") or "the public website"
        findings = data.get("findings") or []
        headline = None
        if findings and isinstance(findings[0], dict):
            headline = findings[0].get("title") or findings[0].get("id")
        components = data.get("observed_components") or data.get("detected_tech") or []
        component_label = ""
        if components and isinstance(components[0], dict):
            component_label = components[0].get("name") or ""
            if components[0].get("version"):
                component_label = f"{component_label} {components[0]['version']}".strip()
        observed = headline or component_label or target
        self._add_question(
            questions,
            600,
            f"SiteChecker found website evidence for {target}{f' ({observed})' if observed else ''}. Who can check or change this website?",
            self._update_owner_answers(),
            source_module="sitechecker",
            source_file="sitechecker/sitechecker.json",
            observed_item=str(observed),
            context_kind="website_ownership",
        )
