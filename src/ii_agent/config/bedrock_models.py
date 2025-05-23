"""
Configuración de modelos AWS Bedrock para II-agent.
"""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class BedrockModelConfig:
    """Configuración para un modelo de Bedrock."""
    model_id: str
    name: str
    provider: str
    max_tokens: int
    temperature: float
    supports_system_messages: bool
    supports_streaming: bool
    cost_per_1k_input_tokens: float
    cost_per_1k_output_tokens: float


# Configuraciones de modelos disponibles en Bedrock
BEDROCK_MODELS = {
    # Claude Models
    "claude-3-7-sonnet": BedrockModelConfig(
        model_id="anthropic.claude-3-7-sonnet-20250219-v1:0",
        name="Claude 3.7 Sonnet",
        provider="anthropic",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.003,
        cost_per_1k_output_tokens=0.015
    ),
    "claude-3-5-sonnet": BedrockModelConfig(
        model_id="anthropic.claude-3-5-sonnet-20240620-v1:0",
        name="Claude 3.5 Sonnet",
        provider="anthropic",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.003,
        cost_per_1k_output_tokens=0.015
    ),
    "claude-3-sonnet": BedrockModelConfig(
        model_id="anthropic.claude-3-sonnet-20240229-v1:0",
        name="Claude 3 Sonnet",
        provider="anthropic",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.003,
        cost_per_1k_output_tokens=0.015
    ),
    "claude-3-haiku": BedrockModelConfig(
        model_id="anthropic.claude-3-haiku-20240307-v1:0",
        name="Claude 3 Haiku",
        provider="anthropic",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.00025,
        cost_per_1k_output_tokens=0.00125
    ),

    # Amazon Nova Models
    "nova-pro": BedrockModelConfig(
        model_id="amazon.nova-pro-v1:0",
        name="Amazon Nova Pro",
        provider="amazon",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.0008,
        cost_per_1k_output_tokens=0.0032
    ),
    "nova-lite": BedrockModelConfig(
        model_id="amazon.nova-lite-v1:0",
        name="Amazon Nova Lite",
        provider="amazon",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.0002,
        cost_per_1k_output_tokens=0.0008
    ),
    "nova-micro": BedrockModelConfig(
        model_id="amazon.nova-micro-v1:0",
        name="Amazon Nova Micro",
        provider="amazon",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=True,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.000035,
        cost_per_1k_output_tokens=0.00014
    ),

    # Titan Models
    "titan-text-express": BedrockModelConfig(
        model_id="amazon.titan-text-express-v1",
        name="Amazon Titan Text Express",
        provider="amazon",
        max_tokens=4096,
        temperature=0.7,
        supports_system_messages=False,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.0008,
        cost_per_1k_output_tokens=0.0016
    ),
    "titan-embed-image": BedrockModelConfig(
        model_id="amazon.titan-embed-image-v1",
        name="Amazon Titan Multimodal Embeddings G1",
        provider="amazon",
        max_tokens=0,  # Embeddings model
        temperature=0.0,
        supports_system_messages=False,
        supports_streaming=False,
        cost_per_1k_input_tokens=0.0001,
        cost_per_1k_output_tokens=0.0000
    ),
}

# Mapeo de aliases para facilitar el uso
MODEL_ALIASES = {
    "claude": "claude-3-7-sonnet",  # Usar la versión más reciente por defecto
    "claude-3.7": "claude-3-7-sonnet",
    "claude-sonnet": "claude-3-5-sonnet",
    "claude-3.5": "claude-3-5-sonnet",
    "claude-3": "claude-3-sonnet",
    "claude-fast": "claude-3-haiku",
    "nova": "nova-pro",
    "nova-pro": "nova-pro",
    "nova-lite": "nova-lite",
    "nova-micro": "nova-micro",
    "titan": "titan-text-express",
    "titan-embeddings": "titan-embed-image",
}

# Configuración por defecto - Nova Pro como modelo principal
DEFAULT_MODEL = "nova-pro"


def get_model_config(model_name: str) -> BedrockModelConfig:
    """
    Obtiene la configuración de un modelo.

    Args:
        model_name: Nombre del modelo o alias

    Returns:
        Configuración del modelo

    Raises:
        ValueError: Si el modelo no existe
    """
    # Resolver alias
    resolved_name = MODEL_ALIASES.get(model_name, model_name)

    if resolved_name not in BEDROCK_MODELS:
        available_models = list(BEDROCK_MODELS.keys()) + list(MODEL_ALIASES.keys())
        raise ValueError(f"Modelo '{model_name}' no encontrado. Modelos disponibles: {available_models}")

    return BEDROCK_MODELS[resolved_name]


def list_available_models() -> Dict[str, BedrockModelConfig]:
    """
    Lista todos los modelos disponibles.

    Returns:
        Diccionario con todos los modelos disponibles
    """
    return BEDROCK_MODELS.copy()


def get_model_by_provider(provider: str) -> Dict[str, BedrockModelConfig]:
    """
    Obtiene modelos filtrados por proveedor.

    Args:
        provider: Proveedor (anthropic, amazon)

    Returns:
        Diccionario con modelos del proveedor especificado
    """
    return {
        name: config for name, config in BEDROCK_MODELS.items()
        if config.provider == provider
    }


def estimate_cost(
    model_name: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estima el costo de una consulta.

    Args:
        model_name: Nombre del modelo
        input_tokens: Número de tokens de entrada
        output_tokens: Número de tokens de salida

    Returns:
        Costo estimado en USD
    """
    config = get_model_config(model_name)

    input_cost = (input_tokens / 1000) * config.cost_per_1k_input_tokens
    output_cost = (output_tokens / 1000) * config.cost_per_1k_output_tokens

    return input_cost + output_cost
