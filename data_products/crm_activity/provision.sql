-- Remove any existing files in the stage folder before re-provisioning
REMOVE @~/crm_activity/;

-- Upload seed data into the user stage under crm_activity/
PUT file://app/data/account.csv  @~/crm_activity/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
PUT file://app/data/activity.csv @~/crm_activity/ AUTO_COMPRESS=FALSE OVERWRITE=TRUE;
