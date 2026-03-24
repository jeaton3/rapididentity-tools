# Examples

This folder contains runnable examples for workflows that are implemented in the current codebase.

## Available examples

- `archive_action_history.py`
  - Run: `python examples/archive_action_history.py --config prod`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Fetches actions, then action history versions for each action id
  - Writes historical XML to `~/rapididentity/{tier}/archive/xml/{name}-{version}.xml`
  - Writes decoded scripts to `~/rapididentity/{tier}/archive/js/{name}-{version}.js`

- `get_adapters.py`
  - Run: `python examples/get_adapters.py --config prod`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Prints the result of `RapidIdentityClient.from_config(cfg).connect.get_adapters()`

- `get_connect_endpoint.py`
  - Run: `python examples/get_connect_endpoint.py --config prod --endpoint adapters`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Prints the result of `RapidIdentityClient.from_config(cfg).get(path)`, where `path` is the resolved `/admin/connect/...` endpoint

- `get_actions.py`
  - Run: `python examples/get_actions.py --config prod`
  - Fetches Connect actionDefs via `RapidIdentityClient.from_config(cfg).connect.get_actions()`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Writes XML files to `~/rapididentity/{tier}/xml`
  - Writes script files for non-empty actionDefs to `~/rapididentity/{tier}/actions`

- `put_action.py`
  - Run: `python examples/put_action.py --config prod ~/rapididentity/test/xml/SalesforceToMeta.xml`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Reads an actionDef XML file and posts it to `/admin/connect/actions`

- `actiondef_to_script.py`
  - Converts a single actionDef XML file into script text
  - Uses `rapididentity.utils.actiondef_file_to_script`

- `inspect_swagger.py`
  - Run: `python examples/inspect_swagger.py --config prod`
  - Loads config from `~/rapididentity/config/prod.json` (when `--config prod`)
  - Retrieves API docs and searches path names by keyword
  - Saves the fetched document to `~/rapididentity/{tier}/swagger.json`
  - Useful for discovering tenant-specific endpoints

## Removed examples

The following examples were removed because they implied user/group management flows that are not guaranteed by the implemented Connect-focused workflow:

- `basic_usage.py`
- `split_action_defs.py` (functionality moved into `get_actions.py`)
 - `split_action_defs.py` (functionality moved into `get_actions.py`)
