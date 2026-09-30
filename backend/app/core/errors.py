"""Application error taxonomy shared by services and API handlers."""


class AppError(Exception):
    """Base error with a stable public code and HTTP status."""

    code = "application_error"
    status_code = 500

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ResourceNotFoundError(AppError):
    """Requested data does not exist or is not visible to the caller."""

    code = "resource_not_found"
    status_code = 404


class MissingInformationError(AppError):
    """The request lacks information needed to complete an operation."""

    code = "missing_information"
    status_code = 400


class ToolExecutionError(AppError):
    """A backend tool could not complete its operation."""

    code = "tool_failure"
    status_code = 502


class RetrievalError(AppError):
    """Knowledge retrieval or vector search failed."""

    code = "retrieval_failure"
    status_code = 502


class LLMError(AppError):
    """The language model failed to produce a response."""

    code = "llm_failure"
    status_code = 502
