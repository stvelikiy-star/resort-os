"""Shared Three Crowns production database release contract.

Keep deployment preflight, backup and restore verification aligned with the exact
committed migration/invariant boundary. This module intentionally fails closed:
when a forward migration changes production truth, this contract must be reviewed
and updated in the same release.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

EXPECTED_MIGRATIONS = (
    "0_init",
    "1_site_content",
    "2_guest_service_tasks",
    "3_owner_analytics_snapshots",
    "4_guest_engagements",
    "5_guest_os_core",
    "6_service_point_qr_operations",
    "7_kitchen_operations",
    "8_dining_service_control",
    "9_guest_offer_campaigns",
    "z10_service_point_paid_access",
)

# Explicit business/data-integrity CHECK/EXCLUDE constraints whose loss must make
# production preflight and backup verification fail. Foreign keys and uniqueness
# have additional migration-level tests; this fingerprint focuses on the
# fail-closed domain constraints that protect Resort Core behaviour.
CRITICAL_CONSTRAINTS = frozenset(
    {
        "rate_period_valid_dates",
        "rate_period_nonnegative_price",
        "reservation_request_valid_dates",
        "reservation_request_positive_adults",
        "reservation_request_nonnegative_children",
        "reservation_valid_dates",
        "reservation_positive_adults",
        "reservation_nonnegative_children",
        "reservation_nonnegative_total",
        "inventory_block_valid_dates",
        "no_overlapping_active_room_blocks",
        "payment_positive_amount",
        "payment_has_context",
        "site_content_documents_locale_check",
        "site_content_documents_scope_check",
        "operational_tasks_service_context_type_check",
        "operational_tasks_service_time_check",
        "owner_analytics_snapshots_horizon_check",
        "owner_analytics_snapshots_payload_object_check",
        "guest_engagements_kind_check",
        "guest_engagements_status_check",
        "guest_engagements_score_check",
        "guest_engagements_score_kind_check",
        "guest_engagements_feedback_reservation_check",
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
    }
)


def clean_postgres_url(value: str) -> str:
    """Remove Prisma-only schema= while preserving DBaaS TLS/query parameters.

    `schema=public` is understood by Prisma but not by pg_dump/pg_restore/asyncpg.
    Other parameters (notably sslmode=require for managed PostgreSQL) are part of
    the actual transport/security contract and must survive production tooling.
    """
    parts = urlsplit(value)
    query = [
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() != "schema"
    ]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def migration_names_match_exactly(names: list[str] | tuple[str, ...]) -> bool:
    return tuple(names) == EXPECTED_MIGRATIONS
