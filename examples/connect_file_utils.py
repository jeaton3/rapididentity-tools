"""
Utilities for interacting with Connect file endpoints from examples.

Provides simple `ls`-like and `cat`-like helpers that accept a
`RapidIdentityConnect` instance.

Usage (from an example script):
    from rapididentity.client import RapidIdentityClient
    from rapididentity.connect import RapidIdentityConnect
    from examples.connect_file_utils import ls, cat

    client = RapidIdentityClient.from_config(...)  # your config
    connect = RapidIdentityConnect(client)
    ls(connect, path="some/dir")
    cat(connect, path="some/file.txt")
"""
from typing import Any, Optional
import json
import argparse
import os
import sys
import re
import gzip
import time
from html.parser import HTMLParser
from pathlib import Path

# ensure the project package is importable when running the example
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError


def ls(connect: "RapidIdentityConnect", path: Optional[str] = None, project: Optional[str] = None) -> None:
    """List entries at `path` using `connect.get_files` and print ls-like lines.

    The function attempts to be tolerant of different Connect response shapes.
    """
    payload = connect.get_files(path=path, project=project)

    # Connect often returns a dict with a 'fileEntries' list under various
    # wrapper keys. Try to locate that list robustly.
    entries = None
    if isinstance(payload, list):
        entries = payload
    elif isinstance(payload, dict):
        # direct common key
        if isinstance(payload.get("fileEntries"), list):
            entries = payload.get("fileEntries")
        else:
            # try nested shapes
            for k in ("files", "entries", "data", "rows"):
                v = payload.get(k)
                if isinstance(v, list):
                    entries = v
                    break
                if isinstance(v, dict) and isinstance(v.get("fileEntries"), list):
                    entries = v.get("fileEntries")
                    break

        if entries is None:
            # maybe payload itself describes a single file entry
            # or contains a single 'fileEntry' object
            single = payload.get("fileEntry") or payload
            entries = [single]
    else:
        entries = [payload]

    if not entries:
        print("(no entries)")
        return

    for e in entries:
        # normalize wrapper shapes
        if isinstance(e, dict) and isinstance(e.get("fileEntry"), dict):
            e = e.get("fileEntry")

        if not isinstance(e, dict):
            print(str(e))
            continue
        # Prefer the documented attributes
        path_val = e.get("path") or "/"
        # Display the basename for readability
        name = str(path_val).rstrip("/").split("/")[-1] or "/"

        # Directory detection: presence of `fileEntries` indicates a directory
        is_dir = "fileEntries" in e

        size = e.get("size")
        size_display = str(size) if size is not None else "-"

        # timestamp in milliseconds -> ISO8601
        ts = e.get("timestamp")
        mtime = "-"
        if isinstance(ts, (int, float)):
            try:
                from datetime import datetime

                # Format as: YYYY-MM-DD HH:MM:SS (UTC), drop milliseconds and Z
                mtime = datetime.utcfromtimestamp(ts / 1000.0).strftime("%Y-%m-%d %H:%M:%S")
            except Exception:
                mtime = str(ts)

        readable = "r" if e.get("readable") else "-"
        writable = "w" if e.get("writable") else "-"

        type_flag = "d" if is_dir else "-"
        # Columns: type, size, timestamp, perms, name
        print(f"{type_flag} {size_display:>8}  {mtime:20}  {readable}{writable}  {name}")


