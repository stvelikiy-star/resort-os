/**
 * Defensive evidence for Android Metro-bundled JavaScript and npm audit nodes.
 * This is NOT an npm audit waiver, APK/native SBOM, or a release authorization.
 * No native signing, secrets, PMS, guest information, or API credentials used.
 */
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

function validAffectedNode(path) {
  if (typeof path !== 'string' || !path.startsWith('node_modules/') ||
      path.includes('\\') || /%2f|%5c/i.test(path)) return false;
  return path.split('/').every(segment => segment !== '' && segment !== '.' && segment !== '..');
}

export function sourceMatchesAffectedNode(source, node) {
  if (!validAffectedNode(node) || typeof source !== 'string') return false;
  const path = source.replaceAll('\\', '/');
  return path.startsWith(node + '/') || path.includes('/' + node + '/') ||
    path === node || path.endsWith('/' + node);
}

/**
 * Split npm audit packages into:
 *  - directly vulnerable: the package itself has an advisory object in `via`
 *    (this is the code that must not be shipped);
 *  - propagated: every `via` entry is a string naming another vulnerable package.
 * Propagated packages are only trusted as such when the chain resolves, through
 * entries present in the same audit, to at least one directly vulnerable package.
 * Anything unclassifiable (missing/empty `via`, unknown or cyclic chain, advisory
 * object naming a different package) is treated as directly vulnerable: fail closed.
 */
export function classifyAuditPackages(vulnerabilities) {
  const own = new Map();
  for (const [name, report] of Object.entries(vulnerabilities)) {
    const via = report?.via;
    if (!Array.isArray(via) || via.length === 0) { own.set(name, 'unclassified'); continue; }
    const advisories = via.filter(x => x && typeof x === 'object');
    if (advisories.some(a => a.name !== name)) { own.set(name, 'unclassified'); continue; }
    if (!via.every(x => typeof x === 'string' || (x && typeof x === 'object'))) { own.set(name, 'unclassified'); continue; }
    own.set(name, advisories.length > 0 ? 'direct' : 'propagated');
  }
  const roots = new Map();
  const resolve = (name, seen) => {
    if (roots.has(name)) return roots.get(name);
    if (seen.has(name)) return null;
    const kind = own.get(name);
    if (kind === 'direct') return [name];
    if (kind !== 'propagated') return null;
    seen.add(name);
    const found = new Set();
    for (const next of vulnerabilities[name].via) {
      if (typeof next !== 'string' || !(next in vulnerabilities)) { seen.delete(name); return null; }
      const r = resolve(next, seen);
      if (!r) { seen.delete(name); return null; }
      r.forEach(x => found.add(x));
    }
    seen.delete(name);
    return [...found].sort();
  };
  const result = { direct: [], propagated: [] };
  for (const name of Object.keys(vulnerabilities)) {
    if (own.get(name) === 'direct') { result.direct.push({ name, kind: 'direct' }); continue; }
    const r = own.get(name) === 'propagated' ? resolve(name, new Set()) : null;
    if (r && r.length) result.propagated.push({ name, kind: 'propagated', roots: r });
    else result.direct.push({ name, kind: 'unclassified' });
  }
  return result;
}

