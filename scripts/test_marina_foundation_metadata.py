import contextlib
import io
import json
import unittest
from unittest.mock import patch

import verify_marina_multitenant_foundation as gate


class FoundationMetadataTests(unittest.TestCase):
    def test_current_metadata_matches_committed_migrations(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(gate.main(), 0)

    def test_stale_count_is_rejected_without_changing_release_flags(self):
        original = gate.read
        def read(path):
            value = original(path)
            if path == 'release/marina-smart-current-candidate.json':
                data = json.loads(value)
                data['migration_count'] = 32
                return json.dumps(data, indent=2)
            return value
        with patch.object(gate, 'read', side_effect=read):
            with self.assertRaisesRegex(AssertionError, 'migration count'):
                gate.main()

    def test_unverified_production_authorization_is_still_rejected(self):
        original = gate.read
        def read(path):
            value = original(path)
            if path == 'release/marina-smart-current-candidate.json':
                data = json.loads(value)
                data['production_cutover_authorized'] = True
                return json.dumps(data, indent=2)
            return value
        with patch.object(gate, 'read', side_effect=read):
            with self.assertRaisesRegex(AssertionError, 'production_cutover_authorized'):
                gate.main()


if __name__ == '__main__': unittest.main()
