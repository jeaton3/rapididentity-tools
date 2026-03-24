"""Fetch and print an arbitrary /admin/connect endpoint.

Usage:
    python examples/get_connect_endpoint.py --config prod --endpoint adapters
    python examples/get_connect_endpoint.py --config prod --endpoint /admin/connect/actions
    python examples/get_connect_endpoint.py --config prod --endpoint /admin/connect/config --accept text/html
    python examples/get_connect_endpoint.py --config test --endpoint /admin/connect/fileContent/... --binary > out.bin
    python examples/get_connect_endpoint.py --config test --endpoint /admin/connect/fileContent/... --binary --output out.bin
    python examples/get_connect_endpoint.py --config prod --endpoint /admin/connect/jobs --params "limit=10&offset=0"

Loads config from ``~/rapididentity/config/{name}.json`` and prints the result
of ``RapidIdentityClient.from_config(cfg).connect.get(endpoint)``.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qsl
import xml.etree.ElementTree as ET

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch and print a Connect endpoint")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Connect endpoint, relative (e.g. adapters) or absolute (/admin/connect/adapters)",
    )
    parser.add_argument(
        "--accept",
        default=None,
        help="Optional Accept header override (e.g. --accept text/html)",
    )
    parser.add_argument(
        "--params",
        default=None,
        help="Optional query params, e.g. --params 'a=1&b=2'",
    )
    parser.add_argument(
        "--binary",
        action="store_true",
        help="Write raw response bytes to stdout (no JSON/XML formatting)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional output file path for binary mode (e.g. --output out.bin)",
    )
    return parser.parse_args()


def _connect_path(endpoint: str) -> str:
    if endpoint.startswith("/admin/connect/"):
        return endpoint
    if endpoint == "/admin/connect":
        return endpoint

    trimmed = endpoint.strip("/")
    return f"/admin/connect/{trimmed}" if trimmed else "/admin/connect"


def _parse_params(params_text: str | None):
    if not params_text:
        return {}

    params = {}
    for key, value in parse_qsl(params_text, keep_blank_values=True):
        if key:
            params[key] = value
    return params

def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)
    query_params = _parse_params(args.params)

    if not config_path.exists():
        print(f"Configuration file {config_path} not found")
        sys.exit(1)

    cfg = Config(str(config_path))
    with RapidIdentityClient.from_config(cfg) as client:
        try:
            if args.binary:
                path = _connect_path(args.endpoint)
                url = client._build_url(path)
                headers = client.auth_config.get_headers()
                headers["Accept"] = args.accept or "text/json; text/xml; application/octet-stream; */*"

                response = client.session.request(
                    method="GET",
                    url=url,
                    params=query_params or None,
                    headers=headers,
                    verify=client.verify_ssl,
                    timeout=client.timeout,
                )

                if response.status_code >= 400:
                    client._handle_response(response)

                if args.output:
                    output_path = Path(args.output).expanduser()
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_bytes(response.content)
                    print(f"Wrote {len(response.content)} bytes to {output_path}", file=sys.stderr)
                else:
                    sys.stdout.buffer.write(response.content)
                    sys.stdout.buffer.flush()
                return

            headers = {"Accept": args.accept} if args.accept else None
            path = _connect_path(args.endpoint)
            result = client.get(path, params=query_params or None, headers=headers)
            if isinstance(result, str) and result.lstrip().startswith("<"):
                try:
                    tree = ET.ElementTree(ET.fromstring(result))
                    ET.indent(tree, space="  ")
                    ET.dump(tree.getroot())
                except ET.ParseError:
                    print(result)
            else:
                print(json.dumps(result, indent=2))
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read this endpoint")
        except NotFoundError:
            print("Endpoint not found.  Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            import traceback

            print("Request failed:", repr(e))
            traceback.print_exc()


if __name__ == "__main__":
    main()
