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

    assert len(EXPECTED_MIGRATIONS) == 20
    assert EXPECTED_MIGRATIONS[-3:] == (
        "z17_dining_floor_layout_20260905",
        "z18_site_media_slots_20260905",
        "z19_dining_table_status_guard_20260905",
    )
    assert len(CRITICAL_CONSTRAINTS) == 81
    assert {
        "service_points_category_check",
        "service_point_qrs_revocation_check",
        "operational_tasks_service_point_context_check",
        "kitchen_menu_availability_meal_check",
        "kitchen_table_reservations_party_check",
        "kitchen_table_reservations_time_check",
        "kitchen_table_reservations_status_check",
        "guest_offer_campaigns_action_check",
        "guest_offer_campaigns_request_code_check",
        "guest_offer_campaigns_external_url_check",
        "guest_offer_campaigns_window_check",
        "guest_offer_campaigns_audience_check",
        "guest_offer_events_type_check",
        "service_point_access_profiles_currency_check",
        "service_point_access_profiles_paid_config_check",
        "service_point_payment_intents_amount_check",
        "service_point_payment_intents_currency_check",
        "service_point_payment_intents_lock_snapshot_check",
        "service_point_payment_intents_expiry_check",
        "service_point_payment_intents_paid_state_check",
        "service_point_payment_intents_unlocked_state_check",
        "service_point_payment_events_payload_check",
        "service_point_lock_actions_attempts_check",
        "service_point_lock_actions_result_check",
        "property_guest_service_settings_cutoff_check",
        "operational_tasks_charge_status_check",
        "dining_entitlements_status_check",
        "dining_table_sessions_party_sum_check",
        "guest_folio_charges_source_check",
        "booking_groups_dates_check",
        "site_media_assets_mime_check",
        "kitchen_tables_floor_shape_check",
        "site_media_slots_versions_check",
    }.issubset(CRITICAL_CONSTRAINTS)

    print("PASS: DBaaS query parameters survive Prisma schema cleanup")
    print("PASS: exact twenty-migration Resort OS 0.60 release ledger is fail-closed")
    print("PASS: current 0.60 Dining, Guest, CMS, Group Booking and Service Point boundaries are canonical")
    print("PASS: current critical constraint fingerprint contains 81 constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
