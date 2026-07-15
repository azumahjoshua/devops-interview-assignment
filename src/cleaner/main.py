"""Entry point.

Run with:
    python -m cleaner.main
"""

import sys
from dotenv import load_dotenv

from cleaner.config import Config
from cleaner.keycloak_client import KeycloakClient, KeycloakError
from cleaner.policy import find_stale_users


def main() -> int:

    try:
        # Load .env file for local development
        load_dotenv()

        # Load configuration
        config = Config.from_env()

        # Create Keycloak client
        client = KeycloakClient(
            config.keycloak_url,
            config.realm,
            config.client_id,
            config.client_secret,
        )

        # Retrieve all users
        users = client.list_users()

        # Apply cleanup policy
        result = find_stale_users(users, config)

        disabled = 0
        failed = 0

        if config.dry_run:
            print("\n=== DRY RUN ===")

            for user, reason in result.candidates:
                print(
                    f"[DRY RUN] Would disable "
                    f"'{user['username']}' ({reason})"
                )

        else:
            print("\n=== DISABLING USERS ===")

            for user, reason in result.candidates:
                try:
                    client.disable_user(user)

                    disabled += 1

                    print(
                        f"Disabled "
                        f"'{user['username']}' ({reason})"
                    )

                except KeycloakError as exc:
                    failed += 1

                    print(
                        f"Failed to disable "
                        f"'{user['username']}': {exc}"
                    )

        print("\n========== SUMMARY ==========")
        print(f"Users considered      : {result.considered}")
        print(f"Excluded              : {result.excluded}")
        print(f"Already disabled      : {result.skipped_disabled}")
        print(f"Missing lastLogin     : {result.skipped_missing_login}")
        print(f"Below threshold       : {result.below_threshold}")
        print(f"Candidates            : {len(result.candidates)}")
        print(f"Disabled              : {disabled}")
        print(f"Failed                : {failed}")

        return 0

    except Exception as exc:
        print(f"Fatal error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())