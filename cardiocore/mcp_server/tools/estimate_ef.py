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

from fhir.echo_observation import (
    build_echo_observation
)

router = APIRouter()


@router.post(
    "/tools/estimate_ejection_fraction"
)
async def estimate_ejection_fraction(

    file: UploadFile = File(...),

    patient_id: str = Form("")
):

    start = time.perf_counter()

    content = await file.read()

    ext = Path(
        file.filename or "echo.mp4"
    ).suffix.lower()

    # Supported video formats
    if ext not in (
        ".avi",
        ".mp4",
        ".mov"
    ):

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}"
        )

    # Save temp video
    with tempfile.NamedTemporaryFile(
        suffix=ext,
        delete=False
    ) as tmp:

        tmp.write(content)

        tmp_path = tmp.name

    from inference.echo import (
        analyze_echo
    )

    # Run inference
    result = analyze_echo(
        tmp_path
    )

    # Cleanup temp file
    Path(tmp_path).unlink(
        missing_ok=True
    )

    pid = patient_id or "anonymous"

    # Build FHIR observation
    fhir_obs = build_echo_observation(
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

        "tool":
            "estimate_ejection_fraction",

        "status":
            "success",

        "processing_time_ms":
            elapsed_ms,

        "result": {

            **result,

            "patient_id": pid,

            "fhir_observation": fhir_obs
        }
    }
