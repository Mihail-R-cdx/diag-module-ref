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


class LocalProjectGraphHelperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.fake_bin = self.root / "fake-bin"
        self.fake_bin.mkdir()
        self.fake_args = self.root / "graphify-args.jsonl"
        self.fake_script = self.root / "fake_graphify.py"
        self.fake_script.write_text(
            textwrap.dedent(
                r"""
                import json
                import os
                import sys
                from pathlib import Path

                args = sys.argv[1:]
                if args == ["--version"]:
                    print(f"graphify {os.environ.get('GRAPHIFY_FAKE_VERSION', '0.9.26')}")
                    raise SystemExit(0)

                args_file = os.environ["GRAPHIFY_FAKE_ARGS_FILE"]
                with open(args_file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(args) + "\n")

                source = Path(args[1]) if len(args) > 1 and args[0] == "extract" else Path.cwd()
                output = Path(args[args.index("--output") + 1]) if "--output" in args else source / "graphify-out"

                if os.environ.get("GRAPHIFY_FAKE_MUTATE_TRACKED"):
                    (source / "tracked.py").write_text("mutated by fake graphify\n", encoding="utf-8")

                if os.environ.get("GRAPHIFY_FAKE_FAIL"):
                    raise SystemExit(int(os.environ.get("GRAPHIFY_FAKE_FAIL", "7")))

                output.mkdir(parents=True, exist_ok=True)
                unsafe = os.environ.get("GRAPHIFY_FAKE_UNSAFE_TEXT", "")
                graph = {
                    "nodes": [{"id": "tracked", "source_file": "tracked.py", "note": unsafe}],
                    "edges": [],
                }
                (output / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
                (output / "manifest.json").write_text(json.dumps({"tracked.py": {"kind": "code"}}), encoding="utf-8")
                (output / "GRAPH_REPORT.md").write_text("# Local graph\n", encoding="utf-8")
                if os.environ.get("GRAPHIFY_FAKE_HTML"):
                    (output / "graph.html").write_text("<html></html>\n", encoding="utf-8")
                raise SystemExit(0)
                """
            ).strip()
            + "\n",
            encoding="utf-8",
        )
        self.fake_exe = self.fake_bin / "graphify.cmd"
        self.fake_exe.write_text(
            '@echo off\r\n"%PYTHON%" "%FAKE_GRAPHIFY_SCRIPT%" %*\r\nexit /b %ERRORLEVEL%\r\n',
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def make_repo(self, name="repo"):
        repo = self.root / name
        repo.mkdir()
        (repo / "tools").mkdir()
        shutil.copy2(WRAPPER, repo / "tools" / "refresh_project_graph.ps1")
        (repo / ".gitignore").write_text(
            "/.graphify-local/\n/graphify-out/\n__pycache__/\n*.py[cod]\n",
            encoding="utf-8",
        )
        (repo / ".graphifyignore").write_text(
            "\n".join(
                [
                    ".git/",
                    ".agents/",
                    ".codex/",
                    ".worktrees/",
                    ".graphify-local/",
                    "graphify-out/",
                    "node_modules/",
                    ".venv/",
                    "venv/",
                    "__pycache__/",
                    "openspec/changes/archive/",
                    "credentials.local.json",
                    "credentials.local*.json",
                    "equipment_inventory.local.json",
                    ".env",
                    ".env.*",
                    "*.pem",
                    "*.key",
                    "*.pfx",
                    "*.p12",
                    "cookies.txt",
                    "session.txt",
                    "session.json",
                    "**/call_records*.json",
                    "*.xlsx",
                    "*.xls",
                    "logs/",
                    "**/output/",
                    "**/outputs/",
                    "**/generated/",
                    "**/artifacts/",
                    "transfer/",
                    "raw/",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (repo / "tracked.py").write_text("print('stable')\n", encoding="utf-8")
        subprocess.run(["git", "init"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=repo, check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo, check=True)
        subprocess.run(["git", "add", "."], cwd=repo, check=True)
        subprocess.run(["git", "commit", "-m", "initial"], cwd=repo, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return repo

    def env(self, **overrides):
        env = os.environ.copy()
        env.update(
            {
                "PATH": str(self.fake_bin) + os.pathsep + env.get("PATH", ""),
                "PYTHON": sys.executable,
                "FAKE_GRAPHIFY_SCRIPT": str(self.fake_script),
                "GRAPHIFY_FAKE_ARGS_FILE": str(self.fake_args),
            }
        )
        env.update({key: str(value) for key, value in overrides.items()})
        return env

    def run_wrapper(self, repo, *args, env=None):
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo / "tools" / "refresh_project_graph.ps1"),
            *args,
        ]
        return subprocess.run(
            command,
            cwd=repo,
            env=env or self.env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def git(self, repo, *args):
        return subprocess.run(["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)

    def test_wrapper_uses_pinned_version_and_code_only_no_viz(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("graphifyy==0.9.26", result.stdout)
        self.assertIn("Graphify version: 0.9.26", result.stdout)
        args = [json.loads(line) for line in self.fake_args.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(args), 1)
        self.assertIn("--code-only", args[0])
        self.assertIn("--no-viz", args[0])
        self.assertIn("--ignore-file", args[0])

    def test_wrong_graphify_version_fails_nonzero(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_VERSION="0.9.25"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected 0.9.26", result.stderr)

    def test_default_generation_writes_only_to_graphify_local(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((repo / ".graphify-local" / "graph.json").is_file())
        self.assertFalse((repo / "graphify-out").exists())
        self.assertEqual(self.git(repo, "status", "--short", "--untracked-files=all").stdout, "")

    def test_explicit_source_writes_only_to_that_source_repository(self):
        invocation = self.make_repo("invocation")
        source = self.make_repo("source")
        result = self.run_wrapper(invocation, "-SourceRoot", str(source))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((source / ".graphify-local" / "graph.json").is_file())
        self.assertFalse((invocation / ".graphify-local" / "graph.json").exists())
        self.assertFalse((source / "graphify-out").exists())

    def test_no_output_root_or_publication_target_interface_remains(self):
        repo = self.make_repo()
        for args in (("-OutputRoot", str(repo)), ("-TargetBranch", "master")):
            with self.subTest(args=args):
                result = self.run_wrapper(repo, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("parameter", (result.stderr + result.stdout).lower())

    def test_retired_publication_parameters_and_modes_are_rejected(self):
        repo = self.make_repo()
        retired_invocations = (
            ("-Mode", "Incremental"),
            ("-BaselineStage", "Final"),
            ("-SourceRef", "origin/master"),
            ("-PostArchiveValidationEvidence", "openspec/validation/evidence.json"),
        )
        for args in retired_invocations:
            with self.subTest(args=args):
                result = self.run_wrapper(repo, *args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("parameter", (result.stderr + result.stdout).lower())

    def test_successful_generation_does_not_mutate_tracked_files(self):
        repo = self.make_repo()
        before = self.git(repo, "rev-parse", "HEAD").stdout.strip()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((repo / "tracked.py").read_text(encoding="utf-8"), "print('stable')\n")
        self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout.strip(), before)
        self.assertEqual(self.git(repo, "status", "--short").stdout, "")

    def test_failed_generation_does_not_mutate_tracked_files(self):
        repo = self.make_repo()
        result = self.run_wrapper(
            repo,
            env=self.env(GRAPHIFY_FAKE_MUTATE_TRACKED="1", GRAPHIFY_FAKE_FAIL="9"),
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((repo / "tracked.py").read_text(encoding="utf-8"), "print('stable')\n")
        self.assertEqual(self.git(repo, "status", "--short").stdout, "")

    def test_graphify_local_and_graphify_out_are_ignored_and_untracked(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.graphify-local/", gitignore)
        self.assertIn("/graphify-out/", gitignore)
        remaining = subprocess.run(
            ["git", "ls-files", "graphify-out"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(remaining, "")

    def test_graphifyignore_excludes_local_output_and_sensitive_paths(self):
        ignore = (REPO_ROOT / ".graphifyignore").read_text(encoding="utf-8")
        for expected in (
            ".git/",
            ".agents/",
            ".codex/",
            ".worktrees/",
            ".graphify-local/",
            "graphify-out/",
            "node_modules/",
            "__pycache__/",
            "openspec/changes/archive/",
            "credentials.local*.json",
            "equipment_inventory.local.json",
            ".env",
            "*.pem",
            "*.key",
            "*.xlsx",
            "cookies.txt",
            "session.json",
            "**/call_records*.json",
            "logs/",
            "transfer/",
            "raw/",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, ignore)

    def test_html_visualization_is_not_accepted_or_committed(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_HTML="1"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTML visualization", result.stderr)
        tracked_local = self.git(repo, "ls-files", ".graphify-local").stdout.strip()
        self.assertEqual(tracked_local, "")

    def test_secret_like_output_is_rejected_without_echoing_secret(self):
        repo = self.make_repo()
        secret = "password=supersecretvalue12345"
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_UNSAFE_TEXT=secret))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsafe Graphify output rejected", result.stderr)
        self.assertNotIn("supersecretvalue12345", result.stderr + result.stdout)

    def test_user_specific_absolute_paths_are_rejected(self):
        repo = self.make_repo()
        unsafe_values = (
            r"C:\Users\Mih\repo\tracked.py",
            r"\\server\share\repo\tracked.py",
            "/home/mih/repo/tracked.py",
        )
        for value in unsafe_values:
            with self.subTest(value=value):
                result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_UNSAFE_TEXT=value))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("Unsafe Graphify output rejected", result.stderr)

    def test_wrapper_never_creates_publication_state(self):
        repo = self.make_repo()
        before_head = self.git(repo, "rev-parse", "HEAD").stdout.strip()
        before_branches = self.git(repo, "branch", "--format=%(refname:short)").stdout
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(repo, "rev-parse", "HEAD").stdout.strip(), before_head)
        self.assertEqual(self.git(repo, "branch", "--format=%(refname:short)").stdout, before_branches)
        self.assertFalse((repo / ".git" / "worktrees").exists())
        self.assertFalse((repo / "openspec" / "validation").exists())
        self.assertNotIn("push", self.fake_args.read_text(encoding="utf-8"))
        self.assertNotIn("archive", self.fake_args.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