def cat(connect: "RapidIdentityConnect", path: str, project: Optional[str] = None) -> None:
    """Print the contents of `path`.

    Fetches raw bytes, detects gzip, and decompresses on the fly when stdout
    is a terminal. Structured JSON payloads are pretty-printed.
    """
    client = connect.client
    endpoint = f"/admin/connect/fileContent/{path}"
    url = client._build_url(endpoint)
    headers = client.auth_config.get_headers()
    headers["Accept"] = "application/json"

    resp = client.session.request(
        "GET",
        url,
        params={"project": project} if project else None,
        headers=headers,
        verify=client.verify_ssl,
        timeout=client.timeout,
    )
    if resp.status_code >= 400:
        client._handle_response(resp)

    response_bytes = resp.content

    # Try to unwrap JSON envelope and recover binary data.
    raw: bytes | None = None
    json_payload = None
    try:
        parsed = json.loads(response_bytes)
        if isinstance(parsed, dict) and "data" in parsed:
            data_val = parsed["data"]
            if isinstance(data_val, str):
                raw = data_val.encode("utf-8", errors="surrogateescape")
            elif isinstance(data_val, bytes):
                raw = data_val
            else:
                json_payload = parsed
        elif isinstance(parsed, (dict, list)):
            json_payload = parsed
        else:
            raw = response_bytes
    except Exception:
        raw = response_bytes

    if json_payload is not None:
        print(json.dumps(json_payload, indent=2))
        return

    if raw is None:
        return

    is_tty = sys.stdout.isatty()

    # Detect gzip magic bytes and decompress when writing to a terminal.
    if raw[:2] == b"\x1f\x8b":
        if is_tty:
            import io
            with gzip.GzipFile(fileobj=io.BytesIO(raw)) as gz:
                decompressed = gz.read()
            # Attempt UTF-8 decode for display; fall back to latin-1.
            try:
                text = decompressed.decode("utf-8")
            except UnicodeDecodeError:
                text = decompressed.decode("latin-1")
            # If it looks like HTML, strip tags for readability.
            if "<html" in text[:200].lower() or "<body" in text[:500].lower():
                parser = _HTMLToTextParser()
                parser.feed(text)
                parser.close()
                print(parser.text())
            else:
                sys.stdout.write(text)
                if not text.endswith("\n"):
                    sys.stdout.write("\n")
        else:
            # Piped to a file or another process — write raw compressed bytes.
            sys.stdout.buffer.write(raw)
        return

    # Plain bytes: write to buffer if binary, else decode and print.
    try:
        text = raw.decode("utf-8")
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
    except UnicodeDecodeError:
        sys.stdout.buffer.write(raw)


