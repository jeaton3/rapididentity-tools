"""
Parser utilities for RapidIdentity API interactions.
"""

from typing import Dict, Any, List, Optional
import json
from datetime import datetime


def parse_api_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse and normalize RapidIdentity API response.

    Args:
        response: Raw API response dictionary

    Returns:
        Normalized response data
    """
    if not isinstance(response, dict):
        return {"data": response}

    # Extract common response patterns
    result = {}

    # Check for common RapidIdentity response structures
    if "data" in response:
        result["data"] = response["data"]
    elif "result" in response:
        result["data"] = response["result"]
    elif "items" in response:
        result["data"] = response["items"]
    else:
        # Return all data if no standard wrapper found
        result["data"] = response

    # Extract metadata if present
    if "meta" in response:
        result["meta"] = response["meta"]
    if "pagination" in response:
        result["pagination"] = response["pagination"]
    if "errors" in response:
        result["errors"] = response["errors"]
    if "message" in response:
        result["message"] = response["message"]

    return result


def format_api_request(
    endpoint: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Format request data for API call.

    Args:
        endpoint: API endpoint
        method: HTTP method
        data: Request body data
        params: Query parameters

    Returns:
        Formatted request dictionary
    """
    request = {
        "endpoint": endpoint,
        "method": method,
        "timestamp": datetime.utcnow().isoformat(),
    }

    if data:
        request["data"] = data
    if params:
        request["params"] = params

    return request


def flatten_dict(data: Dict[str, Any], parent_key: str = "", sep: str = ".") -> Dict[str, Any]:
    """
    Flatten nested dictionary.

    Args:
        data: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        elif isinstance(v, list):
            items.append((new_key, v))
        else:
            items.append((new_key, v))
    return dict(items)


def unflatten_dict(data: Dict[str, Any], sep: str = ".") -> Dict[str, Any]:
    """
    Unflatten a dictionary.

    Args:
        data: Flattened dictionary
        sep: Separator used for nested keys

    Returns:
        Unflattened dictionary
    """
    result = {}
    for key, value in data.items():
        parts = key.split(sep)
        current = result
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value
    return result


def extract_fields(data: Dict[str, Any], fields: List[str]) -> Dict[str, Any]:
    """
    Extract specific fields from a dictionary.

    Args:
        data: Source dictionary
        fields: List of field names to extract

    Returns:
        Dictionary with only requested fields
    """
    return {field: data.get(field) for field in fields if field in data}


def filter_fields(data: Dict[str, Any], exclude_fields: List[str]) -> Dict[str, Any]:
    """
    Filter out specific fields from a dictionary.

    Args:
        data: Source dictionary
        exclude_fields: List of field names to exclude

    Returns:
        Dictionary without excluded fields
    """
    return {k: v for k, v in data.items() if k not in exclude_fields}
