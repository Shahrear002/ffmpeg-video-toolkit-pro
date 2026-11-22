# Security Policy

## 1. Supported Versions

| Version | Supported |
|---|---|
| `1.0.x` | :white_check_mark: |
| `< 1.0` | :x: |

---

## 2. Threat Model & Security Boundaries

**FFmpeg Video Toolkit Pro** is engineered from the ground up for safe execution in automated AI environments and restricted desktop environments.

### 2.1 Subprocess & Shell Injection Prevention
* **Strict Non-Shell Invocation**: All subprocess executions (`subprocess.Popen` / `subprocess.run`) utilize explicit argument arrays with `shell=False`. At no point are user inputs concatenated into raw shell strings.
* **Canonical Path Resolution**: Every input and output path is converted to a canonical absolute path (`pathlib.Path.resolve()`), protecting against directory traversal, leading-dash injection (`-v`, `--help`), and whitespace mangling.
* **Filtergraph Command File Isolation**: Long or complex filtergraphs (such as silence cuts spanning hundreds of segments) are written to temporary script files and passed to FFmpeg via `-filter_complex_script`. This eliminates command-line buffer overflow vulnerabilities (such as Windows' 8,191 character limit).

### 2.2 Complete Network Isolation (Air-Gapped by Design)
* **Zero Network Requests**: The Python engine (`video_toolkit.py`) imports no network libraries (`urllib`, `requests`, `http`, `socket`). It operates 100% locally and offline.
* **Zero Telemetry**: Neither the skill package nor the desktop application contains tracking, analytics, crash reporters, or phone-home telemetry.
* **Strict Desktop CSP**: The Tauri webview enforces a Content Security Policy prohibiting remote connections:
  ```http
  default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: asset:; font-src 'self'; connect-src 'self'; media-src 'self' asset:;
  ```

### 2.3 Automated AST Security Audit
All code packaged into the Agensi Agent Skill (`skill/`) is audited before compilation using `scripts/audit_self.py`. The auditor inspects the Abstract Syntax Tree (AST) for:
- Calls to `eval()`, `exec()`, `compile()`, or `__import__()`.
- Network and socket module imports (`urllib`, `requests`, `http.client`, `socket`, `ftplib`).
- Prompt injection or jailbreak patterns instructing agents to ignore safety guidelines.

Any violation causes the build to fail immediately.

### 2.4 Tauri Scoped Capabilities
The desktop application utilizes Tauri v2 capabilities (`desktop/src-tauri/capabilities/default.json`):
- Sidecar execution is strictly limited to the bundled binaries (`binaries/video_toolkit`, `binaries/ffmpeg`, `binaries/ffprobe`).
- Arbitrary command execution is disallowed.
- File system access is scoped to user-selected files and directories via native system dialogs (`tauri-plugin-dialog`).

---

## 3. Reporting a Vulnerability

If you discover a security vulnerability in FFmpeg Video Toolkit Pro, please report it privately:

1. **Email**: `security@agensi.io` (or through the Agensi Marketplace Vendor Portal).
2. **Details**: Include a description of the vulnerability, steps to reproduce, and affected operating system/environment.
3. **Response Window**: We acknowledge security reports within 48 hours and provide patches within 7 business days.

Please do not open public GitHub issues for security vulnerabilities.
