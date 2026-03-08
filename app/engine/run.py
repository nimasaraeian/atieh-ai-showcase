import logging
from pathlib import Path

from app.engine.scheduler import build_schedule_draft, generate_recommendations
from app.engine.recommender import recommendations_to_csv
from app.loaders.atieh_excel_loader import (
    parse_doctor_shifts,
    parse_insurance_priority,
    parse_services_catalog,
    parse_unfinished_catalog,
)

logger = logging.getLogger(__name__)


def run_from_files(payload: dict, input_dir: str = "data/inputs", output_dir: str = "data/outputs") -> dict:
    input_path = Path(input_dir)
    ref_path = input_path / "reference"
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    from app.loaders.atieh_loader import _EXCEL_FILES
    doctor_df = parse_doctor_shifts(str(ref_path / _EXCEL_FILES["shifts"]))
    insurance_df = parse_insurance_priority(str(ref_path / _EXCEL_FILES["insurance"]))
    service_df = parse_services_catalog(str(ref_path / _EXCEL_FILES["services"]))
    backlog_df = parse_unfinished_catalog(str(ref_path / _EXCEL_FILES["unfinished"]))

    doctor_df.to_csv(output_path / "normalized_doctor_shifts.csv", index=False)
    insurance_df.to_csv(output_path / "insurance_payment_priority.csv", index=False)
    service_df.to_csv(output_path / "services_catalog.csv", index=False)
    backlog_df.to_csv(output_path / "unfinished_treatments_catalog.csv", index=False)

    recommendations = generate_recommendations(
        payload,
        doctor_df=doctor_df,
        insurance_df=insurance_df,
        service_df=service_df,
        backlog_df=backlog_df,
    )
    draft = build_schedule_draft(recommendations)

    # Use unified CSV exporter so doctor_id / doctor_norm are always present
    recommendations_to_csv(recommendations, str(output_path / "slot_recommendations.csv"))
    pd.DataFrame([draft] if draft else []).to_csv(
        output_path / "schedule_draft.csv", index=False
    )

    logger.info("Outputs written to %s", output_path)
    return {
        "recommendations": recommendations,
        "draft": draft,
    }
