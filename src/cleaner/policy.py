from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

User = dict[str, Any]
Candidate = tuple[User, str]


@dataclass
class CleanupResult:
    """Summary of the cleanup policy evaluation."""

    considered: int
    excluded: int
    skipped_disabled: int
    skipped_missing_login: int
    below_threshold: int
    candidates: list[Candidate]


def find_stale_users(users: list[User], config) -> CleanupResult:
    """Evaluate users and return cleanup candidates plus summary statistics."""

    now = datetime.now(timezone.utc)

    candidates: list[Candidate] = []

    excluded = 0
    skipped_disabled = 0
    skipped_missing_login = 0
    below_threshold = 0

    for user in users:

        username = user["username"]

        # Skip already-disabled users
        if not user.get("enabled", True):
            skipped_disabled += 1
            print(f"Skipping {username}: already disabled.")
            continue

        # Skip excluded usernames
        if username in config.exclusions:
            excluded += 1
            print(f"Skipping {username}: excluded.")
            continue

        attributes = user.get("attributes", {})

        last_login = attributes.get("lastLogin")

        # Skip users without a lastLogin attribute
        if not last_login:
            skipped_missing_login += 1
            print(f"Skipping {username}: missing lastLogin.")
            continue

        last_login_ms = int(last_login[0])

        last_login_dt = datetime.fromtimestamp(
            last_login_ms / 1000,
            tz=timezone.utc,
        )

        inactive_days = (now - last_login_dt).days

        if inactive_days >= config.inactivity_days:
            candidates.append(
                (
                    user,
                    f"inactive for {inactive_days} days",
                )
            )
        else:
            below_threshold += 1

    return CleanupResult(
        considered=len(users),
        excluded=excluded,
        skipped_disabled=skipped_disabled,
        skipped_missing_login=skipped_missing_login,
        below_threshold=below_threshold,
        candidates=candidates,
    )