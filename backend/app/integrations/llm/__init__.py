from app.integrations.llm.azure_foundry import AzureFoundryLLMProvider
from app.integrations.llm.base import DisabledLLMProvider


def build_llm_provider(settings):
    if settings.llm_provider == "disabled":
        return DisabledLLMProvider()
    return AzureFoundryLLMProvider(
        endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
        deployment=settings.llm_model,
    )


__all__ = ["AzureFoundryLLMProvider", "DisabledLLMProvider", "build_llm_provider"]
