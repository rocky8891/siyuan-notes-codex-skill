---
name: siyuan-notes
description: Connect to a local or remote SiYuan note workspace through the SiYuan HTTP API. Use when Codex needs to read, search, create, update, delete, move, rename, export, template-render, or otherwise manage SiYuan notebooks, documents, blocks, block attributes, files/assets, flashcards/riff cards, attribute-view/database tables, or note content from any project.
---

# SiYuan Notes

Use this skill to operate SiYuan through its HTTP API. Prefer the bundled CLI for repeatable work; use `api` as the escape hatch for new or version-specific endpoints.

This skill is grounded in SiYuan's official API documentation from `siyuan-note/siyuan` and borrows practical endpoint grouping from `Achuan-2/siyuan-plugin-copilot`.

## Connection

Use environment variables unless the user provides temporary values in the current task:

- `SIYUAN_BASE_URL`: base URL of the user's SiYuan service; default local URL is `http://127.0.0.1:6806`
- `SIYUAN_API_TOKEN`: API token from SiYuan settings

Never write tokens, passwords, internal-only URLs, private keys, usernames, or personal note content into the skill, generated notes, logs, commits, or final summaries. Do not echo secrets back to the user.

All JSON API calls use:

- `POST <SIYUAN_BASE_URL>/api/...`
- SiYuan token authorization header
- `Content-Type: application/json; charset=utf-8`

If network access is blocked by the runtime, request approval/escalation instead of pretending the API is down.

## CLI

Run the helper from this skill directory:

```bash
python scripts/siyuan_cli.py version
python scripts/siyuan_cli.py notebooks
python scripts/siyuan_cli.py sql "select id, content, hpath, box from blocks where type='d' order by updated desc limit 10"
python scripts/siyuan_cli.py kramdown DOCUMENT_ID
python scripts/siyuan_cli.py list-docs NOTEBOOK_ID /
python scripts/siyuan_cli.py create-doc NOTEBOOK_ID /new-note.md ./note.md
python scripts/siyuan_cli.py update-block BLOCK_ID ./table.md
python scripts/siyuan_cli.py attrs-get BLOCK_ID
python scripts/siyuan_cli.py api /api/system/currentTime '{}'
```

Arguments that accept text can be literal text, a file path, or `-` for stdin. Arguments that accept JSON can be a JSON string, `@file.json`, or `-` for stdin.

## Workflows

Read before write:

1. Resolve notebook/document/block IDs using `notebooks`, `sql`, `list-docs`, `search-docs`, `hpath-by-id`, or `ids-by-hpath`.
2. Read current content with `kramdown`, `export-md`, `children`, `attrs-get`, or SQL.
3. Make the smallest safe write.
4. Verify with a separate read.

For targeted edits, preserve unrelated content, block IDs, document structure, table columns, and existing formatting. For table updates, remove blank data rows unless the user explicitly asks to keep spacing rows.

Do not invent note content. If a note has only a title or no concrete body, say/write `无` only when the user's workflow requires a placeholder; otherwise use the title only.

## API Coverage

Official SiYuan API groups:

- System: `version`, `current-time`, `boot-progress`
- Notebook: `notebooks`, `open-notebook`, `close-notebook`, `create-notebook`, `rename-notebook`, `remove-notebook`, `notebook-conf`, `set-notebook-conf`
- Document/file tree: `create-doc`, `rename-doc`, `rename-doc-id`, `remove-doc`, `remove-doc-id`, `move-docs`, `move-docs-id`, `hpath-by-path`, `hpath-by-id`, `path-by-id`, `ids-by-hpath`
- Blocks: `kramdown`, `children`, `insert-block`, `append-block`, `prepend-block`, `update-block`, `delete-block`, `move-block`, `fold-block`, `unfold-block`, `transfer-ref`
- Attributes: `attrs-get`, `attrs-set`
- SQL: `sql`, `flush`
- Templates: `template-render`, `sprig`
- Files/assets/export/convert: `file-get`, `file-put`, `file-remove`, `file-rename`, `read-dir`, `asset-upload`, `export-md`, `export-resources`, `pandoc`
- Notification/network: `notify`, `notify-err`, `forward-proxy`

Plugin-practice endpoints from `siyuan-plugin-copilot`:

- File tree helpers: `get-doc`, `list-docs`, `search-docs`
- DOM read: `dom`
- Flashcards/riff: `riff-decks`, `riff-create-deck`, `riff-remove-deck`, `riff-rename-deck`, `riff-cards`, `riff-add-cards`, `riff-remove-cards`
- Attribute views/databases: `av-search`, `av-keys`, `av-render`, `av-append-detached`, `av-add-blocks`, `av-set-cell`, `av-batch-set`, `av-block-keys`, `av-bound-ids`, `av-item-ids`, `av-add-key`, `av-remove-key`, `av-remove-blocks`

Treat plugin-practice endpoints as useful but version-dependent. If they fail, fall back to `api` and inspect the returned error instead of guessing.

## Safety Rules

- Use SQL for discovery and filtering; use block/document APIs for writes.
- Before creating a document, query by notebook and `hpath` to avoid duplicates unless the user explicitly wants a new copy.
- Confirm exact targets before deleting notebooks, documents, broad document trees, or files.
- Avoid `removeNotebook`, `removeDoc`, `removeDocByID`, `deleteBlock`, `removeFile`, and attribute-view remove commands unless deletion is explicitly requested.
- For secrets found in notes, redact them in summaries and generated reports.
- If an endpoint returns `code != 0`, stop and surface the message; do not continue a multi-step write blindly.

## Verification

After writes:

1. Re-read the changed block/document/table/attribute view.
2. Confirm expected content exists.
3. Confirm no duplicate document or blank table row was introduced when relevant.
4. Summarize changed notebook/document/block/table IDs without exposing credentials.
