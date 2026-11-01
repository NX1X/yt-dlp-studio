# Code Signing - Internal Maintainer Notes

Status as of 2026-05-10, still true for release 0.3.1: **release binaries
are not Authenticode-signed.** Users see a SmartScreen "Unknown publisher"
warning on the first run. This document records the plan to fix that without
paying for a certificate.

This is an internal/maintainer document. End-user verification instructions
live in [`SECURITY.md`](../SECURITY.md).

---

## What we already have

The build workflows produce a **Sigstore-signed SLSA build provenance
attestation** for every release EXE (`actions/attest-build-provenance` in
`.github/workflows/build.yml` and `.github/workflows/release.yml`). The
release workflow also attests the Linux binary and packages. The Windows
installer is not attested.

The attestation binds the SHA-256 of the EXE to the workflow file, the
commit and the runner that produced it. Anyone can verify it with:

```bash
gh attestation verify yt-dlp-studio.exe --repo NX1X/yt-dlp-studio
```

**What this gives us:** strong supply-chain integrity. A user who runs the
verification command can prove that the downloaded binary is the one our CI
built, with no changes.

**What this does NOT give us:** Windows does not natively trust Sigstore
signatures. SmartScreen and the UAC prompt both ignore the attestation. For
this reason, the first-run "Unknown publisher" warning stays until we add
Authenticode on top.

The two complement each other. Keep both after Authenticode is in place.

---

## Why we need Authenticode (separately from Sigstore)

Authenticode is the only signature format Windows actually checks at runtime:

- **SmartScreen** uses the Authenticode publisher identity to compute reputation.
  Without it, every release re-triggers the warning regardless of how many
  prior versions ran cleanly.
- **UAC prompts** show "Verified publisher: ..." when a trusted CA signed the
  binary with Authenticode. Unsigned binaries show "Unknown publisher" in red.
- **Some enterprise environments** (AppLocker, WDAC) refuse to execute
  unsigned binaries entirely.

Even with perfect Sigstore provenance, an unsigned EXE causes user friction
on every release.

---

## The free path: SignPath Foundation

[SignPath Foundation](https://signpath.org/) is a non-profit that signs
open-source artifacts with its own paid Authenticode certificate, free of
charge. Windows trusts these signatures the same as a $400/year EV
certificate.

Established projects signed via SignPath include NUnit, NLog, Paint.NET,
and many others.

### Eligibility

- Public source code under an OSI-approved license. Yes: Apache-2.0 (see
  `LICENSE`).
- Public GitHub or GitLab repository. Yes.
- Maintainer willing to undergo a lightweight identity check.
- Project must be reasonably mature / not abandoned.

### Application process

1. Submit at <https://signpath.org/apply>. Provide:
   - Repository URL
   - Short project description
   - Maintainer name + contact
   - License confirmation
2. Wait for review. Typical turnaround is 2 to 4 weeks.
3. If approved, SignPath provisions:
   - A SignPath organization for the project
   - A signing policy tied to specific GitHub repositories and branches
   - API credentials for the `signpath/github-action-submit-signing-request`
     GitHub Action

### CI integration (after approval)

The integration shape is below. It cannot be written before approval,
because the IDs are account-specific.

```yaml
# After the Build executable step in .github/workflows/build.yml:

- name: Submit unsigned exe to SignPath
  uses: signpath/github-action-submit-signing-request@<pinned-sha>
  with:
    api-token: ${{ secrets.SIGNPATH_API_TOKEN }}
    organization-id: ${{ vars.SIGNPATH_ORG_ID }}
    project-slug: yt-dlp-studio
    signing-policy-slug: release-signing
    artifact-configuration-slug: exe
    github-artifact-id: ${{ steps.upload-unsigned.outputs.artifact-id }}
    wait-for-completion: true
    output-artifact-directory: signed/
```

Notes on what this implies for the workflow:

- The current `Upload artifact` step needs an `id:` so we can pass its
  artifact ID into the signing step.
- A second upload step replaces the signed exe in the published artifact.
- The build provenance attestation must run **after** signing. The
  attestation must bind to the final signed binary, not the unsigned one.
- Set the `SIGNPATH_API_TOKEN` secret and the `SIGNPATH_ORG_ID` variable in
  the GitHub repository settings before the first signed build.
- Since 0.3.0, the Inno Setup installer wraps the same EXE. Not designed yet
  (assumption): sign the EXE before `ISCC` builds the installer, then sign the
  installer too.

---

## Alternatives considered and rejected

### Self-signed certificate

This produces an Authenticode signature, but no Windows root store trusts
the signing identity. SmartScreen and UAC both treat self-signed binaries as
**more** suspicious than unsigned ones, because an entity that Windows
actively distrusts signed them. **Net negative.**

### Microsoft Trusted Signing

A real, working option: about $10/month, identity verification required,
runs in Azure. It is the cheapest legitimate paid path. It is rejected only
because the owner prefers "no recurring cost". Keep it on the shortlist if
SignPath declines or stalls indefinitely.

### Sigstore / cosign alone

Already in use through `actions/attest-build-provenance`. It gives strong
supply-chain integrity, but Windows does not trust it at runtime. It does not
replace Authenticode.

### SmartScreen reputation accrual

Over time, if enough different machines run an unsigned EXE without
flagging it, SmartScreen starts to trust it. In practice:

- Reputation is tied to the file hash. Every rebuild resets it.
- Any binary change also resets it. With PyInstaller, even a rebuild of the
  same source can produce a different hash.
- For a project that ships several releases per year, reputation never
  becomes stable.

**Not a strategy.** At best it is a side effect. Do not rely on it.

### Free Authenticode CAs

There are none. Running an Authenticode CA is expensive (HSMs, audits, CA/B
Forum requirements), and there is no "Let's Encrypt for code signing".
Rumors about free CAs are usually expired promotions, paid services with a
short free trial, or scams. **Do not pursue.**

---

## Tracking

The application step is tracked in [`ROADMAP.md`](../ROADMAP.md) under v1.0.0.
The roadmap item is explicitly **non-blocking**. If SignPath approval is
slow, ship v1.0.0 unsigned. Add signing in the first patch release after the
credentials arrive.

When signing lands, update [`SECURITY.md`](../SECURITY.md). Mention the
Authenticode signature next to the existing build provenance verification.
Also update the SmartScreen sections in [`README.md`](../README.md) and
[`INSTALLATION_GUIDE.md`](INSTALLATION_GUIDE.md).
