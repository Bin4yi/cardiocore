import uuid
from datetime import datetime, timezone


def build_ecg_observation(
    ecg_result: dict,
    patient_id: str
) -> dict:

    interpretation_code = (
        "N"
        if ecg_result["rhythm_class"] == "NORM"
        else "A"
    )

    return {

        "resourceType": "Observation",

        "id": str(uuid.uuid4()),

        "status": "final",

        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "8625-6",
                "display": "ECG rhythm"
            }]
        },

        "subject": {
            "reference": f"Patient/{patient_id}"
        },

        "effectiveDateTime": datetime.now(
            timezone.utc
        ).isoformat(),

        "valueCodeableConcept": {
            "coding": [{
                "system": "http://snomed.info/sct",
                "code": ecg_result["snomed_code"],
                "display": ecg_result["snomed_description"]
            }]
        },

        "interpretation": [{
            "coding": [{
                "system":
                    "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",

                "code": interpretation_code
            }]
        }],

        "note": [{
            "text": "; ".join(
                ecg_result.get(
                    "clinical_flags",
                    []
                )
            )
        }]
    }
