from nxd.spec import SamplingMethod
from nxd.spec import semantic_model
from nxd.spec.data_types import float64
from nxd.spec.data_types import int64
from nxd.spec.data_types import string

adverse_event_summary = (
    semantic_model("adverse_event_summary")
    .sampling(method=SamplingMethod.Head)
    .description(
        "FAERS-shaped adverse-event summary per product, region, and reporting period. "
        "Pharmacovigilance / Drug Safety team. SYNTHETIC data; FICTIONAL products. "
        "Provides the adverse-event numerator for the federated reporting-rate calculation."
    )
    .schema({
        "product_id":           (string(),  "Product identifier. Federated join key."),
        "product_name":         (string(),  "Brand name of the product (fictional)."),
        "region":               (string(),  "Geographic region. Join key: North America / Europe / Asia-Pacific."),
        "report_period":        (string(),  "Reporting quarter. Join key. e.g. 2025-Q1."),
        "adverse_event_count":  (int64(),   "Total adverse-event reports — the numerator for reporting rate per 1k Rx."),
        "serious_event_count":  (int64(),   "Subset of adverse events flagged serious per regulatory criteria."),
        "hospitalization_count":(int64(),   "Adverse events that led to hospitalisation."),
        "death_count":          (int64(),   "Adverse events with a fatal outcome."),
        "top_reaction_group":   (string(),  "Leading MedDRA System Organ Class for this slice."),
        "primary_suspect_count":(int64(),   "Cases where this product was the primary suspect drug."),
        "avg_patient_age":      (float64(), "Mean patient age across the reports."),
    })
)
