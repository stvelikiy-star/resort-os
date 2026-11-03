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

  const affected = [];
  for (const [name, report] of Object.entries(audit.vulnerabilities)) {
    if (!report || typeof report !== 'object' ||
        !Array.isArray(report.nodes) || report.nodes.length === 0) {
      throw new Error('Incomplete npm advisory location evidence: ' + name);
    }
    for (const location of report.nodes) {
      if (!validAffectedNode(location)) {
        throw new Error('Unsafe npm advisory node path: ' + String(location));
      }
      affected.push({ name, location });
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
  return {
    policy: 'METRO_SOURCE_MAP_DIAGNOSTIC_ONLY_NOT_NPM_AUDIT_OR_APK_RELEASE_WAIVER',
    sourceCommit,
    mapDigests,
    totalDistinctSources: allSources.length,
    nodeModulesSourceCount,
    expoRouterSourceCount,
    npmAdvisoryPackageNames: Object.keys(audit.vulnerabilities).length,
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
