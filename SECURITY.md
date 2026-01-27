# Security Policy

## Supported Versions

We release patches for security vulnerabilities in the following versions:

| Version | Supported          |
| ------- | ------------------ |
| 2.0.x   | :white_check_mark: |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: **daniel.hhd@gmail.com**

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information in your report:

* Type of vulnerability (e.g., SQL injection, cross-site scripting, etc.)
* Full paths of source file(s) related to the manifestation of the vulnerability
* The location of the affected source code (tag/branch/commit or direct URL)
* Any special configuration required to reproduce the issue
* Step-by-step instructions to reproduce the issue
* Proof-of-concept or exploit code (if possible)
* Impact of the issue, including how an attacker might exploit it

This information will help us triage your report more quickly.

## Disclosure Policy

When we receive a security bug report, we will:

1. Confirm the problem and determine the affected versions
2. Audit code to find any similar problems
3. Prepare fixes for all supported versions
4. Release patches as soon as possible

## Security Best Practices

When using AI-First Runtime in production:

1. **Enable Audit Logging**: Always enable the compliance engine to track all operations
2. **Review Undo History**: Regularly review undo operations for suspicious activity
3. **Sanitize Sensitive Data**: Ensure sensitive parameters are properly redacted in logs
4. **Use Confirmation Callbacks**: Require user confirmation for dangerous operations
5. **Sandbox Workspace**: Always run agents in isolated workspace directories
6. **Keep Updated**: Regularly update to the latest version to receive security patches

## Security Features

AI-First Runtime includes several built-in security features:

* **Automatic Data Sanitization**: Sensitive parameters (tokens, keys, passwords) are automatically redacted in audit logs
* **Workspace Sandboxing**: All file operations are restricted to the configured workspace root
* **Confirmation Callbacks**: Dangerous operations can require explicit user approval
* **Tamper-Resistant Audit Logs**: SQLite database with WAL mode for integrity
* **Undo Mechanism**: All operations can be rolled back to prevent irreversible damage

## Known Security Considerations

* **Undo Limitations**: The undo mechanism cannot reverse network operations (e.g., API calls, emails sent)
* **Audit Log Access**: Audit logs may contain sensitive information; restrict access appropriately
* **Workspace Escape**: Ensure handlers properly validate paths to prevent directory traversal attacks

## Contact

For security-related questions or concerns, please contact: **daniel.hhd@gmail.com**
