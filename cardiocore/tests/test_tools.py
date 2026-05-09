# OWNER: Binula
# DAY:   4
# PURPOSE: Tests for all 5 MCP tool endpoints using mock models
#
# Run with: pytest tests/test_tools.py -v
#
# Uses FastAPI TestClient so no running server needed.
# Uses unittest.mock to replace real models with mock responses.
# All tests should pass without GPU.

"""
Integration tests for the 5 MCP tools.

Tests boot a FastAPI test client and exercise each tool's HTTP endpoint
without needing the specialist server, vLLM, or any GPU. Tests that
need real model output (analyze_ecg_leads, estimate_ejection_fraction,
analyze_cardiac_structure) are skipped unless the relevant backends
are reachable.
"""
import io
import json
import os
import struct
import zlib

import httpx
import pytest
from fastapi.testclient import TestClient


# -------- helpers ----------------------------------------------------

def _tiny_png() -> bytes:
    """Build a valid 1x1 PNG in memory (no PIL/numpy needed)."""
    def chunk(name: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(name + data) & 0xffffffff
        return struct.pack('>I', len(data)) + name + data + struct.pack('>I', crc)

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = chunk(b'IHDR', struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0))
    idat = chunk(b'IDAT', zlib.compress(b'\x00\xff\xff\xff'))
    iend = chunk(b'IEND', b'')
    return sig + ihdr + idat + iend


def _tiny_avi() -> bytes:
    """Minimal placeholder bytes labelled as .avi.

    These will be rejected by imageio inside the inference layer, but
    that's fine — these tests verify routing and validation, not
    actual video decoding.
    """
    return b'RIFF\x00\x00\x00\x00AVI '


def _specialist_reachable() -> bool:
    """Skip ECG / echo tests if Instance B's specialist server is down."""
    url = os.getenv('SPECIALIST_SERVER_URL', 'http://localhost:9001')
    try:
        return httpx.get(f'{url}/health', timeout=3).status_code == 200
    except Exception:
        return False


def _vllm_reachable() -> bool:
    """Skip Gemma 4 dependent tests if vLLM is down."""
    url = os.getenv('VLLM_SERVER_URL', 'http://localhost:9000/v1')
    try:
        return httpx.get(f'{url}/models', timeout=3).status_code == 200
    except Exception:
        return False


@pytest.fixture(scope='module')
def client():
    """Boot the MCP app once per module."""
    from mcp_server.main import app
    with TestClient(app) as c:
        yield c


# -------- /mcp/tools and /health ------------------------------------

def test_health_endpoint(client):
    r = client.get('/health')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'healthy'


def test_mcp_tools_lists_all_five(client):
    r = client.get('/mcp/tools')
    assert r.status_code == 200
    body = r.json()
    names = {t['name'] for t in body['tools']}
    assert names == {
        'analyze_ecg_leads',
        'estimate_ejection_fraction',
        'analyze_cardiac_structure',
        'risk_stratify',
        'generate_cardiac_report',
    }


def test_well_known_mcp(client):
    r = client.get('/.well-known/mcp')
    assert r.status_code == 200
    assert r.json()['mcp_tools_url'] == '/mcp/tools'


# -------- Tool 1: analyze_ecg_leads ---------------------------------

def test_ecg_rejects_missing_file(client):
    r = client.post('/tools/analyze_ecg_leads')
    assert r.status_code == 422  # FastAPI validation


def test_ecg_rejects_unsupported_extension(client):
    r = client.post(
        '/tools/analyze_ecg_leads',
        files={'file': ('ecg.txt', b'not an image', 'text/plain')},
    )
    assert r.status_code == 400
    assert 'unsupported' in r.json().get('error', '').lower()


@pytest.mark.skipif(
    not _specialist_reachable(),
    reason='Specialist server (PULSE-7B) not reachable',
)
def test_ecg_routes_to_specialist(client):
    r = client.post(
        '/tools/analyze_ecg_leads',
        files={'file': ('ecg.png', _tiny_png(), 'image/png')},
        data={'patient_id': 'test-001'},
    )
    assert r.status_code == 200
    body = r.json()
    assert body['tool'] == 'analyze_ecg_leads'
    assert body['status'] == 'success'
    result = body['result']
    assert result['rhythm_class'] in ['NORM', 'MI', 'STTC', 'CD', 'HYP']
    assert 'snomed_code' in result
    assert result['patient_id'] == 'test-001'
    assert 'fhir_observation' in result


# -------- Tool 2: estimate_ejection_fraction ------------------------

def test_ef_rejects_unsupported_extension(client):
    r = client.post(
        '/tools/estimate_ejection_fraction',
        files={'file': ('echo.txt', b'not a video', 'text/plain')},
    )
    assert r.status_code == 400


# -------- Tool 3: analyze_cardiac_structure -------------------------

def test_structure_rejects_unsupported_extension(client):
    r = client.post(
        '/tools/analyze_cardiac_structure',
        files={'file': ('echo.txt', b'not a video', 'text/plain')},
    )
    assert r.status_code == 400


# -------- Tool 4: risk_stratify -------------------------------------

