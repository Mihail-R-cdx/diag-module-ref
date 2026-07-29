import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "tools" / "refresh_project_graph.ps1"
PYTHON = r"C:\Users\Mih\AppData\Local\Programs\Python\Python312\python.exe"


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
                import time
                from pathlib import Path

                args = sys.argv[1:]
                if args == ["--version"]:
                    print(f"graphify {os.environ.get('GRAPHIFY_FAKE_VERSION', '0.9.26')}")
                    raise SystemExit(0)
                if args == ["extract", "--help"]:
                    print("Usage: graphify extract <path> [--out DIR|--output DIR] [--code-only] [--no-cluster]")
                    raise SystemExit(0)

                args_file = os.environ["GRAPHIFY_FAKE_ARGS_FILE"]
                with open(args_file, "a", encoding="utf-8") as handle:
                    handle.write(json.dumps(args) + "\n")

                if len(args) != 6 or args[0] != "extract":
                    print("unsupported graphify invocation", file=sys.stderr)
                    raise SystemExit(64)
                source = Path(args[1])
                expected_tail = ["--code-only", "--no-cluster", "--out"]
                if args[2:5] != expected_tail:
                    print(f"unsupported graphify arguments: {args}", file=sys.stderr)
                    raise SystemExit(64)
                output_root = Path(args[5])

                started = os.environ.get("GRAPHIFY_FAKE_STARTED_FILE")
                if started:
                    Path(started).write_text("started\n", encoding="utf-8")
                continue_file = os.environ.get("GRAPHIFY_FAKE_CONTINUE_FILE")
                if continue_file:
                    deadline = time.time() + 30
                    while not Path(continue_file).exists():
                        if time.time() > deadline:
                            print("timed out waiting for continue marker", file=sys.stderr)
                            raise SystemExit(65)
                        time.sleep(0.05)

                if os.environ.get("GRAPHIFY_FAKE_MUTATE_SOURCE"):
                    (source / "tracked.py").write_text("mutated disposable source\n", encoding="utf-8")

                if os.environ.get("GRAPHIFY_FAKE_FAIL_BEFORE_OUTPUT"):
                    raise SystemExit(int(os.environ.get("GRAPHIFY_FAKE_FAIL_BEFORE_OUTPUT", "7")))

                graph_dir = output_root / "graphify-out"
                graph_dir.mkdir(parents=True, exist_ok=True)
                (graph_dir / ".graphify_root").write_text(str(source), encoding="utf-8")
                cache_dir = graph_dir / "cache"
                cache_dir.mkdir(parents=True, exist_ok=True)
                (cache_dir / "stat-index.json").write_text(json.dumps({"root": str(source)}), encoding="utf-8")
                unsafe = os.environ.get("GRAPHIFY_FAKE_UNSAFE_TEXT", "")
                marker = os.environ.get("GRAPHIFY_FAKE_MARKER", "current")
                tracked_text = ""
                tracked_path = source / "tracked.py"
                if tracked_path.exists():
                    tracked_text = tracked_path.read_text(encoding="utf-8")
                graph = {
                    "nodes": [
                        {
                            "id": "tracked",
                            "source_file": "tracked.py",
                            "marker": marker,
                            "note": unsafe,
                            "tracked_text": tracked_text,
                        }
                    ],
                    "edges": [],
                }
                (graph_dir / "graph.json").write_text(json.dumps(graph), encoding="utf-8")
                (graph_dir / "manifest.json").write_text(json.dumps({"tracked.py": {"kind": "code"}}), encoding="utf-8")
                if os.environ.get("GRAPHIFY_FAKE_HTML"):
                    (graph_dir / "graph.html").write_text("<html></html>\n", encoding="utf-8")
                if os.environ.get("GRAPHIFY_FAKE_FAIL_AFTER_OUTPUT"):
                    raise SystemExit(int(os.environ.get("GRAPHIFY_FAKE_FAIL_AFTER_OUTPUT", "8")))
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
                "PYTHON": PYTHON if Path(PYTHON).exists() else sys.executable,
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

    def start_wrapper(self, repo, *args, env=None):
        command = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(repo / "tools" / "refresh_project_graph.ps1"),
            *args,
        ]
        return subprocess.Popen(
            command,
            cwd=repo,
            env=env or self.env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def git(self, repo, *args, check=True):
        return subprocess.run(["git", *args], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=check)

    def accepted_graph(self, repo):
        return repo / ".graphify-local" / "accepted" / "graphify-out" / "graph.json"

    def local_files(self, repo):
        root = repo / ".graphify-local"
        if not root.exists():
            return []
        return [path for path in root.rglob("*") if path.is_file()]

    def staging_dirs(self, repo):
        root = repo / ".graphify-local"
        if not root.exists():
            return []
        return [path for path in root.iterdir() if path.is_dir() and path.name.startswith(".staging-")]

    def wait_for_file(self, path):
        deadline = time.time() + 30
        while not path.exists():
            if time.time() > deadline:
                self.fail(f"timed out waiting for {path}")
            time.sleep(0.05)

    def test_actual_expected_cli_arguments_match_pinned_contract(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        args = [json.loads(line) for line in self.fake_args.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(args), 1)
        invocation = args[0]
        self.assertEqual(invocation[0], "extract")
        self.assertEqual(invocation[2:], ["--code-only", "--no-cluster", "--out", invocation[5]])
        self.assertIn(".graphify-local", invocation[1])
        self.assertIn(".staging-", invocation[1])
        self.assertTrue(invocation[1].endswith("source"))
        self.assertIn(".graphify-local", invocation[5])
        self.assertTrue(invocation[5].endswith("output"))
        self.assertNotIn("--ignore-file", invocation)
        self.assertNotIn("--no-viz", invocation)

    def test_fake_cli_rejects_unknown_arguments(self):
        result = subprocess.run(
            [str(self.fake_exe), "extract", "repo", "--code-only", "--bad", "--out", "out"],
            env=self.env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unsupported", result.stderr)

    def test_wrong_graphify_version_fails_nonzero(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_VERSION="0.9.25"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Expected 0.9.26", result.stderr)

    def test_real_output_nesting_is_promoted_to_accepted_output(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.accepted_graph(repo).is_file())
        self.assertFalse((repo / ".graphify-local" / "accepted" / "graphify-out" / ".graphify_root").exists())
        self.assertFalse((repo / ".graphify-local" / "accepted" / "graphify-out" / "cache").exists())
        self.assertFalse((repo / "graphify-out").exists())
        self.assertEqual(self.git(repo, "status", "--short", "--untracked-files=all").stdout, "")

    def test_explicit_source_writes_only_to_that_source_repository(self):
        invocation = self.make_repo("invocation")
        source = self.make_repo("source")
        result = self.run_wrapper(invocation, "-SourceRoot", str(source))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(self.accepted_graph(source).is_file())
        self.assertFalse(self.accepted_graph(invocation).exists())
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

    def test_failed_generation_preserves_previous_accepted_output(self):
        repo = self.make_repo()
        first = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_MARKER="accepted-v1"))
        self.assertEqual(first.returncode, 0, first.stderr)
        before = self.accepted_graph(repo).read_text(encoding="utf-8")

        second = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_UNSAFE_TEXT="password=supersecretvalue12345"))

        self.assertNotEqual(second.returncode, 0)
        self.assertEqual(self.accepted_graph(repo).read_text(encoding="utf-8"), before)
        self.assertIn("accepted-v1", self.accepted_graph(repo).read_text(encoding="utf-8"))

    def test_unsafe_secret_candidate_is_removed_without_echoing_secret(self):
        repo = self.make_repo()
        secret = "password=supersecretvalue12345"
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_UNSAFE_TEXT=secret))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsafe Graphify output rejected", result.stderr)
        self.assertNotIn("supersecretvalue12345", result.stderr + result.stdout)
        self.assertFalse(any(secret in path.read_text(encoding="utf-8", errors="ignore") for path in self.local_files(repo)))

    def test_html_candidate_is_removed(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_HTML="1"))

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("HTML visualization", result.stderr)
        self.assertFalse(any(path.suffix.lower() in {".html", ".htm", ".xhtml"} for path in self.local_files(repo)))

    def test_absolute_path_candidates_are_removed(self):
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
                self.assertFalse(any(value in path.read_text(encoding="utf-8", errors="ignore") for path in self.local_files(repo)))

    def test_staging_and_candidate_are_removed_after_success(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.staging_dirs(repo), [])
        self.assertTrue(self.accepted_graph(repo).is_file())

    def test_staging_and_candidate_are_removed_after_failure(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_FAIL_AFTER_OUTPUT="9"))

        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.staging_dirs(repo), [])
        self.assertFalse(self.accepted_graph(repo).exists())

    def test_graphify_mutation_of_disposable_source_does_not_touch_real_checkout(self):
        repo = self.make_repo()
        result = self.run_wrapper(repo, env=self.env(GRAPHIFY_FAKE_MUTATE_SOURCE="1"))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((repo / "tracked.py").read_text(encoding="utf-8"), "print('stable')\n")
        self.assertEqual(self.git(repo, "status", "--short").stdout, "")

    def test_concurrent_user_edit_real_tracked_file_is_not_lost(self):
        repo = self.make_repo()
        started = self.root / "started.txt"
        keep_going = self.root / "continue.txt"
        proc = self.start_wrapper(
            repo,
            env=self.env(GRAPHIFY_FAKE_STARTED_FILE=started, GRAPHIFY_FAKE_CONTINUE_FILE=keep_going),
        )
        self.wait_for_file(started)
        (repo / "tracked.py").write_text("print('user edit while graphify runs')\n", encoding="utf-8")
        keep_going.write_text("continue\n", encoding="utf-8")
        stdout, stderr = proc.communicate(timeout=30)

        self.assertEqual(proc.returncode, 0, stderr)
        self.assertIn("Accepted local output", stdout)
        self.assertEqual((repo / "tracked.py").read_text(encoding="utf-8"), "print('user edit while graphify runs')\n")
        self.assertEqual(self.git(repo, "status", "--short").stdout, " M tracked.py\n")

    def test_deleted_tracked_working_file_is_not_restored(self):
        repo = self.make_repo()
        (repo / "tracked.py").unlink()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((repo / "tracked.py").exists())
        self.assertEqual(self.git(repo, "status", "--short").stdout, " D tracked.py\n")

    def test_existing_dirty_tracked_worktree_remains_byte_identical(self):
        repo = self.make_repo()
        dirty = "print('dirty working bytes')\n"
        (repo / "tracked.py").write_text(dirty, encoding="utf-8")
        before = (repo / "tracked.py").read_bytes()
        result = self.run_wrapper(repo)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((repo / "tracked.py").read_bytes(), before)
        self.assertEqual((repo / "tracked.py").read_text(encoding="utf-8"), dirty)
        self.assertEqual(self.git(repo, "status", "--short").stdout, " M tracked.py\n")

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

    def test_graphify_local_and_graphify_out_are_ignored_and_untracked(self):
        gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("/.graphify-local/", gitignore)
        self.assertIn("/graphify-out/", gitignore)
        tracked_legacy = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", "graphify-out"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        tracked_local = subprocess.run(
            ["git", "ls-files", ".graphify-local"],
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(tracked_legacy, "")
        self.assertEqual(tracked_local, "")

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


if __name__ == "__main__":
    unittest.main()
