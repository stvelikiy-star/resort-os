"""Reject migration drift and incomplete release gates before RC1 acceptance."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from marina_candidate_truth_guard import ROOT, REQUIRED_WORKFLOWS, validate_source_lock


class SourceLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = json.loads((ROOT / 'release/marina-smart-current-candidate.json').read_text())
        shutil.copytree(ROOT / 'packages/database/prisma/migrations',
                        self.root / 'packages/database/prisma/migrations')
        workflow_dir = self.root / '.github/workflows'
        workflow_dir.mkdir(parents=True)
        for name in REQUIRED_WORKFLOWS:
            shutil.copyfile(ROOT / '.github/workflows' / name, workflow_dir / name)

    def test_reviewed_source_is_accepted_without_asserting_rollout(self):
        self.assertEqual(validate_source_lock(self.manifest, self.root), [])
        for key in ('external_staging_verified', 'backup_restore_target_verified',
                    'production_cutover_authorized', 'cross_tenant_e2e_verified'):
            self.assertIs(self.manifest[key], False)

    def test_changed_historical_sql_is_rejected(self):
        path = self.root / 'packages/database/prisma/migrations/0_init/migration.sql'
        path.write_bytes(path.read_bytes() + b'\n-- unexpected drift\n')
        self.assertIn('migration SHA-256 lock differs from committed SQL',
                      validate_source_lock(self.manifest, self.root))

    def test_unrecorded_migration_is_rejected(self):
        path = self.root / 'packages/database/prisma/migrations/zz999_unreviewed'
        path.mkdir()
        (path / 'migration.sql').write_text('SELECT 1;')
        self.assertTrue(validate_source_lock(self.manifest, self.root))

    def test_omitted_and_duplicated_gate_are_rejected(self):
        for required in (self.manifest['required_workflows'][:-1],
                         self.manifest['required_workflows'] + [self.manifest['required_workflows'][0]]):
            manifest = copy.deepcopy(self.manifest)
            manifest['required_workflows'] = required
            self.assertIn('mandatory workflow set is incomplete or duplicated',
                          validate_source_lock(manifest, self.root))

    def test_missing_workflow_is_rejected(self):
        (self.root / '.github/workflows/marina-hold-migration.yml').unlink()
        self.assertTrue(validate_source_lock(self.manifest, self.root))

    def test_push_only_manifest_trigger_is_insufficient(self):
        path = self.root / '.github/workflows/marina-shared-auth-preview-ci.yml'
        path.write_text("on:\n  push:\n    paths:\n      - 'release/marina-smart-current-candidate.json'\n"
                        "  pull_request:\n    paths:\n      - 'services/api/app/auth.py'\n  workflow_dispatch:\n")
        self.assertTrue(validate_source_lock(self.manifest, self.root))

    def test_source_lock_cannot_claim_shared_runtime_acceptance(self):
        self.manifest['release_stage'] = 'PRODUCTION_READY'
        self.assertIn('shared runtime acceptance must remain pending',
                      validate_source_lock(self.manifest, self.root))


if __name__ == '__main__':
    unittest.main()
