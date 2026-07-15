"""Keycloak Admin API client.

Suggested shape:
    - get_token()          - fetch an access token via client_credentials
    - list_users()         - paginate through the realm's users
    - delete_user(user_id) - delete (or disable, if you prefer soft delete)

You can use `python-keycloak`, `requests`, `httpx`, or roll your own.
No requirement — pick whatever fits your approach.
"""

import httpx
from datetime import datetime, timezone


class KeycloakError(Exception):
    """Raised when communication with Keycloak fails."""


class KeycloakClient:
    def __init__(self, base_url: str, realm: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret

    def get_token(self) -> str:
        """Fetch an OAuth2 access token using the client credentials grant."""

        token_url = (
            f"{self.base_url}/realms/"
            f"{self.realm}/protocol/openid-connect/token"
        )

        try:
            response = httpx.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                timeout=10.0,
            )
        except httpx.RequestError as exc:
            raise KeycloakError(
                f"Unable to connect to Keycloak at {self.base_url}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise KeycloakError(
                f"Failed to obtain access token "
                f"(HTTP {response.status_code}): {response.text}"
            )

        token = response.json().get("access_token")

        if not token:
            raise KeycloakError(
                "Keycloak response did not contain an access token."
            )

        return token

    def list_users(self) -> list[dict]:
        """Return all non-service-account users in the realm."""

        token = self.get_token()

        users = []
        first = 0
        page_size = 100

        headers = {
            "Authorization": f"Bearer {token}"
        }

        users_url = f"{self.base_url}/admin/realms/{self.realm}/users"

        while True:
            try:
                response = httpx.get(
                    users_url,
                    headers=headers,
                    params={
                        "first": first,
                        "max": page_size,
                    },
                    timeout=10.0,
                )
            except httpx.RequestError as exc:
                raise KeycloakError(
                    f"Unable to retrieve users from Keycloak: {exc}"
                ) from exc

            if response.status_code != 200:
                raise KeycloakError(
                    f"Failed to list users "
                    f"(HTTP {response.status_code}): {response.text}"
                )

            page = response.json()

            # No more users to fetch.
            if not page:
                break

            # Ignore service-account users.
            for user in page:
                if "serviceAccountClientId" in user:
                    continue

                users.append(user)

            first += page_size

        return users

    def disable_user(self, user: dict) -> None:
        """Disable a user instead of permanently deleting them."""

        token = self.get_token()

        user_id = user["id"]

        user["enabled"] = False

        attributes = user.setdefault("attributes", {})

        attributes["disabledBy"] = [self.client_id]
        attributes["disabledAt"] = [
            datetime.now(timezone.utc).isoformat()
        ]

        url = (
            f"{self.base_url}/admin/realms/"
            f"{self.realm}/users/{user_id}"
        )

        try:
            response = httpx.put(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json=user,
                timeout=10.0,
            )
        except httpx.RequestError as exc:
            raise KeycloakError(
                f"Unable to disable user "
                f"{user['username']}: {exc}"
            ) from exc

        if response.status_code not in (200, 204):
            raise KeycloakError(
                f"Failed to disable "
                f"{user['username']} "
                f"(HTTP {response.status_code}): "
                f"{response.text}"
            )