# G01 Operations

Required commands:

- bash shield/scripts/run-g01.sh — bootstrap, execute the deterministic test suite twice, generate evidence, and teardown.
- bash shield/scripts/destroy-test-env.sh — destroy any disposable environment.
- bash shield/scripts/verify-clean.sh — verify namespaces, temporary state, and test interfaces are gone.

The test environment identifier is shield-g01-<short-sha>-<run-id> when CI supplies those values.

No command in this directory may contact Stripe, production infrastructure, customer systems, or arbitrary public services.
