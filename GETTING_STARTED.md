# Getting Started with RapidIdentity Python Library

## Overview

You now have a complete, production-ready Python library for interacting with RapidIdentity REST APIs. This guide will help you get started.

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Navigate to the project directory:**
   ```bash
   cd /home/jeaton3/rapididentity-tools
   ```

2. **Install the library:**
   ```bash
   pip install -e .
   ```

3. **Verify installation:**
   ```bash
   python -c "from rapididentity import RapidIdentityClient; print('✅ Installation successful!')"
   ```

## Configuration

### Option 1: Environment Variables

Create a `.env` file in your project:
```bash
RAPIDIDENTITY_HOST=https://rapididentity.example.com
RAPIDIDENTITY_API_KEY=your-api-key-here
RAPIDIDENTITY_TIMEOUT=30
RAPIDIDENTITY_VERIFY_SSL=true
```

Then load it in Python:
```python
from rapididentity import Config, RapidIdentityClient

config = Config()
client = RapidIdentityClient.with_api_key(
    host=config.get_host(),
    api_key=config.get("api_key")
)
```

### Option 2: JSON Configuration File

Create `config.json`:
```json
{
  "host": "https://rapididentity.example.com",
  "auth_type": "api_key",
  "api_key": "your-api-key-here",
  "timeout": 30,
  "verify_ssl": true
}
```

Then use it:
```python
from rapididentity import Config, RapidIdentityClient

config = Config("config.json")
client = RapidIdentityClient.with_api_key(
    host=config.get_host(),
    api_key=config.get("api_key")
)
```

### Option 3: Direct Configuration

```python
from rapididentity import RapidIdentityClient

client = RapidIdentityClient.with_api_key(
    host="https://rapididentity.example.com",
    api_key="your-api-key-here"
)
```

## Basic Usage

### Simple GET Request

```python
from rapididentity import RapidIdentityClient

with RapidIdentityClient.with_api_key(
    host="https://api.example.com",
    api_key="your-key"
) as client:
    users = client.get("/users")
    print(users)
```

### CREATE, UPDATE, DELETE

```python
# Create
new_user = {"username": "john", "email": "john@example.com"}
response = client.post("/users", data=new_user)

# Update
client.put("/users/123", data={"status": "active"})

# Delete
client.delete("/users/123")
```

### With Query Parameters

```python
params = {
    "status": "active",
    "page": 1,
    "per_page": 50
}
response = client.get("/users", params=params)
```

### Discovering Tenant-Specific Endpoints

RapidIdentity installations may expose slightly different paths depending on
version and configuration. If you're unsure where to find a particular
resource (for example, retrieving a single user record) you can download and
scan the OpenAPI/Swagger document using the helper script:

```bash
python examples/inspect_swagger.py prod-config.json
```

That will print all paths containing keywords like "user" or "person" so you
can pick the correct endpoint and update your code accordingly.  Many
instances perform lookups via the `/users` search endpoint; the script above
also shows the supported query parameters (e.g. `search` and `criteria`).

```python
# once you know the appropriate search type, call the users endpoint
result = client.get(
    "/users",
    params={"search": "id", "criteria": "12345"},
)
```

The `examples/fetch_user.py` script demonstrates this pattern.


## Validation Utilities

```python
from rapididentity.utils import (
    validate_email,
    validate_username,
    validate_url,
    validate_phone
)

# Each returns True/False
validate_email("user@example.com")      # True
validate_username("john_doe")           # True
validate_url("https://example.com")     # True
validate_phone("+1-234-567-8900")       # True
```

## Pagination

```python
from rapididentity.utils import paginate_results

# Get all results automatically paginated
all_users = paginate_results(
    client,
    "/users",
    per_page=100,
    max_pages=None  # Get all pages
)

for user in all_users:
    print(user["username"])
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
    
except AuthenticationError:
    print("Authentication failed - check credentials")
    
except NotFoundError as e:
    print(f"Resource not found: {e}")
    
except APIError as e:
    print(f"API error {e.status_code}: {e.message}")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Common Patterns

### Retry with Automatic Retries

```python
from rapididentity.utils import retry_on_failure

@retry_on_failure(max_retries=3, delay=1.0)
def fetch_users():
    return client.get("/users")

users = fetch_users()
```

### Batch Processing

```python
from rapididentity.utils.helpers import batch_items

users = [{"username": f"user{i}"} for i in range(1000)]
batches = batch_items(users, batch_size=100)

for batch in batches:
    # Process each batch
    for user in batch:
        client.post("/users", data=user)
