"""Stateless helper functions (mirrors Rust's ``functions.rs``).

Includes the small extras that make the SDK feel Pythonic: ``normalize_body``
turns a dataclass, a plain ``dict``, or ``**kwargs`` into a single typed body.
"""

from __future__ import annotations

import json
from dataclasses import is_dataclass
from typing import Any, Dict, Type, TypeVar

from .errors import JsonBankError

T = TypeVar("T")


def is_valid_json(value: str) -> bool:
    """Return ``True`` if ``value`` is a valid JSON string."""
    try:
        json.loads(value)
        return True
    except (ValueError, TypeError):
        return False


def make_document_path(body: Any) -> str:
    """Build a document's full path: ``project/[folder/]name``."""
    folder = f"{body.folder}/" if getattr(body, "folder", None) else ""
    return f"{body.project}/{folder}{body.name}"


def make_folder_path(body: Any) -> str:
    """Build a folder's full path: ``project/[parent/]name``."""
    parent = f"{body.folder}/" if getattr(body, "folder", None) else ""
    return f"{body.project}/{parent}{body.name}"


def normalize_body(body: Any, kwargs: Dict[str, Any], cls: Type[T]) -> T:
    """Coerce a dataclass instance, a ``dict``, or ``**kwargs`` into ``cls``.

    This is what lets every write method accept whichever input style the caller
    prefers, e.g. all three of these are equivalent::

        jsb.create_document(name="x.json", project="p", content={"a": 1})
        jsb.create_document({"name": "x.json", "project": "p", "content": {"a": 1}})
        jsb.create_document(CreateDocumentBody(name="x.json", project="p", content={"a": 1}))
    """
    if isinstance(body, cls):
        if kwargs:
            raise JsonBankError(
                "bad_request",
                "Pass either a body object or keyword arguments, not both",
            )
        return body

    if body is None:
        data = kwargs
    elif isinstance(body, dict):
        if kwargs:
            raise JsonBankError(
                "bad_request",
                "Pass either a body dict or keyword arguments, not both",
            )
        data = body
    elif is_dataclass(body):
        raise JsonBankError(
            "bad_request",
            f"Expected {cls.__name__}, got {type(body).__name__}",
        )
    else:
        raise JsonBankError(
            "bad_request",
            f"Body must be a {cls.__name__}, dict, or keyword arguments",
        )

    try:
        return cls(**data)
    except TypeError as err:
        raise JsonBankError("bad_request", str(err))
