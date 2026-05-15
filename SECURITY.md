# Security Policy

## Supported Versions

YT-DLP Studio follows a rolling-release model. Only the latest published
release receives security patches.

| Version       | Supported          |
|---------------|--------------------|
| latest        | :white_check_mark: |
| < latest      | :x:                |

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, report them privately via one of:

1. **GitHub Security Advisories** (preferred):
   - Go to [Security > Advisories](https://github.com/NX1X/yt-dlp-studio/security/advisories)
   - Click **"Report a vulnerability"**
   - Fill out the form with a clear description and reproduction steps

2. **Email**: contact the maintainer through [nx1xlab.dev](https://nx1xlab.dev)

### What to include

- A description of the vulnerability and its impact
- Steps to reproduce (a minimal proof-of-concept is ideal)
- Affected version(s) of YT-DLP Studio
- Your environment (OS, Python version, etc.)
- Whether the issue has been disclosed publicly anywhere

### What to expect

- **Acknowledgement** within 72 hours
- **Initial assessment** within 7 days
- **Fix and coordinated disclosure** as soon as practical, depending on severity
- You will be credited in the changelog and the published advisory unless you
  prefer to remain anonymous

## Security Practices

- **Dependency monitoring**: Dependabot watches GitHub Actions and Python
  dependencies (pip + pyproject.toml). See [.github/dependabot.yml](.github/dependabot.yml).
- **Daily security channel**: A dedicated daily Dependabot entry opens
  security-only PRs in addition to the weekly version channel.
- **Static analysis**: CI runs `ruff` (with `flake8-bandit` security rules
  available) on every push and PR.
- **Secret hygiene**: No credentials, tokens, or private keys are committed.
  GitHub push protection should be enabled on the public repo.
- **Release integrity**: Release artifacts are built in GitHub Actions from a
  pinned source revision. Each release executable is published with a
  Sigstore-signed [SLSA build provenance attestation][slsa] cryptographically
  binding the binary's SHA-256 to the exact workflow run, commit, and runner
  that produced it.

  [slsa]: https://slsa.dev/spec/v1.0/provenance

### Verifying a downloaded release

Install the [GitHub CLI](https://cli.github.com/) (`gh`), then:

```bash
gh attestation verify yt-dlp-studio.exe --repo NX1X/yt-dlp-studio
```

A successful verification confirms:

1. The exe was built by `.github/workflows/build.yml` in this repository.
2. The build ran on a GitHub-hosted runner from a specific commit.
3. The binary has not been modified since it was produced.

If the command fails, **do not run the executable** - it has been tampered
with, repackaged, or downloaded from an unofficial source.

### Build-time supply-chain hardening

The build workflow itself is hardened to make tampering during the build
detectable:

- All `actions/*` references are pinned to immutable commit SHAs (not tags).
- Bundled third-party binaries (Deno, FFmpeg) are pinned by version **and**
  SHA-256, verified before unpacking. Deno is additionally cross-checked
  against the publisher's official `.sha256sum` sidecar.
- Python dependencies are installed via `pip --require-hashes` against a
  hash-locked manifest (`requirements.lock`).
- Workflow jobs run with a least-privilege `permissions:` token.

## Third-Party Components

YT-DLP Studio bundles or depends on:

- [PySide6](https://www.qt.io/qt-for-python) - LGPL v3
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - The Unlicense (Public Domain)
- [FFmpeg](https://ffmpeg.org/) - LGPL/GPL depending on build

Vulnerabilities in those upstream projects should be reported to their
respective maintainers. We track upstream advisories that affect YT-DLP
Studio and ship updates accordingly.

## Out of Scope

- Vulnerabilities in user-supplied URLs or downloaded media
- Issues that require privileged local access already sufficient to compromise
  the host independently
- Behaviour of remote sites yt-dlp downloads from (those are upstream concerns)
