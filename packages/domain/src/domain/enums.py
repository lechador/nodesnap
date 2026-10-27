"""Normative status vocabulary — spec Part A6.3. Do not invent synonyms."""
from enum import Enum


class InputBasis(str, Enum):
    OFFICIAL_DATASET = "official_dataset"
    PROJECT_DOCUMENT = "project_document"
    USER_SUPPLIED = "user_supplied"
    DEMONSTRATION_ASSUMPTION = "demonstration_assumption"
    DERIVED = "derived"


class MethodState(str, Enum):
    RESEARCH_REQUIRED = "research_required"
    IMPLEMENTED = "implemented"
    VERIFIED_FOR_SCOPE = "verified_for_scope"


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    ERROR = "error"


class CheckOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"
    NOT_APPLICABLE = "not_applicable"


class FreshnessStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"


class ReviewStatus(str, Enum):
    UNREVIEWED = "unreviewed"
    REVIEW_PENDING = "review_pending"
    REVIEWED_WITH_COMMENTS = "reviewed_with_comments"
    REVIEWED_FOR_SCOPE = "reviewed_for_scope"


class DocumentPresence(str, Enum):
    MISSING = "missing"
    PARTIAL = "partial"
    GENERATED = "generated"
    EXPORT_VERIFIED = "export_verified"


class AuthorityProcess(str, Enum):
    NOT_SUBMITTED = "not_submitted"
    EXTERNAL_STATUS_RECORDED = "external_status_recorded"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCEL_REQUESTED = "cancel_requested"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
