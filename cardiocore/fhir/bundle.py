# OWNER: Binula
# DAY:   3
# PURPOSE: Assemble a FHIR R4 Bundle containing DiagnosticReport + Observations
#
# The Bundle is the final output of CardioCore â€” what Prompt Opinion agents receive.
#
# Expected interface:
#
#   from fhir.bundle import build_fhir_bundle, get_summary
#
#   bundle = build_fhir_bundle(
#       patient_id="patient-001",
#       ecg_result=ecg_result_dict,    # from inference/ecg.py
#       echo_result=echo_result_dict,  # from inference/echo.py
#       risk_result=risk_result_dict,  # from inference/heart_score.py
#   )
#   # bundle is a valid FHIR R4 Bundle dict with 3 entries:
#   # DiagnosticReport, ECG Observation, Echo Observation
#
#   summary = get_summary(bundle)
#   # returns: {bundle_id, resource_count, summary, triage_tier}

import uuid
from datetime import datetime, timezone
from fhir.ecg_observation    import build_ecg_observation
from fhir.echo_observation   import build_echo_observation
from fhir.diagnostic_report  import build_diagnostic_report

def build_fhir_bundle(patient_id, ecg_result, echo_result, risk_result) -> dict:
    ecg_obs  = build_ecg_observation(ecg_result,  patient_id)
    echo_obs = build_echo_observation(echo_result, patient_id)
    report   = build_diagnostic_report(patient_id, ecg_obs, echo_obs, risk_result)
    return {
        'resourceType': 'Bundle',
        'id':           str(uuid.uuid4()),
        'type':         'collection',
        'timestamp':    datetime.now(timezone.utc).isoformat(),
        'meta': {'source': 'cardiocore-v1.0'},
        'entry': [
            {'resource': report,   'fullUrl': f'urn:uuid:{report["id"]}'},
            {'resource': ecg_obs,  'fullUrl': f'urn:uuid:{ecg_obs["id"]}'},
            {'resource': echo_obs, 'fullUrl': f'urn:uuid:{echo_obs["id"]}'},
        ],
    }

def get_summary(bundle) -> dict:
    report = next(e['resource'] for e in bundle['entry']
                  if e['resource']['resourceType']=='DiagnosticReport')
    tier   = next((e['valueString'] for e in report.get('extension',[]) if 'triage' in e.get('url','')), 'Unknown')
    return {'bundle_id':bundle['id'],'resource_count':len(bundle['entry']),
            'summary':report.get('conclusion',''),'triage_tier':tier}

