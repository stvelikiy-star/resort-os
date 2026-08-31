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

    assert len(EXPECTED_MIGRATIONS) == 9
    assert EXPECTED_MIGRATIONS[-4:] == (
        "5_my_stay",
        "6_public_access",
        "7_in_stay_task_context",
        "8_public_access_unlock_claim",
    )
    assert len(CRITICAL_CONSTRAINTS) == 25
    assert "public_access_payment_intents_status_check" in CRITICAL_CONSTRAINTS

    print("PASS: DBaaS query parameters survive Prisma schema cleanup")
    print("PASS: exact nine-migration release ledger is fail-closed")
    print("PASS: MY STAY/public-access/in-stay/unlock-claim migrations are in the production ledger")
    print("PASS: public paid-access status transition constraint is release-critical")
    print("PASS: current critical constraint fingerprint contains 25 constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
