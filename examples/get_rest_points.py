"""Fetch Connect RESTPoints and save raw XML plus one readable JSON file per RESTPoint.

Usage:
    python examples/get_rest_points.py --config prod
    python examples/get_rest_points.py --config prod --project my-project
    python examples/get_rest_points.py --config prod --output-dir /path/to/output

RESTPoints aren't exposed via a dedicated endpoint; they're nested inside each
project's `<restPointProject>/<restPoints>` block in the `<projects>` XML
returned by `/admin/connect/projects`. If no `--output-dir` is given, results
default to ``~/rapididentity/{tier}/restpoints`` where ``tier`` is read from
config:

- ``projects.xml``        the raw `/admin/connect/projects` response, pretty-printed
- ``json/<name>.json``    one file per RESTPoint (named `{project}_{method}_{path}`),
  via ``RapidIdentityClient.from_config(cfg).connect.get_rest_points()`` --
  one file per RESTPoint keeps diffs between runs scoped to what changed

A short summary (project, method, path, action set) is always printed to stdout.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError
from rapididentity.utils.helpers import write_indented_xml, safe_filename

NS_URI = "urn:idauto.net:dss:actiondef"


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def write_rest_point_files(rest_points: List[Dict[str, Any]], json_dir: Path) -> None:
    """Write each RESTPoint to its own JSON file so diffs between runs stay
    scoped to the RESTPoints that actually changed, instead of one big file."""
    json_dir.mkdir(parents=True, exist_ok=True)
    seen_names: Dict[str, int] = {}

    for rp in rest_points:
        project = rp.get("project") or "default"
        method = rp.get("method") or "UNKNOWN"
        path = (rp.get("path") or rp.get("id") or "unnamed").strip("/")
        base = safe_filename(f"{project}_{method}_{path}")

        count = seen_names.get(base, 0)
        seen_names[base] = count + 1
        filename = f"{base}.json" if count == 0 else f"{base}-{count}.json"

        with open(json_dir / filename, "w", encoding="utf-8") as f:
            json.dump(rp, f, indent=2)


def print_summary(rest_points: List[Dict[str, Any]]) -> None:
    for rp in rest_points:
        project = rp.get("project") or "default"
        print(f"[{project}] {rp.get('method')} {rp.get('path')} -> actionSet={rp.get('actionSet')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Connect RESTPoints and save raw/readable output")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Optional project name to filter RESTPoints",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write projects.xml and json/ (default: ~/rapididentity/{tier}/restpoints)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config_path = resolve_config_path(args.config)

    if not config_path.exists():
        print(f"Configuration file {config_path} not found")
        sys.exit(1)

    cfg = Config(str(config_path))
    tier = str(cfg.get_tier())
    target_dir = Path(args.output_dir) if args.output_dir else Path.home() / "rapididentity" / tier / "restpoints"

    with RapidIdentityClient.from_config(cfg) as client:
        try:
            projects_xml = client.connect.get_projects()
            rest_points = client.connect.get_rest_points(project=args.project)

            if not isinstance(projects_xml, str):
                # Some tenants may return already-structured JSON instead of XML.
                print(json.dumps(rest_points, indent=2))
                return

            target_dir.mkdir(parents=True, exist_ok=True)
            xml_path = target_dir / "projects.xml"
            json_dir = target_dir / "json"

            write_indented_xml(xml_path, projects_xml, ns_uri=NS_URI)
            write_rest_point_files(rest_points, json_dir)

            print_summary(rest_points)
            print(f"\nWrote {xml_path} and {len(rest_points)} RESTPoint files to {json_dir}")
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read projects")
        except NotFoundError:
            print("Endpoint not found. Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print("Request failed:", e)


if __name__ == "__main__":
    main()
