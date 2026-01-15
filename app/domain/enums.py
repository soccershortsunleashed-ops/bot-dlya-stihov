from enum import StrEnum, auto


class OrderStatus(StrEnum):
    PENDING = auto()
    PAID = auto()
    CANCELLED = auto()


class OrderStageStatus(StrEnum):
    PENDING = auto()
    PAID = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


class PaymentStatus(StrEnum):
    PENDING = auto()
    SUCCEEDED = auto()
    CANCELED = auto()
    FAILED = auto()


class ProviderKind(StrEnum):
    YANDEX_GPT = auto()
    SPEECHKIT = auto()
    SUNO = auto()
    PIKA = auto()
    DUMMY = auto()
    GEMINI = "gemini"
    OPENAI = auto()


class ArtifactType(StrEnum):
    TEXT = auto()
    AUDIO = auto()
    IMAGE = auto()
    VIDEO = auto()


class StageType(StrEnum):
    POEM = auto()
    VOICE = auto()
    SONG = auto()
    CLIP = auto()