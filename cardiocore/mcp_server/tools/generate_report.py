# OWNER: Binula
# DAY:   3
# PURPOSE: Tool 5 â€” POST /tools/generate_cardiac_report
#
# Accepts: JSON body:
#   {
#     patient_id:        "patient-001",
#     ecg_analysis:      {result: {...}},    <- output from Tool 1
#     echo_analysis:     {result: {...}},    <- output from Tool 2
#     risk_stratification: {result: {...}},  <- output from Tool 4
#   }
#
# Flow:
#   1. Extract result dicts from each analysis
#   2. Build FHIR Bundle via fhir/bundle.py
#   3. Validate bundle via fhir/validator.py
#   4. Return bundle + summary
#
# Returns:
#   {tool, status, processing_time_ms, result: {
#       fhir_bundle, bundle_id, resource_count, summary, triage_tier
#   }}

import time
from fastapi import APIRouter, HTTPException
from fhir.bundle import build_fhir_bundle, get_summary
from fhir.validator import validate_bundle

router = APIRouter()

@router.post('/tools/generate_cardiac_report')
async def generate_cardiac_report(body: dict):
    start      = time.perf_counter()
    patient_id = body.get('patient_id','anonymous')

    def ext(d): return d.get('result', d)

    ecg_result  = ext(body.get('ecg_analysis',{}))
    echo_result = ext(body.get('echo_analysis',{}))
    risk_result = ext(body.get('risk_stratification',{}))

    bundle = build_fhir_bundle(patient_id, ecg_result, echo_result, risk_result)
    valid, errors = validate_bundle(bundle)
    if not valid:
        raise HTTPException(422, f'FHIR validation failed: {errors}')

    summary = get_summary(bundle)
    ms = round((time.perf_counter()-start)*1000,1)
    return {'tool':'generate_cardiac_report','status':'success',
            'processing_time_ms':ms,
            'result':{**summary,'fhir_bundle':bundle,'validation_passed':True}}

