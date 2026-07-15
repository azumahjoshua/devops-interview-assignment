"""Configuration loading.

Reads from environment variables. See .env.example for the expected shape.
"""

import os
from dataclasses import dataclass


@dataclass
class Config:
    keycloak_url: str
    realm: str
    client_id: str
    client_secret: str
    inactivity_days: int
    dry_run: bool
    exclusions: list[str]

    @classmethod
    def from_env(cls) -> "Config":
        def require_env(name: str) -> str:
            value = os.getenv(name)
            if value is None or value.strip() == "":
                raise ValueError(
                    f"Missing required environment variable: {name}"
                )
            return value.strip()

        keycloak_url = require_env("KEYCLOAK_URL")
        realm = require_env("KEYCLOAK_REALM")
        client_id = require_env("KEYCLOAK_CLIENT_ID")
        client_secret = require_env("KEYCLOAK_CLIENT_SECRET")

        try:
            inactivity_days = int(require_env("INACTIVITY_DAYS"))
        except ValueError as exc:
            raise ValueError(
                "INACTIVITY_DAYS must be a valid integer."
            ) from exc

        dry_run_value = require_env("DRY_RUN").lower()
        if dry_run_value == "true":
            dry_run = True
        elif dry_run_value == "false":
            dry_run = False
        else:
            raise ValueError(
                "DRY_RUN must be either 'true' or 'false'."
            )

        exclusions = [
            item.strip()
            for item in require_env("EXCLUSIONS").split(",")
            if item.strip()
        ]

        return cls(
            keycloak_url=keycloak_url,
            realm=realm,
            client_id=client_id,
            client_secret=client_secret,
            inactivity_days=inactivity_days,
            dry_run=dry_run,
            exclusions=exclusions,
        )