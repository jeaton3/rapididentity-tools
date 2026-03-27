# RapidIdentity Python Library

A Python library and utilities for interacting with RapidIdentity REST APIs.  This is nearly all AI-generated code via Github Copilot in VSCode.  It seems to work well enough for my needs, but no promises that it will work in all situations.  The example scripts all only perform read actions, so they should be safe.  You can, of course, call things that execute code or delete things from Rapid Identity by calling the functions yourself using the library directly.

## Notes
 - I have only used API key authentication.  To generate an API key, go to Configuration / Security / Service Identities.  Create a new identity, and click on it and choose "Keys".  Add a key and assign it the appropriate role(s).  Note that you cannot modify roles after the key is created.  You will need to create a new key to add or remove roles.
 - For the ActionSet archiver/decoder, I granted the "Connect Auditor" role which has the ability to fetch the ActionSets.
 - examples/get_actions.py will same each actionset XML to an individual file.  These output files are identical to an export from the web UI, apart from whitespace formatting and the XML preamble.  The tranlated js files attempt to mirror what you see in the Action Sets editor.  "Disabled" likes are prefixed with ## since there's no ASCII strikethrough. The arguments section is expanded and indluded in the file (prefixed with // ), so the line numbers in the exported js file will be off from the online editor by that much.

- examples/connect_file_utils.py lets you view and manipulate files and logs in the connect module.  Even though Logs shows up distinct from Files in the web UI, they are the same to the api. It takes arguments to do a few differnt things:
- -  "ls" to list directories/files
- - "cat" to fetch a file and write it to standard output (automatically un-gzipping if to a terminal and not redirected to a file)
- - rsync to syncronize files from a rapididentity instance to a local repica, with the ability to sync only 
## Features

- **Multiple Authentication Methods**: Support for API Key, Basic Auth, and OAuth2
- **Easy-to-use Client**: Simple, intuitive API client for making requests
- **Built-in Error Handling**: Comprehensive exception handling for API errors
- **Utilities Suite**: Validation, parsing, pagination, and helper functions
- **Retry Logic**: Automatic retry mechanism for failed requests
- **Type Hints**: Full type annotation support for better IDE integration
- **Context Manager Support**: Automatic resource cleanup with context managers

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/rapididentity-tools.git
cd rapididentity-tools

# Install in development mode
pip install -e .

# Install with development dependencies
pip install -e ".[dev]"
```

## Quick Start

### Create Client from Config

The helper method `RapidIdentityClient.from_config()` makes it easy to
construct a client directly from a `rapididentity.Config` instance which can
load from environment variables or a JSON file.

```python
from rapididentity import Config, RapidIdentityClient

config = Config("config.json")
client = RapidIdentityClient.from_config(config)
```

### Basic Usage with API Key

```python
from rapididentity import RapidIdentityClient

# Create client
client = RapidIdentityClient.with_api_key(
    host="https://rapididentity.example.com",
    api_key="your-api-key"
)

# Make API calls
users = client.get("/users")
print(users)

# Don't forget to close
client.close()
```

### Using Context Manager

```python
from rapididentity import RapidIdentityClient

with RapidIdentityClient.with_api_key(
    host="https://rapididentity.example.com",
    api_key="your-api-key"
) as client:
    users = client.get("/users")
    print(users)
```

### Basic Authentication

```python
client = RapidIdentityClient.with_basic_auth(
    host="https://rapididentity.example.com",
    username="admin",
    password="password"
)
```

### OAuth2 Authentication

```python
client = RapidIdentityClient.with_oauth2(
    host="https://rapididentity.example.com",
    access_token="your-oauth-token"
)
```

## Discovering Endpoints

If you're unsure about the exact URL or parameters for a particular resource,
use the `examples/inspect_swagger.py` script to pull your tenant's OpenAPI
spec and search for keywords. The output will list candidate paths and makes
it easy to determine how to invoke the API (e.g. `/users` with
`search`/`criteria` parameters).

```bash
python examples/inspect_swagger.py prod-config.json
```

Also see `examples/fetch_user.py` for a simple user search example.

Another handy script is `examples/show_system_info.py`, which hits
`/admin/systemInfo` and prints whatever your tenant exposes (it’s a good sanity
check for connectivity and permissions).  **You’ll need an API key with
admin/system-info rights** – configure this in the RapidIdentity web console by
assigning the key a System Administrator role or equivalent.

## API Methods

The client supports standard HTTP methods:

### GET Request
```python
response = client.get("/users")
response = client.get("/users", params={"status": "active"})
```

### POST Request
```python
new_user = {
    "username": "john.doe",
    "email": "john@example.com"
}
response = client.post("/users", data=new_user)
```

### PUT Request
```python
update_data = {"email": "newemail@example.com"}
response = client.put("/users/123", data=update_data)
```

### PATCH Request
```python
partial_update = {"status": "inactive"}
response = client.patch("/users/123", data=partial_update)
```

### DELETE Request
```python
response = client.delete("/users/123")
```

## Utilities

### Validation

```python
from rapididentity.utils import (
    validate_email,
    validate_username,
    validate_url,
    validate_phone
)

