#!/usr/bin/env node
/**
 * Install the SINGLE approved MARINA SMART circular PNG master in the
 * protected design worktree. Dry-run by default; never silently deploy.
 *
 * Usage:
 *   node scripts/install-approved-marina-logo.mjs --plan
 *   node scripts/install-approved-marina-logo.mjs --apply /absolute/path/MARINA_SMART_APPROVED_FLAT_1024.png
 *   node scripts/install-approved-marina-logo.mjs --verify-installed
 */
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import path from 'node:path';

const root = path.resolve(import.meta.dirname, '..');
const MASTER_SHA = '24678424bf13e4a983f6225fa72c3a73cabc573205832652ee39ed7b27f15356';
const FILE_NAME = 'marina-smart-approved.png';
const assets = [
  'apps/admin/public/' + FILE_NAME,
  'apps/staff/public/' + FILE_NAME,
  'apps/mobile/assets/' + FILE_NAME,
];
const replacements = [
  { file: 'apps/admin/components/AdminShell.tsx', before: '/marina-smart-logo.webp', after: '/' + FILE_NAME, min: 3 },
  { file: 'apps/staff/components/WaiterEntry.tsx', before: '/marina-smart-logo.webp', after: '/' + FILE_NAME, min: 1 },
  { file: 'apps/mobile/src/components/Brand.tsx', before: 'marina-staff-app-icon.png', after: FILE_NAME, min: 1 },
  { file: 'apps/mobile/app.json', before: 'marina-staff-app-icon.png', after: FILE_NAME, min: 3 },
];
function fail(message) { console.error('APPROVED LOGO INSTALL BLOCKED: ' + message); process.exit(1); }
function sha(data) { return createHash('sha256').update(data).digest('hex'); }
function checkedOriginal(file) {
  const bytes = readFileSync(file);
  if (sha(bytes) !== MASTER_SHA) fail('source SHA-256 not equal to user-approved original');
  if (bytes.subarray(0, 8).toString('hex') !== '89504e470d0a1a0a') fail('not a PNG');
  if (bytes.readUInt32BE(16) !== 1024 || bytes.readUInt32BE(20) !== 1024 || bytes[25] !== 6) fail('expected exact 1024x1024 RGBA PNG master');
  return bytes;
}
function checkedSourceContracts() {
  const changes = [];
  for (const { file, before, after, min } of replacements) {
    const p = path.join(root, file);
    const original = readFileSync(p, 'utf8');
    const count = original.split(before).length - 1;
    if (count < min) fail('unexpected original logo references in ' + file + ': '+count);
    if (original.includes(after)) fail('asset already partially installed in ' + file);
    changes.push([p, original.replaceAll(before, after)]);
  }
  return changes;
}
function verifyInstalled() {
  for (const asset of assets) {
    const p = path.join(root, asset);
    if (!existsSync(p)) fail('canonical logo absent: ' + asset);
    checkedOriginal(p);
  }
  for (const { file, before, after } of replacements) {
    const src=readFileSync(path.join(root,file),'utf8');
    if (src.includes(before) || !src.includes(after)) fail('inconsistent logo reference: ' + file);
  }
  console.log('APPROVED LOGO VERIFIED: same exact 1024px RGBA PNG SHA in Admin, Staff, Expo; all known runtime references updated.');
}
const mode = process.argv[2] ?? '--plan';
if (mode === '--plan') {
  console.log('Logo installation PLAN ONLY; no files modified.');
  console.log('Expected original SHA-256: '+MASTER_SHA);
  console.log('Targets: '+assets.join(', '));
  console.log('References: '+replacements.map(r=>r.file).join(', '));
  console.log('Run --apply <approved original PNG absolute path> ONLY on a clean design branch.');
} else if (mode === '--verify-installed') {
  verifyInstalled();
} else if (mode === '--apply') {
  const source = process.argv[3];
  if (!source || !path.isAbsolute(source)) fail('--apply requires absolute path to approved original PNG');
  let branch='';
  let status='';
  try {
    branch = execFileSync('git', ['branch', '--show-current'], { cwd: root, encoding: 'utf8' }).trim();
    status = execFileSync('git', ['status', '--porcelain'], { cwd: root, encoding: 'utf8' }).trim();
  } catch { fail('cannot verify Git worktree safety'); }
  if (!branch.startsWith('design/')) fail('must run only on separate design/* Git branch');
  if (status) fail('worktree must be clean; preserve existing work');
  const original=checkedOriginal(source);
  const changes=checkedSourceContracts(); // Validate ALL source contracts before mutating.
  for (const asset of assets) {
    const dest=path.join(root,asset); mkdirSync(path.dirname(dest), {recursive:true});
    writeFileSync(dest,original);
  }
  for (const [p,body] of changes) writeFileSync(p,body,'utf8');
  verifyInstalled();
  console.log('Local design worktree changed. REVIEW, BUILD and create a DRAFT PR. NO DEPLOYMENT performed.');
} else {
  fail('unknown mode: '+mode);
}
