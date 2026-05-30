# JsonBank.io Python SDK

The official repository for the [jsonbank.io](https://jsonbank.io) Python SDK.

[Documentation](https://docs.jsonbank.io/sdks/python) | [PyPI](https://pypi.org/project/jsonbank/) | [GitHub](https://github.com/jsonbankio/py-sdk)

## Installation

```bash
pip install jsonbank
```

## Usage

The client can be initialized with or without API keys. Keys are only required to
access **protected/private** documents.

```python
from jsonbank import JsonBank

# Initialize without keys (public content only)
jsb = JsonBank()

# Get json content of a public file
data = jsb.get_content("jsonbank/sdk-test/index")
print(data["author"])  # -> "jsonbank"

# Get a json file from GitHub (default branch)
pkg = jsb.get_github_content("jsonbankio/jsonbank-js/package.json")

# Get document metadata (typed, attribute access)
meta = jsb.get_document_meta("jsonbank/sdk-test/index")
print(meta.id, meta.content_size.number)
```

### Authenticated requests

```python
from jsonbank import JsonBank

# Flat keyword arguments are the primary style
jsb = JsonBank(public_key="JSB_PUBLIC_KEY", private_key="JSB_PRIVATE_KEY")

# Optionally verify the keys
auth = jsb.authenticate()
print("Authenticated as:", auth.username)

# Read your own content
content = jsb.get_own_content("sdk-test/index.json")
```

`JsonBank` also works as a context manager, which closes the underlying HTTP
session on exit:

```python
with JsonBank(public_key="...", private_key="...") as jsb:
    jsb.update_own_document("sdk-test/index.json", {"updated": True})
```

### Flexible inputs

Write methods accept keyword arguments, a plain `dict`, or a typed body object —
whichever you prefer. `content` may be a JSON string **or** any JSON-serializable
object (it is serialized for you):

```python
from jsonbank import JsonBank, CreateDocumentBody

jsb = JsonBank(public_key="...", private_key="...")

# keyword arguments
jsb.create_document(name="movie.json", project="sdk-test", content={"title": "Avatar"})

# a plain dict
jsb.create_document({"name": "movie.json", "project": "sdk-test", "content": "{}"})

# a typed body
jsb.create_document(CreateDocumentBody(name="movie.json", project="sdk-test", content={}))
```

### Errors

Failed requests raise `JsonBankError`, which carries a `code` and `message`:

```python
from jsonbank import JsonBank, JsonBankError

jsb = JsonBank()
try:
    jsb.get_content("does/not/exist")
except JsonBankError as err:
    print(err.code, "-", err.message)  # e.g. "notFound - ..."
```

## Configuration

Keys can be supplied in whichever form is convenient:

```python
from jsonbank import JsonBank, Keys, InitConfig

JsonBank(public_key="...", private_key="...")            # flat kwargs (recommended)
JsonBank(keys={"public": "...", "private": "..."})       # dict (also accepts pub/prv)
JsonBank(keys=Keys(public="...", private="..."))         # typed Keys
JsonBank(config=InitConfig(host="...", keys=Keys(...)))  # full InitConfig
```

## Testing

Create an `.env` file in the root of the project and add the following variables:

```dotenv
JSB_HOST="https://api.jsonbank.io"
JSB_PUBLIC_KEY="your public key"
JSB_PRIVATE_KEY="your private key"
```

Install the dev dependencies and run the tests:

```bash
pip install -e ".[dev]"
pytest
```

The offline helper tests need neither network nor keys:

```bash
pytest tests/test_functions.py
```
