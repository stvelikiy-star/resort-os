import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";

const trustedPackageBlobs = new Map([
  ["apps/admin/package.json", "7f2bff12f481d142ca7c91b02a159f22c9ee364f"],
  ["apps/web/package.json", "81026bed2fee1ca95f0017f7fc30c4cc75dcd5df"],
  ["apps/staff/package.json", "b2e892e15a3da20d88663bed6c78098ba569cef7"],
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
