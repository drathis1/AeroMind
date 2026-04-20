from __future__ import annotations

import json
from typing import Any, TypeVar

from pydantic import BaseModel

from aeromind.config import settings

T = TypeVar("T", bound=BaseModel)


class GeminiClient:
    """Thin wrapper around google-genai with structured JSON output."""

    def __init__(self, *, model: str | None = None, api_key: str | None = None) -> None:
        self.model = model or settings.gemini_model_agents
        self.api_key = api_key if api_key is not None else settings.gemini_api_key

    def enabled(self) -> bool:
        return bool(self.api_key)

    async def generate_json(self, system: str, user: str, schema: type[T]) -> T:
        if not self.enabled():
            raise RuntimeError("Gemini API key not configured")
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        resp = await client.aio.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=user)])],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        text = (resp.text or "").strip()
        data = json.loads(text)
        return schema.model_validate(data)

    async def generate_json_loose(self, system: str, user: str) -> dict[str, Any]:
        if not self.enabled():
            raise RuntimeError("Gemini API key not configured")
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        resp = await client.aio.models.generate_content(
            model=self.model,
            contents=[types.Content(role="user", parts=[types.Part.from_text(text=user)])],
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json",
            ),
        )
        text = (resp.text or "").strip()
        return json.loads(text)
