import time
from collections.abc import Sequence

from langchain_openai import AzureChatOpenAI, ChatOpenAI
from pydantic import BaseModel, SecretStr

from app.infrastructure.observability.metrics import llm_latency, llm_tokens


class AzureFoundryLLMProvider:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: SecretStr,
        api_version: str | None,
        deployment: str,
    ) -> None:
        if endpoint.rstrip("/").endswith("/openai/v1"):
            self.client = ChatOpenAI(
                base_url=endpoint.rstrip("/") + "/",
                api_key=api_key,
                model=deployment,
                temperature=0,
                max_retries=2,
            )
        else:
            if not api_version:
                raise ValueError("Azure deployment endpoints require an API version")
            self.client = AzureChatOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
                azure_deployment=deployment,
                temperature=0,
                max_retries=2,
            )

    async def structured(
        self, messages: Sequence[dict[str, str]], schema: type[BaseModel]
    ) -> BaseModel:
        runnable = self.client.with_structured_output(
            schema, method="json_schema", include_raw=True
        )
        started = time.perf_counter()
        result = await runnable.ainvoke(list(messages))
        llm_latency.record((time.perf_counter() - started) * 1000)
        raw = result.get("raw")
        usage = getattr(raw, "usage_metadata", None) or {}
        for direction in ("input_tokens", "output_tokens"):
            if usage.get(direction) is not None:
                llm_tokens.add(usage[direction], {"direction": direction})
        return result["parsed"]

    async def generate(self, messages: Sequence[dict[str, str]]) -> str:
        started = time.perf_counter()
        result = await self.client.ainvoke(list(messages))
        llm_latency.record((time.perf_counter() - started) * 1000)
        usage = getattr(result, "usage_metadata", None) or {}
        for direction in ("input_tokens", "output_tokens"):
            if usage.get(direction) is not None:
                llm_tokens.add(usage[direction], {"direction": direction})
        return str(result.content).strip()
