#!/usr/bin/env python3
"""Run all current MARINA regressions plus original RC3 tests against its frozen 39-migration tree.

Do not rewrite historical manifest or tests. New release has 40 migrations;
historical RC3 must still pass its *original* unchanged tests in the frozen source.
"""
from __future__ import annotations
import importlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from marina_rc3_source_gate import RC2_FILE,RC3_FILE,REQUIRED_WORKFLOWS,git_blob_sha

def flatten(suite):
    for entry in suite:
        if isinstance(entry,unittest.TestSuite):yield from flatten(entry)
        else:yield entry

def frozen_rc3_snapshot(root:Path)->None:
    rc2=json.loads((ROOT/RC2_FILE).read_text())
    rc3=json.loads((ROOT/RC3_FILE).read_text())
    assert len(rc2["migration_sha256"])==39
    for manifest_file in (RC2_FILE,RC3_FILE):
        dst=root/manifest_file
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(ROOT/manifest_file,dst)
    for name,expected_hash in rc2["migration_sha256"].items():
        src=ROOT/"packages/database/prisma/migrations"/name/"migration.sql"
        assert __import__("hashlib").sha256(src.read_bytes()).hexdigest()==expected_hash
        dst=root/"packages/database/prisma/migrations"/name/"migration.sql"
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(src,dst)
    # Critical reviewed Git source bytes are fetched by their immutable blob
    # hashes. This includes the ORIGINAL RC3 gate and CI workflow even if a
    # later release has revised its own orchestration.
    for rel,sha in rc3["critical_git_blobs"].items():
        obj=subprocess.run(["git","-C",str(ROOT),"cat-file","blob",sha],capture_output=True,check=True).stdout
        assert git_blob_sha(obj)==sha,rel
        dst=root/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(obj)
    for workflow in REQUIRED_WORKFLOWS:
        dst=root/".github/workflows"/workflow
        if not dst.exists():
            dst.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT/".github/workflows"/workflow,dst)

def main()->int:
    discovered=unittest.defaultTestLoader.discover(str(ROOT/"scripts"),pattern="test_marina_*.py")
    tests=list(flatten(discovered))
    legacy=[t for t in tests if t.id().startswith("test_marina_rc3_source_gate.")]
    assert len(legacy)==4, f"expected all 4 immutable RC3 tests, got {len(legacy)}"
    current=[t for t in tests if not t.id().startswith("test_marina_rc3_source_gate.")]
    assert current, "must not skip current MARINA regression tests"
    print(f"CURRENT_MARINA_REGRESSIONS: {len(current)} tests (RC3 historical 4 checked separately)",flush=True)
    result=unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(current))
    if not result.wasSuccessful():return 1
    with tempfile.TemporaryDirectory(prefix="marina-historical-rc3-") as td:
        root=Path(td)
        frozen_rc3_snapshot(root)
        historical=importlib.import_module("test_marina_rc3_source_gate")
        historical.ROOT=root
        old_suite=unittest.defaultTestLoader.loadTestsFromModule(historical)
        print("HISTORICAL_RC3_PINNED_SOURCE: 39 SQL + 22 frozen Git objects",flush=True)
        result=unittest.TextTestRunner(verbosity=2).run(old_suite)
        if not result.wasSuccessful():return 1
    print("MARINA_RC1_AND_FROZEN_RC3_ALL_PASS; current 40 migrations checked separately",flush=True)
    return 0

if __name__=="__main__":raise SystemExit(main())
