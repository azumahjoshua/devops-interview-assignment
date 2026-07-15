# Keycloak User Cleanup Service

A Kubernetes CronJob-based service that identifies inactive Keycloak users and safely disables them using the Keycloak Admin API.

1. Approach chosen, approaches rejected, and reasoning

I chose a modular design by separating the application into three distinct components:

- config.py is responsible for loading and validating runtime configuration from environment variables.
- keycloak_client.py handles all communication with the Keycloak Admin REST API, including authentication using the OAuth 2.0 Client Credentials flow and user management operations.
- policy.py contains the business logic that determines which users are eligible for cleanup based on inactivity, exclusions, and account status.

Separating these responsibilities keeps the business rules independent of the Keycloak API implementation. This improves readability, makes the code easier to maintain, and allows the cleanup policy to be tested or modified without changing how the application communicates with Keycloak.

The cleanup operation disables inactive users instead of deleting them. Disabling accounts is a safer and reversible operation that preserves user information and audit history while preventing inactive users from accessing the system.

The application authenticates to Keycloak using a dedicated service account and the Client Credentials flow instead of an administrator username and password. This follows Keycloak's recommended approach for machine-to-machine applications and limits the permissions granted to the cleanup service.

Configuration is externalized through environment variables, allowing the same container image to be deployed across multiple environments without code changes. When deployed to Kubernetes, non-sensitive configuration is supplied through a ConfigMap, while the Keycloak client secret is injected from a Kubernetes Secret.

During the design, I considered embedding the cleanup policy directly in the Keycloak client and permanently deleting inactive users. I rejected these approaches because they tightly couple business logic to API communication and increase operational risk by making user removal irreversible.

2. How this deploys on K8s (points at `deploy/`)

The Kubernetes deployment is provided in the `deploy/` directory as a Helm chart.

The chart deploys the cleanup application as a Kubernetes CronJob, allowing it to run automatically on a configurable schedule. The `CronJob` executes the Python application (`python -m cleaner.main`) inside a container image built from this project.

Runtime configuration is injected through a `ConfigMap` using `envFrom`, while sensitive information such as the Keycloak client secret is supplied through an existing Kubernetes Secret. This keeps `secrets` separate from application configuration and avoids embedding sensitive values in the Helm chart.

A dedicated Kubernetes `ServiceAccount` is assigned to the `CronJob`. Although the application does not require Kubernetes API permissions, using a dedicated ServiceAccount follows Kubernetes security best practices and clearly separates the Kubernetes identity from the Keycloak service account used for authentication.

The chart also includes a `Role` and `RoleBinding`, currently defined with no permissions because the application does not interact with Kubernetes resources. These resources provide a clear extension point if future versions require access to the Kubernetes API.
They demonstrate the intended security boundary and allow future extension if Kubernetes API access becomes required.

To improve operational reliability, the CronJob is configured with `concurrencyPolicy: Forbid` to prevent overlapping executions, `restartPolicy`: Never, configurable resource requests and limits, and a configurable execution schedule through Helm values.

3. Where per-realm config lives, and safety rails (`exclusions, dry-run, audit`)

The application is designed to process a single Keycloak realm per execution. The realm-specific configuration is externalized through environment variables, allowing the same container image to be reused across different environments without modification.

When deployed to Kubernetes, these values are provided through a `ConfigMap`, while the Keycloak client secret is injected from a Kubernetes `Secret`. The primary realm-specific configuration includes:

- `KEYCLOAK_URL`
- `KEYCLOAK_REALM`
- `KEYCLOAK_CLIENT_ID`
- `INACTIVITY_DAYS`
- `DRY_RUN`
- `EXCLUSIONS`

Several safety mechanisms are built into the cleanup process to reduce operational risk:

- **Dry-run** mode allows the cleanup job to identify candidate users without making any changes. This provides a safe way to validate the cleanup policy before enabling destructive operations.
- **Exclusions** allow privileged or critical accounts, such as break-glass or administrator accounts, to be permanently excluded from cleanup regardless of inactivity.
- **Disabled accounts are skipped**, preventing unnecessary API calls and repeated processing.
- **Users** without a recorded `lastLogin` attribute are skipped, ensuring the application does not make assumptions when sufficient data is unavailable.
- **Execution summary (audit output)** is produced at the end of every run, reporting the number of users considered, excluded accounts, already disabled users, users below the inactivity threshold, cleanup candidates, successfully disabled users, and any failures. This provides an execution audit summary through application logs that operators can review after each run.

4. How the design would extend to many realms. You don't build it. Show the seam.

The current implementation processes one Keycloak realm per execution, with realm configuration supplied through environment variables.

To support multiple realms, I would introduce a realm configuration layer that provides a list of realm-specific settings. The application would iterate through these configurations and create a separate `KeycloakClient` instance for each realm.

The cleanup policy would remain unchanged because it is independent from Keycloak communication. The existing separation between configuration, API client, and cleanup policy provides the extension point for multi-realm support.

For larger environments, separate CronJobs per realm could also be considered to provide isolation and independent scheduling.

5. One thing you'd change in production

In production, I would integrate a dedicated secrets management solution such as HashiCorp Vault with External Secrets Operator (ESO) instead of managing secrets manually through Kubernetes Secrets

This would provide centralized secret management, automatic secret rotation, and reduce the risk of exposing sensitive credentials during deployment.

6. AI usage. Five to ten lines. Where AI helped, where you accepted its output, where you overrode it.

AI was used as a development assistant to help with design discussions, troubleshooting, and reviewing implementation choices.

It helped me understand and validate Keycloak authentication patterns, including the choice of OAuth2 Client Credentials with a service account instead of administrator credentials.

It assisted with reviewing the application structure and supported the separation of responsibilities between configuration loading, the Keycloak API client, and cleanup policy logic.

It also helped review Kubernetes deployment patterns, including Helm templates for the CronJob, ConfigMap, Secret handling, and ServiceAccount configuration.

I accepted suggestions that improved maintainability and security, but I evaluated each recommendation against the assignment requirements. For example, I kept the implementation focused on a single realm rather than adding full multi-realm orchestration because the assignment only required showing the extension point.

I also chose Kubernetes Secrets for the assignment deployment and documented HashiCorp Vault with External Secrets Operator as a production improvement rather than introducing unnecessary infrastructure.

All AI-assisted suggestions were reviewed, adapted, and validated through manual testing using Docker, Kind, Helm, and Keycloak.

I overrode recommendations that increased implementation scope without improving the assignment outcome, such as implementing full multi-realm processing and additional infrastructure before the core workflow was validated.

## Deployment

```bash
helm upgrade --install cleanup ./deploy