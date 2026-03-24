"""
Helper utilities for RapidIdentity API interactions.
"""

from typing import Dict, Any, List, Callable, Optional, TypeVar
import time
import logging
from functools import wraps
import re
from pathlib import Path
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

T = TypeVar("T")


def normalize_payload(payload: Any, list_key: Optional[str] = None) -> Any:
    """Normalize Connect API responses to their most useful value.

    Mirrors the logic used by the Connect client: if the payload is a
    dict with a top-level ``data`` key, return that; if it's a list,
    return it; if it's a dict and ``list_key`` is provided, return the
    value at that key if it's a list. Otherwise return the payload or
    an empty list when payload is ``None``.
    """
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]

    if isinstance(payload, list):
        return payload

    if isinstance(payload, dict) and list_key:
        values = payload.get(list_key)
        if isinstance(values, list):
            return values

    return payload if payload is not None else []


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Decorator to retry a function on failure.

    Args:
        max_retries: Maximum number of retries
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay between retries
        exceptions: Tuple of exceptions to catch and retry

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"All {max_retries + 1} attempts failed.")

            if last_exception:
                raise last_exception

        return wrapper

    return decorator


def paginate_results(
    client: Any,
    endpoint: str,
    per_page: int = 100,
    max_pages: Optional[int] = None,
    **request_kwargs,
) -> List[Dict[str, Any]]:
    """
    Paginate through API results.

    This assumes the API supports 'page' and 'per_page' (or similar) parameters.

    Args:
        client: RapidIdentity client instance
        endpoint: API endpoint to paginate
        per_page: Results per page (default: 100)
        max_pages: Maximum number of pages to retrieve (None = all)
        **request_kwargs: Additional arguments to pass to client.get()

    Returns:
        List of all results from all pages
    """
    all_results = []
    page = 1
    pages_fetched = 0

    while True:
        if max_pages and pages_fetched >= max_pages:
            break

        try:
            params = request_kwargs.get("params", {})
            params["page"] = page
            params["per_page"] = per_page
            request_kwargs["params"] = params

            response = client.get(endpoint, **request_kwargs)

            # Extract data from response
            data = response.get("data", [])
            if isinstance(data, dict):
                # If data is a dict, might be a single result
                all_results.append(data)
            elif isinstance(data, list):
                all_results.extend(data)

            # Check if there are more pages
            meta = response.get("meta", {})
            pagination = response.get("pagination", {})

            # Common pagination indicators
            if not meta and not pagination:
                # If no pagination info and got fewer results than requested, likely last page
                if len(data) < per_page:
                    break
            else:
                # Check if has_more or similar flag
                if meta.get("has_more") is False or pagination.get("has_more") is False:
                    break
                if meta.get("page") == meta.get("total_pages"):
                    break

            pages_fetched += 1
            page += 1

        except StopIteration:
            break
        except Exception as e:
            logger.warning(f"Error fetching page {page}: {e}")
            break

    return all_results


def batch_items(items: List[T], batch_size: int = 100) -> List[List[T]]:
    """
    Split items into batches.

    Args:
        items: List of items to batch
        batch_size: Size of each batch

    Returns:
        List of batches
    """
    batches = []
    for i in range(0, len(items), batch_size):
        batches.append(items[i : i + batch_size])
    return batches


def dict_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries, with override taking precedence.

    Args:
        base: Base dictionary
        override: Dictionary with values to override

    Returns:
        Merged dictionary
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = dict_merge(result[key], value)
        else:
            result[key] = value
    return result


def safe_filename(name: str, fallback: str = "unnamed") -> str:
    """Return a filesystem-safe filename from `name`.

    Replaces characters not in [A-Za-z0-9_.-] with underscore.
    """
    FNAME_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
    return FNAME_SAFE.sub("_", name) or fallback


def extract_xml_payload(payload: Any) -> str:
    """Extract an XML string from common API response shapes.

    Accepts strings or dicts with keys like `xml`, `actionDef`, `actionSetVersion`,
    `payload`, or nested `data` containing those keys.
    """
    if isinstance(payload, str):
        return payload

    if isinstance(payload, dict):
        for key in ("xml", "actionDef", "actionSetVersion", "payload"):
            value = payload.get(key)
            if isinstance(value, str):
                return value

        data = payload.get("data")
        if isinstance(data, str):
            return data
        if isinstance(data, dict):
            for key in ("xml", "actionDef", "actionSetVersion"):
                value = data.get(key)
                if isinstance(value, str):
                    return value

    raise ValueError("Expected XML string payload from endpoint")


def write_indented_xml(path: Path, xml_text: str, ns_uri: Optional[str] = None) -> None:
    """Write `xml_text` to `path` with two-space indentation and XML declaration.

    If `ns_uri` is provided, registers it as the default namespace to avoid
    ns0 prefixes. Falls back to writing raw text if parsing fails.
    """
    try:
        root = ET.fromstring(xml_text)
        tree = ET.ElementTree(root)
        if ns_uri:
            ET.register_namespace("", ns_uri)
        ET.indent(tree, space="  ")
        tree.write(path, encoding="unicode", xml_declaration=True)
    except ET.ParseError:
        path.write_text(xml_text, encoding="utf-8")