```

### Data Parsing

```python
from rapididentity.utils.parsers import (
    extract_fields,
    filter_fields,
    flatten_dict
)

user_data = {
    "id": "123",
    "username": "john",
    "email": "john@example.com",
    "password": "secret",  # Don't want this
    "profile": {
        "first_name": "John",
        "last_name": "Doe"
    }
}

# Extract only needed fields
safe_data = extract_fields(user_data, ["username", "email"])

# Remove sensitive fields
public_data = filter_fields(user_data, ["password"])

# Flatten nested structure
flat = flatten_dict(user_data)
# Result: {"id": "123", "username": "john", ..., "profile.first_name": "John", ...}
```

## Authentication Methods

### API Key Authentication
```python
client = RapidIdentityClient.with_api_key(
    host="https://api.example.com",
    api_key="your-api-key"
)
```

### Basic Authentication
```python
client = RapidIdentityClient.with_basic_auth(
    host="https://api.example.com",
    username="admin",
    password="password123"
)
```

### OAuth2 Authentication
```python
client = RapidIdentityClient.with_oauth2(
    host="https://api.example.com",
    access_token="oauth-token"
)
```

## Custom Requests

For arbitrary endpoints (use the generic client methods):

```python
# Generic HTTP methods
response = client.get(endpoint, params=query_params)
response = client.post(endpoint, data=request_body)
response = client.put(endpoint, data=request_body)
response = client.patch(endpoint, data=request_body)
response = client.delete(endpoint)

# With custom headers
client.get(endpoint, headers={"X-Custom-Header": "value"})
```

## Running Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=rapididentity

# Run specific test
pytest tests/test_client.py::TestRapidIdentityClient::test_get_request
```

All 16 tests should pass! ✅

## Examples

Check the [examples/](examples/) directory for:

1. **basic_usage.py** - Basic client operations
2. **utilities_usage.py** - Using validation and parsing utilities  
3. **real_world_scenarios.py** - Practical examples:
   - Bulk user provisioning
   - User auditing
   - Deactivating inactive users

## API Documentation

Visit your RapidIdentity instance to access the API documentation:

```
https://<your-rapididentity-host>/api/rest/api-docs
```

This shows all available endpoints, parameters, and response formats.

## Troubleshooting

### "ModuleNotFoundError: No module named 'rapididentity'"

**Solution:** Install the package:
```bash
pip install -e /path/to/rapididentity-tools
```

### "AuthenticationError: Authentication failed"

**Solution:** Check your credentials:
- Verify API key is correct
- Check host URL is correct
- Ensure credentials have proper permissions

### "NotFoundError: Resource not found"

**Solution:** 
- Verify the endpoint path is correct
- Check if the resource ID exists
- Review API documentation for correct endpoints

### Connection Timeouts

**Solution:** Increase the timeout:
```python
client = RapidIdentityClient.with_api_key(
    host=host,
    api_key=api_key,
    timeout=60  # Increase from default 30
)
```

## Development

### Install Development Dependencies
```bash
pip install -e ".[dev]"
```

### Code Formatting
```bash
black rapididentity tests examples
isort rapididentity tests examples
```

### Linting
```bash
flake8 rapididentity tests examples
```

### Type Checking
```bash
mypy rapididentity
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for:
- Code style guidelines
- Testing requirements
- Pull request process
- Issue reporting

## Support

For help:
1. Check [README.md](README.md) for full documentation
2. Review examples in [examples/](examples/)
3. Look at test cases in [tests/](tests/) for usage patterns
4. Open an issue on GitHub
5. Contact RapidIdentity support

## Project Structure

```
rapididentity-tools/
├── rapididentity/              # Main library
│   ├── client.py              # API client
│   ├── auth.py                # Authentication
│   ├── config.py              # Configuration
│   ├── (no resource wrappers) # resource wrappers removed
│   ├── exceptions.py          # Exception classes
│   └── utils/                 # Utilities
├── examples/                    # Example scripts
├── tests/                       # Test suite
├── README.md                    # Full documentation
├── CONTRIBUTING.md              # Contribution guide
└── pyproject.toml              # Project config
```

## Next Steps

1. ✅ Installation complete
2. ✅ Configuration set up
3. 🚀 Start using the library:
   ```python
   from rapididentity import RapidIdentityClient
   
   with RapidIdentityClient.with_api_key(host, api_key) as client:
       response = client.get("/users")
       print(response)
   ```

4. 📚 Review examples and documentation
5. 🧪 Write your first script
6. 🤝 Contribute improvements!

Happy coding! 🎉
