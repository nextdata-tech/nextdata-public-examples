-- (Re)create a dedicated named internal stage for the Snowpark handler.
-- CREATE OR REPLACE clears any prior contents, so no separate REMOVE is needed.
CREATE OR REPLACE STAGE rep_territory_performance;

-- Upload the Snowpark handler
PUT file://app/handlers/scorecard.py @rep_territory_performance/ OVERWRITE=TRUE;
