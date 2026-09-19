from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel

from app.core.errors import ProviderError


class DisabledLLMProvider:
    async def structured(
        self, messages: Sequence[dict[str, Any]], schema: type[BaseModel]
    ) -> BaseModel:
        raise ProviderError("LLM integration is disabled; deterministic services remain available")

    async def generate(self, messages: Sequence[dict[str, str]]) -> str:
        raise ProviderError("LLM integration is disabled; deterministic services remain available")
