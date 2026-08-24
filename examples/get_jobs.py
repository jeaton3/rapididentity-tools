"""Fetch Connect jobs and optionally save raw XML plus a human-readable JSON summary.

Usage:
    python examples/get_jobs.py --config prod
    python examples/get_jobs.py --config prod --project my-project
    python examples/get_jobs.py --config prod --output-dir /path/to/output

The Connect `/admin/connect/jobs` endpoint returns a `<jobs>` XML document
(one `<job>` per job, each wrapping the `<action>` it runs and that action's
`<arg>` values). If no `--output-dir` is given, results default to
``~/rapididentity/{tier}/jobs`` where ``tier`` is read from config:

- ``jobs.xml``      the raw response, pretty-printed
- ``json/<name>.json``  one file per job (named after the job), with
  booleans/ints coerced and quoted script-literal arg values unquoted --
  one file per job keeps diffs between runs scoped to the jobs that changed

A short summary (name, schedule, disabled state) is always printed to stdout.
"""

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional

# ensure the project package is importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient
from rapididentity.exceptions import AuthenticationError, APIError, NotFoundError
from rapididentity.utils.helpers import write_indented_xml, safe_filename

NS_URI = "urn:idauto.net:dss:actiondef"

# Job/action attributes known to be boolean or integer in the XML schema;
# everything else is left as a plain string.
BOOL_ATTRS = {"traceEnabled", "disabled", "attachLog", "skipOverlap", "runExternal"}
INT_ATTRS = {"version", "logRetentionDays", "timeoutSeconds"}


def resolve_config_path(config_name: str) -> Path:
    config_file = config_name if config_name.endswith(".json") else f"{config_name}.json"
    return Path.home() / "rapididentity" / "config" / config_file


def _coerce_attrs(attrib: Dict[str, str]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, value in attrib.items():
        if key in BOOL_ATTRS:
            result[key] = value.lower() == "true"
        elif key in INT_ATTRS:
            try:
                result[key] = int(value)
            except ValueError:
                result[key] = value
        else:
            result[key] = value
    return result


def _unquote_arg_value(value: Optional[str]) -> Any:
    """Unwrap action-script literal arg values, e.g. '"normal"' -> 'normal'."""
    if value is None:
        return None
    if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    if value in ("true", "false"):
        return value == "true"
    return value


def parse_jobs_xml(xml_text: str) -> List[Dict[str, Any]]:
    """Parse a `<jobs>` XML document into a list of human-readable job dicts."""
    root = ET.fromstring(xml_text)
    jobs = []

    for job_elem in root.findall(f"{{{NS_URI}}}job"):
        job = _coerce_attrs(job_elem.attrib)

        action_elem = job_elem.find(f"{{{NS_URI}}}action")
        if action_elem is not None:
            args = {
                arg.get("name"): _unquote_arg_value(arg.get("value"))
                for arg in action_elem.findall(f"{{{NS_URI}}}arg")
            }
            job["action"] = {
                "id": action_elem.get("id"),
                "name": action_elem.get("name"),
                "project": action_elem.get("project"),
                "args": args,
            }

        jobs.append(job)

    return jobs


def write_job_files(jobs: List[Dict[str, Any]], json_dir: Path) -> None:
    """Write each job to its own JSON file so diffs between runs stay scoped
    to the jobs that actually changed, instead of one large jobs.json."""
    json_dir.mkdir(parents=True, exist_ok=True)
    seen_names: Dict[str, int] = {}

    for job in jobs:
        base = safe_filename(job.get("name") or job.get("id") or "unnamed")
        count = seen_names.get(base, 0)
        seen_names[base] = count + 1
        filename = f"{base}.json" if count == 0 else f"{base}-{count}.json"

        with open(json_dir / filename, "w", encoding="utf-8") as f:
            json.dump(job, f, indent=2)


def print_summary(jobs: List[Dict[str, Any]]) -> None:
    for job in jobs:
        status = "disabled" if job.get("disabled") else "enabled"
        print(f"{job.get('name')} [{status}] cron='{job.get('cronSpec')}' -> action={job.get('action', {}).get('name')}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Connect jobs and save raw/readable output")
    parser.add_argument(
        "--config",
        default="prod",
        help="Config name under ~/rapididentity/config (e.g. --config prod)",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Optional project name to filter jobs",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory to write jobs.xml and json/ (default: ~/rapididentity/{tier}/jobs)",
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
    target_dir = Path(args.output_dir) if args.output_dir else Path.home() / "rapididentity" / tier / "jobs"

    with RapidIdentityClient.from_config(cfg) as client:
        try:
            result = client.connect.get_jobs(project=args.project)

            if not isinstance(result, str):
                # Some tenants may return already-structured JSON instead of XML.
                print(json.dumps(result, indent=2))
                return

            target_dir.mkdir(parents=True, exist_ok=True)
            xml_path = target_dir / "jobs.xml"
            json_dir = target_dir / "json"

            write_indented_xml(xml_path, result, ns_uri=NS_URI)

            jobs = parse_jobs_xml(result)
            write_job_files(jobs, json_dir)

            print_summary(jobs)
            print(f"\nWrote {xml_path} and {len(jobs)} job files to {json_dir}")
        except AuthenticationError:
            print("Access forbidden: credentials lack permission to read jobs")
        except NotFoundError:
            print("Endpoint not found. Are you pointing at the correct host?")
        except APIError as e:
            print(f"API error {e.status_code}: {e.message}")
        except Exception as e:
            print("Request failed:", e)


if __name__ == "__main__":
    main()
