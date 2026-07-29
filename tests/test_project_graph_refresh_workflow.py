import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "tools" / "refresh_project_graph.ps1"


class ProjectGraphRefreshWorkflowTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for leftover in Path(tempfile.gettempdir()).glob("diag-project-graph-publication-*"):
            if leftover.is_dir():
                shutil.rmtree(leftover, ignore_errors=True)
        self.repo = self.root / "repo"
        self.fake_bin = self.root / "bin"
        self.fake_bin.mkdir()
        self._write_fake_graphify()
        self._init_repo(include_historical_inputs=True)

    def tearDown(self):
        try:
            subprocess.run(["git", "-C", str(self.repo), "worktree", "prune"], check=False, capture_output=True, text=True)
        finally:
            self.tmp.cleanup()

    def run_cmd(self, args, cwd=None, env=None, check=True):
        merged_env = os.environ.copy()
        merged_env["PATH"] = str(self.fake_bin) + os.pathsep + merged_env.get("PATH", "")
        if env:
            merged_env.update(env)
        result = subprocess.run(
            args,
            cwd=str(cwd or self.repo),
            env=merged_env,
            text=True,
            capture_output=True,
        )
        if check and result.returncode != 0:
            self.fail(f"command failed {args}\nstdout={result.stdout}\nstderr={result.stderr}")
        return result

    def git(self, *args, cwd=None, check=True):
        return self.run_cmd(["git", *args], cwd=cwd, check=check)

    def write(self, path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")

    def remove_tree(self, path):
        def clear_readonly(func, target, exc):
            try:
                os.chmod(target, 0o700)
                func(target)
            except FileNotFoundError:
                pass
        shutil.rmtree(path, ignore_errors=False, onexc=clear_readonly) if path.exists() else None

    def _write_fake_graphify(self):
        fake_py = self.fake_bin / "fake_graphify.py"
        self.write(
            fake_py,
            r'''
import json
import os
import sys
from pathlib import Path

args = sys.argv[1:]
if args and args[0] == "--version":
    print("graphify 0.9.26")
    raise SystemExit(0)

cmd = args[0] if args else ""
root = Path(args[1]) if len(args) > 1 else Path.cwd()
case = os.environ.get("GRAPHIFY_FAKE_CASE", "valid")

if cmd in ("check-update", "cluster-only"):
    raise SystemExit(0)
if cmd not in ("extract", "update"):
    print("unsupported fake graphify command", cmd, file=sys.stderr)
    raise SystemExit(2)
if case == "generator_failure":
    raise SystemExit(9)

graph_dir = root / "graphify-out"
graph_dir.mkdir(exist_ok=True)
source_file = "app.py" if (root / "app.py").exists() else "renamed.py"
if case == "ghost":
    source_file = "missing.py"
elif case == "absolute_path":
    source_file = str(root / "app.py")
elif case == "inventory_path":
    source_file = "equipment_inventory.local.json"

nodes = [
    {"id": "module_app", "label": "app", "source_file": source_file, "file_type": "code"},
    {"id": "func_current", "label": "current", "source_file": source_file, "file_type": "code"},
]
links = [{"source": "module_app", "target": "func_current", "relation": "contains", "confidence": "EXTRACTED"}]
manifest = {source_file: {"symbols": ["module_app", "func_current"]}}

if case == "invalid_schema":
    graph = {"schema": "wrong"}
elif case == "graph_root_wrong":
    graph = [{"nodes": nodes, "links": links}, {"nodes": nodes, "links": links}]
elif case == "node_field_wrong_type":
    graph = {"nodes": [{"id": 123, "label": "bad", "source_file": source_file}], "links": links}
elif case == "links_wrong_type":
    graph = {"nodes": nodes, "links": {"source": "module_app", "target": "func_current"}}
elif case == "broken_ref":
    graph = {"nodes": nodes, "links": [{"source": "module_app", "target": "missing", "relation": "calls"}]}
elif case == "zero_counts":
    graph = {"nodes": [], "links": []}
else:
    graph = {"nodes": nodes, "links": links}

if case == "manifest_root_wrong":
    manifest = [manifest, manifest]
elif case == "manifest_entry_wrong_type":
    manifest = {source_file: ["module_app", "func_current"]}
elif case == "manifest_symbols_wrong_type":
    manifest = {source_file: {"symbols": "module_app"}}

(graph_dir / "graph.json").write_text(json.dumps(graph, sort_keys=True), encoding="utf-8", newline="\n")
(graph_dir / "manifest.json").write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8", newline="\n")
(graph_dir / "GRAPH_REPORT.md").write_text("# Fake graph report\n", encoding="utf-8", newline="\n")
raise SystemExit(0)
'''.lstrip(),
        )
        cmd = self.fake_bin / "graphify.cmd"
        self.write(cmd, f'@echo off\r\n"{sys.executable}" "{fake_py}" %*\r\n')

    def _init_repo(self, include_historical_inputs=False):
        self.repo.mkdir()
        self.git("init", "-b", "master")
        self.git("config", "user.email", "test@example.invalid")
        self.git("config", "user.name", "Test User")
        self.write(self.repo / "RULES.md", "Graphify is optional navigation only.\n")
        self.write(self.repo / "openspec.cmd", "@echo off\necho openspec stub\n")
        self.write(
            self.repo / ".gitattributes",
            "\n".join(
                [
                    "/.graphifyignore text eol=lf",
                    "/graphify-out/graph.json text eol=lf",
                    "/graphify-out/manifest.json text eol=lf",
                    "/graphify-out/GRAPH_REPORT.md text eol=lf",
                    "/graphify-out/baseline.json text eol=lf",
                    "",
                ]
            ),
        )
        self.write(
            self.repo / ".graphifyignore",
            "\n".join(
                [
                    ".git/",
                    ".worktrees/",
                    "graphify-out/",
                    "node_modules/",
                    "equipment_inventory.local.json",
                    "credentials.local.json",
                    "credentials.local*.json",
                    "*.xlsx",
                    "*.xls",
                    ".env",
                    "openspec/changes/archive/",
                    "",
                ]
            ),
        )
        self.write(self.repo / "app.py", "def current():\n    return 'ok'\n")
        if include_historical_inputs:
            self.write(self.repo / "verification-report.md", "this is no longer graph authority\n")
            self.write(self.repo / "openspec" / "validation" / "bad.post-archive.json", "{not json\n")
            self.write(self.repo / "openspec" / "changes" / "archive" / "old" / "spec.md", "historical\n")
        self.git("add", ".")
        self.git("commit", "-m", "initial source")
        self.source_sha = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", self.source_sha)
        self.source = self.root / "source"
        self.output = self.root / "output"
        self.git("worktree", "add", "--detach", str(self.source), self.source_sha)
        self.git("worktree", "add", "-b", "graph-refresh", str(self.output), self.source_sha)

    def recreate_repo(self, include_historical_inputs=False):
        if self.source.exists():
            self.git("worktree", "remove", "--force", str(self.source), check=False)
        if self.output.exists():
            self.git("worktree", "remove", "--force", str(self.output), check=False)
        self.remove_tree(self.repo)
        self.remove_tree(self.source)
        self.remove_tree(self.output)
        self._init_repo(include_historical_inputs=include_historical_inputs)

    def run_wrapper(self, source=None, output=None, source_ref="origin/master", target="master", mode="FullRebuild", env=None):
        return self.run_cmd(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WRAPPER),
                "-Mode",
                mode,
                "-SourceRoot",
                str(source or self.source),
                "-SourceRef",
                source_ref,
                "-OutputRoot",
                str(output or self.output),
                "-TargetBranch",
                target,
            ],
            cwd=self.output,
            env=env,
            check=False,
        )

    def assert_wrapper_fails(self, **kwargs):
        result = self.run_wrapper(**kwargs)
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def assert_wrapper_succeeds(self, **kwargs):
        result = self.run_wrapper(**kwargs)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def read_baseline(self):
        return json.loads((self.output / "graphify-out" / "baseline.json").read_text(encoding="utf-8"))

    def changed_paths(self):
        lines = self.git("-C", str(self.output), "status", "--short", "--untracked-files=all").stdout.splitlines()
        return {line[3:].strip().replace("\\", "/") for line in lines if line.strip()}

    def graph_snapshot(self):
        graph_dir = self.output / "graphify-out"
        if not graph_dir.exists():
            return None
        return {
            path.name: path.read_bytes()
            for path in sorted(graph_dir.iterdir())
            if path.is_file()
        }

    def assert_no_publication_temp_dirs(self):
        temp_root = Path(tempfile.gettempdir())
        leftovers = [p for p in temp_root.glob("diag-project-graph-publication-*") if p.is_dir()]
        self.assertEqual([], leftovers)

    def commit_output_as_new_s(self, message="accepted graph"):
        self.git("add", "graphify-out", cwd=self.output)
        self.git("commit", "-m", message, cwd=self.output)
        accepted = self.git("rev-parse", "HEAD", cwd=self.output).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", accepted, cwd=self.output)
        if self.source.exists():
            self.git("worktree", "remove", "--force", str(self.source))
        self.source = self.root / f"source-{accepted[:8]}"
        self.git("worktree", "add", "--detach", str(self.source), accepted)
        self.source_sha = accepted
        return accepted

    def make_source_commit(self, edits, message="source change"):
        for rel, text in edits.items():
            self.write(self.source / rel, text)
        self.git("add", ".", cwd=self.source)
        self.git("commit", "-m", message, cwd=self.source)
        new_sha = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", new_sha, cwd=self.source)
        self.git("reset", "--hard", new_sha, cwd=self.output)
        self.source_sha = new_sha
        return new_sha

    def test_full_rebuild_publishes_from_one_clean_exact_source_sha_without_evidence(self):
        result = self.assert_wrapper_succeeds()
        baseline = self.read_baseline()
        self.assertIn("Graphify version: 0.9.26", result.stdout)
        self.assertEqual(baseline["baseline_stage"], "final")
        self.assertEqual(baseline["indexed_source_commit"], self.source_sha)
        self.assertEqual(baseline["indexed_source_ref"], "origin/master")
        self.assertEqual(baseline["target_branch"], "master")
        self.assertGreater(baseline["node_count"], 0)
        self.assertGreater(baseline["edge_count"], 0)

    def test_source_and_output_must_be_distinct_clean_worktrees_at_s(self):
        self.assert_wrapper_fails(source=self.output, output=self.output)
        self.write(self.source / "dirty.txt", "dirty\n")
        self.assert_wrapper_fails()
        (self.source / "dirty.txt").unlink()
        self.write(self.output / "dirty.txt", "dirty\n")
        self.assert_wrapper_fails()

    def test_output_head_must_equal_s_and_source_ref_must_resolve_to_s(self):
        self.write(self.output / "other.txt", "change\n")
        self.git("add", "other.txt", cwd=self.output)
        self.git("commit", "-m", "move output", cwd=self.output)
        self.assert_wrapper_fails()

        self.git("reset", "--hard", self.source_sha, cwd=self.output)
        self.write(self.repo / "later.py", "x = 1\n")
        self.git("add", "later.py")
        self.git("commit", "-m", "advance ref")
        newer = self.git("rev-parse", "HEAD").stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", newer)
        self.assert_wrapper_fails()

    def test_invalid_target_and_removed_initial_interface_are_rejected(self):
        self.assert_wrapper_fails(target="main")
        result = self.run_cmd(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(WRAPPER),
                "-Mode",
                "Initial",
                "-SourceRoot",
                str(self.source),
                "-OutputRoot",
                str(self.output),
            ],
            cwd=self.output,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_graphifyignore_is_source_policy_and_output_cannot_override_it(self):
        self.write(self.output / ".graphifyignore", "graphify-out/\n")
        self.assert_wrapper_fails()
        self.git("checkout", "--", ".graphifyignore", cwd=self.output)

        self.write(self.source / ".graphifyignore", (self.source / ".graphifyignore").read_text(encoding="utf-8") + "# local\n")
        self.assert_wrapper_fails()

    def test_valid_structural_refactor_does_not_require_old_application_smoke_symbols(self):
        (self.source / "app.py").unlink()
        self.write(self.source / "renamed.py", "def current():\n    return 'moved'\n")
        self.git("rm", "app.py", cwd=self.source)
        self.git("add", "renamed.py", cwd=self.source)
        self.git("commit", "-m", "move old smoke symbol", cwd=self.source)
        new_sha = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", new_sha, cwd=self.source)
        self.git("reset", "--hard", new_sha, cwd=self.output)
        result = self.assert_wrapper_succeeds(env={"GRAPHIFY_FAKE_CASE": "valid"})
        self.assertIn("Baseline stage: final", result.stdout)

    def test_structural_publication_defects_are_blocking(self):
        cases = ["invalid_schema", "broken_ref", "zero_counts", "ghost", "absolute_path", "inventory_path"]
        for case in cases:
            with self.subTest(case=case):
                self.git("reset", "--hard", self.source_sha, cwd=self.output)
                shutil.rmtree(self.output / "graphify-out", ignore_errors=True)
                result = self.run_wrapper(env={"GRAPHIFY_FAKE_CASE": case})
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_schema_specific_graph_and_manifest_defects_are_blocking(self):
        cases = [
            "graph_root_wrong",
            "node_field_wrong_type",
            "links_wrong_type",
            "manifest_root_wrong",
            "manifest_entry_wrong_type",
            "manifest_symbols_wrong_type",
        ]
        for case in cases:
            with self.subTest(case=case):
                self.git("reset", "--hard", self.source_sha, cwd=self.output)
                shutil.rmtree(self.output / "graphify-out", ignore_errors=True)
                result = self.run_wrapper(env={"GRAPHIFY_FAKE_CASE": case})
                self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("schema mismatch", result.stderr + result.stdout)

    def test_publication_tree_contains_four_artifacts_and_diff_is_allowlisted_subset(self):
        self.assert_wrapper_succeeds()
        for rel in [
            "graphify-out/graph.json",
            "graphify-out/manifest.json",
            "graphify-out/GRAPH_REPORT.md",
            "graphify-out/baseline.json",
        ]:
            self.assertTrue((self.output / rel).is_file(), rel)
        changed = self.changed_paths()
        self.assertTrue(changed)
        self.assertTrue(changed <= {
            "graphify-out/graph.json",
            "graphify-out/manifest.json",
            "graphify-out/GRAPH_REPORT.md",
            "graphify-out/baseline.json",
        })

    def test_secret_scan_and_safe_rollback_preserve_previous_baseline(self):
        self.assert_wrapper_succeeds()
        before = self.graph_snapshot()
        result = self.run_wrapper(env={"GRAPHIFY_FAKE_CASE": "absolute_path"})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.graph_snapshot())

    def test_transaction_rolls_back_previous_baseline_after_post_publication_failure(self):
        self.assert_wrapper_succeeds()
        before = self.graph_snapshot()
        self.commit_output_as_new_s()
        self.write(self.source / "AGENTS.md", "forbidden graph integration\n")
        self.git("add", "AGENTS.md", cwd=self.source)
        self.git("commit", "-m", "introduce forbidden integration", cwd=self.source)
        new_sha = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", new_sha, cwd=self.source)
        self.git("reset", "--hard", new_sha, cwd=self.output)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.graph_snapshot())
        self.assert_no_publication_temp_dirs()

    def test_transaction_restores_absent_baseline_after_post_publication_failure(self):
        self.write(self.source / "AGENTS.md", "forbidden graph integration\n")
        self.git("add", "AGENTS.md", cwd=self.source)
        self.git("commit", "-m", "forbidden integration without baseline", cwd=self.source)
        new_sha = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", new_sha, cwd=self.source)
        self.git("reset", "--hard", new_sha, cwd=self.output)
        result = self.run_wrapper()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.output / "graphify-out").exists())
        self.assert_no_publication_temp_dirs()

    def test_noop_ignores_only_volatile_generated_at_and_leaves_output_unchanged(self):
        self.assert_wrapper_succeeds()
        info_exclude = self.output / ".git" / "info" / "exclude"
        if not info_exclude.exists():
            common_dir = self.git("rev-parse", "--git-common-dir", cwd=self.output).stdout.strip()
            info_exclude = (self.output / common_dir / "info" / "exclude").resolve()
        info_exclude.parent.mkdir(parents=True, exist_ok=True)
        info_exclude.write_text(info_exclude.read_text(encoding="utf-8") + "\ngraphify-out/\n", encoding="utf-8")
        accepted = self.git("rev-parse", "HEAD", cwd=self.output).stdout.strip()
        before = self.graph_snapshot()
        result = self.assert_wrapper_succeeds()
        self.assertIn("No graph publication changes", result.stdout)
        self.assertEqual(before, self.graph_snapshot())
        self.assertEqual("", self.git("status", "--short", cwd=self.output).stdout.strip())
        self.assertEqual(accepted, self.git("rev-parse", "HEAD", cwd=self.output).stdout.strip())

    def test_incremental_preconditions_and_ghost_integrity_are_enforced(self):
        self.assert_wrapper_succeeds()
        self.commit_output_as_new_s()
        self.make_source_commit({"app.py": "def current():\n    return 'changed'\n"}, "source delta")
        before = self.graph_snapshot()
        result = self.run_wrapper(mode="Incremental", env={"GRAPHIFY_FAKE_CASE": "ghost"})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, self.graph_snapshot())

    def test_positive_eligible_incremental_refresh(self):
        self.assert_wrapper_succeeds()
        self.commit_output_as_new_s()
        self.make_source_commit({"app.py": "def current():\n    return 'changed'\n"}, "small compatible source delta")
        result = self.assert_wrapper_succeeds(mode="Incremental")
        self.assertIn("Incremental source range", result.stdout)

    def corrupt_baseline_field(self, field, value):
        baseline_path = self.output / "graphify-out" / "baseline.json"
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if value is None:
            baseline.pop(field, None)
        else:
            baseline[field] = value
        baseline_path.write_text(json.dumps(baseline, sort_keys=True), encoding="utf-8", newline="\n")

    def assert_failed_incremental_preserves_baseline(self, field, value):
        self.assert_wrapper_succeeds()
        self.commit_output_as_new_s()
        self.corrupt_baseline_field(field, value)
        self.git("add", "graphify-out/baseline.json", cwd=self.output)
        self.git("commit", "-m", f"corrupt {field}", cwd=self.output)
        accepted = self.git("rev-parse", "HEAD", cwd=self.output).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", accepted, cwd=self.output)
        self.git("worktree", "remove", "--force", str(self.source))
        self.source = self.root / f"source-{accepted[:8]}"
        self.git("worktree", "add", "--detach", str(self.source), accepted)
        self.make_source_commit({"app.py": "def current():\n    return 'changed'\n"}, "source delta after corrupt policy")
        before = self.graph_snapshot()
        result = self.run_wrapper(mode="Incremental")
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("run FullRebuild", result.stderr + result.stdout)
        self.assertEqual(before, self.graph_snapshot())

    def test_incremental_rejects_policy_identity_mismatches_and_old_baselines(self):
        cases = [
            ("gitattributes_sha256", "bad"),
            ("indexed_source_root_policy", "changed-source-root-policy"),
            ("indexed_source_root_policy_sha256", "bad"),
            ("package_boundary_policy", "changed-package-boundary-policy"),
            ("package_boundary_policy_sha256", "bad"),
            ("graph_schema_contract", "changed-graph-schema"),
            ("manifest_schema_contract", "changed-manifest-schema"),
            ("baseline_metadata_contract", "changed-metadata-contract"),
            ("policy_fingerprint_sha256", "bad"),
            ("policy_fingerprint_sha256", None),
        ]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                self.recreate_repo(include_historical_inputs=True)
                self.assert_failed_incremental_preserves_baseline(field, value)

    def test_incremental_rejects_changed_gitattributes_policy(self):
        self.assert_wrapper_succeeds()
        self.commit_output_as_new_s()
        self.make_source_commit({".gitattributes": "/.graphifyignore text eol=lf\n/graphify-out/graph.json text eol=crlf\n"}, "change graph encoding policy")
        before = self.graph_snapshot()
        result = self.run_wrapper(mode="Incremental")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("run FullRebuild", result.stderr + result.stdout)
        self.assertEqual(before, self.graph_snapshot())

    def test_wrapper_does_not_read_verification_report_or_post_archive_evidence(self):
        self.assert_wrapper_succeeds()


if __name__ == "__main__":
    unittest.main()
