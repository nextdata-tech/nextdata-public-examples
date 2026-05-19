TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].account }};

INSERT INTO {{ outputs["snowflake"].account }}
    (account_id, account_type, first_name, last_name, hco_name, npi, specialty, city, state, prescribing_decile, segment, account_value_tier, potential_value_usd, actual_value_usd, preferred_channel, email_opt_in, target_flag, territory_id, primary_rep_id, status)
VALUES
    ('0013x000001', 'Person', 'Maria', 'Gonzalez', NULL, 1457392048, 'Cardiology', 'Northfield', 'CA', 10, 'A', 'High', 392000, 58000, 'F2F', TRUE, 'Y', 'T-01', 'R-001', 'Active'),
    ('0013x000003', 'Person', 'Aisha', 'Khan', NULL, 1773829104, 'Endocrinology', 'Westfield', 'TX', 9, 'A', 'High', 366000, 302000, 'F2F', TRUE, 'Y', 'T-02', 'R-003', 'Active'),
    ('0013x000005', 'Organization', NULL, NULL, 'Bay Heart Clinic', 1029384756, 'Cardiology', 'Northfield', 'CA', 8, 'B', 'Medium', 210000, 160000, 'F2F', NULL, 'Y', 'T-01', 'R-002', 'Active'),
    ('0013x000006', 'Person', 'Wei', 'Chen', NULL, 1564738291, 'Primary Care', 'Eastfield', 'FL', 7, 'B', 'Medium', 178000, 22000, 'Email', TRUE, 'Y', 'T-04', 'R-007', 'Active'),
    ('0013x000019', 'Person', 'Maria', 'Khan', NULL, 1708998071, 'Pulmonology', 'Westfield', 'CA', 3, 'D', 'Low', 52000, 4000, 'Email', TRUE, 'N', 'T-08', 'R-015', 'Active'),
    ('0013x000023', 'Person', 'Wei', 'Lee', NULL, 1122038475, 'Neurology', 'Westfield', 'WA', 1, 'D', 'Low', 21000, 1000, 'Email', NULL, 'N', 'T-06', 'R-011', 'Inactive'),
    ('0013x000025', 'Person', 'carlos', 'Muller', NULL, 1344058677, 'Oncology', 'Northfield', 'CA', 9, 'A', 'High', 372000, 52000, 'Conference', TRUE, 'Y', 'T-08', 'R-016', 'Active'),
    ('0013x000041', 'Person', 'Priya', 'Singh', NULL, 19, 'Oncology', 'Northfield', 'FL', 8, 'B', 'High', 277000, 44000, 'Conference', TRUE, 'Y', 'T-04', 'R-008', 'Active'),
    ('0013x000043', 'Person', 'Emily', 'Smith', NULL, 1122349475, 'Primary Care', 'Westfield', 'WA', 2, 'D', 'Low', 27000, 1500, 'Email', TRUE, 'N', 'T-06', 'R-012', 'Active'),
    ('0013x000044', 'Person', 'David', 'Khan', NULL, 1233359576, 'Cardiology', 'Southfield', 'MA', 9, 'A', 'High', 347000, 55000, 'F2F', TRUE, 'Y', 'T-07', 'R-014', 'Active');

TRUNCATE TABLE IF EXISTS {{ outputs["snowflake"].activity }};

INSERT INTO {{ outputs["snowflake"].activity }}
    (activity_id, account_id, rep_id, territory_id, activity_datetime, activity_month, channel, activity_type, product_discussed, detail_priority, duration_min, engagement_score, response, on_preferred_channel, sample_dropped, sample_quantity, estimated_cost_usd, next_best_action, follow_up_required)
