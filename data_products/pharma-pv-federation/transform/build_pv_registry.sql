-- Build the pharmacovigilance federation registry: one constant anchor row.
--
-- We use CREATE OR REPLACE TABLE ... AS SELECT (not INSERT) on purpose. This
-- transform owns the table definition outright, so the physical table is always
-- rebuilt to exactly match the columns produced here. That makes the deploy
-- self-healing: it cannot fail with an "invalid identifier" error when an older
-- version of this data product left a PV_REGISTRY table behind with a different
-- set of columns. It also reads NO other schema and counts NO upstream rows, so
-- it can never panic on an empty or not-yet-visible source table.
--
-- The table is only an anchor: it gives this data product a concrete Snowflake
-- output so the platform issues live Snowflake credentials, which the MCP tools
-- (get_metadata, execute_federated_query) then borrow to run federated reads.
-- Nothing downstream consumes PV_REGISTRY, so replacing it is safe.
--
-- Plain ASCII only. Do not introduce en-dash or em-dash characters anywhere in
-- this file: the Snowflake SQL parser panics on them inside comments.

CREATE OR REPLACE TABLE {{ outputs["snowflake"].pv_registry }} AS
SELECT
    'pharma-pv-federation'                                                       AS registry_id,
    'PARTNER_AZ_DB.DRUG_SAFETY_SIGNALS.ADVERSE_EVENT_SUMMARY'                     AS safety_source,
    'PARTNER_AZ_DB.COMMERCIAL_PRESCRIPTIONS.PRESCRIPTION_VOLUME'                  AS commercial_source,
    'product_id, region, report_period'                                          AS join_keys,
    '1000.0 * SUM(adverse_event_count) / NULLIF(SUM(total_prescriptions), 0)'    AS rate_metric,
    CURRENT_TIMESTAMP()::STRING                                                   AS built_at;
