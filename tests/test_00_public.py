"""Public (not-authenticated) suite — needs network, no API keys.

The whole module is skipped if the API can't be reached.
"""

import json

from jsonbank import ContentSize, DocumentMeta

GITHUB_PKG = "jsonbankio/jsonbank-js/package.json"
GITHUB_ARRAY = "jsonbankio/documentation/github-test-array.json"


def test_get_content_by_id_and_path(public_doc):
    client = public_doc.client
    by_id = client.get_content(public_doc.id)
    by_path = client.get_content(public_doc.path)

    assert by_id["author"] == "jsonbank"
    assert by_id == by_path


def test_get_content_with_json_extension(public_doc):
    client = public_doc.client
    without_ext = client.get_content(public_doc.id)
    with_ext = client.get_content(public_doc.id + ".json")

    assert without_ext == with_ext


def test_get_content_as_string(public_doc):
    content = public_doc.client.get_content_as_string(public_doc.id)

    assert "author" in content
    assert json.loads(content)["author"] == "jsonbank"


def test_get_document_meta(public_doc):
    client = public_doc.client
    meta_by_id = client.get_document_meta(public_doc.id)
    meta_by_path = client.get_document_meta(public_doc.path)

    assert isinstance(meta_by_id, DocumentMeta)
    assert isinstance(meta_by_id.content_size, ContentSize)
    assert meta_by_id.id == public_doc.id
    assert meta_by_path.id == public_doc.id


def test_get_github_content(public_doc):
    pkg = public_doc.client.get_github_content(GITHUB_PKG)

    assert pkg["name"] == "jsonbank"
    assert pkg["author"] == "jsonbankio"


def test_get_github_array_content(public_doc):
    data = public_doc.client.get_github_content(GITHUB_ARRAY)

    assert data[0] == 1
    assert data[1] == "MultiType Array"
    assert data[2]["name"] == "github-test-array.json"


def test_get_github_content_as_string(public_doc):
    content = public_doc.client.get_github_content_as_string(GITHUB_PKG)

    assert "prepublishOnly" in content