def test_risk_low_risk(client):
    r = client.post(
        '/tools/risk_stratify',
        json={
            'ecg_analysis':  {'result': {'rhythm_class': 'NORM'}},
            'echo_analysis': {'result': {'ef_percent': 60.0}},
            'clinical_context': {
                'age': 35,
                'known_conditions': [],
                'troponin_ratio': 0.5,
                'history_suspicion': 'slightly_nonspecific',
            },
        },
    )
    assert r.status_code == 200
    result = r.json()['result']
    assert result['triage_tier'] in ('Normal', 'Routine')
    assert 0 <= result['heart_score'] <= 10


def test_risk_mi_forces_urgent(client):
    """MI on ECG should override to Urgent regardless of HEART score."""
    r = client.post(
        '/tools/risk_stratify',
        json={
            'ecg_analysis':  {'result': {'rhythm_class': 'MI'}},
            'echo_analysis': {'result': {'ef_percent': 60.0}},
            'clinical_context': {
                'age': 35,
                'known_conditions': [],
                'troponin_ratio': 0.5,
            },
        },
    )
    assert r.status_code == 200
    assert r.json()['result']['triage_tier'] == 'Urgent'


def test_risk_low_ef_forces_urgent(client):
    """EF below 35 should override to Urgent."""
    r = client.post(
        '/tools/risk_stratify',
        json={
            'ecg_analysis':  {'result': {'rhythm_class': 'NORM'}},
            'echo_analysis': {'result': {'ef_percent': 20.0}},
            'clinical_context': {'age': 35, 'known_conditions': []},
        },
    )
    assert r.status_code == 200
    assert r.json()['result']['triage_tier'] == 'Urgent'


def test_risk_returns_processing_time(client):
    r = client.post(
        '/tools/risk_stratify',
        json={
            'ecg_analysis': {'result': {'rhythm_class': 'NORM'}},
            'echo_analysis': {'result': {'ef_percent': 55.0}},
            'clinical_context': {},
        },
    )
    assert r.status_code == 200
    assert r.json()['processing_time_ms'] >= 0


# -------- Tool 5: generate_cardiac_report ---------------------------

def test_report_builds_valid_bundle(client):
    r = client.post(
        '/tools/generate_cardiac_report',
        json={
            'patient_id': 'test-007',
            'ecg_analysis': {
                'result': {
                    'rhythm_class': 'MI',
                    'confidence': 0.91,
                    'snomed_code': '57054005',
                    'snomed_description': 'Acute MI',
                    'clinical_flags': ['ST elevation'],
                },
            },
            'echo_analysis': {
                'result': {
                    'ef_percent': 28.5,
                    'hf_classification': 'HFrEF',
                    'hf_snomed_code': '85232009',
                    'hf_snomed_description': 'HFrEF',
                    'wall_motion_flags': ['Reduced'],
                },
            },
            'risk_stratification': {
                'result': {
                    'triage_tier': 'Urgent',
                    'heart_score': 9,
                    'mace_10day_probability': '> 50%',
                    'recommended_action': 'Immediate cardiology consultation',
                },
            },
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body['tool'] == 'generate_cardiac_report'
    result = body['result']
    assert result['validation_passed'] is True
    assert result['triage_tier'] == 'Urgent'
    bundle = result['fhir_bundle']
    assert bundle['resourceType'] == 'Bundle'
    assert len(bundle['entry']) == 3


def test_report_rejects_invalid_input(client):
    """A report with no underlying observations should fail FHIR validation."""
    r = client.post(
        '/tools/generate_cardiac_report',
        json={'patient_id': 'broken'},
    )
    # Either 422 from FHIR validator or 500 — either is acceptable defensive
    # behavior. We just don't want a 200.
    assert r.status_code != 200


# -------- End-to-end chain (no model dependencies) -------------------

def test_chain_risk_then_report(client):
    """risk_stratify output should feed directly into generate_cardiac_report."""
    risk_resp = client.post(
        '/tools/risk_stratify',
        json={
            'ecg_analysis':  {'result': {'rhythm_class': 'MI', 'confidence': 0.91,
                                          'snomed_code': '57054005',
                                          'snomed_description': 'Acute MI',
                                          'clinical_flags': []}},
            'echo_analysis': {'result': {'ef_percent': 28.5,
                                          'hf_classification': 'HFrEF',
                                          'hf_snomed_code': '85232009',
                                          'hf_snomed_description': 'HFrEF',
                                          'wall_motion_flags': []}},
            'clinical_context': {'age': 67,
                                 'known_conditions': ['diabetes'],
                                 'troponin_ratio': 2.8},
        },
    )
    assert risk_resp.status_code == 200

    report_resp = client.post(
        '/tools/generate_cardiac_report',
        json={
            'patient_id': 'chain-001',
            'ecg_analysis': {'result': {'rhythm_class': 'MI', 'confidence': 0.91,
                                          'snomed_code': '57054005',
                                          'snomed_description': 'Acute MI',
                                          'clinical_flags': []}},
            'echo_analysis': {'result': {'ef_percent': 28.5,
                                          'hf_classification': 'HFrEF',
                                          'hf_snomed_code': '85232009',
                                          'hf_snomed_description': 'HFrEF',
                                          'wall_motion_flags': []}},
            'risk_stratification': risk_resp.json(),
        },
    )
    assert report_resp.status_code == 200
    bundle = report_resp.json()['result']['fhir_bundle']
    # Conclusion text should mention the urgent triage tier from risk
    conclusion = next(
        e['resource']['conclusion']
        for e in bundle['entry']
        if e['resource']['resourceType'] == 'DiagnosticReport'
    )
    assert 'URGENT' in conclusion.upper()