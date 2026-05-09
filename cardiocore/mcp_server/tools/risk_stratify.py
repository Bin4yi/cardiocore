# OWNER: Binula
# DAY:   3
# PURPOSE: Tool 4 â€” POST /tools/risk_stratify
#
# Accepts: JSON body:
#   {
#     ecg_analysis:     {result: {rhythm_class, confidence, ...}},
#     echo_analysis:    {result: {ef_percent, hf_classification, ...}},
#     clinical_context: {age, known_conditions, troponin_ratio, history_suspicion}
#   }
#
# Flow:
#   1. Extract ECG class and map to HEART ECG component score
#   2. Extract EF and apply critical override rules (MI or EF<35 -> Urgent)
#   3. Run HEARTScorer.compute() with all inputs
#   4. Return structured response
#
# Returns:
#   {tool, status, processing_time_ms, result: {
#       heart_score, component_scores, triage_tier,
#       mace_10day_probability, recommended_action
#   }}

import time
from fastapi import APIRouter
from inference.heart_score import HEARTScorer

router  = APIRouter()
_scorer = HEARTScorer()

ECG_TO_HEART = {
    'NORM':'normal','STTC':'nonspecific_repol',
    'MI':'significant_deviation','CD':'nonspecific_repol','HYP':'nonspecific_repol',
}

@router.post('/tools/risk_stratify')
async def risk_stratify(body: dict):
    start   = time.perf_counter()
    ecg     = body.get('ecg_analysis',{}).get('result',{})
    echo    = body.get('echo_analysis',{}).get('result',{})
    clin    = body.get('clinical_context',{})
    ecg_cls = ecg.get('rhythm_class','NORM')
    ef      = float(echo.get('ef_percent', 55.0))
    inputs  = {
        'history_suspicion': clin.get('history_suspicion','moderately'),
        'ecg_result':        ECG_TO_HEART.get(ecg_cls,'nonspecific_repol'),
        'age':               int(clin.get('age', 60)),
        'risk_factors':      clin.get('known_conditions', []),
        'troponin_ratio':    float(clin.get('troponin_ratio', 1.0)),
    }
    result = _scorer.compute(inputs)
    # Override for critical findings
    if ecg_cls == 'MI' or ef < 35:
        result['triage_tier']       = 'Urgent'
        result['recommended_action'] = 'Immediate cardiology consultation'
    ms = round((time.perf_counter()-start)*1000, 1)
    return {'tool':'risk_stratify','status':'success',
            'processing_time_ms':ms,'result':result}


