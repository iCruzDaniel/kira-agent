import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"), override=False)

PROVEEDOR = os.getenv("PROVEEDOR_MODELO", "openrouter").strip().lower()


def _required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Falta la variable de entorno {name} para PROVEEDOR_MODELO={PROVEEDOR}."
        )
    return value


def get_model(temperature: float = 0.3):
    """Crea el modelo del asistente según PROVEEDOR_MODELO.

    Valores soportados: openrouter (default), openai_compatible, bedrock, ollama, gemini.
    """
    if PROVEEDOR == "bedrock":
        from strands.models import BedrockModel

        return BedrockModel(
            model_id=_required("BEDROCK_MODEL_ID"),
            region_name=os.getenv("AWS_REGION", "us-east-2"),
            temperature=temperature,
            max_tokens=1024,
        )

    if PROVEEDOR == "ollama":
        from strands.models.ollama import OllamaModel

        return OllamaModel(
            host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            model_id=os.getenv("OLLAMA_MODEL_ID", "llama3.1"),
        )

    if PROVEEDOR == "gemini":
        from strands.models.gemini import GeminiModel

        return GeminiModel(
            client_args={"api_key": _required("GEMINI_API_KEY")},
            model_id=os.getenv("GEMINI_MODEL_ID", "gemini-2.5-flash"),
            params={"temperature": temperature},
        )

    if PROVEEDOR == "openai_compatible":
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={
                "api_key": _required("OPENAI_COMPAT_API_KEY"),
                "base_url": _required("OPENAI_COMPAT_BASE_URL"),
            },
            model_id=_required("OPENAI_COMPAT_MODEL_ID"),
            params={"temperature": temperature, "max_tokens": 1024},
        )

    if PROVEEDOR == "openrouter":
        from strands.models.openai import OpenAIModel

        return OpenAIModel(
            client_args={
                "api_key": _required("OPEN_ROUTER_API_KEY"),
                "base_url": os.getenv("OPEN_ROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            },
            model_id=_required("OPEN_ROUTER_MODEL"),
            params={
                "temperature": temperature,
                "extra_body": {"reasoning": {"exclude": True}},
                "max_tokens": 1024,
            },
        )

    raise ValueError(
        f"PROVEEDOR_MODELO='{PROVEEDOR}' no soportado. "
        "Usa: openrouter, openai_compatible, bedrock, ollama o gemini."
    )
