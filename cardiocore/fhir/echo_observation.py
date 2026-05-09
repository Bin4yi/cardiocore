import uuid

from datetime import (
    datetime,
    timezone
)


def build_echo_observation(
    echo_result: dict,
    patient_id: str
) -> dict:

    ef = round(
        echo_result.get(
            "ef_percent",
            55.0
        ),
        1
    )

    # Interpretation codes:
    # N  = Normal
    # L  = Low
    # LL = Critically low

    interpretation_code = (
        "LL"
        if ef < 40
        else "L"
        if ef < 55
        else "N"
    )

    return {

        "resourceType": "Observation",

        "id": str(uuid.uuid4()),

        "status": "final",

        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "10230-1",
                "display":
                    "Left ventricular Ejection fraction"
            }]
        },

        "subject": {
            "reference": f"Patient/{patient_id}"
        },

        "effectiveDateTime": datetime.now(
            timezone.utc
        ).isoformat(),

        "valueQuantity": {

            "value": ef,

            "unit": "%",

            "system":
                "http://unitsofmeasure.org",

            "code": "%"
        },

        "interpretation": [{
            "coding": [{
                "system":
                    "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",

                "code": interpretation_code
            }]
        }]
    }
