import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectAndroidMetroAudit, sourceMatchesAffectedNode } from './verify-android-source-audit.mjs';

const benignSources = [
  ...Array.from({ length: 105 }, (_, i) => '../../node_modules/react-native/dist/file' + i + '.js'),
  '../../node_modules/expo-router/entry.js',
  '../../app/index.tsx',
];
function sourceMaps(additional = []) {
  return [{ filename: 'android-entry.map', raw: JSON.stringify({
    version: 3, sources: [...benignSources, ...additional],
  }) }];
}
function audit(nodes) {
  return { vulnerabilities: { jest: { severity: 'moderate', nodes } } };
}

test('passes source-map evidence with visible Metro modules and no vulnerable node', () => {
  const result = inspectAndroidMetroAudit(audit(['node_modules/jest']), sourceMaps(), 'candidate-sha');
  assert.equal(result.totalDistinctSources, 107);
  assert.equal(result.npmAdvisoryPackageNames, 1);
  assert.equal(result.affectedNodePaths, 1);
  assert.equal(result.matchedModulePaths, 0);
  assert.equal(result.sourceCommit, 'candidate-sha');
  assert.match(result.policy, /NOT_NPM_AUDIT_OR_APK_RELEASE_WAIVER/);
  assert.equal(result.mapDigests[0].sha256.length, 64);
});

test('detects vulnerabilities in Metro sources without swallowing failures', () => {
  const result = inspectAndroidMetroAudit(audit(['node_modules/jest']),
    sourceMaps(['../../node_modules/jest/index.js']));
  assert.equal(result.matchedModulePaths, 1);
  assert.equal(result.matches[0].affectedNode, 'node_modules/jest');
});

test('matches exact path segments, not unrelated package name prefixes', () => {
  assert.equal(sourceMatchesAffectedNode('../../node_modules/jester/index.js', 'node_modules/jest'), false);
  assert.equal(sourceMatchesAffectedNode('../../node_modules/jest/index.js', 'node_modules/jest'), true);
  assert.equal(sourceMatchesAffectedNode('../../node_modules/@jest/core/index.js', 'node_modules/@jest/core'), true);
  assert.equal(sourceMatchesAffectedNode('../../node_modules/jest-core/index.js', 'node_modules/jest'), false);
});

test('rejects missing audit nodes, source maps and non-canonical paths', () => {
  assert.throws(() => inspectAndroidMetroAudit({}, sourceMaps()), /audit JSON/);
  assert.throws(() => inspectAndroidMetroAudit(audit(['node_modules/jest']), []), /No Metro source maps/);
  assert.throws(() => inspectAndroidMetroAudit(audit(['../escape']), sourceMaps()), /Unsafe npm advisory/);
  assert.throws(() => inspectAndroidMetroAudit(audit(['node_modules/jest/../other']), sourceMaps()), /Unsafe npm advisory/);
  assert.throws(() => inspectAndroidMetroAudit({ vulnerabilities: { jest: { nodes: [] } } },
    sourceMaps()), /Incomplete npm advisory/);
});

test('rejects opaque source maps with no verifiable Expo/Metro node paths', () => {
  const opaque = [{ filename: 'opaque.map', raw: JSON.stringify({ sources: Array.from({ length: 105 }, (_, i) => 'opaque' + i) }) }];
  assert.throws(() => inspectAndroidMetroAudit(audit(['node_modules/jest']), opaque), /expected visible Expo Router/);
});
