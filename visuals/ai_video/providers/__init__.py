"""Provider registry package."""
from .fal import FalVideoProvider
from .huggingface import HuggingFaceVideoProvider
from .replicate import ReplicateVideoProvider
from .deepinfra import DeepInfraVideoProvider
from .piapi import PiAPIVideoProvider
from .gemini_veo import GeminiVeoProvider
from .local import LocalVideoProvider

ALL_PROVIDER_CLASSES = (
    LocalVideoProvider,
    FalVideoProvider,
    HuggingFaceVideoProvider,
    ReplicateVideoProvider,
    DeepInfraVideoProvider,
    PiAPIVideoProvider,
    GeminiVeoProvider,
)

__all__ = [
    "ALL_PROVIDER_CLASSES",
    "LocalVideoProvider",
    "FalVideoProvider",
    "HuggingFaceVideoProvider",
    "ReplicateVideoProvider",
    "DeepInfraVideoProvider",
    "PiAPIVideoProvider",
    "GeminiVeoProvider",
]
