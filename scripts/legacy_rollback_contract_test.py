#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "scripts" / "legacy_rollback_capture.py"
VERIFY = ROOT / "scripts" / "legacy_rollback_verify.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(script: Path, *args: str, ok: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run([sys.executable, str(script), *args], cwd=ROOT, text=True, capture_output=True, check=False)
    combined = proc.stdout + proc.stderr
    print(combined, end="")
    if ok and proc.returncode != 0:
        raise AssertionError(f"expected success, rc={proc.returncode}:\n{combined}")
    if not ok and proc.returncode == 0:
        raise AssertionError(f"expected failure:\n{combined}")
    return proc


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="three-crowns-legacy-") as tmp:
        base = Path(tmp)
        web = base / "live-web"
        uploads = base / "uploads"
        config = base / "vhost.conf"
        dns = base / "dns.json"
        evidence = base / "evidence"
        offsite = base / "offsite"
        web.mkdir()
        uploads.mkdir()
        (web / "index.html").write_text("<html>legacy three crowns</html>\n", encoding="utf-8")
        (uploads / "hero.jpg").write_bytes(b"synthetic-image-bytes")
        config.write_text("server_name 3korony.com;\n", encoding="utf-8")
        dns.write_text(
            json.dumps(
                {
                    "domain": "3korony.com",
                    "captured_at": "2026-09-01T00:00:00Z",
                    "records": {
                        "A": ["3korony.com. 300 IN A 203.0.113.10"],
                        "NS": ["3korony.com. 300 IN NS ns1.example.test."],
                        "MX": ["3korony.com. 300 IN MX 10 mail.example.test."],
                    },
                }
            ),
            encoding="utf-8",
        )
        original = {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        capture = run(
            CAPTURE,
            "--web-root", str(web),
            "--uploads", str(uploads),
            "--config", str(config),
            "--output-dir", str(evidence),
            "--dns-snapshot-file", str(dns),
            "--offsite-dir", str(offsite),
            "--rollback-owner", "CI_RELEASE_MANAGER",
        )
        assert "ROLLBACK_CAPTURE_OK" in capture.stdout
        assert "CAPTURED_NOT_RESTORED" in capture.stdout
        assert original == {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        manifest_path = evidence / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "CAPTURED_NOT_RESTORED"
        assert manifest["rollback_owner"] == "CI_RELEASE_MANAGER"
        assert manifest["safety"] == {
            "mutates_live_site": False,
            "changes_dns": False,
            "stops_services": False,
            "contains_database_credentials": False,
        }
        assert manifest["offsite_copy"]["status"] == "COPIED"
        copied = offsite / evidence.name
        assert copied.is_dir()
        assert digest(copied / "manifest.json") == digest(manifest_path)

        verify = run(VERIFY, str(evidence), "--mark-verified")
        assert "RESTORE_REHEARSAL_VERIFIED" in verify.stdout
        verified = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert verified["status"] == "RESTORE_VERIFIED"
        assert verified["restore_rehearsal"]["status"] == "VERIFIED"
        assert original == {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        overwrite = run(
            CAPTURE,
            "--web-root", str(web),
            "--output-dir", str(evidence),
            "--dns-snapshot-file", str(dns),
            "--rollback-owner", "CI_RELEASE_MANAGER",
            ok=False,
        )
        assert "output directory must be empty" in (overwrite.stdout + overwrite.stderr)

        bad_dns = base / "wrong-dns.json"
        bad_dns.write_text(json.dumps({"domain": "example.com", "records": {"A": []}}), encoding="utf-8")
        wrong = run(
            CAPTURE,
            "--web-root", str(web),
            "--output-dir", str(base / "wrong-evidence"),
            "--dns-snapshot-file", str(bad_dns),
            "--rollback-owner", "CI_RELEASE_MANAGER",
            ok=False,
        )
        assert "DNS snapshot domain mismatch" in (wrong.stdout + wrong.stderr)

        tampered_archive = evidence / verified["artifacts"]["site_archive"]["path"]
        tampered_archive.write_bytes(tampered_archive.read_bytes() + b"tamper")
        tamper = run(VERIFY, str(evidence), ok=False)
        assert "size mismatch" in (tamper.stdout + tamper.stderr) or "sha256 mismatch" in (tamper.stdout + tamper.stderr)

        missing = run(
            CAPTURE,
            "--web-root", str(base / "missing"),
            "--output-dir", str(base / "missing-evidence"),
            "--dns-snapshot-file", str(dns),
            "--rollback-owner", "CI_RELEASE_MANAGER",
            ok=False,
        )
        assert "web root does not exist" in (missing.stdout + missing.stderr)

    print("PASS: legacy rollback capture is non-destructive, checksum-bound, off-site copied, restore-rehearsed, and fail-closed")


if __name__ == "__main__":
    main()