validate_email("user@example.com")  # True
validate_username("john_doe")       # True
validate_url("https://example.com") # True
```

### Parsing

```python
from rapididentity.utils.parsers import (
    parse_api_response,
    extract_fields,
    filter_fields,
    flatten_dict
)

# Extract specific fields
fields = extract_fields(user_data, ["username", "email"])

# Filter out fields
filtered = filter_fields(user_data, ["password", "secret"])

# Flatten nested structure
flat = flatten_dict(user_data)
```

### Pagination

```python
from rapididentity.utils import paginate_results

# Get all results across pages
all_users = paginate_results(
    client,
    "/users",
    per_page=100,
    max_pages=10
)
```

### Retry Logic

```python
from rapididentity.utils import retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0)
def fetch_data():
    response = client.get("/unstable-endpoint")
    return response
```

## Error Handling

```python
from rapididentity import (
    RapidIdentityClient,
    AuthenticationError,
    NotFoundError,
    APIError
)

try:
    client = RapidIdentityClient.with_api_key(host, api_key)
    response = client.get("/users")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
except NotFoundError as e:
    print(f"Resource not found: {e}")
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
```

## Testing

Run the test suite:

```bash
pytest tests/

# With coverage
pytest tests/ --cov=rapididentity
```

## Configuration

### Environment Variables

You can configure the client using environment variables:

```bash
export RAPIDIDENTITY_HOST="https://rapididentity.example.com"
export RAPIDIDENTITY_API_KEY="your-api-key"
```

### Custom Settings

```python
client = RapidIdentityClient.with_api_key(
    host="https://rapididentity.example.com",
    api_key="your-api-key",
    verify_ssl=True,      # Verify SSL certificates (default: True)
    timeout=30            # Request timeout in seconds (default: 30)
)
```

## Examples

See the [examples/](examples/) directory for more detailed examples:

- [basic_usage.py](examples/basic_usage.py) - Basic client usage patterns
- [utilities_usage.py](examples/utilities_usage.py) - Working with utilities

## Documentation

For detailed API documentation, access the RapidIdentity Swagger UI:

```
https://<your-rapididentity-host>/api/rest/api-docs
```

## Project Structure

```
rapididentity-tools/
├── rapididentity/           # Main library package
│   ├── __init__.py
│   ├── client.py           # Main API client
│   ├── auth.py             # Authentication configurations
│   ├── exceptions.py       # Custom exceptions
│   └── utils/              # Utility modules
│       ├── validators.py   # Validation functions
│       ├── parsers.py      # Data parsing utilities
│       └── helpers.py      # Helper functions
├── examples/               # Example scripts
├── tests/                  # Test suite
└── pyproject.toml         # Project configuration
```

## Development

### Setup Development Environment

```bash
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Lint and Format

```bash
black rapididentity tests examples
isort rapididentity tests examples
flake8 rapididentity tests examples
```

### Type Checking

```bash
mypy rapididentity
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues, questions, or feature requests, please open an issue on GitHub or contact the RapidIdentity support team.

## References

- [RapidIdentity API Documentation](https://help.rapididentity.com/docs/accessing-rapididentity-apis)
- [RapidIdentity OpenAPI/Swagger Docs](https://help.rapididentity.com/docs/accessing-rapididentity-apis?highlight=api)

## Changelog

### Version 0.1.0
- Initial release
- API client with multiple authentication methods
- Utility modules for validation, parsing, and pagination
- Comprehensive error handling
- Full test coverage