class _HTMLToTextParser(HTMLParser):
    """Convert HTML into plain text while preserving readable line breaks."""

    _block_tags = {
        "address",
        "article",
        "aside",
        "blockquote",
        "br",
        "div",
        "dl",
        "dt",
        "dd",
        "fieldset",
        "figcaption",
        "figure",
        "footer",
        "form",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "header",
        "hr",
        "li",
        "main",
        "nav",
        "ol",
        "p",
        "pre",
        "section",
        "table",
        "tr",
        "ul",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            self._skip_depth += 1
            return
        if self._skip_depth == 0 and tag in self._block_tags:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style"}:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth == 0 and tag in self._block_tags:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0 and data:
            self._parts.append(data)

    def text(self) -> str:
        text = "".join(self._parts)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Keep intentional spacing while preventing huge blank gaps.
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def show_gz_log(path: str) -> None:
    """Read a gzipped HTML log file and print a plain-text view."""
    gz_path = Path(path).expanduser()
    if not gz_path.exists():
        raise FileNotFoundError(f"File not found: {gz_path}")

    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace") as fh:
        html_text = fh.read()

    parser = _HTMLToTextParser()
    parser.feed(html_text)
    parser.close()
    print(parser.text())


def rsync(
    connect: "RapidIdentityConnect",
    src: str,
    dest: str,
    project: Optional[str] = None,
    dry_run: bool = False,
    verbose: bool = False,
    exclude: Optional[list[str]] = None,
    recent_logs: bool = False,
    http_count: bool = False,
) -> None:
    """Mirror a Connect path to a local destination directory.

    - Recursively lists `src` on the Connect server
    - Creates directories locally when missing
    - Downloads files when missing or when remote timestamp is newer
    - Skips unchanged files
    """
    from pathlib import Path
    import os

    dest_root = Path(dest).expanduser()
    dest_root.mkdir(parents=True, exist_ok=True)

    def _entries_from_payload(payload: Any):
        # Reuse ls-style extraction to get a list of entry dicts
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            if isinstance(payload.get("fileEntries"), list):
                return payload.get("fileEntries")
            for k in ("files", "entries", "data", "rows"):
                v = payload.get(k)
                if isinstance(v, list):
                    return v
                if isinstance(v, dict) and isinstance(v.get("fileEntries"), list):
                    return v.get("fileEntries")
            single = payload.get("fileEntry") or payload
            return [single]
        return [payload]

    if exclude is None:
        exclude_patterns: list[str] = []
    elif isinstance(exclude, str):
        # Backward compatibility for direct callers passing a single pattern.
        exclude_patterns = [exclude]
    else:
        exclude_patterns = [p for p in exclude if p]

    excl_res = [re.compile(pattern) for pattern in exclude_patterns]
    cutoff_time = time.time() - 172800 if recent_logs else None
    list_http_calls = 0
    content_http_calls = 0

    def _is_excluded(check_path: str, name: str) -> bool:
        if not excl_res:
            return False
        return any(r.search(check_path) or r.search(name) for r in excl_res)

    def _should_skip_recent_log_entry(entry: dict[str, Any], child_server_path: str) -> bool:
        if cutoff_time is None:
            return False

        path_parts = [part for part in child_server_path.strip("/").split("/") if part]
        if len(path_parts) < 3 or path_parts[0] != "log":
            return False

        timestamp = entry.get("timestamp")
        if not isinstance(timestamp, (int, float)):
            return False
        return (timestamp / 1000.0) < cutoff_time


    def _sync_dir(server_path: str, local_dir: Path):
        nonlocal list_http_calls
        list_http_calls += 1
        payload = connect.get_files(path=server_path, project=project)
        entries = _entries_from_payload(payload)

        server_path_norm = (server_path or "").strip().strip("/")

        for e in entries:
            if isinstance(e, dict) and isinstance(e.get("fileEntry"), dict):
                e = e.get("fileEntry")

            if not isinstance(e, dict):
                continue

            entry_path = str(e.get("path") or "")
            entry_path_norm = entry_path.strip().strip("/")

            # Determine child server path using normalized paths so we don't
            # accidentally produce duplicated prefixes like cookies/cookies/x.
            if server_path_norm:
                prefix = server_path_norm + "/"
                if entry_path_norm == server_path_norm or entry_path_norm.startswith(prefix):
                    child_server_path = entry_path_norm
                elif entry_path_norm:
                    child_server_path = prefix + entry_path_norm
                else:
                    child_server_path = server_path_norm
            else:
                child_server_path = entry_path_norm

            # Directory detection: presence of `fileEntries` indicates a directory
            is_dir = "fileEntries" in e

            if _should_skip_recent_log_entry(e, child_server_path):
                if verbose:
                    print(f"  {child_server_path}")
                continue

            # Some API payloads include the current directory as an entry; skip
            # it to avoid recursing into the same path forever.
            if is_dir and child_server_path == server_path_norm:
                continue

            # Local path relative to dest_root
            # Compute relative piece from the server path base (src)
            rel = child_server_path
            src_norm = (src or "").strip().strip("/")
            if src_norm and rel.startswith(src_norm + "/"):
                rel = rel[len(src_norm) + 1 :]
            elif src_norm and rel == src_norm:
                # When syncing a single file (src equals the returned
                # child path) use the full src path to preserve directory structure
                if not is_dir:
                    rel = src_norm
                else:
                    rel = ""
            elif not src_norm:
                # Root sync: entries are already relative to destination root.
                rel = rel.lstrip("/")

            local_target = dest_root.joinpath(rel)

            # Exclude matching paths/names
            if _is_excluded(child_server_path, child_server_path.rstrip("/").split("/")[-1]):
                if(verbose):
                    print(f"Excluding {child_server_path}")
                continue

            if is_dir:
                if not local_target.exists():
                    if dry_run:
                        if verbose:
                             print(f"Would create directory {local_target}")
                    else:
                        print(f"+ {local_target}")
                        local_target.mkdir(parents=True, exist_ok=True)
                else:
                    if verbose:
                        print(f"  {local_target}/")
                # Recurse into directory
                _sync_dir(child_server_path, local_target)
            else:
                # File handling
                server_ts = e.get("timestamp")
                server_mtime = None
                if isinstance(server_ts, (int, float)):
                    server_mtime = server_ts / 1000.0

                need_fetch = True
                if local_target.exists():
                    try:
                        local_mtime = local_target.stat().st_mtime
                        if server_mtime is not None and local_mtime >= server_mtime - 0.5:
                            need_fetch = False
                    except Exception:
                        pass

                if _is_excluded(child_server_path, local_target.name):
                    print(f"Excluding {child_server_path}")
                    continue

                if not local_target.exists():
                    action = "+"
                elif need_fetch:
                    action = "u"
                else:
                    action = " "

                if dry_run:
                    if verbose:  
                        print(f"Would be {action.lower()} {local_target}")
                else:
                    if verbose or action != " ":
                        print(f"{action} {local_target}")

                if need_fetch and not dry_run:
                    # Ensure parent directory exists
                    local_target.parent.mkdir(parents=True, exist_ok=True)

                    # Fetch file content directly using the session to avoid
                    # JSON parsing issues with binary data. The API returns JSON
                    # but we need to preserve the binary `data` field intact.
                    client = connect.client
                    endpoint = f"/admin/connect/fileContent/{child_server_path}"
                    url = client._build_url(endpoint)
                    headers = client.auth_config.get_headers()
                    headers["Accept"] = "application/json"

                    nonlocal content_http_calls
                    content_http_calls += 1
                    resp = client.session.request(
                        "GET",
                        url,
                        params={"project": project} if project else None,
                        headers=headers,
                        verify=client.verify_ssl,
                        timeout=client.timeout,
                    )
                    
                    if resp.status_code >= 400:
                        client._handle_response(resp)

                    # Get the response as raw bytes to preserve binary data
                    response_bytes = resp.content

                    # Try to parse as JSON to extract the `data` field
                    fetched = None
                    try:
                        response_json = json.loads(response_bytes)
                        if isinstance(response_json, dict) and "data" in response_json:
                            # Extract the data field - it may be a string or already bytes
                            data_value = response_json.get("data")
                            if isinstance(data_value, str):
                                # String data - try to recover binary
                                fetched = data_value
                            else:
                                fetched = response_json
                        else:
                            fetched = response_json
                    except Exception:
                        # Not JSON - treat raw response as binary (expected for
                        # some endpoints that return raw gzip/etc without wrapping)
                        fetched = response_bytes
                    


                    # Now write the fetched content
                    wrote_bytes = False
                    
                    # Structured payloads (dict/list) -> pretty-print JSON
                    if isinstance(fetched, (dict, list)):
                        local_target.write_text(json.dumps(fetched, indent=2), encoding="utf-8")
                    elif isinstance(fetched, bytes):
                        # Raw bytes - write directly
                        if fetched.startswith(b"\x1f\x8b"):
                            with open(local_target, "wb") as fh:
                                fh.write(fetched)
                            wrote_bytes = True
                        else:
                            with open(local_target, "wb") as fh:
                                fh.write(fetched)
                            wrote_bytes = True
                    elif isinstance(fetched, str):
                        s = fetched
                        # Try two approaches to recover binary from string:
                        # 1. If string looks like base64, try base64 decode
                        # 2. Try to use encode('utf-8', errors='ignore') to strip
                        #    replacement chars, then encode as latin-1
                        from base64 import b64decode
                        try:
                            decoded = b64decode(s, validate=True)
                            with open(local_target, "wb") as fh:
                                fh.write(decoded)
                            wrote_bytes = True
                        except Exception:
                            # Try to salvage: encode as UTF-8 to get indiv bytes,
                            # then treat as latin-1 repr and extract actual bytes
                            try:
                                # Get the string's UTF-8 bytes, which includes the
                                # replacement chars; use those as-is
                                decoded = s.encode('utf-8', errors='surrogateescape')
                                if decoded.startswith(b"\x1f\x8b"):
                                    with open(local_target, "wb") as fh:
                                        fh.write(decoded)
                                    wrote_bytes = True
                            except Exception:
                                pass

                        if not wrote_bytes:
                            # Treat as textual content
                            local_target.write_text(s, encoding="utf-8")
                    else:
                        # Fallback
                        local_target.write_text(str(fetched), encoding="utf-8")

                    # Update mtime to server timestamp when available
                    if server_mtime is not None:
                        try:
                            os.utime(local_target, (server_mtime, server_mtime))
                        except Exception:
                            pass

    # Start syncing from src
    _sync_dir(src, dest_root)

    if http_count:
        total_calls = list_http_calls + content_http_calls
        print(
            f"HTTP calls: total={total_calls}, list={list_http_calls}, content={content_http_calls}"
        )


def _resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect file utilities: ls, cat, rsync, and log helpers")
    parser.add_argument("--config", default="prod", help="Config name under ~/rapididentity/config (default: prod)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_show = sub.add_parser("showlog", help="Display gzipped HTML log as plain text")
    p_show.add_argument("file", help="Path to local .gz log file")

    p_ls = sub.add_parser("ls", help="List files in a path")
    p_ls.add_argument("path", nargs="?", default=None, help="Path to list (optional)")
    p_ls.add_argument("--project", default=None, help="Project name (optional)")

    p_cat = sub.add_parser("cat", help="Print file contents")
    p_cat.add_argument("path", help="Path to file to print")
    p_cat.add_argument("--project", default=None, help="Project name (optional)")
    p_rsync = sub.add_parser("rsync", help="Mirror a remote Connect path to local directory")
    p_rsync.add_argument("src", help="Source Connect path to mirror")
    p_rsync.add_argument("dest", help="Local destination directory")
    p_rsync.add_argument("--project", default=None, help="Project name (optional)")
    p_rsync.add_argument("--dry-run", action="store_true", help="Show actions without making changes")
    p_rsync.add_argument(
        "--recent-logs",
        action="store_true",
        help="Skip entries under log/*/* that are older than 48 hours based on server timestamps",
    )
    p_rsync.add_argument("--verbose", action="store_true", help="Show detailed actions")
    p_rsync.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Regex to exclude paths/files. Repeat flag to add patterns (e.g. --exclude log --exclude cookies)",
    )
    p_rsync.add_argument(
        "--http-count",
        action="store_true",
        help="Print HTTP call totals for this rsync run (total/list/content)",
    )

    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    if args.cmd == "showlog":
        try:
            show_gz_log(args.file)
        except BrokenPipeError:
            # Normal when piping to tools like `head`.
            return
        except OSError as e:
            print(f"Failed to read gzip log: {e}", file=sys.stderr)
            sys.exit(5)
        return

    config_path = _resolve_config_path(args.config)
    if not config_path.exists():
        print(f"Configuration file {config_path} not found", file=sys.stderr)
        sys.exit(1)

    cfg = Config(str(config_path))
    with RapidIdentityClient.from_config(cfg) as client:
        connect = client.connect
        try:
            if args.cmd == "ls":
                ls(connect, path=args.path, project=getattr(args, "project", None))
            elif args.cmd == "cat":
                # `cat` should print only the `data` payload when available;
                # our `get_file_content` helper already unwraps `data` when present.
                cat(connect, path=args.path, project=getattr(args, "project", None))
            elif args.cmd == "rsync":
                rsync(
                    connect,
                    src=args.src,
                    dest=args.dest,
                    project=getattr(args, "project", None),
                    dry_run=getattr(args, "dry_run", False),
                    recent_logs=getattr(args, "recent_logs", False),
                    http_count=getattr(args, "http_count", False),
                    verbose=getattr(args, "verbose", False),
                    exclude=getattr(args, "exclude", None),
                )
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read this endpoint", file=sys.stderr)
            sys.exit(2)
        except NotFoundError:
            print("Path not found. Are you pointing at the correct host/project?", file=sys.stderr)
            sys.exit(3)
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}", file=sys.stderr)
            sys.exit(4)


if __name__ == "__main__":
    main()
