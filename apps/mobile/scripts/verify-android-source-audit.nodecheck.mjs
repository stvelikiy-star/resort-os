import { test } from 'node:test';
import assert from 'node:assert/strict';
import { inspectAndroidMetroAudit, sourceMatchesAffectedNode, classifyAuditPackages } from './verify-android-source-audit.mjs';

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

// --- direct vs propagated advisories (real npm audit shape: `via`) ---
const adv = (name) => ({ name, range: '<=1.0.0', url: 'https://github.com/advisories/GHSA-test-' + name });
const chain = () => ({
  deepmerge: { severity: 'low', via: [adv('deepmerge')], nodes: ['node_modules/deepmerge'] },
  'jest-config': { severity: 'low', via: ['deepmerge'], nodes: ['node_modules/jest-config'] },
  jest: { severity: 'low', via: ['jest-config'], nodes: ['node_modules/jest'] },
  'expo-router': { severity: 'low', via: ['jest'], nodes: ['node_modules/expo-router'] },
});

test('classifies the advisory source as direct and its dependents as propagated with roots', () => {
  const c = classifyAuditPackages(chain());
  assert.deepEqual(c.direct, [{ name: 'deepmerge', kind: 'direct' }]);
  assert.deepEqual(c.propagated.map(p => p.name).sort(), ['expo-router', 'jest', 'jest-config']);
  assert.ok(c.propagated.every(p => p.roots.length === 1 && p.roots[0] === 'deepmerge'));
});

test('a shipped dependent of a vulnerable test-only package does NOT fail while the vulnerable module is absent', () => {
  const r = inspectAndroidMetroAudit({ vulnerabilities: chain() }, sourceMaps(), 'sha');
  assert.equal(r.matchedModulePaths, 0);
  assert.equal(r.directlyVulnerable.length, 1);
  // visible in evidence, not hidden
  assert.deepEqual(r.propagatedInBundle.map(p => p.name), ['expo-router']);
  assert.ok(r.propagatedInBundle[0].bundledSources > 0);
});

test('FAILS when the directly vulnerable module itself is in the Android bundle', () => {
  const r = inspectAndroidMetroAudit({ vulnerabilities: chain() }, sourceMaps(['../../node_modules/deepmerge/dist/cjs.js']));
  assert.equal(r.matchedModulePaths, 1);
  assert.equal(r.matches[0].advisory, 'deepmerge');
});

test('FAILS when a vulnerable module is bundled as a nested (transitive) copy', () => {
  // npm reports the top-level node; a nested copy elsewhere in node_modules must still be caught.
  const nestedCopy = sourceMaps(['../../node_modules/some-lib/node_modules/deepmerge/dist/cjs.js']);
  assert.equal(inspectAndroidMetroAudit({ vulnerabilities: chain() }, nestedCopy).matchedModulePaths, 1);
  // and when npm reports the nested node path itself
  const nested = chain();
  nested.deepmerge.nodes = ['node_modules/some-lib/node_modules/deepmerge'];
  assert.equal(inspectAndroidMetroAudit({ vulnerabilities: nested }, nestedCopy).matchedModulePaths, 1);
});

test('a package that is both an advisory source and bundled fails even if it also has dependents', () => {
  const v = chain();
  v['expo-router'] = { severity: 'low', via: [adv('expo-router')], nodes: ['node_modules/expo-router'] };
  const r = inspectAndroidMetroAudit({ vulnerabilities: v }, sourceMaps());
  assert.ok(r.matchedModulePaths > 0);
});

test('fails closed: unresolved, cyclic, empty or mismatched chains are treated as directly vulnerable', () => {
  const v = chain();
  v['expo-router'].via = ['not-in-audit'];
  assert.equal(classifyAuditPackages(v).direct.find(x => x.name === 'expo-router').kind, 'unclassified');
  assert.ok(inspectAndroidMetroAudit({ vulnerabilities: v }, sourceMaps()).matchedModulePaths > 0);

  const cyc = { a: { via: ['b'], nodes: ['node_modules/a'] }, b: { via: ['a'], nodes: ['node_modules/b'] } };
  assert.deepEqual(classifyAuditPackages(cyc).direct.map(x => x.kind), ['unclassified', 'unclassified']);

  const noVia = { 'expo-router': { severity: 'low', nodes: ['node_modules/expo-router'] } };
  assert.ok(inspectAndroidMetroAudit({ vulnerabilities: noVia }, sourceMaps()).matchedModulePaths > 0);

  const other = { x: { via: [adv('y')], nodes: ['node_modules/x'] }, y: { via: [adv('y')], nodes: ['node_modules/y'] } };
  assert.equal(classifyAuditPackages(other).direct.find(d => d.name === 'x').kind, 'unclassified');
});

test('no package-name allowlist: any bundled package becomes a failure once it is a direct advisory', () => {
  for (const name of ['expo-router', 'react-native']) {
    const v = { [name]: { severity: 'low', via: [adv(name)], nodes: ['node_modules/' + name] } };
    assert.ok(inspectAndroidMetroAudit({ vulnerabilities: v }, sourceMaps()).matchedModulePaths > 0, name);
  }
});
