"""
PULSE-7B inference for ECG images.
Loaded once at specialist server startup and kept in GPU memory.
"""

import io
import json
import os

import torch
from PIL import Image

from inference.config import ECG_CLASSES, ECG_SNOMED


_MODEL = None
_PROCESSOR = None

_MODEL_ID = os.getenv(
    "PULSE_MODEL_ID",
    "PULSE-ECG/PULSE-7B"
)


ECG_PROMPT = """
You are an ECG classification engine.

Analyze the ECG image carefully.

Return ONLY valid JSON.

Do not explain.
Do not use markdown.
Do not use code fences.

Schema:

{
  "rhythm_class": "NORM|MI|STTC|CD|HYP",
  "confidence": 0.0,
  "clinical_flags": ["finding1", "finding2"],
  "reasoning": "one sentence"
}
"""


def _load_model():
    """
    Load PULSE-7B using native LLaVA runtime.
    """

    global _MODEL, _PROCESSOR

    if _MODEL is not None:
        return _MODEL, _PROCESSOR

    print(f"Loading {_MODEL_ID} with LLaVA runtime...")

    from llava.model.builder import load_pretrained_model
    from llava.mm_utils import get_model_name_from_path
    from transformers import CLIPImageProcessor

    model_name = get_model_name_from_path(_MODEL_ID)
    tokenizer, model, _, context_len = \
    load_pretrained_model(
        model_path=_MODEL_ID,
        model_base=None,
        model_name=model_name,
        device="auto",
    )

    image_processor = CLIPImageProcessor.from_pretrained(
        "openai/clip-vit-large-patch14-336"
    )

    _MODEL = model

    _PROCESSOR = {
        "tokenizer": tokenizer,
        "image_processor": image_processor,
        "context_len": context_len,
    }

    print(
        f"PULSE-7B ready. GPU memory: "
        f"{torch.cuda.memory_allocated()/1e9:.2f}GB"
    )

    return _MODEL, _PROCESSOR


def _extract_json(text: str) -> dict:
    """
    Extract JSON object from model output.
    """

    text = text.strip()

    print("\n========== RAW MODEL OUTPUT ==========")
    print(text)
    print("======================================\n")

    start = text.find("{")
    end = text.rfind("}") + 1

    if start >= 0 and end > start:

        candidate = text[start:end]

        try:
            parsed = json.loads(candidate)

            print("\n========== PARSED JSON ==========")
            print(parsed)
            print("=================================\n")

            return parsed

        except Exception as e:
            print(f"JSON parse failed: {e}")
            print(candidate)

    return {}


def analyze_ecg_image(image_bytes: bytes) -> dict:
    """
    Run PULSE-7B on ECG image.
    """

    from llava.constants import (
        IMAGE_TOKEN_INDEX,
        DEFAULT_IMAGE_TOKEN,
    )

    from llava.conversation import conv_templates

    from llava.mm_utils import tokenizer_image_token

    img = Image.open(
        io.BytesIO(image_bytes)
    ).convert("RGB")

    try:

        model, processor = _load_model()

        tokenizer = processor["tokenizer"]
        image_processor = processor["image_processor"]

        conv = conv_templates["llava_v0"].copy()

        inp = DEFAULT_IMAGE_TOKEN + "\n" + ECG_PROMPT

        conv.append_message(conv.roles[0], inp)
        conv.append_message(conv.roles[1], None)

        prompt = conv.get_prompt()

        input_ids = tokenizer_image_token(
            prompt,
            tokenizer,
            IMAGE_TOKEN_INDEX,
            return_tensors="pt",
        ).unsqueeze(0).to(model.device)

        image_tensor = image_processor.preprocess(
            img,
            return_tensors="pt"
        )["pixel_values"]

        image_tensor = image_tensor.to(
            model.device,
            dtype=torch.float16
        )

        with torch.inference_mode():

            output_ids = model.generate(
                input_ids,
                images=image_tensor,
                image_sizes=[img.size],
                do_sample=True,
                temperature=0.2,
                top_p=0.9,
                max_new_tokens=256,
            )

        input_token_len = input_ids.shape[1]

        decoded = tokenizer.batch_decode(
            output_ids[:, input_token_len:],
            skip_special_tokens=True,
        )[0]

        result = _extract_json(decoded)

    except Exception as e:

        print(f"PULSE-7B inference failed: {e}")

        result = {}

    cls = str(
        result.get("rhythm_class", "NORM")
    ).upper().strip()

    if cls not in ECG_CLASSES:
        cls = "NORM"

    try:

        confidence = float(
            result.get("confidence", 0.5)
        )

        confidence = max(
            0.0,
            min(1.0, confidence)
        )

    except Exception:
        confidence = 0.5

    clinical_flags = result.get(
        "clinical_flags",
        []
    )

    if not isinstance(clinical_flags, list):
        clinical_flags = [
            str(clinical_flags)
        ]

    snomed_code, snomed_desc = ECG_SNOMED.get(
        cls,
        ECG_SNOMED["NORM"]
    )

    return {

        "rhythm_class": cls,

        "confidence": confidence,

        "all_class_probs": {
            c: 0.0
            for c in ECG_CLASSES
        },

        "snomed_code": snomed_code,

        "snomed_description": snomed_desc,

        "clinical_flags": clinical_flags[:4],

        "reasoning": str(
            result.get(
                "reasoning",
                f"Classified as {cls}"
            )
        ),
    }