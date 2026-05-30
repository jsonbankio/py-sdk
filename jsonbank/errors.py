"""JsonBank error types.

Failed requests raise :class:`JsonBankError`, which carries a machine readable
``code`` alongside a human readable ``message``.
"""

from __future__ import annotations


class JsonBankError(Exception):
    """Error raised by the JsonBank SDK.

    Carries a machine readable ``code`` (e.g. ``"notFound"``, ``"name.exists"``,
    ``"bad_request"``) alongside a human readable ``message``.
    """

    code: str
    message: str

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return self.message

    def __repr__(self) -> str:
        return f"JsonBankError(code={self.code!r}, message={self.message!r})"


def invalid_json_error() -> JsonBankError:
    """The shared "content is not valid JSON" error."""
    return JsonBankError(
        "invalid_json_content", "Content is not a valid JSON string"
    )
