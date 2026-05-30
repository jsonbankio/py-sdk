"""Shared pytest fixtures and environment loading.

The suite runs against the live API using a public test document at
``jsonbank/sdk-test/index.json`` and an owned one at ``sdk-test/index.json``.

- Authenticated tests are **skipped** when ``JSB_PUBLIC_KEY`` / ``JSB_PRIVATE_KEY``
  are not set (instead of hard-failing).
- Network tests are **skipped** when the API can't be reached, so the offline
  helper tests in ``test_functions.py`` always pass on their own.
"""

import os
from types import SimpleNamespace

import pytest

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv is only a dev dependency
    pass

from jsonbank import DEFAULT_HOST, JsonBank, JsonBankError

JSB_HOST = os.environ.get("JSB_HOST") or DEFAULT_HOST
JSB_PUBLIC_KEY = os.environ.get("JSB_PUBLIC_KEY", "")
JSB_PRIVATE_KEY = os.environ.get("JSB_PRIVATE_KEY", "")
HAS_KEYS = bool(JSB_PUBLIC_KEY and JSB_PRIVATE_KEY)

# Public access needs the username prefix; authenticated access does not.
PUBLIC_PROJECT = "jsonbank/sdk-test"
OWN_PROJECT = "sdk-test"
TEST_FILE_NAME = "index.json"
PUBLIC_TEST_PATH = f"{PUBLIC_PROJECT}/{TEST_FILE_NAME}"
OWN_TEST_PATH = f"{OWN_PROJECT}/{TEST_FILE_NAME}"

TEST_FILE_CONTENT = {
    "name": "JsonBank SDK Test File",
    "author": "jsonbank",
}

# Errors that mean "couldn't reach the API", not "the API said no".
_OFFLINE_CODES = {"request_error", "json_error"}


def skip_if_offline(err: JsonBankError) -> None:
    """Turn a connection-level error into a skip rather than a failure."""
    if err.code in _OFFLINE_CODES:
        pytest.skip(f"JsonBank API unavailable: {err}")


@pytest.fixture(scope="module")
def public_doc():
    """A client plus the public test document's id/path (no keys needed)."""
    jsb = JsonBank()
    jsb.set_host(JSB_HOST)
    try:
        meta = jsb.get_document_meta(PUBLIC_TEST_PATH)
    except JsonBankError as err:
        skip_if_offline(err)
        if err.code == "notFound":
            pytest.fail(
                f"Test document not found at '{PUBLIC_TEST_PATH}'. Create it with "
                f"content {TEST_FILE_CONTENT} before running tests."
            )
        raise
    return SimpleNamespace(client=jsb, id=meta.id, path=PUBLIC_TEST_PATH)


@pytest.fixture(scope="module")
def auth_doc():
    """An authenticated client plus the owned test document (skips without keys)."""
    if not HAS_KEYS:
        pytest.skip("JSB_PUBLIC_KEY and JSB_PRIVATE_KEY are required for authenticated tests")

    jsb = JsonBank(
        host=JSB_HOST, public_key=JSB_PUBLIC_KEY, private_key=JSB_PRIVATE_KEY
    )
    try:
        jsb.authenticate()
        doc = jsb.create_document_if_not_exists(
            name=TEST_FILE_NAME, project=OWN_PROJECT, content=TEST_FILE_CONTENT
        )
    except JsonBankError as err:
        skip_if_offline(err)
        raise
    return SimpleNamespace(
        client=jsb, id=doc.id, path=OWN_TEST_PATH, project=OWN_PROJECT
    )
