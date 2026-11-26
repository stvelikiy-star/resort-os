-- Read-only commercial participant detail. No new payout or accrual writer.
BEGIN;
GRANT SELECT(id,hotel_id,sku,agent_id) ON flex_partner_rule_versions TO flex_agent_statement_reader;
GRANT SELECT(id,hotel_id,sku,investor_id) ON flex_partner_rule_versions TO flex_investor_statement_reader;
CREATE POLICY flex_agent_rule_own_read ON flex_partner_rule_versions FOR SELECT TO flex_agent_statement_reader
 USING(agent_id=NULLIF(current_setting('flex.authorized_agent_id',true),'')::uuid);
CREATE POLICY flex_investor_rule_own_read ON flex_partner_rule_versions FOR SELECT TO flex_investor_statement_reader
 USING(investor_id=NULLIF(current_setting('flex.authorized_investor_id',true),'')::uuid);
GRANT SELECT(agent_id,hotel_id,sku,attributed_at) ON flex_agent_attributions TO flex_agent_statement_reader;
CREATE POLICY flex_agent_attribution_own_read ON flex_agent_attributions FOR SELECT TO flex_agent_statement_reader
 USING(agent_id=NULLIF(current_setting('flex.authorized_agent_id',true),'')::uuid);
GRANT SELECT(id,display_name,status) ON flex_hotels TO flex_agent_statement_reader;
CREATE POLICY flex_agent_assigned_hotel_read ON flex_hotels FOR SELECT TO flex_agent_statement_reader
 USING(EXISTS(SELECT 1 FROM flex_agent_attributions a WHERE a.hotel_id=flex_hotels.id));
GRANT SELECT(id,investor_id,contract_key,version,principal,share_bps,effective_from)
 ON flex_investor_contract_versions TO flex_investor_statement_reader;
CREATE POLICY flex_investor_contract_own_read ON flex_investor_contract_versions FOR SELECT TO flex_investor_statement_reader
 USING(investor_id=NULLIF(current_setting('flex.authorized_investor_id',true),'')::uuid);
COMMIT;
