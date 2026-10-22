import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const trustedPackageBlobs = new Map([
  ["apps/admin/package.json", "750dd4a5486bcbac0ba6452d35909a4ce81d927f"],
  ["apps/web/package.json", "82a9815d3fcdca8df08ae31436c831f1dc3eac04"],
  ["apps/staff/package.json", "45235005c65ad9ae231b7d8b772eb694d36647a0"],
]);

function gitBlobSha(path) {
  const content = readFileSync(path);
  return createHash("sha1")
    .update(`blob ${content.length}\0`)
    .update(content)
    .digest("hex");
}

function fail(message) {
  console.error(`[control-center-verify] ${message}`);
  process.exit(1);
}

for (const [path, expected] of trustedPackageBlobs) {
  const actual = gitBlobSha(path);
  if (actual !== expected) {
    fail(`trusted package manifest drift: ${path}; expected ${expected}, got ${actual}`);
  }
}

const checks = [
  ["npm", ["--prefix", "apps/admin", "run", "typecheck"]],
  ["npm", ["--prefix", "apps/web", "run", "typecheck"]],
  ["npm", ["--prefix", "apps/staff", "run", "typecheck"]],
  ["npm", ["--prefix", "apps/admin", "run", "build"]],
  ["npm", ["--prefix", "apps/web", "run", "build"]],
  ["npm", ["--prefix", "apps/staff", "run", "build"]],
  ["python3", ["-m", "compileall", "-q", "services/api/app", "scripts"]],
];

for (const [command, args] of checks) {
  const result = spawnSync(command, args, { stdio: "inherit", shell: false });
  if (result.error) {
    fail(`unable to execute ${command}: ${result.error.message}`);
  }
  if (result.status !== 0) {
    fail(`check failed (${result.status}): ${command} ${args.join(" ")}`);
  }
}

console.log("CONTROL_CENTER_MONOREPO_CONTRACT_PASS");
