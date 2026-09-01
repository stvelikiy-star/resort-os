#!/usr/bin/env python3
from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS, clean_postgres_url, migration_names_match_exactly


def main() -> int:
    source = "postgresql://user:pass@db.example:5432/resort?schema=public&sslmode=require&connect_timeout=7"
    cleaned = clean_postgres_url(source)
    assert "schema=" not in cleaned
    assert "sslmode=require" in cleaned
    assert "connect_timeout=7" in cleaned
    assert cleaned.startswith("postgresql://user:pass@db.example:5432/resort?")

    assert migration_names_match_exactly(list(EXPECTED_MIGRATIONS))
    assert not migration_names_match_exactly(list(EXPECTED_MIGRATIONS[:-1]))
    assert not migration_names_match_exactly([*EXPECTED_MIGRATIONS, "unexpected_migration"])
    assert not migration_names_match_exactly(list(reversed(EXPECTED_MIGRATIONS)))

    assert len(EXPECTED_MIGRATIONS) == 7
    assert EXPECTED_MIGRATIONS[-1] == "6_service_point_qr_operations"
    assert len(CRITICAL_CONSTRAINTS) == 24

    print("PASS: DBaaS query parameters survive Prisma schema cleanup")
    print("PASS: exact seven-migration release ledger is fail-closed")
    print("PASS: Service Point QR operations migration is part of the canonical release boundary")
    print("PASS: current critical constraint fingerprint contains 24 constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())