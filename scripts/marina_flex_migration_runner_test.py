import unittest
from marina_flex_migration_runner import manifest, plan, body, FROZEN


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.files = manifest()
        self.rows = [
            dict(migration_id=n, filename=v[0], git_blob_sha=v[1],
                 disposition=FROZEN if n == 9 else "APPLIED")
            for n,v in self.files.items() if n <= 15
        ]

    def test_incremental(self):
        self.assertEqual(plan(self.rows,self.files),list(range(16,len(self.files)+1)))

    def test_repeat_is_noop(self):
        self.rows.extend(dict(migration_id=n,filename=v[0],git_blob_sha=v[1],disposition="APPLIED")
                         for n,v in self.files.items() if n > 15)
        self.assertEqual(plan(self.rows,self.files),[])

    def test_checksum_rejected(self):
        self.rows[0]["git_blob_sha"]="0"*40
        with self.assertRaisesRegex(ValueError,"SHA"):
            plan(self.rows,self.files)

    def test_freeze_rejected(self):
        self.rows[8]["disposition"]="APPLIED"
        with self.assertRaisesRegex(ValueError,"disposition"):
            plan(self.rows,self.files)

    def test_missing_baseline_rejected(self):
        with self.assertRaisesRegex(ValueError,"Baseline"):
            plan(self.rows[:13],self.files)

    def test_gap_rejected(self):
        with self.assertRaisesRegex(ValueError,"gap"):
            plan(self.rows[:7]+self.rows[8:],self.files)

    def test_pending_transaction_wrappers(self):
        for n in plan(self.rows,self.files):
            self.assertTrue(body(self.files[n][2]).strip())

if __name__=="__main__":
    unittest.main(verbosity=2)
