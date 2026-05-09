# OWNER: Binula
# DAY:   4
# PURPOSE: Tests for HEART score formula
#
# Run with: pytest tests/test_heart_score.py -v

from inference.heart_score import HEARTScorer

def test_low_risk():
    s = HEARTScorer()
    r = s.compute({'history_suspicion':'slightly_nonspecific',
                   'ecg_result':'normal','age':40,'risk_factors':[],
                   'troponin_ratio':0.8})
    assert r['heart_score'] == 0
    assert r['triage_tier'] == 'Normal'

def test_high_risk():
    s = HEARTScorer()
    r = s.compute({'history_suspicion':'highly_suspicious',
                   'ecg_result':'significant_deviation','age':70,
                   'risk_factors':['diabetes','hypertension','smoking'],
                   'troponin_ratio':4.0})
    assert r['heart_score'] == 10
    assert r['triage_tier'] == 'Urgent'

def test_components_sum():
    r = HEARTScorer().compute({})
    assert sum(r['component_scores'].values()) == r['heart_score']

