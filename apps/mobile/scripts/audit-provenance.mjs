/**
 * Annotate npm audit output with npm lockfile's dev/devOptional flags.
 * This is diagnostic evidence only: npm audit remains the release gate.
 * Do NOT mistake devOptional metadata for proof of absence from a native APK.
 */
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

export function classifyAdvisoryProvenance(audit, lock) {
  if (!audit || typeof audit !== 'object' || !audit.vulnerabilities || typeof audit.vulnerabilities !== 'object' ||
      !lock || typeof lock !== 'object' || !lock.packages || typeof lock.packages !== 'object') {
    throw new Error('Valid npm audit JSON and npm lockfile v3 are required');
  }
  const packages = lock.packages;
  const reports = [];
  for (const [name, report] of Object.entries(audit.vulnerabilities)) {
    if (!Array.isArray(report?.nodes) || report.nodes.length === 0) {
      throw new Error(`Missing affected nodes for ${name}`);
    }
    const nodes = report.nodes.map(path => {
      if (typeof path !== 'string' || !path.startsWith('node_modules/')) throw new Error(`Invalid affected path for ${name}`);
      const manifest = packages[path];
      if (!manifest || typeof manifest !== 'object') return { path, classification: 'unknown' };
      // devOptional is a lockfile installation classification, not a bundle proof.
      const classification = manifest.dev === true || manifest.devOptional === true
        ? 'devOrDevOptional' : 'potentialRuntimeOrBuild';
      return { path, version: manifest.version ?? 'unknown', classification };
    });
    const status = nodes.some(n => n.classification === 'unknown') ? 'unverified'
      : nodes.some(n => n.classification === 'potentialRuntimeOrBuild') ? 'potentialRuntimeOrBuild'
        : 'devOrDevOptionalOnly';
    reports.push({ name, severity: report.severity ?? 'unknown', status, nodes });
  }
  reports.sort((a,b)=>a.name.localeCompare(b.name));
  const counts = {
    advisoryNames: reports.length,
    devOrDevOptionalOnly: reports.filter(x=>x.status==='devOrDevOptionalOnly').length,
    potentialRuntimeOrBuild: reports.filter(x=>x.status==='potentialRuntimeOrBuild').length,
    unverified: reports.filter(x=>x.status==='unverified').length,
  };
  return {
    policy: 'DIAGNOSTIC_ONLY_NOT_RELEASE_CLEARANCE',
    counts,
    npmReportedCounts: audit.metadata?.vulnerabilities ?? null,
    reports,
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  try {
    const [auditPath,lockPath] = process.argv.slice(2);
    if (!auditPath || !lockPath) throw new Error('Usage: node audit-provenance.mjs audit.json package-lock.json');
    const result = classifyAdvisoryProvenance(JSON.parse(readFileSync(auditPath, 'utf8')),
      JSON.parse(readFileSync(lockPath, 'utf8')));
    console.log(JSON.stringify(result,null,2));
    // Do not make vulnerability audit silently pass. Unknown affected
    // locations make even diagnostic status unreliable.
    if (result.counts.unverified > 0) process.exitCode = 2;
  } catch(error) {
    console.error(error instanceof Error ? error.message : String(error));
    process.exitCode = 2;
  }
}
