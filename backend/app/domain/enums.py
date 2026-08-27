from enum import StrEnum


class Persona(StrEnum):
    CATEGORY_MANAGER = "Category Manager"
    CXO = "CXO"


class Route(StrEnum):
    RESOLVED = "RESOLVED"
    FAST_PATH = "FAST_PATH"
    UNRESOLVED_CONFLICT = "UNRESOLVED_CONFLICT"
    ABSTAIN = "ABSTAIN"


class Decision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    IGNORED = "ignored"
