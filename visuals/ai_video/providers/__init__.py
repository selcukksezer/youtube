"""Provider registry package."""
from .fal import FalVideoProvider
from .huggingface import HuggingFaceVideoProvider
from .replicate import ReplicateVideoProvider
from .deepinfra import DeepInfraVideoProvider
from .piapi import PiAPIVideoProvider
from .gemini_veo import GeminiVeoProvider
from .local import LocalVideoProvider
from .runway import RunwayVideoProvider
from .luma import LumaVideoProvider
from .minimax import MiniMaxVideoProvider
from .openai_sora import OpenAISoraProvider
from .higgsfield import HiggsfieldVideoProvider

ALL_PROVIDER_CLASSES = (
    LocalVideoProvider,
    FalVideoProvider,
    HiggsfieldVideoProvider,
    RunwayVideoProvider,
    LumaVideoProvider,
    MiniMaxVideoProvider,
    OpenAISoraProvider,
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
    "HiggsfieldVideoProvider",
    "RunwayVideoProvider",
    "LumaVideoProvider",
    "MiniMaxVideoProvider",
    "OpenAISoraProvider",
    "HuggingFaceVideoProvider",
    "ReplicateVideoProvider",
    "DeepInfraVideoProvider",
    "PiAPIVideoProvider",
    "GeminiVeoProvider",
]