VALUES
    ('a0G000001', '0013x000001', 'R-001', 'T-01', '2025-05-14 09:15', '2025-05', 'F2F', 'Detail', 'Cardivex 10mg', 1, 18, 84, 'Positive', TRUE, TRUE, 5, 165, 'Schedule follow-up detail', TRUE),
    ('a0G000002', '0013x000001', 'R-001', 'T-01', '2025-11-18 10:45', '2025-11', 'Email', 'Detail', 'Cardivex 10mg', 2, 4, 52, 'Neutral', FALSE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000003', '0013x000003', 'R-003', 'T-02', '2025-05-06 08:45', '2025-05', 'F2F', 'Detail', 'Glucenta XR', 1, 22, 88, 'Positive', TRUE, TRUE, 5, 165, 'No action - recently engaged', TRUE),
    ('a0G000004', '0013x000003', 'R-003', 'T-02', '2025-09-09 11:30', '2025-09', 'F2F', 'Detail', 'Glucenta XR', 1, 19, 85, 'Positive', TRUE, FALSE, 0, 165, 'No action - recently engaged', TRUE),
    ('a0G000005', '0013x000003', 'R-003', 'T-02', '2026-02-10 11:30', '2026-02', 'Remote', 'Detail', 'Glucenta XR', 1, 14, 74, 'Positive', FALSE, FALSE, 0, 55, 'Schedule follow-up detail', TRUE),
    ('a0G000006', '0013x000005', 'R-002', 'T-01', '2025-06-10 13:00', '2025-06', 'F2F', 'Sample Drop', 'Cardivex 20mg', 1, 16, 77, 'Positive', TRUE, TRUE, 4, 165, 'Drop samples', TRUE),
    ('a0G000007', '0013x000006', 'R-007', 'T-04', '2025-07-08 10:30', '2025-07', 'Email', 'Detail', 'Neurolyn', 2, 4, 55, 'Neutral', TRUE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000008', '0013x000019', 'R-015', 'T-08', '2025-05-05 09:00', '2025-05', 'F2F', 'Detail', 'Cardivex 10mg', 2, 14, 40, 'Negative', FALSE, TRUE, 4, 165, 'Re-assign / deprioritize', TRUE),
    ('a0G000009', '0013x000019', 'R-015', 'T-08', '2025-08-25 10:45', '2025-08', 'F2F', 'Detail', 'Cardivex 20mg', 2, 13, 39, 'No Response', FALSE, FALSE, 0, 165, 'Re-assign / deprioritize', FALSE),
    ('a0G000010', '0013x000019', 'R-015', 'T-08', '2025-12-09 14:30', '2025-12', 'F2F', 'Follow-up', 'Cardivex 10mg', 2, 12, 37, 'Negative', FALSE, FALSE, 0, 165, 'Re-assign / deprioritize', TRUE),
    ('a0G000011', '0013x000043', 'R-012', 'T-06', '2025-10-21 13:15', '2025-10', 'F2F', 'Detail', 'Neurolyn', 2, 13, 41, 'Negative', FALSE, TRUE, 4, 165, 'Re-assign / deprioritize', TRUE),
    ('a0G000012', '0013x000025', 'R-016', 'T-08', '2026-01-13 13:45', '2026-01', 'Conference', 'Detail', 'Neurolyn', 1, 30, 80, 'Positive', TRUE, FALSE, 0, 240, 'Schedule follow-up detail', TRUE),
    ('a0G000013', '0013x000041', 'R-008', 'T-04', '2025-09-23 14:45', '2025-09', 'Conference', 'Detail', 'Neurolyn', 1, 28, 78, 'Positive', TRUE, FALSE, 0, 240, 'Schedule follow-up detail', TRUE),
    ('a0G000014', '0013x000044', 'R-014', 'T-07', '2026-03-10 10:45', '2026-03', 'Phone', 'Follow-up', 'Cardivex 10mg', 1, 8, 58, 'Neutral', FALSE, FALSE, 0, 25, 'Schedule follow-up detail', FALSE),
    ('a0G000015', '0013x000023', 'R-011', 'T-06', '2025-06-17 09:00', '2025-06', 'Phone', 'Medical Inquiry', 'Neurolyn', 3, 5, 30, 'No Response', FALSE, FALSE, 0, 25, 'No action - recently engaged', FALSE),
    ('a0G000016', '0013x000003', 'MKTG-01', 'T-MKT', '2025-10-15 08:00', '2025-10', 'Email', 'Marketing Email', 'Glucenta XR', 3, 2, 49, 'Neutral', FALSE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000017', '0013x000006', 'MKTG-01', 'T-MKT', '2025-11-15 08:00', '2025-11', 'Email', 'Marketing Email', 'Neurolyn', 3, 2, 44, 'No Response', TRUE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000018', '0013x000019', 'MKTG-01', 'T-MKT', '2026-02-15 08:00', '2026-02', 'Email', 'Marketing Email', 'Cardivex 10mg', 3, 3, 51, 'Neutral', TRUE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000019', '0013x000901', 'R-005', 'T-03', '2025-08-12 11:00', '2025-08', 'Remote', 'Detail', 'Cardivex 20mg', 1, 12, 68, 'Positive', FALSE, FALSE, 0, 55, 'Schedule follow-up detail', TRUE),
    ('a0G000020', '0013x000947', 'MKTG-01', 'T-MKT', '2026-04-20 08:00', '2026-04', 'Email', 'Marketing Email', 'Glucenta XR', 3, 2, 46, 'No Response', FALSE, FALSE, 0, 4, 'Send approved email', FALSE),
    ('a0G000021', '0013x000006', 'R-007', 'T-04', '2026-01-20 14:00', '2026-01', 'Virtual Event', 'Detail', 'Neurolyn', 1, 15, 69, 'Positive', FALSE, FALSE, 0, 70, 'Invite to virtual speaker event', TRUE);
