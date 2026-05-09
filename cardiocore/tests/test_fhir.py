# OWNER: Binula
# DAY:   4
# PURPOSE: Tests for FHIR builders and validator
#
# Run with: pytest tests/test_fhir.py -v
#
# Mock data to use in tests:
MOCK_ECG_RESULT = {
    "rhythm_class": "MI",
    "confidence": 0.91,
    "snomed_code": "57054005",
    "snomed_description": "Acute myocardial infarction",
    "clinical_flags": ["ST elevation pattern detected"],
    "reasoning": "ST elevation in V1-V4.",
}

MOCK_ECHO_RESULT = {
    "ef_percent": 28.5,
    "hf_classification": "HFrEF",
    "hf_snomed_code": "85232009",
    "hf_snomed_description": "Heart failure with reduced ejection fraction",
    "wall_motion_flags": ["Severely reduced systolic function"],
    "confidence": 0.87,
    "reasoning": "Reduced LV contractility.",
}

MOCK_RISK_RESULT = {
    "heart_score": 9,
    "triage_tier": "Urgent",
    "mace_10day_probability": "> 50%",
    "recommended_action": "Immediate cardiology consultation",
    "component_scores": {"H": 2, "E": 2, "A": 2, "R": 1, "T": 2},
}

import json
from fhir.bundle import build_fhir_bundle, get_summary
from fhir.validator import validate_bundle

ECG  = {'rhythm_class':'MI','confidence':0.91,'snomed_code':'57054005',
        'snomed_description':'Acute MI','clinical_flags':['ST elevation']}
ECHO = {'ef_percent':28.5,'hf_classification':'HFrEF','hf_snomed_code':'85232009',
        'hf_snomed_description':'HFrEF','wall_motion_flags':['Reduced']}
RISK = {'triage_tier':'Urgent','heart_score':9,'mace_10day_probability':'> 50%',
        'recommended_action':'Immediate cardiology consultation'}

def test_bundle_structure():
    b = build_fhir_bundle('p001', ECG, ECHO, RISK)
    assert b['resourceType'] == 'Bundle'
    assert len(b['entry']) == 3

def test_bundle_validates():
    b = build_fhir_bundle('p001', ECG, ECHO, RISK)
    ok, errs = validate_bundle(b)
    assert ok, f'Validation failed: {errs}'

def test_bundle_json_serializable():
    b = build_fhir_bundle('p001', ECG, ECHO, RISK)
    assert len(json.dumps(b)) > 100

def test_bundle_summary():
    b = build_fhir_bundle('p001', ECG, ECHO, RISK)
    s = get_summary(b)
    assert s['triage_tier'] == 'Urgent'
    assert len(s['summary']) > 20

