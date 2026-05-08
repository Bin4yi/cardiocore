import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

VLLM_SERVER_URL = os.getenv('VLLM_SERVER_URL', 'http://localhost:9000/v1')
VLLM_TIMEOUT    = float(os.getenv('VLLM_TIMEOUT', '60'))
HF_TOKEN        = os.getenv('HF_TOKEN')

ECG_CLASSES = ['NORM', 'MI', 'STTC', 'CD', 'HYP']
ECG_SNOMED  = {
    'NORM': ('251139008', 'Normal sinus rhythm'),
    'MI':   ('57054005',  'Acute myocardial infarction'),
    'STTC': ('428750005', 'ST-T wave change'),
    'CD':   ('44808001',  'Conduction disorder of heart'),
    'HYP':  ('266249003', 'Cardiac hypertrophy'),
}
HF_CLASSES = {
    'HFrEF':     ('85232009',  'Heart failure with reduced ejection fraction',   0,  40),
    'HFmrEF':    ('703272007', 'Heart failure with mid-range ejection fraction', 40, 50),
    'Borderline':('40739000',  'Reduced cardiac function',                       50, 55),
    'Normal':    ('72696002',  'Normal cardiac function',                         55,100),
}
LOINC_ECG    = '8625-6'
LOINC_EF     = '10230-1'
LOINC_REPORT = '34552-0'
