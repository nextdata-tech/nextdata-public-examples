-- Registers the two federated pharmacovigilance tables and captures the
-- current safety row count as a health signal.
-- The Snowflake output port this writes to anchors the credential context
-- that get_metadata and execute_federated_query need at runtime.
INSERT INTO {{ outputs["snowflake"].pv_registry }}
  (safety_table, commercial_table, join_keys, safety_row_count, registered_at)
SELECT
  'drug_safety_signals.adverse_event_summary'                     AS safety_table,
  'commercial_prescriptions.prescription_volume'                  AS commercial_table,
  'product_id, region, report_period'                             AS join_keys,
  COUNT(*)                                                        AS safety_row_count,
  CURRENT_TIMESTAMP()::STRING                                     AS registered_at
FROM {{ inputs.data_products["drug-safety-signals"]["snowflake"].adverse_event_summary }};
