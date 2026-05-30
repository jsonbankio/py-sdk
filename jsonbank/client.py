"""The :class:`JsonBank` client.

A pooled :class:`requests.Session`, exceptions on failure, typed dataclasses on
the way out, and flexible ``dict`` / ``**kwargs`` / dataclass inputs on the way in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import requests

from .errors import JsonBankError, invalid_json_error
from .functions import (
    is_valid_json,
    make_document_path,
    make_folder_path,
    normalize_body,
)
from .structs import (
    AuthenticatedData,
    CreateDocumentBody,
    CreateFolderBody,
    DeletedDocument,
    DocumentMeta,
    Folder,
    InitConfig,
    Keys,
    NewDocument,
    NewFolder,
    UpdatedDocument,
    UploadDocumentBody,
)

#: The ``jsonbank`` keyword.
JSONBANK = "jsonbank"
#: The ``jsonbankio`` keyword.
JSONBANK_IO = "jsonbankio"
#: The default JsonBank API host.
DEFAULT_HOST = "https://api.jsonbank.io"

KeysInput = Union[Keys, Dict[str, Optional[str]], None]


@dataclass
class _Endpoints:
    v1: str
    public: str


class JsonBank:
    """JsonBank SDK client.

    The client can be created with or without API keys. Keys are only required
    to access protected/private documents.

    Examples::

        # Without keys (public content only)
        jsb = JsonBank()
        data = jsb.get_content("jsonbank/sdk-test/index")

        # With keys (flat kwargs is the primary style)
        jsb = JsonBank(public_key="...", private_key="...")
        jsb.authenticate()

        # As a context manager (closes the underlying session)
        with JsonBank() as jsb:
            jsb.get_content("jsonbank/sdk-test/index")
    """

    config: InitConfig

    def __init__(
        self,
        *,
        host: Optional[str] = None,
        public_key: Optional[str] = None,
        private_key: Optional[str] = None,
        keys: KeysInput = None,
        config: Optional[InitConfig] = None,
        timeout: Optional[float] = None,
    ) -> None:
        resolved_host, resolved_keys = _resolve_config(
            host, public_key, private_key, keys, config
        )

        self.config = InitConfig(host=resolved_host, keys=resolved_keys)
        self._endpoints = self._make_endpoints(resolved_host)
        self._authenticated_data: Optional[AuthenticatedData] = None
        self._timeout = timeout

        # One pooled session with the shared JSON content-type header.
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    @classmethod
    def without_config(cls) -> "JsonBank":
        """Create a client without keys."""
        return cls()

    # -- context manager ------------------------------------------------------
    def __enter__(self) -> "JsonBank":
        return self

    def __exit__(self, *exc: object) -> bool:
        self.close()
        return False

    def close(self) -> None:
        """Close the underlying :class:`requests.Session`."""
        self._session.close()

    # -- config ---------------------------------------------------------------
    @staticmethod
    def _make_endpoints(host: str) -> _Endpoints:
        return _Endpoints(v1=f"{host}/v1", public=host)

    def set_host(self, host: str) -> None:
        """Point the client at a different host (rebuilds the endpoints)."""
        self.config.host = host
        self._endpoints = self._make_endpoints(host)

    def _key(self, which: str) -> Optional[str]:
        keys = self.config.keys
        if keys is None:
            return None
        return keys.public if which == "public" else keys.private

    # -- request core ---------------------------------------------------------
    def _public_url(self, paths: List[str]) -> str:
        return f"{self._endpoints.public}/{'/'.join(paths)}"

    def _v1_url(self, paths: List[str]) -> str:
        return f"{self._endpoints.v1}/{'/'.join(paths)}"

    def _request(
        self,
        method: str,
        url: str,
        body: Optional[Dict[str, Any]] = None,
        require_pub_key: bool = False,
        require_prv_key: bool = False,
    ) -> requests.Response:
        headers: Dict[str, str] = {}

        if require_pub_key:
            pub = self._key("public")
            if not pub:
                raise JsonBankError("bad_request", "Public key is not set")
            headers["jsb-pub-key"] = pub

        if require_prv_key:
            prv = self._key("private")
            if not prv:
                raise JsonBankError("bad_request", "Private key is not set")
            headers["jsb-prv-key"] = prv

        method = method.upper()
        try:
            if method == "POST":
                return self._session.post(
                    url, json=body or {}, headers=headers, timeout=self._timeout
                )
            if method == "DELETE":
                return self._session.delete(
                    url, headers=headers, timeout=self._timeout
                )
            # GET: body (if any) is sent as query parameters
            return self._session.get(
                url, params=body or None, headers=headers, timeout=self._timeout
            )
        except requests.RequestException as err:
            raise JsonBankError("request_error", str(err))

    @staticmethod
    def _raise_response_error(res: requests.Response) -> "Any":
        status = str(res.status_code)
        try:
            data = res.json()
        except ValueError:
            raise JsonBankError(status, "Unknown error")

        error = data.get("error") if isinstance(data, dict) else None
        if isinstance(error, dict):
            raise JsonBankError(
                error.get("code", status), error.get("message", "Unknown error")
            )
        if isinstance(error, str):
            raise JsonBankError(status, error)
        raise JsonBankError(status, "Unknown error")

    def _process_response(self, res: requests.Response) -> Any:
        if res.ok:
            try:
                return res.json()
            except ValueError as err:
                raise JsonBankError("json_error", str(err))
        return self._raise_response_error(res)

    def _process_response_as_string(self, res: requests.Response) -> str:
        if res.ok:
            return res.text
        return self._raise_response_error(res)

    # thin wrappers for the public / read / write / delete request patterns
    def _public_request(self, paths: List[str]) -> Any:
        return self._process_response(self._request("GET", self._public_url(paths)))

    def _public_request_as_string(self, paths: List[str]) -> str:
        return self._process_response_as_string(
            self._request("GET", self._public_url(paths))
        )

    def _read_request(
        self, paths: List[str], query: Optional[Dict[str, Any]] = None
    ) -> Any:
        return self._process_response(
            self._request("GET", self._v1_url(paths), body=query, require_pub_key=True)
        )

    def _read_request_as_string(
        self, paths: List[str], query: Optional[Dict[str, Any]] = None
    ) -> str:
        return self._process_response_as_string(
            self._request("GET", self._v1_url(paths), body=query, require_pub_key=True)
        )

    def _read_post_request(
        self, paths: List[str], body: Optional[Dict[str, Any]] = None
    ) -> Any:
        return self._process_response(
            self._request("POST", self._v1_url(paths), body=body, require_pub_key=True)
        )

    def _write_request(
        self, paths: List[str], body: Optional[Dict[str, Any]] = None
    ) -> Any:
        return self._process_response(
            self._request("POST", self._v1_url(paths), body=body, require_prv_key=True)
        )

    def _delete_request(self, paths: List[str]) -> Any:
        return self._process_response(
            self._request("DELETE", self._v1_url(paths), require_prv_key=True)
        )

    @staticmethod
    def _prepare_content(content: Any) -> str:
        """Normalize ``content`` to a validated JSON string.

        A ``str`` is treated as raw JSON text; anything else is serialized with
        :func:`json.dumps`.
        """
        if content is None:
            raise JsonBankError("bad_request", "Content required")
        if isinstance(content, str):
            text = content
        else:
            try:
                # Minified to keep the payload small over the wire.
                text = json.dumps(content, separators=(",", ":"))
            except (TypeError, ValueError):
                raise invalid_json_error()
        if not text:
            raise JsonBankError("bad_request", "Content required")
        if not is_valid_json(text):
            raise invalid_json_error()
        return text

    # ========================================================================
    # Public content
    # ========================================================================
    def get_content(self, id_or_path: str) -> Any:
        """Get public content (parsed JSON) by id or path."""
        return self._public_request(["f", id_or_path])

    def get_content_as_string(self, id_or_path: str) -> str:
        """Get public content as a raw JSON string by id or path."""
        return self._public_request_as_string(["f", id_or_path])

    def get_document_meta(self, id_or_path: str) -> DocumentMeta:
        """Get public document metadata (no content) by id or path."""
        data = self._public_request(["meta/f", id_or_path])
        return DocumentMeta.from_dict(data)

    def get_github_content(self, path: str) -> Any:
        """Get a public JSON file from GitHub's default branch."""
        return self._public_request(["gh", path])

    def get_github_content_as_string(self, path: str) -> str:
        """Get a public JSON file from GitHub as a raw string."""
        return self._public_request_as_string(["gh", path])

    # ========================================================================
    # Authentication
    # ========================================================================
    def authenticate(self) -> AuthenticatedData:
        """Authenticate using the configured public key."""
        data = self._read_post_request(["authenticate"])
        auth = AuthenticatedData.from_dict(data)
        self._authenticated_data = auth
        return auth

    def is_authenticated(self) -> bool:
        """Return whether :meth:`authenticate` has succeeded."""
        return bool(self._authenticated_data and self._authenticated_data.authenticated)

    def get_username(self) -> str:
        """Return the authenticated username.

        Raises ``not_authenticated`` if :meth:`authenticate` was not called.
        """
        if self._authenticated_data is None:
            raise JsonBankError("not_authenticated", "User is not authenticated")
        return self._authenticated_data.username

    # ========================================================================
    # Owned content
    # ========================================================================
    def get_own_content(self, id_or_path: str) -> Any:
        """Get content (parsed JSON) of a document you own."""
        return self._read_request(["file", id_or_path])

    def get_own_content_as_string(self, id_or_path: str) -> str:
        """Get content of a document you own as a raw JSON string."""
        return self._read_request_as_string(["file", id_or_path])

    def get_own_document_meta(self, id_or_path: str) -> DocumentMeta:
        """Get metadata of a document you own."""
        data = self._read_request(["meta/file", id_or_path])
        return DocumentMeta.from_dict(data)

    def has_own_document(self, id_or_path: str) -> bool:
        """Return whether a document exists. Re-raises non-``notFound`` errors."""
        try:
            self.get_own_document_meta(id_or_path)
            return True
        except JsonBankError as err:
            if err.code == "notFound":
                return False
            raise

    def create_document(
        self, body: Union[CreateDocumentBody, Dict[str, Any], None] = None, /, **kwargs: Any
    ) -> NewDocument:
        """Create a document. Accepts a body object, a dict, or keyword args."""
        doc = normalize_body(body, kwargs, CreateDocumentBody)
        if not doc.project:
            raise JsonBankError("bad_request", "Project required")
        if not doc.name:
            raise JsonBankError("bad_request", "Name required")

        payload: Dict[str, Any] = {
            "name": doc.name,
            "project": doc.project,
            "content": self._prepare_content(doc.content),
        }
        if doc.folder:
            payload["folder"] = doc.folder

        data = self._write_request(["project", doc.project, "document"], payload)
        return NewDocument.from_dict(data)

    def create_document_if_not_exists(
        self, body: Union[CreateDocumentBody, Dict[str, Any], None] = None, /, **kwargs: Any
    ) -> NewDocument:
        """Create a document, or fetch it if it already exists.

        On ``name.exists`` the existing document's metadata is fetched and
        returned with ``exists=True``.
        """
        doc = normalize_body(body, kwargs, CreateDocumentBody)
        try:
            return self.create_document(doc)
        except JsonBankError as err:
            if err.code == "name.exists":
                meta = self.get_own_document_meta(make_document_path(doc))
                return NewDocument(
                    id=meta.id,
                    name=doc.name,
                    path=meta.path,
                    project=meta.project,
                    created_at=meta.created_at,
                    exists=True,
                )
            raise

    def update_own_document(
        self, id_or_path: str, content: Any
    ) -> UpdatedDocument:
        """Update a document you own. ``content`` may be a string or an object."""
        text = self._prepare_content(content)
        data = self._write_request(["file", id_or_path], {"content": text})
        return UpdatedDocument(changed=bool(data.get("changed", False)))

    def upload_document(
        self, body: Union[UploadDocumentBody, Dict[str, Any], None] = None, /, **kwargs: Any
    ) -> NewDocument:
        """Upload a JSON file from disk as a new document.

        ``name`` defaults to the file name. The file path is used as given
        (relative to the current working directory or absolute).
        """
        up = normalize_body(body, kwargs, UploadDocumentBody)
        if not up.project:
            raise JsonBankError("bad_request", "Project required")

        path = Path(up.file_path)
        if not path.is_file():
            raise JsonBankError("file_not_found", "File does not exist")

        try:
            file_content = path.read_text(encoding="utf-8")
        except OSError as err:
            raise JsonBankError("invalid_file", str(err))

        if not is_valid_json(file_content):
            raise invalid_json_error()

        return self.create_document(
            CreateDocumentBody(
                name=up.name or path.name,
                project=up.project,
                content=file_content,
                folder=up.folder,
            )
        )

    def delete_document(self, id_or_path: str) -> DeletedDocument:
        """Delete a document. Returns ``deleted=False`` if it did not exist."""
        try:
            data = self._delete_request(["file", id_or_path])
            return DeletedDocument(deleted=bool(data.get("deleted", False)))
        except JsonBankError as err:
            if err.code == "notFound":
                return DeletedDocument(deleted=False)
            raise

    # ========================================================================
    # Folders
    # ========================================================================
    def create_folder(
        self, body: Union[CreateFolderBody, Dict[str, Any], None] = None, /, **kwargs: Any
    ) -> Folder:
        """Create a folder. Accepts a body object, a dict, or keyword args."""
        folder = normalize_body(body, kwargs, CreateFolderBody)
        if not folder.project:
            raise JsonBankError("bad_request", "Project required")
        if not folder.name:
            raise JsonBankError("bad_request", "Name required")

        payload: Dict[str, Any] = {"name": folder.name, "project": folder.project}
        if folder.folder:
            payload["folder"] = folder.folder

        data = self._write_request(["project", folder.project, "folder"], payload)
        return Folder.from_dict(data)

    def create_folder_if_not_exists(
        self, body: Union[CreateFolderBody, Dict[str, Any], None] = None, /, **kwargs: Any
    ) -> NewFolder:
        """Create a folder, or fetch it if it already exists.

        On ``name.exists`` the existing folder is fetched and returned with
        ``exists=True``.
        """
        folder_body = normalize_body(body, kwargs, CreateFolderBody)
        try:
            folder = self.create_folder(folder_body)
            return NewFolder.from_folder(folder, exists=False)
        except JsonBankError as err:
            if err.code == "name.exists":
                folder = self.get_folder(make_folder_path(folder_body))
                return NewFolder.from_folder(folder, exists=True)
            raise

    def _get_folder(self, id_or_path: str, include_stats: bool) -> Folder:
        query = {"stats": "true"} if include_stats else None
        data = self._read_request(["folder", id_or_path], query)
        return Folder.from_dict(data)

    def get_folder(self, id_or_path: str) -> Folder:
        """Get a folder by id or path."""
        return self._get_folder(id_or_path, False)

    def get_folder_with_stats(self, id_or_path: str) -> Folder:
        """Get a folder including its document/folder counts."""
        return self._get_folder(id_or_path, True)


def _normalize_keys(keys: KeysInput) -> Keys:
    """Accept a :class:`Keys`, a dict (``public``/``private`` or ``pub``/``prv``)."""
    if keys is None:
        return Keys()
    if isinstance(keys, Keys):
        return Keys(public=keys.public, private=keys.private)
    if isinstance(keys, dict):
        return Keys(
            public=keys.get("public", keys.get("pub")),
            private=keys.get("private", keys.get("prv")),
        )
    raise JsonBankError("bad_request", "keys must be a Keys instance or a dict")


def _resolve_config(
    host: Optional[str],
    public_key: Optional[str],
    private_key: Optional[str],
    keys: KeysInput,
    config: Optional[InitConfig],
) -> "tuple[str, Keys]":
    if config is not None:
        host = host or config.host
        if keys is None:
            keys = config.keys

    resolved_keys = _normalize_keys(keys)

    # Flat kwargs take precedence / fill in.
    if public_key is not None:
        resolved_keys.public = public_key
    if private_key is not None:
        resolved_keys.private = private_key

    return host or DEFAULT_HOST, resolved_keys
