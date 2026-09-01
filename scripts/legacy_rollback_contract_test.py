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
GATE = ROOT / "scripts" / "legacy_rollback_gate.py"


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


def write_dns(path: Path, domain: str = "3korony.com") -> None:
    path.write_text(json.dumps({
        "domain": domain,
        "captured_at": "2026-09-01T00:00:00Z",
        "records": {
            "A": [f"{domain}. 300 IN A 203.0.113.10"],
            "AAAA": [],
            "CNAME": [],
            "NS": [f"{domain}. 300 IN NS ns1.example.test."],
            "MX": [f"{domain}. 300 IN MX 10 mail.example.test."],
            "TXT": [f'{domain}. 300 IN TXT "v=spf1 -all"'],
            "SOA": [f"{domain}. 300 IN SOA ns1.example.test. hostmaster.example.test. 1 3600 600 86400 300"],
        },
    }), encoding="utf-8")


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="three-crowns-legacy-") as tmp:
        base = Path(tmp)
        web = base / "live-web"
        uploads = base / "uploads"
        config = base / "vhost.conf"
        dns = base / "dns.json"
        evidence = base / "evidence"
        offsite = base / "offsite"
        web.mkdir(); uploads.mkdir()
        (web / "index.html").write_text("<html>legacy three crowns</html>\n", encoding="utf-8")
        (uploads / "hero.jpg").write_bytes(b"synthetic-image-bytes")
        config.write_text("server_name 3korony.com;\n", encoding="utf-8")
        write_dns(dns)
        original = {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        capture = run(CAPTURE,
            "--web-root", str(web),
            "--uploads", str(uploads),
            "--config", str(config),
            "--database-absent-confirmed",
            "--authoritative-dns-reviewed",
            "--output-dir", str(evidence),
            "--dns-snapshot-file", str(dns),
            "--offsite-dir", str(offsite),
            "--rollback-owner", "CI_RELEASE_MANAGER")
        assert "ROLLBACK_CAPTURE_OK" in capture.stdout
        assert original == {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        manifest_path = evidence / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["artifacts"]["database_dump"]["status"] == "ABSENT_CONFIRMED"
        assert manifest["evidence_decisions"]["authoritative_dns_reviewed"] is True
        copied = offsite / evidence.name
        assert digest(copied / "manifest.json") == digest(manifest_path)

        blocked_before_restore = run(GATE, str(evidence), ok=False)
        assert "restore rehearsal is not verified" in (blocked_before_restore.stdout + blocked_before_restore.stderr)

        verify = run(VERIFY, str(evidence), "--mark-verified")
        assert "RESTORE_REHEARSAL_VERIFIED" in verify.stdout
        assert "VERIFIED_MANIFEST_SYNCED" in verify.stdout
        assert digest(copied / "manifest.json") == digest(manifest_path)
        assert original == {"index": digest(web / "index.html"), "upload": digest(uploads / "hero.jpg"), "config": digest(config)}

        gate = run(GATE, str(evidence))
        assert "LEGACY_ROLLBACK_GATE_OK" in gate.stdout
        assert "CUTOVER_ROLLBACK_PREREQUISITE_GREEN" in gate.stdout

        ambiguous = base / "ambiguous"
        run(CAPTURE,
            "--web-root", str(web),
            "--uploads-absent-confirmed",
            "--config-absent-confirmed",
            "--authoritative-dns-reviewed",
            "--output-dir", str(ambiguous),
            "--dns-snapshot-file", str(dns),
            "--offsite-dir", str(base / "ambiguous-offsite"),
            "--rollback-owner", "CI_RELEASE_MANAGER")
        run(VERIFY, str(ambiguous), "--mark-verified")
        ambiguous_gate = run(GATE, str(ambiguous), ok=False)
        assert "database presence is undetermined" in (ambiguous_gate.stdout + ambiguous_gate.stderr)

        no_dns_review = base / "no-dns-review"
        run(CAPTURE,
            "--web-root", str(web),
            "--uploads-absent-confirmed",
            "--config-absent-confirmed",
            "--database-absent-confirmed",
            "--output-dir", str(no_dns_review),
            "--dns-snapshot-file", str(dns),
            "--offsite-dir", str(base / "no-dns-offsite"),
            "--rollback-owner", "CI_RELEASE_MANAGER")
        run(VERIFY, str(no_dns_review), "--mark-verified")
        dns_gate = run(GATE, str(no_dns_review), ok=False)
        assert "authoritative DNS/mail review" in (dns_gate.stdout + dns_gate.stderr)

        stale_offsite_manifest = copied / "manifest.json"
        stale_offsite_manifest.write_text("{}\n", encoding="utf-8")
        stale_gate = run(GATE, str(evidence), ok=False)
        assert "off-site manifest is not synchronized" in (stale_gate.stdout + stale_gate.stderr)

        overwrite = run(CAPTURE,
            "--web-root", str(web),
            "--output-dir", str(evidence),
            "--dns-snapshot-file", str(dns),
            "--rollback-owner", "CI_RELEASE_MANAGER", ok=False)
        assert "output directory must be empty" in (overwrite.stdout + overwrite.stderr)

        bad_dns = base / "wrong-dns.json"; write_dns(bad_dns, "example.com")
        wrong = run(CAPTURE,
            "--web-root", str(web),
            "--output-dir", str(base / "wrong-evidence"),
            "--dns-snapshot-file", str(bad_dns),
            "--rollback-owner", "CI_RELEASE_MANAGER", ok=False)
        assert "DNS snapshot domain mismatch" in (wrong.stdout + wrong.stderr)

        verified = json.loads(manifest_path.read_text(encoding="utf-8"))
        tampered_archive = evidence / verified["artifacts"]["site_archive"]["path"]
        tampered_archive.write_bytes(tampered_archive.read_bytes() + b"tamper")
        tamper = run(VERIFY, str(evidence), ok=False)
        assert "size mismatch" in (tamper.stdout + tamper.stderr) or "sha256 mismatch" in (tamper.stdout + tamper.stderr)

        missing = run(CAPTURE,
            "--web-root", str(base / "missing"),
            "--output-dir", str(base / "missing-evidence"),
            "--dns-snapshot-file", str(dns),
            "--rollback-owner", "CI_RELEASE_MANAGER", ok=False)
        assert "web root does not exist" in (missing.stdout + missing.stderr)

    print("PASS: legacy rollback capture/verify/final gate is non-destructive, explicit, off-site synchronized, restore-rehearsed, and fail-closed")


if __name__ == "__main__":
    main()
