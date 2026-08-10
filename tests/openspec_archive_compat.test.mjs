import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { cpSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import test, { afterEach } from 'node:test';
import { fileURLToPath } from 'node:url';

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const helper = path.join(repoRoot, 'tools', 'openspec_archive_compat.mjs');
const wrapper = path.join(repoRoot, 'openspec.cmd');
const temporaryRepos = new Set();

afterEach(() => {
  for (const directory of temporaryRepos) rmSync(directory, { recursive: true, force: true });
  temporaryRepos.clear();
});

function run(command, args, cwd, options = {}) {
  return spawnSync(command, args, { cwd, encoding: 'utf8', ...options });
}

function makeRepo() {
  const directory = mkdtempSync(path.join(tmpdir(), 'openspec-archive-compat-'));
  temporaryRepos.add(directory);
  execFileSync('git', ['init', '-q'], { cwd: directory });
  execFileSync('git', ['config', 'user.email', 'test@example.invalid'], { cwd: directory });
  execFileSync('git', ['config', 'user.name', 'Test'], { cwd: directory });
  mkdirSync(path.join(directory, 'openspec', 'specs', 'capability'), { recursive: true });
  writeFileSync(path.join(directory, 'openspec', 'specs', 'capability', 'spec.md'), '# Capability\n\n## Requirements\n\n### Requirement: Base\n\nBase text\n');
  writeFileSync(path.join(directory, 'unrelated.md'), 'unchanged\n');
  execFileSync('git', ['add', '.'], { cwd: directory });
  execFileSync('git', ['commit', '-qm', 'baseline'], { cwd: directory });
  return directory;
}

function postflight(directory) {
  return run(process.execPath, [helper, 'postflight'], directory);
}

test('normalizes only terminal blank lines and retains trailing content whitespace', () => {
  const directory = makeRepo();
  const spec = path.join(directory, 'openspec/specs/capability/spec.md');
  writeFileSync(spec, 'content   \n\n \t\n');
  assert.equal(postflight(directory).status, 1, 'trailing content whitespace remains detectable');
  assert.equal(readFileSync(spec, 'utf8'), 'content   \n');
});

test('preserves LF, CRLF, internal blank lines, and is idempotent', () => {
  for (const [name, input, expected] of [
    ['lf', 'first\n\nsecond\n\n\n', 'first\n\nsecond\n'],
    ['crlf', 'first\r\n\r\nsecond\r\n \t\r\n', 'first\r\n\r\nsecond\r\n'],
    ['no-newline', 'content', 'content\n'],
    ['one-newline', 'content\n', 'content\n'],
  ]) {
    const directory = makeRepo();
    const spec = path.join(directory, 'openspec/specs/capability/spec.md');
    writeFileSync(spec, input);
    assert.equal(postflight(directory).status, 0, name);
    assert.equal(readFileSync(spec, 'utf8'), expected, name);
    assert.equal(postflight(directory).status, 0, `${name} rerun`);
    assert.equal(readFileSync(spec, 'utf8'), expected, `${name} idempotence`);
  }
});

test('does not rewrite unrelated files or archived change artifacts', () => {
  const directory = makeRepo();
  const spec = path.join(directory, 'openspec/specs/capability/spec.md');
  const archived = path.join(directory, 'openspec/changes/archive/example.md');
  mkdirSync(path.dirname(archived), { recursive: true });
  writeFileSync(spec, 'content\n\n');
  writeFileSync(archived, 'archive\n\n');
  writeFileSync(path.join(directory, 'unrelated.md'), 'unrelated\n\n');
  assert.equal(postflight(directory).status, 1, 'repository-wide diff check still rejects unrelated whitespace');
  assert.equal(readFileSync(spec, 'utf8'), 'content\n');
  assert.equal(readFileSync(archived, 'utf8'), 'archive\n\n');
  assert.equal(readFileSync(path.join(directory, 'unrelated.md'), 'utf8'), 'unrelated\n\n');
});

test('excludes deleted root specs from normalization targets', () => {
  const directory = makeRepo();
  const removed = path.join(directory, 'openspec/specs/old-capability/spec.md');
  mkdirSync(path.dirname(removed), { recursive: true });
  writeFileSync(removed, 'old\n');
  execFileSync('git', ['add', '.'], { cwd: directory });
  execFileSync('git', ['commit', '-qm', 'add old capability'], { cwd: directory });
  rmSync(removed);
  assert.equal(postflight(directory).status, 0);
  assert.equal(run('cmd.exe', ['/d', '/c', 'if', 'exist', removed, '(exit 1)', 'else', '(exit 0)'], directory).status, 0);
  assert.match(execFileSync('git', ['status', '--porcelain'], { cwd: directory, encoding: 'utf8' }), /D  openspec\/specs\/old-capability\/spec.md| D openspec\/specs\/old-capability\/spec.md/);
});

test('preserves a UTF-8 BOM and all semantic bytes before the terminal region', () => {
  const directory = makeRepo();
  const spec = path.join(directory, 'openspec/specs/capability/spec.md');
  const prefix = Buffer.from('\ufeff# Кириллица\n\nСмысл сохраняется   ', 'utf8');
  writeFileSync(spec, Buffer.concat([prefix, Buffer.from('\n\n', 'utf8')]));
  assert.equal(postflight(directory).status, 1);
  const output = readFileSync(spec);
  assert.deepEqual(output.subarray(0, 3), Buffer.from([0xef, 0xbb, 0xbf]));
  assert.deepEqual(output.subarray(3, output.length - 1), prefix.subarray(3));
  assert.equal(output.at(-1), 10);
});

test('preflight rejects dirty tracked, staged, and untracked root paths', () => {
  for (const mode of ['modified', 'staged', 'untracked']) {
    const directory = makeRepo();
    const spec = path.join(directory, 'openspec/specs/capability/spec.md');
    if (mode === 'untracked') writeFileSync(path.join(directory, 'openspec/specs/new.md'), 'new\n');
    else {
      writeFileSync(spec, 'dirty\n');
      if (mode === 'staged') execFileSync('git', ['add', spec], { cwd: directory });
    }
    assert.equal(run(process.execPath, [helper, 'preflight'], directory).status, 1, mode);
  }
});

test('empty and whitespace-only selected specs fail closed without rewriting bytes', () => {
  for (const contents of ['', ' \t\r\n']) {
    const directory = makeRepo();
    const spec = path.join(directory, 'openspec/specs/capability/spec.md');
    writeFileSync(spec, contents);
    assert.equal(postflight(directory).status, 1);
    assert.equal(readFileSync(spec, 'utf8'), contents);
  }
});

test('staged root output fails closed and leaves index and bytes untouched', () => {
  const directory = makeRepo();
  const spec = path.join(directory, 'openspec/specs/capability/spec.md');
  writeFileSync(spec, 'staged\n\n');
  execFileSync('git', ['add', spec], { cwd: directory });
  const indexBefore = execFileSync('git', ['diff', '--cached', '--', spec], { cwd: directory, encoding: 'utf8' });
  assert.equal(postflight(directory).status, 1);
  assert.equal(readFileSync(spec, 'utf8'), 'staged\n\n');
  assert.equal(execFileSync('git', ['diff', '--cached', '--', spec], { cwd: directory, encoding: 'utf8' }), indexBefore);
});

test('clean new untracked root spec passes, remains untracked, and bad whitespace fails', () => {
  for (const [contents, status] of [['clean\n\n', 0], ['bad   \n\n', 1]]) {
    const directory = makeRepo();
    const spec = path.join(directory, 'openspec/specs/new-capability/spec.md');
    mkdirSync(path.dirname(spec), { recursive: true });
    writeFileSync(spec, contents);
    assert.equal(postflight(directory).status, status);
    assert.match(execFileSync('git', ['status', '--porcelain'], { cwd: directory, encoding: 'utf8' }), /\?\? openspec\/specs\/new-capability\//);
    assert.equal(execFileSync('git', ['diff', '--cached', '--name-only'], { cwd: directory, encoding: 'utf8' }), '');
  }
});

test('wrapper preserves non-archive arguments, output, and upstream exit code', () => {
  const directory = makeRepo();
  mkdirSync(path.join(directory, 'node_modules/.bin'), { recursive: true });
  mkdirSync(path.join(directory, 'tools'), { recursive: true });
  cpSync(wrapper, path.join(directory, 'openspec.cmd'));
  cpSync(helper, path.join(directory, 'tools/openspec_archive_compat.mjs'));
  writeFileSync(path.join(directory, 'node_modules/.bin/openspec.cmd'), '@echo off\necho OUT:%*\necho ERR:%* 1>&2\nexit /b 7\n');
  const result = run('cmd.exe', ['/d', '/c', 'openspec.cmd', 'validate', 'quoted value'], directory);
  assert.equal(result.status, 7);
  assert.match(result.stdout, /OUT:validate "quoted value"/);
  assert.match(result.stderr, /ERR:validate "quoted value"/);
});

test('wrapper archive runs preflight, preserves upstream output and args, then normalizes successful output', () => {
  const directory = makeRepo();
  const spec = path.join(directory, 'openspec/specs/capability/spec.md');
  mkdirSync(path.join(directory, 'node_modules/.bin'), { recursive: true });
  mkdirSync(path.join(directory, 'tools'), { recursive: true });
  cpSync(wrapper, path.join(directory, 'openspec.cmd'));
  cpSync(helper, path.join(directory, 'tools/openspec_archive_compat.mjs'));
  writeFileSync(path.join(directory, 'node_modules/.bin/openspec.cmd'), '@echo off\necho UP:%*\necho UPERR:%* 1>&2\n> upstream_args.txt echo %*\n> openspec\\specs\\capability\\spec.md echo normalized target\n>> openspec\\specs\\capability\\spec.md echo.\nexit /b 0\n');
  const result = run('cmd.exe', ['/d', '/c', 'openspec.cmd', 'archive', 'synthetic', '--yes'], directory);
  assert.equal(result.status, 0);
  assert.match(result.stdout, /UP:archive synthetic --yes/);
  assert.match(result.stderr, /UPERR:archive synthetic --yes/);
  assert.equal(readFileSync(spec, 'utf8'), 'normalized target\r\n');
  assert.equal(readFileSync(path.join(directory, 'unrelated.md'), 'utf8'), 'unchanged\n');
  assert.equal(execFileSync('git', ['diff', '--cached', '--name-only'], { cwd: directory, encoding: 'utf8' }), '');
});

test('failed upstream archive is not postprocessed', () => {
  const directory = makeRepo();
  mkdirSync(path.join(directory, 'node_modules/.bin'), { recursive: true });
  mkdirSync(path.join(directory, 'tools'), { recursive: true });
  cpSync(wrapper, path.join(directory, 'openspec.cmd'));
  cpSync(helper, path.join(directory, 'tools/openspec_archive_compat.mjs'));
  writeFileSync(path.join(directory, 'node_modules/.bin/openspec.cmd'), '@echo off\n> openspec\\specs\\capability\\spec.md echo partial\nexit /b 9\n');
  const result = run('cmd.exe', ['/d', '/c', 'openspec.cmd', 'archive', 'synthetic', '--yes'], directory);
  assert.equal(result.status, 9);
  assert.equal(readFileSync(path.join(directory, 'openspec/specs/capability/spec.md'), 'utf8'), 'partial\r\n');
});
