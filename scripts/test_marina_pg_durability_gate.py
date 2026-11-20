"""MARINA SMART: a PostgreSQL fixture must survive reboots."""
import unittest
from marina_pg_durability_gate import PGDATA, inspect_errors


def volume(name="marina-rc426-persist-pgdata", writable=True):
    return [{"Type": "volume", "Name": name, "Destination": PGDATA, "RW": writable}]


class DockerPgDurabilityGateTests(unittest.TestCase):
    def test_named_volume_and_restart_are_accepted(self):
        self.assertEqual(inspect_errors(volume(), None, "unless-stopped", "marina-rc426-persist-pgdata"), [])

    def test_named_volume_always_restart_is_accepted(self):
        self.assertEqual(inspect_errors(volume(), None, "always"), [])

    def test_existing_bind_mount_is_persistent(self):
        mounts = [{"Type": "bind", "Source": "/opt/marina/pgdata", "Destination": PGDATA, "RW": True}]
        self.assertEqual(inspect_errors(mounts, None, "unless-stopped"), [])

    def test_tmpfs_exact_data_dir_rejected(self):
        self.assertIn("PGDATA_TMPFS_FORBIDDEN",
                      inspect_errors([], {PGDATA: "rw,size=384m"}, "no"))

    def test_tmpfs_cannot_hide_behind_volume(self):
        self.assertIn("PGDATA_TMPFS_FORBIDDEN",
                      inspect_errors(volume(), {PGDATA: "rw,size=384m"}, "always"))

    def test_implicit_container_layer_is_rejected(self):
        self.assertIn("PGDATA_REQUIRES_ONE_EXPLICIT_PERSISTENT_MOUNT",
                      inspect_errors([], None, "unless-stopped"))

    def test_mounted_tmpfs_is_rejected(self):
        mounts = [{"Type": "tmpfs", "Destination": PGDATA, "RW": True}]
        self.assertIn("PGDATA_MOUNT_NOT_PERSISTENT", inspect_errors(mounts, None, "always"))

    def test_wrong_named_volume_rejected(self):
        self.assertIn("PGDATA_NAMED_VOLUME_MISMATCH",
                      inspect_errors(volume("other"), None, "always",
                                     "marina-rc426-persist-pgdata"))

    def test_readonly_mount_rejected(self):
        self.assertIn("PGDATA_MOUNT_READONLY",
                      inspect_errors(volume(writable=False), None, "always"))

    def test_disabled_restart_rejected(self):
        self.assertIn("POSTGRES_AUTO_RESTART_NOT_CONFIGURED",
                      inspect_errors(volume(), None, "no"))

    def test_only_one_pgdata_mount_is_allowed(self):
        self.assertIn("PGDATA_REQUIRES_ONE_EXPLICIT_PERSISTENT_MOUNT",
                      inspect_errors(volume() + volume("wrong"), None, "always"))

    def test_mounting_parent_dir_does_not_count(self):
        mounts = [{"Type": "volume", "Destination": "/var/lib/postgresql",
                   "Name": "parent", "RW": True}]
        self.assertIn("PGDATA_REQUIRES_ONE_EXPLICIT_PERSISTENT_MOUNT",
                      inspect_errors(mounts, None, "always"))


if __name__ == "__main__":
    unittest.main()