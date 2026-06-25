#!/usr/bin/env python3
"""SiYuan HTTP API CLI for Codex skills.

Configuration:
  SIYUAN_BASE_URL   Base URL of the user's SiYuan service
  SIYUAN_API_TOKEN  API token, required unless --token is passed
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


JSON = dict[str, Any]


def read_text_arg(value: str) -> str:
    if value == "-":
        return sys.stdin.read()
    p = Path(value)
    if p.exists() and p.is_file():
        return p.read_text(encoding="utf-8")
    return value


def read_json_arg(value: str) -> Any:
    if value == "-":
        value = sys.stdin.read()
    elif value.startswith("@"):
        value = Path(value[1:]).read_text(encoding="utf-8")
    return json.loads(value)


def csv_or_json_list(value: str) -> list[Any]:
    value = value.strip()
    if value.startswith("["):
        data = json.loads(value)
        if not isinstance(data, list):
            raise SystemExit("Expected a JSON array.")
        return data
    return [item.strip() for item in value.split(",") if item.strip()]


def endpoint(base_url: str, path: str) -> str:
    if not path.startswith("/"):
        path = "/" + path
    return base_url.rstrip("/") + path


def post_json(base_url: str, token: str, path: str, payload: JSON) -> JSON:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint(base_url, path),
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    raw = open_request(req)
    try:
        result = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON response: {raw[:500]!r}") from exc
    if isinstance(result, dict) and result.get("code", 0) != 0:
        print_json(result)
        raise SystemExit(2)
    return result


def post_raw(base_url: str, token: str, path: str, payload: JSON) -> tuple[bytes, str]:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        endpoint(base_url, path),
        data=data,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read(), resp.headers.get("Content-Type", "")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connection failed: {exc.reason}") from exc


def multipart_body(fields: dict[str, str], files: list[tuple[str, Path]]) -> tuple[bytes, str]:
    boundary = f"----codex-siyuan-{int(time.time() * 1000)}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        chunks.append(str(value).encode("utf-8"))
        chunks.append(b"\r\n")
    for field_name, file_path in files:
        filename = file_path.name
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        chunks.append(f"--{boundary}\r\n".encode())
        chunks.append(
            f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
        )
        chunks.append(f"Content-Type: {ctype}\r\n\r\n".encode())
        chunks.append(file_path.read_bytes())
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"


def post_multipart(
    base_url: str,
    token: str,
    path: str,
    fields: dict[str, str],
    files: list[tuple[str, Path]],
) -> JSON:
    body, content_type = multipart_body(fields, files)
    req = urllib.request.Request(
        endpoint(base_url, path),
        data=body,
        headers={
            "Authorization": f"Token {token}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    raw = open_request(req)
    try:
        result = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON response: {raw[:500]!r}") from exc
    if isinstance(result, dict) and result.get("code", 0) != 0:
        print_json(result)
        raise SystemExit(2)
    return result


def open_request(req: urllib.request.Request) -> bytes:
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} {exc.reason}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connection failed: {exc.reason}") from exc


def print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def add_text_arg(parser: argparse.ArgumentParser, name: str = "markdown") -> None:
    parser.add_argument(name, help="Text, file path, or - for stdin")


def require_token(args: argparse.Namespace) -> str:
    if not args.token:
        raise SystemExit("Missing token. Set SIYUAN_API_TOKEN or pass --token.")
    return args.token


def require_url(args: argparse.Namespace) -> str:
    if not args.url:
        raise SystemExit("Missing URL. Set SIYUAN_BASE_URL or pass --url.")
    return args.url


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SiYuan HTTP API helper")
    parser.add_argument("--url", default=os.environ.get("SIYUAN_BASE_URL"))
    parser.add_argument("--token", default=os.environ.get("SIYUAN_API_TOKEN"))
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("version", help="Get /api/system/version")
    sub.add_parser("current-time", help="Get /api/system/currentTime")
    sub.add_parser("boot-progress", help="Get /api/system/bootProgress")

    sub.add_parser("notebooks", help="List notebooks")
    p = sub.add_parser("open-notebook", help="Open notebook")
    p.add_argument("notebook")
    p = sub.add_parser("close-notebook", help="Close notebook")
    p.add_argument("notebook")
    p = sub.add_parser("create-notebook", help="Create notebook")
    p.add_argument("name")
    p = sub.add_parser("rename-notebook", help="Rename notebook")
    p.add_argument("notebook")
    p.add_argument("name")
    p = sub.add_parser("remove-notebook", help="Remove notebook")
    p.add_argument("notebook")
    p = sub.add_parser("notebook-conf", help="Get notebook config")
    p.add_argument("notebook")
    p = sub.add_parser("set-notebook-conf", help="Set notebook config from JSON")
    p.add_argument("notebook")
    p.add_argument("conf_json", help="JSON string, @file.json, or -")

    p = sub.add_parser("sql", help="Run /api/query/sql")
    p.add_argument("stmt")
    sub.add_parser("flush", help="Flush SQLite transaction")

    p = sub.add_parser("api", help="Call an arbitrary JSON POST API path")
    p.add_argument("path")
    p.add_argument("payload", nargs="?", default="{}", help="JSON string, @file.json, or -")

    p = sub.add_parser("kramdown", help="Get block Kramdown")
    p.add_argument("id")
    p.add_argument("--mode", default=None, help="Optional SiYuan mode, e.g. md or textmark")
    p = sub.add_parser("dom", help="Get block DOM; plugin-practice endpoint")
    p.add_argument("id")
    p = sub.add_parser("children", help="Get child blocks")
    p.add_argument("id")

    p = sub.add_parser("insert-block", help="Insert a block before/after/under an anchor")
    add_text_arg(p, "data")
    p.add_argument("--data-type", default="markdown", choices=["markdown", "dom"])
    p.add_argument("--next-id", default="")
    p.add_argument("--previous-id", default="")
    p.add_argument("--parent-id", default="")
    p = sub.add_parser("append-block", help="Append content under a parent block")
    p.add_argument("parent_id")
    add_text_arg(p)
    p.add_argument("--data-type", default="markdown", choices=["markdown", "dom"])
    p = sub.add_parser("prepend-block", help="Prepend content under a parent block")
    p.add_argument("parent_id")
    add_text_arg(p)
    p.add_argument("--data-type", default="markdown", choices=["markdown", "dom"])
    p = sub.add_parser("update-block", help="Update a block/document")
    p.add_argument("id")
    add_text_arg(p)
    p.add_argument("--data-type", default="markdown", choices=["markdown", "dom"])
    p = sub.add_parser("delete-block", help="Delete a block/document")
    p.add_argument("id")
    p = sub.add_parser("move-block", help="Move a block")
    p.add_argument("id")
    p.add_argument("--previous-id", default="")
    p.add_argument("--parent-id", default="")
    p = sub.add_parser("fold-block", help="Fold a block")
    p.add_argument("id")
    p = sub.add_parser("unfold-block", help="Unfold a block")
    p.add_argument("id")
    p = sub.add_parser("transfer-ref", help="Transfer block references")
    p.add_argument("from_id")
    p.add_argument("to_id")
    p.add_argument("ref_ids", nargs="?", default="[]", help="JSON/comma list; omit for all refs")

    p = sub.add_parser("create-doc", help="Create a document from Markdown")
    p.add_argument("notebook")
    p.add_argument("path")
    add_text_arg(p)
    p = sub.add_parser("get-doc", help="Get doc tree/content; plugin-practice endpoint")
    p.add_argument("id")
    p = sub.add_parser("list-docs", help="List docs by notebook/path; plugin-practice endpoint")
    p.add_argument("notebook")
    p.add_argument("path")
    p.add_argument("--sort", type=int, default=15)
    p.add_argument("--show-hidden", action="store_true")
    p.add_argument("--max-list-count", type=int, default=10000)
    p = sub.add_parser("search-docs", help="Search docs; plugin-practice endpoint")
    p.add_argument("keyword")
    p.add_argument("--flashcard", action="store_true")
    p = sub.add_parser("rename-doc", help="Rename doc by notebook/path")
    p.add_argument("notebook")
    p.add_argument("path")
    p.add_argument("title")
    p = sub.add_parser("rename-doc-id", help="Rename doc by ID")
    p.add_argument("id")
    p.add_argument("title")
    p = sub.add_parser("remove-doc", help="Remove doc by notebook/path")
    p.add_argument("notebook")
    p.add_argument("path")
    p = sub.add_parser("remove-doc-id", help="Remove doc by ID")
    p.add_argument("id")
    p = sub.add_parser("move-docs", help="Move docs by storage paths")
    p.add_argument("from_paths", help="JSON/comma list")
    p.add_argument("to_notebook")
    p.add_argument("to_path")
    p = sub.add_parser("move-docs-id", help="Move docs by IDs")
    p.add_argument("from_ids", help="JSON/comma list")
    p.add_argument("to_id")
    p = sub.add_parser("hpath-by-path", help="Get human path by storage path")
    p.add_argument("notebook")
    p.add_argument("path")
    p = sub.add_parser("hpath-by-id", help="Get human path by ID")
    p.add_argument("id")
    p = sub.add_parser("path-by-id", help="Get storage path by ID")
    p.add_argument("id")
    p = sub.add_parser("ids-by-hpath", help="Get IDs by human path")
    p.add_argument("notebook")
    p.add_argument("path")

    p = sub.add_parser("attrs-get", help="Get block attrs")
    p.add_argument("id")
    p = sub.add_parser("attrs-set", help="Set block attrs")
    p.add_argument("id")
    p.add_argument("attrs_json", help="JSON string, @file.json, or -")

    p = sub.add_parser("template-render", help="Render a template file")
    p.add_argument("id")
    p.add_argument("path")
    p = sub.add_parser("sprig", help="Render a Sprig template")
    p.add_argument("template")

    p = sub.add_parser("file-get", help="Get workspace file")
    p.add_argument("path")
    p.add_argument("--output")
    p = sub.add_parser("file-put", help="Put workspace file or create directory")
    p.add_argument("path")
    p.add_argument("--file", dest="file_path")
    p.add_argument("--is-dir", action="store_true")
    p.add_argument("--mod-time", default=None)
    p = sub.add_parser("file-remove", help="Remove workspace file")
    p.add_argument("path")
    p = sub.add_parser("file-rename", help="Rename workspace file")
    p.add_argument("path")
    p.add_argument("new_path")
    p = sub.add_parser("read-dir", help="Read workspace directory")
    p.add_argument("path")
    p = sub.add_parser("asset-upload", help="Upload assets")
    p.add_argument("assets_dir_path")
    p.add_argument("files", nargs="+")

    p = sub.add_parser("export-md", help="Export document Markdown content")
    p.add_argument("id")
    p.add_argument("--yfm", action="store_true")
    p.add_argument("--fill-css-var", action="store_true")
    p.add_argument("--ref-mode", type=int, default=2)
    p.add_argument("--embed-mode", type=int, default=0)
    p.add_argument("--adjust-heading-level", action="store_true")
    p = sub.add_parser("export-resources", help="Export resources")
    p.add_argument("paths", help="JSON/comma list")
    p.add_argument("--name", default="")
    p = sub.add_parser("pandoc", help="Run SiYuan Pandoc conversion")
    p.add_argument("dir")
    p.add_argument("args_json", help="JSON array of pandoc args")

    p = sub.add_parser("notify", help="Push SiYuan message")
    p.add_argument("msg")
    p.add_argument("--timeout", type=int, default=7000)
    p = sub.add_parser("notify-err", help="Push SiYuan error message")
    p.add_argument("msg")
    p.add_argument("--timeout", type=int, default=7000)
    p = sub.add_parser("forward-proxy", help="Call SiYuan forward proxy")
    p.add_argument("target_url")
    p.add_argument("--method", default="GET")
    p.add_argument("--payload", default="{}")
    p.add_argument("--headers", default="[]")
    p.add_argument("--timeout", type=int, default=7000)
    p.add_argument("--content-type", default="application/json")

    sub.add_parser("riff-decks", help="List riff decks; plugin-practice endpoint")
    p = sub.add_parser("riff-create-deck", help="Create riff deck")
    p.add_argument("name")
    p = sub.add_parser("riff-remove-deck", help="Remove riff deck")
    p.add_argument("deck_id")
    p = sub.add_parser("riff-rename-deck", help="Rename riff deck")
    p.add_argument("deck_id")
    p.add_argument("name")
    p = sub.add_parser("riff-cards", help="List riff cards")
    p.add_argument("deck_id")
    p = sub.add_parser("riff-add-cards", help="Add blocks as riff cards")
    p.add_argument("deck_id")
    p.add_argument("block_ids", help="JSON/comma list")
    p = sub.add_parser("riff-remove-cards", help="Remove riff cards")
    p.add_argument("deck_id")
    p.add_argument("block_ids", help="JSON/comma list")

    p = sub.add_parser("av-search", help="Search attribute views/databases")
    p.add_argument("keyword")
    p.add_argument("--av-id", default="")
    p = sub.add_parser("av-keys", help="Get database columns by avID")
    p.add_argument("av_id")
    p = sub.add_parser("av-render", help="Render database view")
    p.add_argument("id")
    p.add_argument("view_id")
    p.add_argument("--page-size", type=int, default=9999999)
    p.add_argument("--page", type=int, default=1)
    p.add_argument("--create-if-not-exist", action="store_true")
    p = sub.add_parser("av-append-detached", help="Append detached database rows with values")
    p.add_argument("av_id")
    p.add_argument("blocks_values", help="JSON 2D array, @file.json, or -")
    p = sub.add_parser("av-add-blocks", help="Add bound blocks to database")
    p.add_argument("av_id")
    p.add_argument("srcs", help="JSON array, @file.json, or -")
    p = sub.add_parser("av-set-cell", help="Set one database cell")
    p.add_argument("av_id")
    p.add_argument("key_id")
    p.add_argument("item_id")
    p.add_argument("value", help="JSON value/object, @file.json, or -")
    p = sub.add_parser("av-batch-set", help="Batch set database cells")
    p.add_argument("av_id")
    p.add_argument("values", help="JSON array, @file.json, or -")
    p = sub.add_parser("av-block-keys", help="Get databases containing a block")
    p.add_argument("id")
    p = sub.add_parser("av-bound-ids", help="Get bound block IDs by item IDs")
    p.add_argument("av_id")
    p.add_argument("item_ids", help="JSON/comma list")
    p = sub.add_parser("av-item-ids", help="Get item IDs by bound block IDs")
    p.add_argument("av_id")
    p.add_argument("block_ids", help="JSON/comma list")
    p = sub.add_parser("av-add-key", help="Add database column")
    p.add_argument("av_id")
    p.add_argument("key_id")
    p.add_argument("key_name")
    p.add_argument("key_type")
    p.add_argument("previous_key_id")
    p.add_argument("--key-icon", default="")
    p = sub.add_parser("av-remove-key", help="Remove database column")
    p.add_argument("av_id")
    p.add_argument("key_id")
    p = sub.add_parser("av-remove-blocks", help="Remove database rows/blocks")
    p.add_argument("av_id")
    p.add_argument("src_ids", help="JSON/comma list")

    return parser


def dispatch(args: argparse.Namespace) -> Any:
    token = require_token(args)
    u = require_url(args)
    cmd = args.cmd

    no_arg_paths = {
        "version": "/api/system/version",
        "current-time": "/api/system/currentTime",
        "boot-progress": "/api/system/bootProgress",
        "notebooks": "/api/notebook/lsNotebooks",
        "flush": "/api/sqlite/flushTransaction",
        "riff-decks": "/api/riff/getRiffDecks",
    }
    if cmd in no_arg_paths:
        return post_json(u, token, no_arg_paths[cmd], {})

    if cmd == "api":
        return post_json(u, token, args.path, read_json_arg(args.payload))
    if cmd == "sql":
        return post_json(u, token, "/api/query/sql", {"stmt": args.stmt})

    if cmd == "open-notebook":
        return post_json(u, token, "/api/notebook/openNotebook", {"notebook": args.notebook})
    if cmd == "close-notebook":
        return post_json(u, token, "/api/notebook/closeNotebook", {"notebook": args.notebook})
    if cmd == "create-notebook":
        return post_json(u, token, "/api/notebook/createNotebook", {"name": args.name})
    if cmd == "rename-notebook":
        return post_json(u, token, "/api/notebook/renameNotebook", {"notebook": args.notebook, "name": args.name})
    if cmd == "remove-notebook":
        return post_json(u, token, "/api/notebook/removeNotebook", {"notebook": args.notebook})
    if cmd == "notebook-conf":
        return post_json(u, token, "/api/notebook/getNotebookConf", {"notebook": args.notebook})
    if cmd == "set-notebook-conf":
        return post_json(u, token, "/api/notebook/setNotebookConf", {"notebook": args.notebook, "conf": read_json_arg(args.conf_json)})

    if cmd == "kramdown":
        payload: JSON = {"id": args.id}
        if args.mode:
            payload["mode"] = args.mode
        return post_json(u, token, "/api/block/getBlockKramdown", payload)
    if cmd == "dom":
        return post_json(u, token, "/api/block/getBlockDOM", {"id": args.id})
    if cmd == "children":
        return post_json(u, token, "/api/block/getChildBlocks", {"id": args.id})
    if cmd == "insert-block":
        if not (args.next_id or args.previous_id or args.parent_id):
            raise SystemExit("insert-block needs --next-id, --previous-id, or --parent-id.")
        return post_json(u, token, "/api/block/insertBlock", {
            "dataType": args.data_type,
            "data": read_text_arg(args.data),
            "nextID": args.next_id,
            "previousID": args.previous_id,
            "parentID": args.parent_id,
        })
    if cmd == "append-block":
        return post_json(u, token, "/api/block/appendBlock", {
            "parentID": args.parent_id,
            "dataType": args.data_type,
            "data": read_text_arg(args.markdown),
        })
    if cmd == "prepend-block":
        return post_json(u, token, "/api/block/prependBlock", {
            "parentID": args.parent_id,
            "dataType": args.data_type,
            "data": read_text_arg(args.markdown),
        })
    if cmd == "update-block":
        return post_json(u, token, "/api/block/updateBlock", {
            "id": args.id,
            "dataType": args.data_type,
            "data": read_text_arg(args.markdown),
        })
    if cmd == "delete-block":
        return post_json(u, token, "/api/block/deleteBlock", {"id": args.id})
    if cmd == "move-block":
        if not (args.previous_id or args.parent_id):
            raise SystemExit("move-block needs --previous-id or --parent-id.")
        return post_json(u, token, "/api/block/moveBlock", {
            "id": args.id,
            "previousID": args.previous_id,
            "parentID": args.parent_id,
        })
    if cmd == "fold-block":
        return post_json(u, token, "/api/block/foldBlock", {"id": args.id})
    if cmd == "unfold-block":
        return post_json(u, token, "/api/block/unfoldBlock", {"id": args.id})
    if cmd == "transfer-ref":
        return post_json(u, token, "/api/block/transferBlockRef", {
            "fromID": args.from_id,
            "toID": args.to_id,
            "refIDs": csv_or_json_list(args.ref_ids),
        })

    if cmd == "create-doc":
        return post_json(u, token, "/api/filetree/createDocWithMd", {
            "notebook": args.notebook,
            "path": args.path,
            "markdown": read_text_arg(args.markdown),
        })
    if cmd == "get-doc":
        return post_json(u, token, "/api/filetree/getDoc", {"id": args.id})
    if cmd == "list-docs":
        return post_json(u, token, "/api/filetree/listDocsByPath", {
            "notebook": args.notebook,
            "path": args.path,
            "sort": args.sort,
            "showHidden": args.show_hidden,
            "maxListCount": args.max_list_count,
        })
    if cmd == "search-docs":
        return post_json(u, token, "/api/filetree/searchDocs", {"k": args.keyword, "flashcard": args.flashcard})
    if cmd == "rename-doc":
        return post_json(u, token, "/api/filetree/renameDoc", {"notebook": args.notebook, "path": args.path, "title": args.title})
    if cmd == "rename-doc-id":
        return post_json(u, token, "/api/filetree/renameDocByID", {"id": args.id, "title": args.title})
    if cmd == "remove-doc":
        return post_json(u, token, "/api/filetree/removeDoc", {"notebook": args.notebook, "path": args.path})
    if cmd == "remove-doc-id":
        return post_json(u, token, "/api/filetree/removeDocByID", {"id": args.id})
    if cmd == "move-docs":
        return post_json(u, token, "/api/filetree/moveDocs", {
            "fromPaths": csv_or_json_list(args.from_paths),
            "toNotebook": args.to_notebook,
            "toPath": args.to_path,
        })
    if cmd == "move-docs-id":
        return post_json(u, token, "/api/filetree/moveDocsByID", {"fromIDs": csv_or_json_list(args.from_ids), "toID": args.to_id})
    if cmd == "hpath-by-path":
        return post_json(u, token, "/api/filetree/getHPathByPath", {"notebook": args.notebook, "path": args.path})
    if cmd == "hpath-by-id":
        return post_json(u, token, "/api/filetree/getHPathByID", {"id": args.id})
    if cmd == "path-by-id":
        return post_json(u, token, "/api/filetree/getPathByID", {"id": args.id})
    if cmd == "ids-by-hpath":
        return post_json(u, token, "/api/filetree/getIDsByHPath", {"notebook": args.notebook, "path": args.path})

    if cmd == "attrs-get":
        return post_json(u, token, "/api/attr/getBlockAttrs", {"id": args.id})
    if cmd == "attrs-set":
        return post_json(u, token, "/api/attr/setBlockAttrs", {"id": args.id, "attrs": read_json_arg(args.attrs_json)})

    if cmd == "template-render":
        return post_json(u, token, "/api/template/render", {"id": args.id, "path": args.path})
    if cmd == "sprig":
        return post_json(u, token, "/api/template/renderSprig", {"template": args.template})

    if cmd == "file-get":
        raw, ctype = post_raw(u, token, "/api/file/getFile", {"path": args.path})
        if args.output:
            Path(args.output).write_bytes(raw)
            return {"code": 0, "msg": "", "data": {"output": args.output, "contentType": ctype, "bytes": len(raw)}}
        try:
            sys.stdout.write(raw.decode("utf-8"))
        except UnicodeDecodeError:
            sys.stdout.buffer.write(raw)
        return None
    if cmd == "file-put":
        fields = {
            "path": args.path,
            "isDir": "true" if args.is_dir else "false",
            "modTime": str(args.mod_time or int(time.time())),
        }
        files: list[tuple[str, Path]] = []
        if args.file_path:
            files.append(("file", Path(args.file_path)))
        elif not args.is_dir:
            raise SystemExit("file-put needs --file unless --is-dir is set.")
        return post_multipart(u, token, "/api/file/putFile", fields, files)
    if cmd == "file-remove":
        return post_json(u, token, "/api/file/removeFile", {"path": args.path})
    if cmd == "file-rename":
        return post_json(u, token, "/api/file/renameFile", {"path": args.path, "newPath": args.new_path})
    if cmd == "read-dir":
        return post_json(u, token, "/api/file/readDir", {"path": args.path})
    if cmd == "asset-upload":
        return post_multipart(
            u,
            token,
            "/api/asset/upload",
            {"assetsDirPath": args.assets_dir_path},
            [("file[]", Path(file_name)) for file_name in args.files],
        )

    if cmd == "export-md":
        return post_json(u, token, "/api/export/exportMdContent", {
            "id": args.id,
            "yfm": args.yfm,
            "fillCSSVar": args.fill_css_var,
            "refMode": args.ref_mode,
            "embedMode": args.embed_mode,
            "adjustHeadingLevel": args.adjust_heading_level,
        })
    if cmd == "export-resources":
        payload: JSON = {"paths": csv_or_json_list(args.paths)}
        if args.name:
            payload["name"] = args.name
        return post_json(u, token, "/api/export/exportResources", payload)
    if cmd == "pandoc":
        return post_json(u, token, "/api/convert/pandoc", {"dir": args.dir, "args": read_json_arg(args.args_json)})

    if cmd == "notify":
        return post_json(u, token, "/api/notification/pushMsg", {"msg": args.msg, "timeout": args.timeout})
    if cmd == "notify-err":
        return post_json(u, token, "/api/notification/pushErrMsg", {"msg": args.msg, "timeout": args.timeout})
    if cmd == "forward-proxy":
        return post_json(u, token, "/api/network/forwardProxy", {
            "url": args.target_url,
            "method": args.method,
            "timeout": args.timeout,
            "contentType": args.content_type,
            "headers": read_json_arg(args.headers),
            "payload": read_json_arg(args.payload),
        })

    if cmd == "riff-create-deck":
        return post_json(u, token, "/api/riff/createRiffDeck", {"name": args.name})
    if cmd == "riff-remove-deck":
        return post_json(u, token, "/api/riff/removeRiffDeck", {"deckID": args.deck_id})
    if cmd == "riff-rename-deck":
        return post_json(u, token, "/api/riff/renameRiffDeck", {"deckID": args.deck_id, "name": args.name})
    if cmd == "riff-cards":
        return post_json(u, token, "/api/riff/getRiffCards", {"deckID": args.deck_id})
    if cmd == "riff-add-cards":
        return post_json(u, token, "/api/riff/addRiffCards", {"deckID": args.deck_id, "blockIDs": csv_or_json_list(args.block_ids)})
    if cmd == "riff-remove-cards":
        return post_json(u, token, "/api/riff/removeRiffCards", {"deckID": args.deck_id, "blockIDs": csv_or_json_list(args.block_ids)})

    if cmd == "av-search":
        payload = {"keyword": args.keyword}
        if args.av_id:
            payload["avID"] = args.av_id
        return post_json(u, token, "/api/av/searchAttributeView", payload)
    if cmd == "av-keys":
        return post_json(u, token, "/api/av/getAttributeViewKeysByAvID", {"avID": args.av_id})
    if cmd == "av-render":
        return post_json(u, token, "/api/av/renderAttributeView", {
            "id": args.id,
            "viewID": args.view_id,
            "pageSize": args.page_size,
            "page": args.page,
            "createIfNotExist": args.create_if_not_exist,
        })
    if cmd == "av-append-detached":
        return post_json(u, token, "/api/av/appendAttributeViewDetachedBlocksWithValues", {
            "avID": args.av_id,
            "blocksValues": read_json_arg(args.blocks_values),
        })
    if cmd == "av-add-blocks":
        return post_json(u, token, "/api/av/addAttributeViewBlocks", {"avID": args.av_id, "srcs": read_json_arg(args.srcs)})
    if cmd == "av-set-cell":
        return post_json(u, token, "/api/av/setAttributeViewBlockAttr", {
            "avID": args.av_id,
            "keyID": args.key_id,
            "itemID": args.item_id,
            "value": read_json_arg(args.value),
        })
    if cmd == "av-batch-set":
        return post_json(u, token, "/api/av/batchSetAttributeViewBlockAttrs", {"avID": args.av_id, "values": read_json_arg(args.values)})
    if cmd == "av-block-keys":
        return post_json(u, token, "/api/av/getAttributeViewKeys", {"id": args.id})
    if cmd == "av-bound-ids":
        return post_json(u, token, "/api/av/getAttributeViewBoundBlockIDsByItemIDs", {"avID": args.av_id, "itemIDs": csv_or_json_list(args.item_ids)})
    if cmd == "av-item-ids":
        return post_json(u, token, "/api/av/getAttributeViewItemIDsByBoundIDs", {"avID": args.av_id, "blockIDs": csv_or_json_list(args.block_ids)})
    if cmd == "av-add-key":
        return post_json(u, token, "/api/av/addAttributeViewKey", {
            "avID": args.av_id,
            "keyID": args.key_id,
            "keyName": args.key_name,
            "keyType": args.key_type,
            "keyIcon": args.key_icon,
            "previousKeyID": args.previous_key_id,
        })
    if cmd == "av-remove-key":
        return post_json(u, token, "/api/av/removeAttributeViewKey", {"avID": args.av_id, "keyID": args.key_id})
    if cmd == "av-remove-blocks":
        return post_json(u, token, "/api/av/removeAttributeViewBlocks", {"avID": args.av_id, "srcIDs": csv_or_json_list(args.src_ids)})

    raise SystemExit(f"Unknown command: {cmd}")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = dispatch(args)
    if result is not None:
        print_json(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
