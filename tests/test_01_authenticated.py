"""Authenticated suite — needs network and API keys.

Skipped entirely when ``JSB_PUBLIC_KEY`` / ``JSB_PRIVATE_KEY`` are unset.

Tests run in definition order (pytest default), so the folder is created before
the tests that depend on it.
"""

import json
import os

from conftest import OWN_PROJECT, TEST_FILE_CONTENT

from jsonbank import (
    DocumentMeta,
    Folder,
    FolderStats,
    JsonBankError,
    NewDocument,
    NewFolder,
)

UPLOAD_FILE = os.path.join(os.path.dirname(__file__), "upload.json")


def test_is_authenticated(auth_doc):
    assert auth_doc.client.is_authenticated() is True


def test_get_username(auth_doc):
    assert auth_doc.client.get_username() == "jsonbank"


def test_get_own_content_by_id(auth_doc):
    assert auth_doc.client.get_own_content(auth_doc.id) == TEST_FILE_CONTENT


def test_get_own_content_by_path(auth_doc):
    assert auth_doc.client.get_own_content(auth_doc.path) == TEST_FILE_CONTENT


def test_get_own_content_as_string(auth_doc):
    content = auth_doc.client.get_own_content_as_string(auth_doc.path)
    assert json.loads(content) == TEST_FILE_CONTENT


def test_get_own_document_meta(auth_doc):
    meta = auth_doc.client.get_own_document_meta(auth_doc.id)
    assert isinstance(meta, DocumentMeta)
    assert meta.id == auth_doc.id


def test_has_own_document(auth_doc):
    assert auth_doc.client.has_own_document(auth_doc.id) is True
    assert auth_doc.client.has_own_document("not-existing-id") is False


def test_update_own_document(auth_doc):
    client = auth_doc.client
    new_content = dict(TEST_FILE_CONTENT, updated=True)

    res = client.update_own_document(auth_doc.path, new_content)
    assert res.changed is True

    # revert
    client.update_own_document(auth_doc.path, TEST_FILE_CONTENT)


def test_create_folder(auth_doc):
    client = auth_doc.client
    try:
        folder = client.create_folder(name="folder", project=OWN_PROJECT)
        assert folder.name == "folder"
        assert folder.project == OWN_PROJECT
    except JsonBankError as err:
        # the folder already existing is fine
        if err.code != "name.exists":
            raise


def test_create_document_in_folder(auth_doc):
    client = auth_doc.client
    path = f"{OWN_PROJECT}/folder/new_doc"

    client.delete_document(path)
    doc = client.create_document(
        name="new_doc",
        project=OWN_PROJECT,
        folder="folder",
        content={"name": "new_doc"},
    )

    assert isinstance(doc, NewDocument)
    assert doc.project == OWN_PROJECT

    client.delete_document(path)


def test_upload_document(auth_doc):
    client = auth_doc.client
    client.delete_document(f"{OWN_PROJECT}/folder/upload.json")

    doc = client.upload_document(
        file_path=UPLOAD_FILE, project=OWN_PROJECT, folder="folder"
    )

    assert doc.project == OWN_PROJECT
    assert doc.path == "folder/upload.json"


def test_get_folder(auth_doc):
    client = auth_doc.client
    folder = client.get_folder(f"{OWN_PROJECT}/folder")

    assert isinstance(folder, Folder)
    assert folder.project == OWN_PROJECT

    by_id = client.get_folder(folder.id)
    assert by_id.id == folder.id


def test_get_folder_with_stats(auth_doc):
    folder = auth_doc.client.get_folder_with_stats(f"{OWN_PROJECT}/folder")

    assert folder.stats is not None
    assert isinstance(folder.stats, FolderStats)


def test_create_folder_if_not_exists(auth_doc):
    folder = auth_doc.client.create_folder_if_not_exists(
        name="folder", project=OWN_PROJECT
    )

    assert isinstance(folder, NewFolder)
    assert folder.name == "folder"
    assert folder.project == OWN_PROJECT
