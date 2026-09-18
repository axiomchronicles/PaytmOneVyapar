from enum import StrEnum


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    MODIFIED = "MODIFIED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class OrderStatus(StrEnum):
    PROPOSED = "PROPOSED"
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVED = "APPROVED"
    EXECUTING = "EXECUTING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class ExecutionStatus(StrEnum):
    NOT_STARTED = "NOT_STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class NegotiationStatus(StrEnum):
    STARTED = "STARTED"
    COUNTER_OFFER = "COUNTER_OFFER"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class AgentRunStatus(StrEnum):
    RUNNING = "RUNNING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ChannelType(StrEnum):
    API = "API"
    FLUTTER = "FLUTTER"
    WHATSAPP = "WHATSAPP"  # Coming soon
    TELEGRAM = "TELEGRAM"
    VOICE = "VOICE"


class TransactionStatus(StrEnum):
    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class OtpPurpose(StrEnum):
    LOGIN = "LOGIN"
    REGISTRATION = "REGISTRATION"


class OAuthProvider(StrEnum):
    GOOGLE = "GOOGLE"
    APPLE = "APPLE"


class NotificationType(StrEnum):
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    ORDER_UPDATE = "ORDER_UPDATE"
    INVENTORY_ALERT = "INVENTORY_ALERT"
