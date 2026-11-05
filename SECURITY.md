# Reporting a security issue

Please report exploitable vulnerabilities privately rather than including attack details,
credentials, microphone recordings, or learner data in a public issue. Use the repository's
private vulnerability-reporting option if the maintainer has enabled it; otherwise arrange a
private channel with the maintainer first. This repository does not promise a monitored security
email address, a response deadline, or long-term support for old MVP releases.

Useful details include the affected versions, a minimal reproduction with synthetic data,
expected/actual behavior, and redacted logs. Ordinary usability bugs can use public issues.

The supported deployment is one Windows host and an Android client on a trusted home LAN.
Developer control endpoints are loopback-only and the debug APK is not the secure release path.
See [the security architecture](docs/architecture/security.md) for the intended boundaries.
