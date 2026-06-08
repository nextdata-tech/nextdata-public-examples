from nxd.spec import SamplingMethod
from nxd.spec import semantic_model
from nxd.spec.data_types import float64
from nxd.spec.data_types import int64
from nxd.spec.data_types import string

prescription_volume = (
    semantic_model("prescription_volume")
    .sampling(method=SamplingMethod.Head)
    .description(
        "Prescription volume per product, region, and reporting period. "
        "Commercial Analytics team. Provides the exposure denominator. "
        "SYNTHETIC data; FICTIONAL products."
    )
    .schema({
        "product_id":          (string(),  "Product identifier. Federated join key."),
        "product_name":        (string(),  "Brand name of the product (fictional)."),
        "region":              (string(),  "Geographic region. Join key: North America / Europe / Asia-Pacific."),
        "report_period":       (string(),  "Reporting quarter. Join key. e.g. 2025-Q1."),
        "total_prescriptions": (int64(),   "Total prescriptions (TRx) — the exposure denominator for reporting rate."),
        "new_prescriptions":   (int64(),   "New prescriptions (NRx) in the period."),
        "patient_count":       (int64(),   "Distinct patients treated."),
        "units_dispensed":     (int64(),   "Total units dispensed."),
        "avg_days_of_therapy": (float64(), "Average days of therapy per patient."),
        "prescriber_count":    (int64(),   "Distinct prescribers."),
    })
)
