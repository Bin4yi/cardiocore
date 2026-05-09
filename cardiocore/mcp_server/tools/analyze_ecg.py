import time
import tempfile

from pathlib import Path

from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    HTTPException
)

from fhir.ecg_observation import (
    build_ecg_observation
)

router = APIRouter()


@router.post("/tools/analyze_ecg_leads")
async def analyze_ecg_leads(

    file: UploadFile = File(...),

    patient_id: str = Form("")
):

    start = time.perf_counter()

    content = await file.read()

    ext = Path(
        file.filename or "ecg.png"
    ).suffix.lower()

    # Supported formats
    if ext not in (
        ".png",
        ".jpg",
        ".jpeg",
        ".csv"
    ):

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}"
        )

    from inference.ecg import (
        analyze_from_image_bytes,
        analyze_from_csv
    )

    # CSV ECG signal
    if ext == ".csv":

        with tempfile.NamedTemporaryFile(
            suffix=".csv",
            delete=False
        ) as tmp:

            tmp.write(content)

            tmp_path = tmp.name

        result = analyze_from_csv(
            tmp_path
        )

        Path(tmp_path).unlink(
            missing_ok=True
        )

    # ECG image
    else:

        result = analyze_from_image_bytes(
            content
        )

    pid = patient_id or "anonymous"

    # Build FHIR observation
    fhir_obs = build_ecg_observation(
        result,
        pid
    )

    elapsed_ms = round(
        (
            time.perf_counter() - start
        ) * 1000,
        1
    )

    return {

        "tool": "analyze_ecg_leads",

        "status": "success",

        "processing_time_ms": elapsed_ms,

        "result": {

            **result,

            "patient_id": pid,

            "fhir_observation": fhir_obs
        }
    }
