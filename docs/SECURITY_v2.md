
# Security Policy

Version: 2.0

Status: ACTIVE

---

# Purpose

PHASENOX processes professional audio, AI models and engineering knowledge.
Security is a core engineering requirement.

---

# Supported Versions

| Version | Supported |
|---------|-----------|
| 2.x | Yes |
| 1.x | Limited |
| Older | No |

---

# Reporting a Vulnerability

If you discover a security issue:

1. Do not publish it publicly.
2. Prepare a reproducible description.
3. Include affected version, operating system and reproduction steps.
4. Contact the maintainers privately.
5. Allow time for investigation before disclosure.

---

# Security Principles

- Least privilege
- Defense in depth
- Secure defaults
- Explicit configuration
- Dependency isolation
- Principle of minimal trust

---

# AI Security

The system should:

- Validate model outputs.
- Treat AI responses as untrusted until validated.
- Prevent prompt injection where applicable.
- Keep reasoning separate from execution.
- Require confirmation before destructive actions.

---

# Dependency Security

- Pin dependency versions where practical.
- Review updates before adoption.
- Remove unused packages.
- Monitor security advisories.

---

# Data Protection

PHASENOX should minimize stored data.

Sensitive project material should not be retained longer than necessary.

---

# Responsible Disclosure

Contributors are encouraged to report vulnerabilities responsibly.
Security reports receive priority over feature requests.

---

# Long-Term Goal

Build an Audio Intelligence System that is secure, transparent, auditable and
safe for professional production environments.
