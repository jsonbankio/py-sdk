"""Typed models for the JsonBank SDK.

Response models are ``@dataclass`` objects with ``from_dict`` converters that map
the API's camelCase JSON onto Pythonic ``snake_case`` attributes (the equivalent
of Go's ``DataToDocumentMeta`` and Rust's ``json_object_to_*`` functions).

Request bodies (``CreateDocumentBody`` etc.) are *optional* typed conveniences —
the write methods also accept a plain ``dict`` or ``**kwargs``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ============================================================
# Config
# ============================================================
@dataclass
class Keys:
    """Public and private API keys."""

    public: Optional[str] = None
    private: Optional[str] = None


@dataclass
class InitConfig:
    """Minimal configuration accepted by :class:`~jsonbank.client.JsonBank`."""

    host: Optional[str] = None
    keys: Optional[Keys] = None


# ============================================================
# Authentication
# ============================================================
@dataclass
class AuthenticatedKey:
    """Information about the authenticated API key."""

    title: str
    projects: List[str] = field(default_factory=list)


@dataclass
class AuthenticatedData:
    """Data returned by :meth:`JsonBank.authenticate`."""

    authenticated: bool
    username: str
    api_key: AuthenticatedKey

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuthenticatedData":
        api_key = data.get("apiKey") or {}
        return cls(
            authenticated=bool(data.get("authenticated", False)),
            username=data.get("username", ""),
            api_key=AuthenticatedKey(
                title=api_key.get("title", ""),
                projects=list(api_key.get("projects") or []),
            ),
        )


# ============================================================
# Documents
# ============================================================
@dataclass
class ContentSize:
    """String and number information about a document's content size."""

    number: int
    string: str


@dataclass
class DocumentMeta:
    """Metadata about a document (does not include its content)."""

    id: str
    project: str
    path: str
    name: str
    content_size: ContentSize
    created_at: str
    updated_at: str
    folder_id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DocumentMeta":
        size = data.get("contentSize") or {}
        return cls(
            id=data["id"],
            project=data["project"],
            path=data["path"],
            name=data["name"],
            content_size=ContentSize(
                number=size.get("number", 0),
                string=size.get("string", ""),
            ),
            created_at=data["createdAt"],
            updated_at=data["updatedAt"],
            folder_id=data.get("folderId"),
        )


@dataclass
class NewDocument:
    """A freshly created document.

    ``exists`` is not returned by the API; it is set by
    :meth:`JsonBank.create_document_if_not_exists` to indicate whether the
    document already existed.
    """

    id: str
    name: str
    path: str
    project: str
    created_at: str
    exists: bool = False

    @classmethod
    def from_dict(cls, data: Dict[str, Any], exists: bool = False) -> "NewDocument":
        return cls(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            project=data["project"],
            created_at=data["createdAt"],
            exists=exists,
        )


@dataclass
class UpdatedDocument:
    """Result of :meth:`JsonBank.update_own_document`."""

    changed: bool


@dataclass
class DeletedDocument:
    """Result of :meth:`JsonBank.delete_document`."""

    deleted: bool


# ============================================================
# Folders
# ============================================================
@dataclass
class FolderStats:
    """Number of documents and folders contained in a folder."""

    documents: int
    folders: int


@dataclass
class Folder:
    """A folder. ``stats`` is only present when requested with stats."""

    id: str
    name: str
    path: str
    project: str
    created_at: str
    updated_at: str
    stats: Optional[FolderStats] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Folder":
        stats = None
        if data.get("stats") is not None:
            s = data["stats"]
            stats = FolderStats(
                documents=s.get("documents", 0),
                folders=s.get("folders", 0),
            )
        return cls(
            id=data["id"],
            name=data["name"],
            path=data["path"],
            project=data["project"],
            created_at=data["createdAt"],
            updated_at=data["updatedAt"],
            stats=stats,
        )


@dataclass
class NewFolder(Folder):
    """A folder returned by :meth:`JsonBank.create_folder_if_not_exists`.

    ``exists`` indicates whether the folder already existed.
    """

    exists: bool = False

    @classmethod
    def from_folder(cls, folder: Folder, exists: bool) -> "NewFolder":
        return cls(
            id=folder.id,
            name=folder.name,
            path=folder.path,
            project=folder.project,
            created_at=folder.created_at,
            updated_at=folder.updated_at,
            stats=folder.stats,
            exists=exists,
        )


# ============================================================
# Request bodies (optional typed conveniences)
# ============================================================
@dataclass
class CreateDocumentBody:
    """Body for :meth:`JsonBank.create_document`.

    ``content`` may be a JSON string or any JSON-serializable object.
    """

    name: str
    project: str
    content: Any
    folder: Optional[str] = None


@dataclass
class CreateFolderBody:
    """Body for :meth:`JsonBank.create_folder`."""

    name: str
    project: str
    folder: Optional[str] = None


@dataclass
class UploadDocumentBody:
    """Body for :meth:`JsonBank.upload_document`.

    ``name`` defaults to the file name when not provided.
    """

    file_path: str
    project: str
    name: Optional[str] = None
    folder: Optional[str] = None
