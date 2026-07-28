import json
import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path


class ProjectGraphRefreshWorkflowTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.repo_root = Path(__file__).resolve().parents[1]
        self.wrapper_text = (self.repo_root / "tools" / "refresh_project_graph.ps1").read_text(
            encoding="utf-8"
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self.tmp.name)
        self.fixture_index = 0
        self.toolbin = self.tmp_path / "toolbin"
        self.toolbin.mkdir()
        self._write_fake_graphify()

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, args, cwd, check=True, env=None):
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if check and completed.returncode != 0:
            self.fail(
                "command failed\n"
                f"args={args}\n"
                f"stdout={completed.stdout}\n"
                f"stderr={completed.stderr}"
            )
        return completed

    def _git(self, repo, *args, check=True):
        return self._run(["git", *args], cwd=repo, check=check)

    def _write(self, root, relative, text):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def _commit(self, repo, message):
        self._git(repo, "add", ".")
        self._git(repo, "commit", "-m", message)
        return self._git(repo, "rev-parse", "HEAD").stdout.strip()

    def _init_repo(self, repo):
        repo.mkdir(parents=True, exist_ok=True)
        self._git(repo, "init")
        self._git(repo, "config", "user.email", "test@example.invalid")
        self._git(repo, "config", "user.name", "Project Graph Test")
        self._write(repo, ".graphifyignore", "\n".join((
            "graphify-out/",
            ".worktrees/",
            "equipment_inventory.local.json",
            "*.xlsx",
            "*.xls",
            ".env",
            "credentials.local.json",
            "openspec/changes/archive/",
        )) + "\n")
        self._write(repo, "RULES.md", "# Rules\n")
        self._write(repo, "openspec.cmd", "@echo off\n")
        self._write(repo, "docs/project-graph-runbook.md", "# Runbook\n")
        self._write(repo, "tools/refresh_project_graph.ps1", self.wrapper_text)

    def _add_smoke_sources(self, repo):
        self._write(repo, "gui/pdu_controller.py", "class PDUController:\n    pass\n")
        self._write(
            repo,
            "core/interactive_session.py",
            "class InteractiveSessionController:\n"
            "    def acquire_handler(self, context, start_index):\n"
            "        return CredentialAttemptPlan(context.candidates, start_index)\n",
        )
        self._write(repo, "core/equipment_inventory.py", "class EquipmentInventory:\n    pass\n")
        self._write(
            repo,
            "gui/main_window.py",
            "class VCSDiagnosticApp:\n"
            "    def _on_pdu_refresh_accepted_for_enrichment(self):\n"
            "        return self.pdu_room_codec_controller\n",
        )
        self._write(
            repo,
            "core/room_context.py",
            "class RoomContextResolver:\n"
            "    def resolve_related_codec(self, inventory, pdu_ip_address):\n"
            "        return inventory.find_by_ip(pdu_ip_address)\n",
        )
        self._write(
            repo,
            "gui/pdu_room_codec_enrichment.py",
            "class PDURoomCodecEnrichmentController:\n"
            "    def handler_factory(self, related_handler, expected_model):\n"
            "        return _status_adapter.read_status(related_handler, expected_model)\n",
        )

    def _write_fake_graphify(self):
        graph_json = json.dumps({
            "nodes": [
                {
                    "id": "gui_pdu_controller_pducontroller",
                    "label": "PDUController",
                    "source_file": "gui/pdu_controller.py",
                    "file_type": "code",
                },
                {
                    "id": "core_interactive_session_interactivesessioncontroller",
                    "label": "InteractiveSessionController",
                    "source_file": "core/interactive_session.py",
                    "file_type": "code",
                },
                {
                    "id": "core_equipment_inventory_equipmentinventory",
                    "label": "EquipmentInventory",
                    "source_file": "core/equipment_inventory.py",
                    "file_type": "code",
                },
                {
                    "id": "core_interactive_session_interactivesessioncontroller_acquire_handler",
                    "label": "acquire_handler",
                    "source_file": "core/interactive_session.py",
                    "file_type": "code",
                },
                {
                    "id": "core_credentials_credentialattemptplan",
                    "label": "CredentialAttemptPlan",
                    "source_file": "core/interactive_session.py",
                    "file_type": "code",
                },
                {
                    "id": "gui_main_window_vcsdiagnosticapp_on_pdu_refresh_accepted_for_enrichment",
                    "label": "_on_pdu_refresh_accepted_for_enrichment",
                    "source_file": "gui/main_window.py",
                    "file_type": "code",
                },
                {
                    "id": "gui_main_window_vcsdiagnosticapp_pdu_room_codec_controller",
                    "label": "pdu_room_codec_controller",
                    "source_file": "gui/main_window.py",
                    "file_type": "code",
                },
                {
                    "id": "core_room_context_roomcontextresolver_resolve_related_codec",
                    "label": "resolve_related_codec",
                    "source_file": "core/room_context.py",
                    "file_type": "code",
                },
                {
                    "id": "gui_pdu_room_codec_enrichment_pduroomcodecenrichmentcontroller_handler_factory",
                    "label": "handler_factory",
                    "source_file": "gui/pdu_room_codec_enrichment.py",
                    "file_type": "code",
                },
                {
                    "id": "core_related_codec_status_relatedcodecstatusadapter_read_status",
                    "label": "read_status",
                    "source_file": "gui/pdu_room_codec_enrichment.py",
                    "file_type": "code",
                },
            ],
            "links": [
                {
                    "source": "core_interactive_session_interactivesessioncontroller_acquire_handler",
                    "target": "core_credentials_credentialattemptplan",
                    "relation": "calls",
                    "confidence": "EXTRACTED",
                    "source_file": "core/interactive_session.py",
                    "source_location": "1",
                },
                {
                    "source": "gui_main_window_vcsdiagnosticapp_on_pdu_refresh_accepted_for_enrichment",
                    "target": "gui_main_window_vcsdiagnosticapp_pdu_room_codec_controller",
                    "relation": "calls",
                    "confidence": "EXTRACTED",
                    "source_file": "gui/main_window.py",
                    "source_location": "1",
                },
                {
                    "source": "core_room_context_roomcontextresolver_resolve_related_codec",
                    "target": "core_equipment_inventory_equipmentinventory",
                    "relation": "references",
                    "confidence": "EXTRACTED",
                    "source_file": "core/room_context.py",
                    "source_location": "1",
                },
                {
                    "source": "gui_pdu_room_codec_enrichment_pduroomcodecenrichmentcontroller_handler_factory",
                    "target": "core_related_codec_status_relatedcodecstatusadapter_read_status",
                    "relation": "indirect_call",
                    "confidence": "EXTRACTED",
                    "source_file": "gui/pdu_room_codec_enrichment.py",
                    "source_location": "1",
                },
            ],
        })
        manifest_json = json.dumps({
            "gui/pdu_controller.py": {"semantic_hash": "a"},
            "core/interactive_session.py": {"semantic_hash": "b"},
            "core/equipment_inventory.py": {"semantic_hash": "c"},
            "gui/main_window.py": {"semantic_hash": "d"},
            "core/room_context.py": {"semantic_hash": "e"},
            "gui/pdu_room_codec_enrichment.py": {"semantic_hash": "f"},
        })
        script = textwrap.dedent(f"""\
            @echo off
            if "%1"=="--version" (
              echo graphify 0.9.26
              exit /b 0
            )
            if "%1"=="extract" (
              mkdir graphify-out 2>nul
              > graphify-out\\graph.json echo {graph_json}
              > graphify-out\\manifest.json echo {manifest_json}
              > graphify-out\\GRAPH_REPORT.md echo # Graph Report
              >> graphify-out\\GRAPH_REPORT.md echo ## Graph Freshness
              >> graphify-out\\GRAPH_REPORT.md echo graphify update . after code changes
              exit /b 0
            )
            if "%1"=="cluster-only" exit /b 0
            if "%1"=="check-update" exit /b 0
            if "%1"=="update" exit /b 0
            exit /b 1
            """)
        (self.toolbin / "graphify.cmd").write_text(script, encoding="utf-8", newline="\r\n")

    def _metadata_block(self, source_commit, verdict="APPROVE", **overrides):
        values = {
            "schema_version": "1",
            "validated_remote_branch": "agent/example-change",
            "validated_source_commit": source_commit,
            "verdict": verdict,
            "archive_permitted": "true",
            "merge_permitted": "false",
            "production_code_changed_by_validator": "false",
            "tests_changed_by_validator": "false",
        }
        values.update(overrides)
        return "\n".join((
            "BEGIN VALIDATION METADATA",
            f"schema_version: {values['schema_version']}",
            f"validated_remote_branch: {values['validated_remote_branch']}",
            f"validated_source_commit: {values['validated_source_commit']}",
            f"verdict: {values['verdict']}",
            f"archive_permitted: {values['archive_permitted']}",
            f"merge_permitted: {values['merge_permitted']}",
            f"production_code_changed_by_validator: {values['production_code_changed_by_validator']}",
            f"tests_changed_by_validator: {values['tests_changed_by_validator']}",
            "END VALIDATION METADATA",
        ))

    def _ordinary_fixture(
        self,
        name="example-change",
        evidence_path=None,
        evidence_mutator=None,
        report_text_mutator=None,
        report_metadata_overrides=None,
        extra_vr_path=None,
        extra_re_path=None,
        modify_evidence_after_commit=False,
    ):
        self.fixture_index += 1
        fixture_name = f"{self.fixture_index}-{name}"
        source = self.tmp_path / ("source-" + fixture_name)
        output = self.tmp_path / ("output-" + fixture_name)
        self._init_repo(source)
        self._add_smoke_sources(source)
        self._write(source, f"openspec/changes/{name}/spec.md", "# active\n")
        self._git(source, "checkout", "-b", f"agent/{name}")
        self._commit(source, "initial active change")

        archive_path = f"openspec/changes/archive/2026-07-28-{name}"
        active = source / "openspec" / "changes" / name
        shutil.rmtree(active)
        self._write(source, f"{archive_path}/spec.md", "# archived\n")
        archive_commit = self._commit(source, "archive change")
        validated_source_commit = archive_commit

        report_path = f"{archive_path}/verification-report.md"
        report = "\n".join((
            "# Verification Report",
            "validated remote branch: agent/example-change",
            f"validated source commit: {validated_source_commit}",
            "verdict: APPROVE",
            "archive permitted: true",
            "merge permitted: false",
            "production code changed by validator: false",
            "tests changed by validator: false",
            self._metadata_block(
                validated_source_commit,
                **(report_metadata_overrides or {}),
            ),
            "",
        ))
        if report_text_mutator:
            report = report_text_mutator(report)
        self._write(source, report_path, report)
        if extra_vr_path:
            self._write(source, extra_vr_path, "extra\n")
        report_commit = self._commit(source, "record validation report")

        evidence = {
            "schema_version": 1,
            "change_name": name,
            "archive_path": archive_path,
            "archive_commit": archive_commit,
            "validated_source_commit": validated_source_commit,
            "verification_report_path": report_path,
            "verification_report_commit": report_commit,
            "openspec_all_validation": {"status": "pass"},
            "python_tests": {
                "status": "pass",
                "tests": 1,
                "failures": 0,
                "errors": 0,
                "skips": 0,
            },
            "git_diff_check": {"status": "pass"},
            "repository_protection": {"status": "pass"},
            "verdict": "APPROVE",
        }
        if evidence_mutator:
            evidence_mutator(evidence)
        path = evidence_path or f"openspec/validation/{name}.post-archive.json"
        self._write(source, path, json.dumps(evidence, indent=2) + "\n")
        if extra_re_path:
            self._write(source, extra_re_path, "extra\n")
        evidence_commit = self._commit(source, "record graphify evidence")
        if modify_evidence_after_commit:
            self._write(source, path, json.dumps({**evidence, "verdict": "APPROVE WITH NON-BLOCKING NOTES"}, indent=2) + "\n")

        self._init_repo(output)
        self._commit(output, "initial output")
        return {
            "source": source,
            "output": output,
            "evidence_path": path,
            "evidence_commit": evidence_commit,
        }

    def _historical_fixture(self):
        source = self.tmp_path / "source-historical"
        output = self.tmp_path / "output-historical"
        self._init_repo(source)
        self._add_smoke_sources(source)
        self._git(source, "checkout", "-b", "agent/frozen-project-graph-baseline")
        self._write(source, "openspec/changes/frozen-project-graph-baseline/spec.md", "# active\n")
        self._commit(source, "initial historical")
        shutil.rmtree(source / "openspec" / "changes" / "frozen-project-graph-baseline")
        self._write(
            source,
            "openspec/changes/archive/2026-07-27-frozen-project-graph-baseline/specs/agent-project-navigation/spec.md",
            "# archived\n",
        )
        archive_commit = self._commit(source, "archive historical")
        evidence = {
            "change_name": "frozen-project-graph-baseline",
            "archive_commit": archive_commit,
            "validated_source_commit": archive_commit,
            "openspec_change_validation": {"status": "pass"},
            "openspec_all_validation": {"status": "pass"},
            "python_tests": {"status": "pass"},
            "git_diff_check": {"status": "pass"},
        }
        evidence_path = "openspec/validation/frozen-project-graph-baseline.post-archive.json"
        self._write(source, evidence_path, json.dumps(evidence, indent=2) + "\n")
        evidence_commit = self._commit(source, "record historical evidence")

        self._init_repo(output)
        self._commit(output, "initial output")
        return {
            "source": source,
            "output": output,
            "evidence_path": evidence_path,
            "evidence_commit": evidence_commit,
        }

    def _invoke_wrapper(self, fixture):
        env = os.environ.copy()
        env["PATH"] = str(self.toolbin) + os.pathsep + env.get("PATH", "")
        return self._run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(fixture["source"] / "tools" / "refresh_project_graph.ps1"),
                "-Mode",
                "FullRebuild",
                "-BaselineStage",
                "Final",
                "-SourceRoot",
                str(fixture["source"]),
                "-SourceRef",
                "HEAD",
                "-OutputRoot",
                str(fixture["output"]),
                "-TargetBranch",
                "master",
                "-PostArchiveValidationEvidence",
                fixture["evidence_path"],
            ],
            cwd=fixture["output"],
            check=False,
            env=env,
        )

    def assertAccepted(self, fixture):
        result = self._invoke_wrapper(fixture)
        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        baseline = json.loads((fixture["output"] / "graphify-out" / "baseline.json").read_text(encoding="utf-8"))
        self.assertEqual("final", baseline["baseline_stage"])
        self.assertEqual(fixture["evidence_commit"], baseline["indexed_source_commit"])
        return result

    def assertRejected(self, fixture, category):
        result = self._invoke_wrapper(fixture)
        self.assertNotEqual(0, result.returncode, result.stdout)
        combined = result.stdout + result.stderr
        self.assertIn(category, combined)
        self.assertNotIn(str(self.tmp_path), combined)
        self.assertFalse((fixture["output"] / "graphify-out" / "baseline.json").exists())
        return result

    def test_historical_frozen_baseline_workflow_remains_valid(self):
        self.assertAccepted(self._historical_fixture())

    def test_ordinary_valid_v_r_e_gate_accepts_and_indexes_evidence_commit(self):
        self.assertAccepted(self._ordinary_fixture())

    def test_ordinary_verdict_with_non_blocking_notes_is_allowed(self):
        fixture = self._ordinary_fixture(
            evidence_mutator=lambda evidence: evidence.update({"verdict": "APPROVE WITH NON-BLOCKING NOTES"}),
            report_metadata_overrides={"verdict": "APPROVE WITH NON-BLOCKING NOTES"},
        )
        self.assertAccepted(fixture)

    def test_evidence_json_schema_and_path_fail_closed(self):
        cases = {
            "missing field": (lambda e: e.pop("repository_protection"), "EVIDENCE_SCHEMA"),
            "unknown field": (lambda e: e.update({"unexpected": True}), "EVIDENCE_SCHEMA"),
            "nested missing field": (lambda e: e["python_tests"].pop("skips"), "EVIDENCE_SCHEMA"),
            "nested unknown field": (lambda e: e["git_diff_check"].update({"detail": "ok"}), "REQUIRED_CHECK"),
            "wrong type": (lambda e: e.update({"schema_version": "1"}), "EVIDENCE_SCHEMA"),
            "uppercase sha": (lambda e: e.update({"archive_commit": e["archive_commit"].upper()}), "COMMIT_IDENTITY"),
            "partial sha": (lambda e: e.update({"validated_source_commit": e["validated_source_commit"][:12]}), "COMMIT_IDENTITY"),
            "non resolving sha": (lambda e: e.update({"archive_commit": "0" * 40}), "COMMIT_IDENTITY"),
            "failed status": (lambda e: e["openspec_all_validation"].update({"status": "fail"}), "REQUIRED_CHECK"),
            "negative test count": (lambda e: e["python_tests"].update({"failures": -1}), "EVIDENCE_SCHEMA"),
            "disallowed verdict": (lambda e: e.update({"verdict": "CHANGES REQUIRED"}), "VERDICT"),
            "self referential evidence commit": (lambda e: e.update({"evidence_commit": "0" * 40}), "EVIDENCE_SCHEMA"),
            "self referential indexed source": (lambda e: e.update({"indexed_source_commit": "0" * 40}), "EVIDENCE_SCHEMA"),
            "wrong archive pairing": (lambda e: e.update({"archive_path": "openspec/changes/archive/2026-07-28-other-change"}), "EVIDENCE_PATH"),
            "alternate extension": (lambda e: None, "EVIDENCE_PATH", "openspec/validation/example-change.post-archive.txt"),
            "path traversal": (lambda e: None, "EVIDENCE_PATH", "openspec/validation/../example-change.post-archive.json"),
        }
        for label, spec in cases.items():
            with self.subTest(label=label):
                mutator, category, *path = spec
                fixture = self._ordinary_fixture(evidence_mutator=mutator, evidence_path=path[0] if path else None)
                self.assertRejected(fixture, category)

    def test_metadata_block_failures_are_rejected_without_substring_fallback(self):
        cases = {
            "missing begin": lambda text: text.replace("BEGIN VALIDATION METADATA\n", ""),
            "duplicate begin": lambda text: text.replace("BEGIN VALIDATION METADATA", "BEGIN VALIDATION METADATA\nBEGIN VALIDATION METADATA", 1),
            "two blocks": lambda text: text + "\n" + self._metadata_block("0" * 40),
            "marker order": lambda text: text.replace("BEGIN VALIDATION METADATA", "TEMP", 1).replace("END VALIDATION METADATA", "BEGIN VALIDATION METADATA", 1).replace("TEMP", "END VALIDATION METADATA", 1),
            "blank line": lambda text: text.replace("schema_version: 1", "schema_version: 1\n", 1),
            "indentation": lambda text: text.replace("schema_version: 1", " schema_version: 1", 1),
            "comment": lambda text: text.replace("schema_version: 1", "# comment\nschema_version: 1", 1),
            "quoted": lambda text: text.replace("BEGIN VALIDATION METADATA", "```text\nBEGIN VALIDATION METADATA", 1).replace("END VALIDATION METADATA", "END VALIDATION METADATA\n```", 1),
            "reordered": lambda text: text.replace("schema_version: 1\nvalidated_remote_branch", "validated_remote_branch: agent/example-change\nschema_version", 1),
            "duplicate key": lambda text: text.replace("schema_version: 1", "schema_version: 1\nschema_version: 1", 1),
            "unknown key": lambda text: text.replace("schema_version: 1", "schema_version: 1\nunknown_key: value", 1),
            "extra colon": lambda text: text.replace("schema_version: 1", "schema_version: 1: extra", 1),
            "invalid branch": lambda text: text.replace("validated_remote_branch: agent/example-change", "validated_remote_branch: bad branch", 1),
            "control branch": lambda text: text.replace("validated_remote_branch: agent/example-change", "validated_remote_branch: agent/example\tchange", 1),
            "partial sha": lambda text: text.replace("validated_source_commit: ", "validated_source_commit: 123456789abc #", 1),
            "uppercase boolean": lambda text: text.replace("archive_permitted: true", "archive_permitted: True", 1),
            "archive denied": lambda text: text.replace("archive_permitted: true", "archive_permitted: false", 1),
            "production changed": lambda text: text.replace("production_code_changed_by_validator: false", "production_code_changed_by_validator: true", 1),
            "tests changed": lambda text: text.replace("tests_changed_by_validator: false", "tests_changed_by_validator: true", 1),
            "human contradiction": lambda text: text.replace("archive permitted: true", "archive permitted: false", 1),
        }
        for label, mutator in cases.items():
            with self.subTest(label=label):
                fixture = self._ordinary_fixture(report_text_mutator=mutator)
                self.assertRejected(fixture, "REPORT_METADATA")

    def test_lineage_report_and_working_byte_failures_are_rejected(self):
        cases = {
            "extra v r path": lambda: self._ordinary_fixture(extra_vr_path="extra-vr.txt"),
            "extra r e path": lambda: self._ordinary_fixture(extra_re_path="extra-re.txt"),
            "modified evidence": lambda: self._ordinary_fixture(modify_evidence_after_commit=True),
            "historical impersonation": lambda: self._ordinary_fixture(
                name="frozen-project-graph-baseline",
                evidence_path="openspec/validation/frozen-project-graph-baseline.post-archive.json",
            ),
        }
        categories = {
            "extra v r path": "LINEAGE",
            "extra r e path": "LINEAGE",
            "modified evidence": "EVIDENCE_BYTES",
            "historical impersonation": "HISTORICAL_COMPATIBILITY",
        }
        for label, factory in cases.items():
            with self.subTest(label=label):
                self.assertRejected(factory(), categories[label])


if __name__ == "__main__":
    unittest.main()
