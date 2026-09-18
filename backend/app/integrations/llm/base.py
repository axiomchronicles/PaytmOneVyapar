from collections.abc import Sequence

from pydantic import BaseModel

from app.core.errors import ProviderError


class DisabledLLMProvider:
    async def structured(
        self, messages: Sequence[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        raise ProviderError("LLM integration is disabled; deterministic services remain available")
