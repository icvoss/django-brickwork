# Security Policy

## Supported Versions

The latest minor release of the **current major version** receives security
fixes. The previous major version continues to receive security fixes for
**6 months** after the current major's first release; after that window it
is unsupported. Anything older than the previous major is unsupported.

This is expressed as a rule rather than a version table so the policy does
not go stale at the next major release; it is self-maintaining as the
package advances. As of this writing the package is on the `3.x` line
(`3.0.0` shipped 2026-08-06), so `3.x` is supported, `2.x` is supported
until 2027-02-06, and `1.x` and earlier are unsupported. `2.x` gets a
window rather than an immediate cutoff because consumers pinned
`>=2,<3` exist and need a realistic migration runway, not an instant one.

If you are unsure whether your installed version is still covered, check
the current major in `pyproject.toml` on `main` and compare against the rule
above, or ask via the reporting channel below.

## Reporting a Vulnerability

Please do **not** open a public GitHub issue for security vulnerabilities.

Report vulnerabilities by email to **itsonlyme@nigelcopley.com**. Include:

- A description of the vulnerability and its potential impact.
- Steps to reproduce or a minimal proof-of-concept.
- The django-brickwork version you tested against.
- Any suggested remediation if you have one.

You will receive an acknowledgement within **3 business days**. We aim to
provide an initial assessment within **7 days** of receipt.

## Disclosure Policy

django-brickwork follows **coordinated disclosure** with a **90-day embargo**
period:

1. Vulnerability is reported privately to the maintainers.
2. Maintainers assess severity and develop a fix.
3. A patched release is published.
4. A security advisory is issued at the same time as the release.
5. If no fix is available after 90 days, the reporter may disclose publicly.

We will credit reporters in the advisory unless anonymity is requested.