export function inspectAndroidMetroAudit(audit, sourceMaps, sourceCommit = 'unknown') {
  if (!audit || typeof audit !== 'object' || !audit.vulnerabilities ||
      typeof audit.vulnerabilities !== 'object' || Array.isArray(audit.vulnerabilities)) {
    throw new Error('Missing or invalid npm audit JSON');
  }
  if (!Array.isArray(sourceMaps) || sourceMaps.length === 0) {
    throw new Error('No Metro source maps: cannot verify Android JavaScript inputs');
  }

  const sources = new Set();
  const mapDigests = [];
  for (const input of sourceMaps) {
    if (typeof input?.filename !== 'string' || typeof input?.raw !== 'string') {
      throw new Error('Invalid source map input');
    }
    const map = JSON.parse(input.raw);
    if (!Array.isArray(map.sources) || map.sources.length === 0 ||
        !map.sources.every(source => typeof source === 'string')) {
      throw new Error('Source map missing module sources');
    }
    mapDigests.push({
      filename: input.filename,
      sha256: createHash('sha256').update(input.raw).digest('hex'),
      sourceCount: map.sources.length,
    });
    for (const source of map.sources) sources.add(source.replaceAll('\\', '/'));
  }
  const allSources = [...sources];
  const nodeModulesSourceCount = allSources.filter(s => s.includes('node_modules/')).length;
  const expoRouterSourceCount = allSources.filter(s => s.includes('node_modules/expo-router/')).length;
  if (allSources.length < 100 || nodeModulesSourceCount < 100 || expoRouterSourceCount < 1) {
    throw new Error('Metro map does not contain expected visible Expo Router dependency sources');
  }
  if (!sourceMatchesAffectedNode('../../node_modules/jest/index.js', 'node_modules/jest') ||
      sourceMatchesAffectedNode('../../node_modules/jester/index.js', 'node_modules/jest')) {
    throw new Error('Source matcher positive and negative controls failed');
  }

  const classes = classifyAuditPackages(audit.vulnerabilities);
  const directNames = new Set(classes.direct.map(x => x.name));
  const affected = [];
  const propagatedNodes = [];
  for (const [name, report] of Object.entries(audit.vulnerabilities)) {
    if (!report || typeof report !== 'object' ||
        !Array.isArray(report.nodes) || report.nodes.length === 0) {
      throw new Error('Incomplete npm advisory location evidence: ' + name);
    }
    for (const location of report.nodes) {
      if (!validAffectedNode(location)) {
        throw new Error('Unsafe npm advisory node path: ' + String(location));
      }
      if (directNames.has(name)) affected.push({ name, location });
      else propagatedNodes.push({ name, location });
    }
  }

  const matches = [];
  for (const source of allSources) {
    for (const entry of affected) {
      if (sourceMatchesAffectedNode(source, entry.location)) {
        matches.push({ source, advisory: entry.name, affectedNode: entry.location });
      }
    }
  }
  // Not hidden: dependents flagged by npm audit that ship in the bundle are
  // reported as evidence, but only directly vulnerable modules fail the check.
  const propagatedInBundle = classes.propagated.map(p => ({
    name: p.name, roots: p.roots,
    bundledSources: propagatedNodes.filter(n => n.name === p.name)
      .reduce((count, n) => count + allSources.filter(src => sourceMatchesAffectedNode(src, n.location)).length, 0),
  })).filter(p => p.bundledSources > 0);
  return {
    policy: 'METRO_SOURCE_MAP_DIAGNOSTIC_ONLY_NOT_NPM_AUDIT_OR_APK_RELEASE_WAIVER',
    sourceCommit,
    mapDigests,
    totalDistinctSources: allSources.length,
    nodeModulesSourceCount,
    expoRouterSourceCount,
    npmAdvisoryPackageNames: Object.keys(audit.vulnerabilities).length,
    directlyVulnerable: classes.direct,
    propagatedPackages: classes.propagated,
    propagatedInBundle,
    affectedNodePaths: affected.length,
    matchedModulePaths: matches.length,
    matches,
  };
}

export function findMetroMaps(directory) {
  const results = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const file = join(directory, entry.name);
    if (entry.isDirectory()) results.push(...findMetroMaps(file));
    else if (entry.isFile() && file.endsWith('.map') && statSync(file).size > 0) {
      results.push({ filename: file, raw: readFileSync(file, 'utf8') });
    }
  }
  return results;
}

if (process.argv[1] && import.meta.url === new URL('file://' + process.argv[1]).href) {
  try {
    const [auditPath, mapsDir, evidencePath] = process.argv.slice(2);
    if (!auditPath || !mapsDir || !evidencePath) {
      throw new Error('Usage: node verify-android-source-audit.mjs audit.json metro-output-dir evidence.json');
    }
    const audit = JSON.parse(readFileSync(auditPath, 'utf8'));
    const evidence = inspectAndroidMetroAudit(audit, findMetroMaps(mapsDir), process.env.MARINA_SOURCE_SHA || 'unknown');
    writeFileSync(evidencePath, JSON.stringify(evidence, null, 2));
    console.log('ANDROID_METRO_AUDIT_EVIDENCE', JSON.stringify({
      sourceCommit: evidence.sourceCommit,
      maps: evidence.mapDigests.length,
      sources: evidence.totalDistinctSources,
      expoRouterSources: evidence.expoRouterSourceCount,
      directlyVulnerable: evidence.directlyVulnerable.length,
      propagatedPackages: evidence.propagatedPackages.length,
      propagatedDependentsInBundle: evidence.propagatedInBundle.length,
      affectedNodePaths: evidence.affectedNodePaths,
      matchingModules: evidence.matchedModulePaths,
      diagnosticOnly: true,
    }));
    if (evidence.matchedModulePaths) process.exitCode = 2;
  } catch (error) {
    console.error('ANDROID_METRO_AUDIT_FAIL_CLOSED', error instanceof Error ? error.message : String(error));
    process.exitCode = 2;
  }
}
