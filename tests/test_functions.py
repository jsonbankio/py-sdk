"""Offline unit tests — no network or API keys required.

Run on their own with::

    pytest tests/test_functions.py
"""

import pytest

from jsonbank import (
    DEFAULT_HOST,
    CreateDocumentBody,
    DocumentMeta,
    Folder,
    JsonBank,
    JsonBankError,
    Keys,
    NewDocument,
    NewFolder,
    is_valid_json,
    make_document_path,
    make_folder_path,
)
from jsonbank.functions import normalize_body


# -- helpers ------------------------------------------------------------------
def test_is_valid_json():
    assert is_valid_json('{"a": 1}') is True
    assert is_valid_json("[1, 2, 3]") is True
    assert is_valid_json('"a string"') is True
    assert is_valid_json("not json") is False
    assert is_valid_json("{bad}") is False
    assert is_valid_json("") is False


def test_make_document_path():
    assert (
        make_document_path(CreateDocumentBody(name="a.json", project="p", content={}))
        == "p/a.json"
    )
    assert (
        make_document_path(
            CreateDocumentBody(name="a.json", project="p", content={}, folder="f")
        )
        == "p/f/a.json"
    )


def test_make_folder_path():
    from jsonbank import CreateFolderBody

    assert make_folder_path(CreateFolderBody(name="f", project="p")) == "p/f"
    assert (
        make_folder_path(CreateFolderBody(name="f", project="p", folder="parent"))
        == "p/parent/f"
    )


# -- normalize_body -----------------------------------------------------------
def test_normalize_body_from_kwargs():
    body = normalize_body(None, {"name": "a.json", "project": "p", "content": {}}, CreateDocumentBody)
    assert isinstance(body, CreateDocumentBody)
    assert body.name == "a.json"
    assert body.folder is None


def test_normalize_body_from_dict():
    body = normalize_body({"name": "a.json", "project": "p", "content": "{}"}, {}, CreateDocumentBody)
    assert body.project == "p"


def test_normalize_body_passthrough():
    original = CreateDocumentBody(name="a.json", project="p", content={})
    assert normalize_body(original, {}, CreateDocumentBody) is original


def test_normalize_body_rejects_body_and_kwargs():
    original = CreateDocumentBody(name="a.json", project="p", content={})
    with pytest.raises(JsonBankError) as exc:
        normalize_body(original, {"name": "b.json"}, CreateDocumentBody)
    assert exc.value.code == "bad_request"


def test_normalize_body_rejects_bad_type():
    with pytest.raises(JsonBankError):
        normalize_body(123, {}, CreateDocumentBody)


# -- converters ---------------------------------------------------------------
def test_document_meta_from_dict():
    meta = DocumentMeta.from_dict(
        {
            "id": "abc",
            "project": "sdk-test",
            "path": "index.json",
            "name": "index.json",
            "contentSize": {"number": 42, "string": "42 B"},
            "createdAt": "2024-01-01",
            "updatedAt": "2024-01-02",
            "folderId": "fid",
        }
    )
    assert meta.id == "abc"
    assert meta.content_size.number == 42
    assert meta.content_size.string == "42 B"
    assert meta.folder_id == "fid"


def test_document_meta_from_dict_without_folder():
    meta = DocumentMeta.from_dict(
        {
            "id": "abc",
            "project": "sdk-test",
            "path": "index.json",
            "name": "index.json",
            "contentSize": {"number": 1, "string": "1 B"},
            "createdAt": "x",
            "updatedAt": "y",
        }
    )
    assert meta.folder_id is None


def test_folder_from_dict_with_and_without_stats():
    base = {
        "id": "f1",
        "name": "folder",
        "path": "folder",
        "project": "sdk-test",
        "createdAt": "x",
        "updatedAt": "y",
    }
    assert Folder.from_dict(base).stats is None

    with_stats = dict(base, stats={"documents": 3, "folders": 1})
    folder = Folder.from_dict(with_stats)
    assert folder.stats is not None
    assert folder.stats.documents == 3
    assert folder.stats.folders == 1


def test_new_folder_from_folder():
    folder = Folder(
        id="f1", name="folder", path="folder", project="p",
        created_at="x", updated_at="y",
    )
    new = NewFolder.from_folder(folder, exists=True)
    assert isinstance(new, NewFolder)
    assert new.id == "f1"
    assert new.exists is True


def test_new_document_defaults_exists_false():
    doc = NewDocument.from_dict(
        {
            "id": "d1",
            "name": "index.json",
            "path": "index.json",
            "project": "p",
            "createdAt": "x",
        }
    )
    assert doc.exists is False


# -- config resolution --------------------------------------------------------
def test_default_host_and_no_keys():
    jsb = JsonBank()
    assert jsb.config.host == DEFAULT_HOST
    assert jsb.config.keys == Keys(public=None, private=None)


def test_flat_kwargs_keys():
    jsb = JsonBank(public_key="pub", private_key="prv", host="https://example.test")
    assert jsb.config.host == "https://example.test"
    assert jsb.config.keys.public == "pub"
    assert jsb.config.keys.private == "prv"


def test_keys_dict_public_private():
    jsb = JsonBank(keys={"public": "pub", "private": "prv"})
    assert jsb.config.keys.public == "pub"
    assert jsb.config.keys.private == "prv"


def test_keys_dict_pub_prv_alias():
    jsb = JsonBank(keys={"pub": "pub", "prv": "prv"})
    assert jsb.config.keys.public == "pub"
    assert jsb.config.keys.private == "prv"


def test_set_host_updates_endpoints():
    jsb = JsonBank()
    jsb.set_host("https://example.test")
    assert jsb._v1_url(["authenticate"]) == "https://example.test/v1/authenticate"
    assert jsb._public_url(["f", "a/b"]) == "https://example.test/f/a/b"


# -- content preparation ------------------------------------------------------
def test_prepare_content_serializes_objects_minified():
    assert JsonBank._prepare_content({"a": 1, "b": 2}) == '{"a":1,"b":2}'
    assert JsonBank._prepare_content([1, 2, 3]) == "[1,2,3]"


def test_prepare_content_accepts_valid_json_string():
    assert JsonBank._prepare_content('{"a": 1}') == '{"a": 1}'


def test_prepare_content_rejects_invalid_json_string():
    with pytest.raises(JsonBankError) as exc:
        JsonBank._prepare_content("not json")
    assert exc.value.code == "invalid_json_content"


def test_prepare_content_rejects_empty():
    with pytest.raises(JsonBankError) as exc:
        JsonBank._prepare_content("")
    assert exc.value.code == "bad_request"


# -- errors -------------------------------------------------------------------
def test_jsonbank_error_attributes():
    err = JsonBankError("notFound", "missing")
    assert err.code == "notFound"
    assert err.message == "missing"
    assert str(err) == "missing"
