"""
ECG analysis client. Calls the specialist server, which runs PULSE-7B
on Instance B. This module does no model loading itself.
"""
import base64
import io
import os
from typing import Optional

import httpx
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

from inference.config import ECG_CLASSES, ECG_SNOMED


SPECIALIST_URL = os.getenv('SPECIALIST_SERVER_URL',
                            'http://INSTANCE_B_IP:9001')

LEAD_NAMES = ['I', 'II', 'III', 'aVR', 'aVL', 'aVF',
              'V1', 'V2', 'V3', 'V4', 'V5', 'V6']


def analyze_from_image_bytes(image_bytes: bytes) -> dict:
    """Send ECG image to specialist server (PULSE-7B). Return structured result."""
    try:
        with httpx.Client(timeout=120) as client:
            r = client.post(
                f'{SPECIALIST_URL}/models/ecg/classify',
                files={'file': ('ecg.png', image_bytes, 'image/png')},
            )
            r.raise_for_status()
            return r.json()
    except Exception as e:
        # Fallback: return a benign default so downstream code still works
        snomed_code, snomed_desc = ECG_SNOMED['NORM']
        return {
            'rhythm_class':       'NORM',
            'confidence':         0.0,
            'all_class_probs':    {c: 0.0 for c in ECG_CLASSES},
            'snomed_code':        snomed_code,
            'snomed_description': snomed_desc,
            'clinical_flags':     [],
            'reasoning':          f'PULSE-7B unavailable: {e}',
        }


def analyze_from_csv(csv_path: str) -> dict:
    """Render CSV signal as image, then send to specialist server."""
    import pandas as pd
    sig = pd.read_csv(csv_path, header=None).values.T.astype('float32')
    img_bytes = render_signal(sig)
    return analyze_from_image_bytes(img_bytes)


def render_signal(signal: np.ndarray) -> bytes:
    """Render a 12-lead signal array as a PNG image."""
    fig = plt.figure(figsize=(14, 7), facecolor='white')
    gs = gridspec.GridSpec(6, 2, figure=fig, hspace=0.55, wspace=0.25)
    t = np.linspace(0, 10, signal.shape[1])
    for i, lead in enumerate(LEAD_NAMES):
        ax = fig.add_subplot(gs[i % 6, i // 6])
        ax.plot(t, signal[i], 'k-', linewidth=0.7)
        ax.set_title(lead, fontsize=9, pad=1)
        ax.set_xlim(0, 10)
        ax.set_ylim(-4, 4)
        ax.tick_params(labelsize=6)
        ax.grid(True, alpha=0.3, color='salmon', linestyle=':')
        ax.set_facecolor('#fff8f0')
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close(fig)
    return buf.getvalue()


# Kept for backwards compatibility with mcp_server/main.py — now a no-op
def get_classifier():
    """No longer loads anything. Kept so existing imports don't break."""
    return None
