# Security Policy

## Supported versions

YT-DLP Studio uses a rolling release model. Only the latest published release receives security fixes.

| Version | Supported |
|---------|-----------|
| Latest release | Yes |
| Older releases | No |

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

Report it privately through one of these channels:

1. **GitHub Security Advisories (preferred):**
   1. Go to [Security > Advisories](https://github.com/NX1X/yt-dlp-studio/security/advisories).
   2. Click **Report a vulnerability**.
   3. Fill in the form with a clear description and the steps to reproduce.
2. **Email:** contact the maintainer through [nx1xlab.dev](https://nx1xlab.dev).

### What to include

- A description of the vulnerability and its impact.
- Steps to reproduce. A minimal proof of concept is ideal.
- The affected version or versions of YT-DLP Studio.
- Your environment (operating system, Python version and so on).
- Whether the issue is already public anywhere.

### What to expect

- **Acknowledgement** within 72 hours.
- **Initial assessment** within 7 days.
- **Fix and coordinated disclosure** as soon as practical, depending on severity.
- **Credit** in the changelog and in the published advisory, unless you prefer to stay anonymous.

## Security practices

- **Dependency updates:** Renovate opens dependency update pull requests, with a cooldown for regular updates: 14 days for most dependencies, 7 days for the yt-dlp engine. Security fixes skip the cooldown. See [.github/renovate.json5](.github/renovate.json5).
- **Security alerts:** GitHub Dependabot security updates are on in the repository settings. Dependabot version updates are off, because Renovate owns them. See [.github/dependabot.yml](.github/dependabot.yml).
- **Static analysis:** CI runs `ruff` on every push and pull request, with the flake8-bandit (`S`) security rules enabled. CodeQL also runs on pushes, pull requests and every week.
- **Vulnerability scans:** a weekly workflow audits the hash-pinned lock files with `pip-audit` and checks the workflows with `zizmor`. It also runs OpenSSF Scorecard.
- **Secret hygiene:** no credentials, tokens or private keys are committed. GitHub push protection should be enabled on the public repository.
- **Release integrity:** GitHub Actions builds the release files from a pinned source revision. Each release publishes a Sigstore-signed [SLSA build provenance attestation][slsa]. The attestation binds the SHA-256 of each file to the workflow run, the commit and the runner that produced it.

  [slsa]: https://slsa.dev/spec/v1.0/provenance

### Verifying a downloaded release

The attestation covers these release files:

- the portable EXE (`YT-DLP.Studio.exe` on the release page, and `yt-dlp-studio.exe` in the portable ZIP);
- the Linux binary in the `.tar.gz` archive;
- the AppImage, the `.deb` package and the `.rpm` package.

The Windows installer (`YT-DLP-Studio-Setup-<version>.exe`) has no attestation.

1. Install the [GitHub CLI](https://cli.github.com/) (`gh`).
2. Run the command below. Use the name of the file you downloaded.

```bash
gh attestation verify yt-dlp-studio.exe --repo NX1X/yt-dlp-studio
```

A successful verification confirms that:

1. A GitHub Actions workflow in this repository built the file.
2. The build ran on a GitHub-hosted runner, from a specific commit.
3. Nobody changed the file after the build.

If the command fails, **do not run the file**. Someone may have changed or repackaged it, or you downloaded it from an unofficial source.

### Build-time supply-chain hardening

The build workflows are hardened, so that tampering during the build is detectable:

- All GitHub Actions references are pinned to immutable commit SHAs, not tags.
- Bundled third-party binaries (Deno, FFmpeg) are pinned by version **and** by SHA-256. The build verifies them before it unpacks them. The build also cross-checks Deno against the publisher's official `.sha256sum` file.
- Python dependencies are installed with `pip --require-hashes` from hash-locked files (`requirements/lock.txt` and the other files in `requirements/`).
- Workflow jobs run with a least-privilege `permissions:` token.

## Third-party components

YT-DLP Studio bundles or depends on:

- [PySide6](https://www.qt.io/qt-for-python): LGPL v3.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): The Unlicense (public domain).
- [FFmpeg](https://ffmpeg.org/): LGPL or GPL, depending on the build.
- [Deno](https://deno.land/): MIT.

Report vulnerabilities in these projects to their maintainers. We track upstream advisories that affect YT-DLP Studio and ship updates for them.

## Out of scope

- Vulnerabilities in user-supplied URLs or in downloaded media.
- Issues that need privileged local access that is already enough to compromise the host on its own.
- The behavior of the remote sites that yt-dlp downloads from. These are upstream concerns.
