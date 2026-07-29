import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "tools" / "refresh_project_graph.ps1"


class ProjectGraphRefreshWorkflowTests(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
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
elif case == "broken_ref":
    graph = {"nodes": nodes, "links": [{"source": "module_app", "target": "missing", "relation": "calls"}]}
elif case == "zero_counts":
    graph = {"nodes": [], "links": []}
else:
    graph = {"nodes": nodes, "links": links}

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
        shutil.rmtree(self.repo, ignore_errors=True)
        shutil.rmtree(self.source, ignore_errors=True)
        shutil.rmtree(self.output, ignore_errors=True)
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
        before = {
            path.name: path.read_bytes()
            for path in (self.output / "graphify-out").iterdir()
            if path.is_file()
        }
        result = self.run_wrapper(env={"GRAPHIFY_FAKE_CASE": "absolute_path"})
        self.assertNotEqual(result.returncode, 0)
        after = {
            path.name: path.read_bytes()
            for path in (self.output / "graphify-out").iterdir()
            if path.is_file()
        }
        self.assertEqual(before, after)

    def test_incremental_preconditions_and_ghost_integrity_are_enforced(self):
        self.assert_wrapper_succeeds()
        self.git("add", "graphify-out", cwd=self.output)
        self.git("commit", "-m", "accepted graph", cwd=self.output)
        accepted = self.git("rev-parse", "HEAD", cwd=self.output).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", accepted, cwd=self.output)
        self.git("worktree", "remove", "--force", str(self.source))
        self.source = self.root / "source2"
        self.git("worktree", "add", "--detach", str(self.source), accepted)

        self.write(self.source / "app.py", "def current():\n    return 'changed'\n")
        self.git("add", "app.py", cwd=self.source)
        self.git("commit", "-m", "source delta", cwd=self.source)
        delta = self.git("rev-parse", "HEAD", cwd=self.source).stdout.strip()
        self.git("update-ref", "refs/remotes/origin/master", delta, cwd=self.source)
        self.git("reset", "--hard", delta, cwd=self.output)
        result = self.run_wrapper(mode="Incremental", env={"GRAPHIFY_FAKE_CASE": "ghost"})
        self.assertNotEqual(result.returncode, 0)

    def test_wrapper_does_not_read_verification_report_or_post_archive_evidence(self):
        self.assert_wrapper_succeeds()


if __name__ == "__main__":
    unittest.main()
