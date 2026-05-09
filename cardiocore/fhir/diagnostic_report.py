# OWNER: Binula
# DAY:   3
# PURPOSE: Build a FHIR R4 DiagnosticReport resource
#
# FHIR spec used:
#   resourceType: DiagnosticReport
#   code: LOINC 34552-0 (Cardiac study)
#   result: references to ECG and Echo Observation resources
#   conclusion: human-readable triage summary
#   extension: triage-tier (string) and heart-score (integer)
#
# Expected interface:
#
#   from fhir.diagnostic_report import build_diagnostic_report
#   report = build_diagnostic_report(patient_id, ecg_obs, echo_obs, risk_result)
#   # returns a valid FHIR R4 DiagnosticReport dict

import uuid
from datetime import datetime, timezone

def build_diagnostic_report(patient_id, ecg_obs, echo_obs, risk_result) -> dict:
    tier  = risk_result.get('triage_tier','Unknown')
    score = risk_result.get('heart_score', 0)
    ef    = echo_obs.get('valueQuantity',{}).get('value','?')
    ecg_d = ecg_obs.get('valueCodeableConcept',{}).get('coding',[{}])[0].get('display','?')
    mace  = risk_result.get('mace_10day_probability','?')
    reco  = risk_result.get('recommended_action','?')
    conclusion = (f'CARDIAC TRIAGE: {tier.upper()} (HEART score {score}/10). '
                  f'ECG: {ecg_d}. EF: {ef}%. MACE risk: {mace}. {reco}')
    return {
        'resourceType': 'DiagnosticReport',
        'id': str(uuid.uuid4()),
        'status': 'final',
        'code': {'coding':[{'system':'http://loinc.org','code':'34552-0','display':'Cardiac study'}]},
        'subject': {'reference': f'Patient/{patient_id}'},
        'effectiveDateTime': datetime.now(timezone.utc).isoformat(),
        'result': [
            {'reference':f'Observation/{ecg_obs["id"]}'},
            {'reference':f'Observation/{echo_obs["id"]}'},
        ],
        'conclusion': conclusion,
        'extension': [
            {'url':'triage-tier',  'valueString':  tier},
            {'url':'heart-score',  'valueInteger': score},
        ],
    }
