# Integration diagnostic

The Drive collection contains multiple upstream repositories, each with its own entrypoint, license, and runtime. This monorepo intentionally does not rewrite those upstream projects. `integrations.yaml` records the discovered path and likely start command; verify each upstream README and Dockerfile before production deployment.

The orchestrator currently provides safe wrappers and configuration templates. Provider activation still requires human-supplied jurisdiction, credentials, legal text, and test destinations.
