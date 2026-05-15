# Code Signing - Internal Maintainer Notes

Status as of 2026-05-10: **release binaries are not Authenticode-signed.**
End users see a SmartScreen "Unknown publisher" warning on first run. This
document records the plan to fix that without paying for a certificate.

This is an internal/maintainer document. End-user verification instructions
live in [`SECURITY.md`](../SECURITY.md).

---

## What we already have

The build workflow produces a **Sigstore-signed SLSA build provenance
attestation** for every release exe (`actions/attest-build-provenance` in
`.github/workflows/build.yml`).

That attestation cryptographically binds the exe's SHA-256 to the workflow
file, commit, and runner that produced it. Anyone can verify with:

```bash
gh attestation verify yt-dlp-studio.exe --repo NX1X/yt-dlp-studio
```

**What this gives us:** strong supply-chain integrity. A user who runs the
verification command can prove the binary they downloaded was the one our CI
built, unmodified.

**What this does NOT give us:** Windows does not natively trust Sigstore
signatures. SmartScreen and the UAC prompt both ignore the attestation. So
the first-run "Unknown publisher" warning remains until we add Authenticode
on top.

The two are complementary, not redundant - keep both once Authenticode is in
place.

---

## Why we need Authenticode (separately from Sigstore)

Authenticode is the only signature format Windows actually checks at runtime:

- **SmartScreen** uses the Authenticode publisher identity to compute reputation.
  Without it, every release re-triggers the warning regardless of how many
  prior versions ran cleanly.
- **UAC prompts** show "Verified publisher: …" when a binary is Authenticode-signed
  by a trusted CA. Unsigned binaries say "Unknown publisher" in red.
- **Some enterprise environments** (AppLocker, WDAC) refuse to execute
  unsigned binaries entirely.

So even with perfect Sigstore provenance, an unsigned exe creates user friction
on every release.

---

## The free path: SignPath Foundation

[SignPath Foundation](https://signpath.org/) is a non-profit that signs OSS
artifacts with their own paid Authenticode certificate, free of charge. The
resulting signatures are trusted by Windows the same as a $400/year EV cert.

Established projects signed via SignPath include NUnit, NLog, Paint.NET,
and many others.

### Eligibility

- Public source code under an OSI-approved license. ✓ (we are MIT/whatever
  applies - confirm against `LICENSE`)
- Public GitHub or GitLab repository. ✓
- Maintainer willing to undergo a lightweight identity check.
- Project must be reasonably mature / not abandoned.

### Application process

1. Submit at <https://signpath.org/apply>. Provide:
   - Repository URL
   - Short project description
   - Maintainer name + contact
   - License confirmation
2. Wait for review. Typical turnaround is 2–4 weeks.
3. If approved, SignPath provisions:
   - A SignPath organization for the project
   - A signing policy tied to specific GitHub repositories and branches
   - API credentials for the `signpath/github-action-submit-signing-request`
     GitHub Action

### CI integration (after approval)

The integration shape (cannot be written before approval - IDs are
account-specific):

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
- The build-provenance attestation must run **after** signing - the
  attestation should bind to the final signed binary, not the unsigned one.
- The `SIGNPATH_API_TOKEN` secret and `SIGNPATH_ORG_ID` variable need
  populating in GitHub repository settings before the first signed build.

---

## Alternatives considered and rejected

### Self-signed certificate

Generates an Authenticode signature, but the signing identity isn't trusted
by any Windows root store. SmartScreen and UAC both treat self-signed
binaries as **more** suspicious than unsigned ones (signed by an entity
Windows actively distrusts). **Net negative.**

### Microsoft Trusted Signing

A real, working option - ~$10/month, identity verification required, runs
in Azure. Cheapest legitimate paid path. Rejected only because the user
preference is "no recurring cost." Keep on the shortlist if SignPath
declines or stalls indefinitely.

### Sigstore / cosign alone

Already in use via `actions/attest-build-provenance`. Strong supply-chain
property, zero Windows-runtime trust. Doesn't replace Authenticode.

### SmartScreen reputation accrual

Over time, if enough distinct machines successfully run an unsigned exe
without flagging it, SmartScreen will warm up to it. In practice:

- Reputation is scoped per-file-hash. Every rebuild resets it.
- Reset is also triggered by any binary change (even rebuilding the same
  source can produce a different hash with PyInstaller).
- For a project shipping multiple releases per year, reputation never
  stabilises.

**Not a strategy** - at best a side-effect, not something to rely on.

### Free Authenticode CAs

There are none. Authenticode CA operations are expensive (HSMs, audits, CA/B
Forum requirements), and there is no "Let's Encrypt for code signing"
equivalent. Periodic rumours about free CAs are usually either expired
promotions, paid services with a brief free trial, or scams. **Do not pursue.**

---

## Tracking

The application step is tracked on [`ROADMAP.md`](../ROADMAP.md) under v1.0.0.
The roadmap item is explicitly **non-blocking** - if SignPath approval is
slow, ship v1.0.0 unsigned and add signing in the first patch release once
credentials are in hand.

When this lands, update [`SECURITY.md`](../SECURITY.md) to mention the
Authenticode signature alongside the existing build-provenance verification.
