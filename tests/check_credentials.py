"""Simple script to verify credentials from a config file."""

# ensure local package is on path
import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from rapididentity import Config, RapidIdentityClient, APIError


def main(config_path: str = "prod-config.json"):
    cfg = Config(config_path)
    client = RapidIdentityClient.with_api_key(
        host=cfg.get_host(),
        api_key=cfg.get("api_key"),
    )

    try:
        # a simple request; some tenants don't accept paging parameters
        print("Hitting /users endpoint to verify credentials...")
        response = client.get("/users")
        print("Success! Response:", response)
        print("✅ Credentials look valid")
    except APIError as e:
        # retry without params if the first call failed with a 400 bad request
        if e.status_code == 400:
            print("Got 400, retrying without /users path")
            try:
                resp2 = client.get("/")
                print("Root request returned:", resp2)
                # some tenants return 404 for root but the key still worked
                print("✅ Credentials appear valid (authenticated but root path not exposed)")
            except Exception as exc:
                # if we get 404, still treat as success
                if isinstance(exc, APIError) and exc.status_code == 404:
                    print("Received 404 on root – authentication succeeded though the endpoint is not available")
                    print("✅ Credentials appear valid")
                else:
                    print("Second attempt failed:", exc)
        else:
            print(f"API error {e.status_code}: {e.message}")
    except Exception as e:
        print("Failed to connect or authenticate:", e)
    finally:
        client.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()
