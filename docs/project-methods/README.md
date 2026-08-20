# Project Method Runtime Binding

Project method profiles under this directory are **non-authoritative execution-method metadata**.

Tenfold may bind an active profile to a campaign runtime through the project-method registry in `registry.json`. The binding is exact-content-addressed: a saved binding includes the profile identity, revision, path and SHA-256 digest of the profile document. If the profile changes, the old binding becomes stale and must not be silently reused.

The runtime binding is intentionally outside `CampaignManifest` and therefore outside campaign authority. It cannot change:

- blueprint identity or digest;
- campaign identity or digest;
- dependency relationships or Foreman frontier;
- Assurance Matrix requirements;
- mutation permissions;
- milestone proof or Ship authority.

Method observations and revision proposals are evidence for improving how Tenfold executes a project. They do not self-apply. A profile revision remains an explicit reviewed documentation/configuration change.

Use `TEMPLATE.md` to create new profiles and update `registry.json` with the active project/profile mapping.
