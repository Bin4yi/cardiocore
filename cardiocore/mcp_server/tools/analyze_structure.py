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

router = APIRouter()


@router.post(
    "/tools/analyze_cardiac_structure"
)
async def analyze_cardiac_structure(

    file: UploadFile = File(...),

    patient_id: str = Form("")
):

    start = time.perf_counter()

    content = await file.read()

    ext = Path(
        file.filename or "echo.mp4"
    ).suffix.lower()

    # Supported echo video formats
    if ext not in (
        ".avi",
        ".mp4",
        ".mov"
    ):

        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {ext}"
        )

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(
        suffix=ext,
        delete=False
    ) as tmp:

        tmp.write(content)

        tmp_path = tmp.name

    from inference.echo_structure import (
        analyze_structure
    )

    # Run structural analysis
    result = analyze_structure(
        tmp_path
    )

    # Cleanup temp file
    Path(tmp_path).unlink(
        missing_ok=True
    )

    elapsed_ms = round(
        (
            time.perf_counter() - start
        ) * 1000,
        1
    )

    return {

        "tool":
            "analyze_cardiac_structure",

        "status":
            "success",

        "processing_time_ms":
            elapsed_ms,

        "result": {

            **result,

            "patient_id":
                patient_id or "anonymous"
        }
    }
