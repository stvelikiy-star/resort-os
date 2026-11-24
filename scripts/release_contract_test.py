#!/usr/bin/env python3
from release_contract import CRITICAL_CONSTRAINTS, EXPECTED_MIGRATIONS, clean_postgres_url, migration_names_match_exactly


def main() -> int:
    source = "postgresql://user@db.example:5432/resort?schema=public&sslmode=require&connect_timeout=7"
    cleaned = clean_postgres_url(source)
    assert "schema=" not in cleaned
    assert "sslmode=require" in cleaned
    assert "connect_timeout=7" in cleaned
    assert cleaned.startswith("postgresql://user@db.example:5432/resort?")

    assert migration_names_match_exactly(list(EXPECTED_MIGRATIONS))
    assert not migration_names_match_exactly(list(EXPECTED_MIGRATIONS[:-1]))
    assert not migration_names_match_exactly([*EXPECTED_MIGRATIONS, "unexpected_migration"])
    assert not migration_names_match_exactly(list(reversed(EXPECTED_MIGRATIONS)))

    assert len(EXPECTED_MIGRATIONS) == 53
    assert EXPECTED_MIGRATIONS[-33:] == (
        "z19_dining_table_status_guard_20260905",
        "z20_dining_active_table_unique_20260906",
        "z21_dining_production_snapshots_20260906",
        "z99_marketing_consent_attribution_20260912",
        "zz100_owner_ops_corrections_20260914",
        "zz101_marina_product_settings_20260926",
        "zz102_marina_full_modules_20260927",
        "zz103_agent_access_20260927",
        "zz104_public_kz_20260929",
        "zz105_guest_dynamic_kz_20260929",
        "zz106_marina_split_cook_waiter_20261007",
        "zz107_marina_tenants_20261008",
        "zz108_marina_channel_mappings_20261016",
        "zz109_marina_review_stars_20261022",
        "zz110_marina_guest_stay_reviews_20261022",
        "zz111_marina_room_wayfinding_20261022",
        "zz112_marina_staff_module_permissions_20261022",
        "zz113_marina_housekeeping_schedule_date_20261027",
        "zz114_marina_60minute_holds_20261029",
        "zz115_marina_chef_production_targets_20261110",
        "zz116_marina_kitchen_recipes_20261111",
        "zz117_marina_kitchen_stock_20261111",
        "zz118_marina_kitchen_waste_spoilage_20261115",
        "zz119_marina_kitchen_procurement_20261115",
        "zz120_marina_owner_expenses_20261115",
        "zz121_marina_supplier_documents_20261116",
        "zz122_marina_supplier_returns_20261116",
        "zz123_marina_owner_revenue_source_events_20261116",
        "zz124_marina_owner_revenue_corrections_20261116",
        "zz125_marina_owner_revenue_evidence_bytes_20261116",
        "zz126_marina_owner_accounting_journal_proposals_20261116",
        "zz127_marina_served_batch_allocation_20261124",
        "zz128_marina_owner_accounting_decision_evidence_20261124",
    )
    assert len(CRITICAL_CONSTRAINTS) == 119
    assert {
        "service_points_category_check",
        "service_point_qrs_revocation_check",
        "operational_tasks_service_point_context_check",
        "kitchen_menu_availability_meal_check",
        "kitchen_menu_recipe_shape",
        "kitchen_served_allocation_portions_check",
        "kitchen_served_allocation_unit_cost_check",
        "kitchen_served_allocation_total_cost_check",
        "kitchen_served_allocation_source_check",
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
        "dining_production_snapshots_meal_check",
        "dining_production_snapshots_adult_check",
        "dining_production_snapshots_child_check",
        "dining_production_snapshots_entitlement_count_check",
        "dining_production_snapshots_fingerprint_check",
        "dining_production_snapshots_reason_check",
        "booking_agents_status_check",
        "booking_agent_interactions_kind_check",
        "reservations_extra_bed_count_check",
        "reservations_extra_bed_unit_check",
        "reservations_discount_percent_check",
        "inventory_blocks_usage_category_check",
    }.issubset(CRITICAL_CONSTRAINTS)

    print("PASS: DBaaS query parameters survive Prisma schema cleanup")
    print(f"PASS: exact {len(EXPECTED_MIGRATIONS)}-migration current candidate ledger is fail-closed")
    print("PASS: current Dining, Guest, CMS, Group Booking, Service Point, Marketing and Owner Operations boundaries are canonical")
    print(f"PASS: current critical constraint fingerprint contains {len(CRITICAL_CONSTRAINTS)} constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
