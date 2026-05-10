import json
import logging
import os
from typing import List, Optional

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

logging.basicConfig(level=logging.INFO)

GEMMA_BASE_URL = os.getenv(
    "GEMMA_BASE_URL",
    "http://localhost:9000/v1"
)

MODEL_NAME = os.getenv(
    "MODEL_NAME",
    "google/gemma-3-4b-it"
)


class Gemma4Client:

    def __init__(self):

        self.client = OpenAI(
            base_url=GEMMA_BASE_URL,
            api_key="not-needed"
        )

        # Auto-discover model from vLLM instead of using hardcoded name
        try:
            models = self.client.models.list()
            self._model_id = models.data[0].id
            logging.info(f"Auto-discovered model: {self._model_id}")
        except Exception as e:
            logging.warning(f"Could not auto-discover model, using default: {e}")
            self._model_id = MODEL_NAME

    @property
    def model_id(self):

        return self._model_id

    def healthy(self) -> bool:

        try:

            models = self.client.models.list()

            return len(models.data) > 0

        except Exception as e:

            logging.error(f"Health check failed: {e}")

            return False

    def chat(
        self,
        system_prompt: str,
        user_text: str,
        images_b64: Optional[List[str]] = None,
        max_tokens: int = 300,
        temperature: float = 0.2
    ) -> str:

        try:

            logging.info("Sending request to Gemma")

            content = []

            if images_b64:

                for img_b64 in images_b64:

                    content.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_b64}"
                        }
                    })

            content.append({
                "type": "text",
                "text": user_text
            })

            response = self.client.chat.completions.create(
                model=self.model_id,
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                max_tokens=max_tokens,
                temperature=temperature
            )

            result = response.choices[0].message.content

            logging.info("Gemma response received")

            return result

        except Exception as e:

            logging.error(f"Gemma request failed: {e}")

            raise

    def parse_json(self, text: str):

        t = text.strip()

        if "```" in t:

            parts = t.split("```")

            for p in parts:

                p = p.strip().lstrip("json").strip()

                try:
                    return json.loads(p)

                except:
                    pass

        return json.loads(t)


_client = None


def get_client():

    global _client

    if _client is None:

        _client = Gemma4Client()

    return _client
