# SiYuan Notes Codex Skill

A reusable Codex skill for connecting to SiYuan through the HTTP API. It can read, search, create, update, delete, move, rename, export, template-render, and manage notebooks, documents, blocks, attributes, files/assets, flashcards, and attribute-view/database tables.

The skill is based on the official SiYuan API documentation and practical endpoint grouping from `Achuan-2/siyuan-plugin-copilot`.

## Install

Clone this repository into your Codex skills directory:

```powershell
git clone https://github.com/rocky8891/siyuan-notes-codex-skill.git "$env:USERPROFILE\.codex\skills\siyuan-notes"
```

Or copy the folder manually:

```text
C:\Users\<you>\.codex\skills\siyuan-notes
```

## Configure

Set these environment variables before using the CLI or asking Codex to operate SiYuan:

```powershell
$env:SIYUAN_BASE_URL = "http://127.0.0.1:6806"
$env:SIYUAN_API_TOKEN = "<your-api-token>"
```

`http://127.0.0.1:6806` is the default local SiYuan service URL. Set `SIYUAN_BASE_URL` to another address only when connecting to a remote SiYuan service.

Do not commit tokens, internal addresses, usernames, personal note content, or screenshots that expose private data. That is how keys learn to escape.

## Examples

```powershell
python scripts\siyuan_cli.py version
python scripts\siyuan_cli.py notebooks
python scripts\siyuan_cli.py sql "select id, content, hpath, box from blocks where type='d' order by updated desc limit 10"
python scripts\siyuan_cli.py kramdown DOCUMENT_ID
python scripts\siyuan_cli.py list-docs NOTEBOOK_ID /
python scripts\siyuan_cli.py create-doc NOTEBOOK_ID /new-note.md .\note.md
python scripts\siyuan_cli.py update-block BLOCK_ID .\table.md
python scripts\siyuan_cli.py attrs-get BLOCK_ID
python scripts\siyuan_cli.py api /api/system/currentTime "{}"
```

## Capabilities

- System: version, current time, boot progress
- Notebook: list/open/close/create/rename/remove/config
- Document tree: create, rename, remove, move, path lookup, list/search docs
- Blocks: insert, append, prepend, update, delete, move, fold, unfold, children, kramdown, DOM
- Attributes: get/set block attributes
- SQL: query and flush transaction
- Templates: render template and Sprig
- Files/assets: get, put, remove, rename, read directory, upload assets
- Export/convert: export Markdown/resources, Pandoc
- Notification/network: push messages and forward proxy
- Flashcards/riff cards
- Attribute-view/database helpers
- Generic API fallback: `api /api/... '{}'`

## Safety

The skill is designed for read-before-write workflows:

1. Resolve notebook/document/block IDs.
2. Read the current content.
3. Make the smallest safe write.
4. Verify with a separate read.

Deletion commands exist, but use them deliberately. Deleting the wrong note is not a productivity technique.
