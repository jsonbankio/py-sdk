"""JsonBank.io Python SDK.

Docs: https://docs.jsonbank.io/sdks/python | https://github.com/jsonbankio/py-sdk

Quick start::

    from jsonbank import JsonBank

    jsb = JsonBank()
    data = jsb.get_content("jsonbank/sdk-test/index")
    print(data["author"])  # -> "jsonbank"
"""

from __future__ import annotations

from typing import Any, Dict, List

from .client import DEFAULT_HOST, JSONBANK, JSONBANK_IO, JsonBank
from .errors import JsonBankError, invalid_json_error
from .functions import is_valid_json, make_document_path, make_folder_path
from .structs import (
    AuthenticatedData,
    AuthenticatedKey,
    ContentSize,
    CreateDocumentBody,
    CreateFolderBody,
    DeletedDocument,
    DocumentMeta,
    Folder,
    FolderStats,
    InitConfig,
    Keys,
    NewDocument,
    NewFolder,
    UpdatedDocument,
    UploadDocumentBody,
)

__version__ = "0.1.0"

#: Any decoded JSON value (parity with the Rust SDK's ``JsonValue``).
JsonValue = Any
#: A decoded JSON object (parity with the Rust SDK's ``JsonObject``).
JsonObject = Dict[str, Any]
#: A decoded JSON array (parity with the Rust SDK's ``JsonArray``).
JsonArray = List[Any]

__all__ = [
    # client + constants
    "JsonBank",
    "JSONBANK",
    "JSONBANK_IO",
    "DEFAULT_HOST",
    # errors
    "JsonBankError",
    "invalid_json_error",
    # config
    "Keys",
    "InitConfig",
    # request bodies
    "CreateDocumentBody",
    "CreateFolderBody",
    "UploadDocumentBody",
    # responses
    "AuthenticatedData",
    "AuthenticatedKey",
    "ContentSize",
    "DocumentMeta",
    "NewDocument",
    "UpdatedDocument",
    "DeletedDocument",
    "Folder",
    "FolderStats",
    "NewFolder",
    # helpers
    "is_valid_json",
    "make_document_path",
    "make_folder_path",
    # type aliases
    "JsonValue",
    "JsonObject",
    "JsonArray",
    "__version__",
]
