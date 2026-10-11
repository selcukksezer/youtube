"""Provider registry package."""
from .agnes import AgnesVideoProvider
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
from .helios import HeliosVideoProvider
from .pollinations import PollinationsVideoProvider

ALL_PROVIDER_CLASSES = (
    LocalVideoProvider,
    AgnesVideoProvider,
    PollinationsVideoProvider,
    HeliosVideoProvider,
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
    "AgnesVideoProvider",
    "LocalVideoProvider",
    "PollinationsVideoProvider",
    "HeliosVideoProvider",
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
