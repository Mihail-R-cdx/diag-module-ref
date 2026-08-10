import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { TextDecoder } from 'node:util';

const ROOT_SPECS = 'openspec/specs';
const ROOT_SPEC_PATTERN = /^openspec\/specs\/.+\/spec\.md$/;
const utf8 = new TextDecoder('utf-8', { fatal: true });

function git(args, options = {}) {
  return execFileSync('git', args, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], ...options });
}

function fail(message) {
  process.stderr.write(`OpenSpec archive compatibility: ${message}\n`);
  process.exitCode = 1;
}

function rootSpecPaths(command) {
  return command.split(/\r?\n/).filter((item) => ROOT_SPEC_PATTERN.test(item));
}

function normalizeEof(text) {
  const pieces = text.split(/(\r\n|\n|\r)/);
  const lines = [];
  for (let index = 0; index < pieces.length; index += 2) {
    lines.push({ content: pieces[index], ending: pieces[index + 1] ?? '' });
  }

  let lastContent = lines.length - 1;
  while (lastContent >= 0 && /^\s*$/.test(lines[lastContent].content)) {
    lastContent -= 1;
  }
  if (lastContent < 0) {
    throw new Error('selected root specification is empty or whitespace-only');
  }

  const previousEnding = lastContent > 0 ? lines[lastContent - 1].ending : '';
  const ending = lines[lastContent].ending || previousEnding || '\n';
  return `${lines.slice(0, lastContent).map((line) => `${line.content}${line.ending}`).join('')}${lines[lastContent].content}${ending}`;
}

function preflight() {
  const status = git(['status', '--porcelain=v1', '-z', '--untracked-files=all', '--', ROOT_SPECS]);
  if (status.length > 0) {
    fail(`refusing archive because ${ROOT_SPECS}/ has pre-existing tracked, staged, or untracked changes`);
  }
}

function checkUntrackedFile(file) {
  const directory = mkdtempSync(path.join(tmpdir(), 'openspec-empty-baseline-'));
  const baseline = path.join(directory, 'empty');
  try {
    writeFileSync(baseline, '');
    try {
      git(['diff', '--no-index', '--check', '--', baseline, file]);
    } catch (error) {
      const output = `${error.stdout ?? ''}${error.stderr ?? ''}`;
      // --no-index returns 1 for a non-empty clean diff; diagnostics mean whitespace failure.
      const diagnostics = output.split(/\r?\n/).filter((line) => line && !line.startsWith('warning:'));
      if (diagnostics.length) throw new Error(diagnostics.join('\n'));
    }
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

function postflight() {
  const staged = git(['diff', '--cached', '--name-only', '--', ROOT_SPECS]);
  if (staged.trim()) {
    fail(`refusing normalization because upstream staged root-spec output:\n${staged.trim()}`);
    return;
  }

  const modified = rootSpecPaths(git(['diff', '--name-only', '--', ROOT_SPECS]));
  const untracked = rootSpecPaths(git(['ls-files', '--others', '--exclude-standard', '--', ROOT_SPECS]));
  const targets = [...new Set([...modified, ...untracked])];
  const decoded = [];
  try {
    for (const target of targets) {
      const info = statSync(target);
      if (!info.isFile()) throw new Error(`${target} is not a regular file`);
      const text = utf8.decode(readFileSync(target));
      if (!/\S/.test(text)) throw new Error(`${target} is empty or whitespace-only`);
      decoded.push({ target, text });
    }
  } catch (error) {
    fail(String(error.message || error));
    return;
  }

  for (const { target, text } of decoded) {
    const normalized = normalizeEof(text);
    if (normalized !== text) writeFileSync(target, normalized, 'utf8');
  }

  try {
    git(['diff', '--check']);
    git(['diff', '--cached', '--check']);
    for (const target of untracked) checkUntrackedFile(target);
  } catch (error) {
    fail(String(error.stdout || error.stderr || error.message || error));
  }
}

const action = process.argv[2];
if (action === 'preflight') preflight();
else if (action === 'postflight') postflight();
else fail('expected preflight or postflight action');
