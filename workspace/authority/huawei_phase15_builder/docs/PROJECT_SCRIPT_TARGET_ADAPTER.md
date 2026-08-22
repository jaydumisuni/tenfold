# Project-owned target script adapter

The Builder remains the shared build authority. A project may already own a proven, deterministic build script whose semantics must not be replaced by Builder's language-default adapter. In that case the project can bind one configured output target on one exact detected build root to that script through `techguy-build.json`.

This is an opt-in target adapter. Projects that do not configure `targetAdapters` continue through the existing Builder adapters unchanged.

## Contract

```json
{
  "targets": ["windows-exe"],
  "targetAdapters": {
    "windows-exe": {
      "kind": "project-script",
      "rootKind": "python-qt",
      "rootPath": ".",
      "runner": "powershell",
      "script": "build_windows.ps1",
      "workingDirectory": ".",
      "args": [],
      "artifact": "dist/Example.exe",
      "toolchains": {
        "python": "3.11",
        "rust": "1.75.0"
      }
    }
  }
}
```

Fields:

- `kind` must be `project-script`.
- `rootKind` is required and binds the adapter to the exact detected Builder root kind, for example `python-qt`.
- `rootPath` is required and binds the adapter to the exact project-relative Builder root directory. A different selected root falls back to the normal adapter instead of executing the whole-project script under false root provenance.
- `runner` is allowlisted: `powershell`, `python`, `bash`, or `node`.
- `script` must be a project-relative file and its extension must match the runner.
- `workingDirectory` is optional and defaults to the project root. It must remain inside the project.
- `args` is an optional array of literal strings. Builder never evaluates them through a shell.
- `artifact` is the project-relative canonical artifact the script promises to create.
- `toolchains.python` optionally requests an exact Python major.minor or major.minor.patch version.
- `toolchains.rust` optionally requests an exact Rust toolchain version managed through an existing rustup installation.
- The target must also be present in the project's top-level `targets` array.

## Builder-owned toolchain environment

When `toolchains.python` is declared, Builder reuses its managed-Python resolver and creates a target-specific virtual environment below `builder_cache/project-script-envs`. The application project never receives a `.venv`. The target environment is prepended to `PATH`, exported as `VIRTUAL_ENV`, and isolated from user-site packages. Project-owned scripts may install their own release dependencies into that isolated target environment without contaminating Builder's UI Python or a machine-wide Python installation.

When `toolchains.rust` is declared, Builder first resolves `rustup` and `cargo` from the inherited PATH, `CARGO_HOME`, or the standard user `.cargo/bin` directory. This makes existing Rust installations deterministic even when a workstation RPC session has a reduced PATH. Builder pins the requested toolchain through `RUSTUP_TOOLCHAIN`. If the requested toolchain is absent, Builder installs it through the existing rustup only when dependency installation was explicitly authorized; otherwise the build fails closed. Builder does not silently install a separate Rust distribution.

Dependency provisioning is **not** automatically implied by a build request. The headless Builder path grants it for one execution only with:

```text
python scripts/builder_ops.py execute --project <project-root> --target <target-id> --install-dependencies
```

Without `--install-dependencies`, Builder removes any inherited internal dependency-install grant before spawning the target execution and missing requested toolchains remain a truthful blocked state. The hardened generic adapter consumes the one-shot internal grant, converts it to the existing project-script `--install-dependencies` flag, then removes the internal marker before the project-owned build environment is prepared. This keeps install authority explicit and prevents project scripts from inheriting Builder's internal authorization signal.

## Progress and runtime proof

The adapter continues Builder's existing stage contract rather than opening a second nested progress sequence. Windows executable work occupies stages 2 through 6 of the normal eight-stage application flow; runtime verification remains stage 7 and final completion remains stage 8. Windows installer work uses the corresponding twelve-stage flow.

After staging, Windows runtime smoke verification treats the exact artifact recorded in `build_config/thetechguy.target-adapter-report.json` as authoritative. For `project-script` reports, the verifier also requires the requested target to match, the executable to remain inside the Builder-recorded output directory, and the live staged file SHA-256 to equal the digest recorded when Builder accepted the artifact. A missing or changed staged payload fails closed instead of falling back to another executable. Other executables found in project `dist` locations remain diagnostic candidates but cannot outrank the exact Builder-staged payload.

## Boundaries

Builder executes the script as a process argument vector with `shell=False`. PowerShell scripts are invoked with `-NoProfile`, `-NonInteractive`, and `-File`. Selected root, configured root binding, script, working-directory, artifact and Builder staging paths are confined to the selected project root. Symlink components are rejected before execution and the artifact/output paths are re-resolved after the project process exits, so a build cannot replace a previously checked directory with a symlink and escape containment. Missing root bindings, missing scripts, path escapes, mismatched runner/script types, non-zero script exits, stale/missing/empty artifacts, malformed toolchain requests, and unconfigured targets fail closed.

Final artifact staging is also protected at the **file-entry** boundary. Builder copies the accepted canonical artifact to a fresh temporary file inside the revalidated output directory, rechecks the source fingerprint, then atomically replaces the final artifact entry. A project-created symlink at the final staged filename is replaced as an entry rather than followed to its target. Builder-owned adapter and blocked reports use the same temporary-file plus atomic-replacement pattern, so a project-created report-file symlink cannot redirect Builder's report write outside the project.

The canonical project artifact remains inside the project. Builder stages an exact copy into its normal project-local target-artifact output and records the selected root, configured root binding, source artifact, staged artifact, SHA-256, runner, script, artifact freshness, and resolved toolchain evidence in `build_config/thetechguy.target-adapter-report.json`.

## Ownership

Use this contract when project-specific build semantics already exist and are part of that project's release authority. Do not copy Builder implementation scripts into the project. Shared execution logic, environment/toolchain management, validation, containment, runtime verification and reporting stay in Builder; the project owns only its build script and `techguy-build.json` configuration.
