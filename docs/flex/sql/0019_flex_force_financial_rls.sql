-- FLEX only. Existing policies and grants are intentionally unchanged.
BEGIN;
ALTER TABLE flex_agent_attributions FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_agent_commission_accruals FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_allocation_reversals FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_confirmed_payments FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_investor_accruals FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_investor_contract_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_allocations FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_intents FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_payment_reversals FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_provider_event_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE flex_provider_events FORCE ROW LEVEL SECURITY;
COMMIT;
