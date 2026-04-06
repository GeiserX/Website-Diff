# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Security Audit Report (2025-12-13)

### Security Measures Implemented

#### 1. URL Validation and SSRF Protection
- **Location**: `website_diff/fetcher.py`
- **Implementation**: 
  - URL scheme validation (only http/https allowed)
  - Basic SSRF protection with localhost/internal network detection
  - URL parsing using `urllib.parse.urlparse` for safe parsing
- **Status**: ✅ Implemented
- **Note**: Localhost access is allowed for development/testing purposes

#### 2. Input Sanitization
- **Location**: `website_diff/cli.py`, `website_diff/link_traverser.py`
- **Implementation**:
  - URL normalization and validation
  - Filtering of dangerous protocols (javascript:, mailto:, tel:, etc.)
  - Email address detection and filtering
- **Status**: ✅ Implemented

#### 3. File Path Security
- **Location**: All file operations
- **Implementation**:
  - Uses `pathlib.Path` for safe path handling
  - Paths are relative to user-specified directories
  - No direct user input used in file paths without validation
- **Status**: ✅ Safe
- **Note**: All file operations use `Path` objects which prevent path traversal

#### 4. No Command Injection
- **Status**: ✅ Verified
- **Findings**: No use of `eval()`, `exec()`, `subprocess` with `shell=True`, or `os.system()`

#### 5. No Hardcoded Secrets
- **Status**: ✅ Verified
- **Findings**: 
  - No passwords, API keys, or tokens in code
  - Secrets only referenced via environment variables in GitHub Actions
  - Docker credentials stored as GitHub secrets

#### 6. Safe File Operations
- **Status**: ✅ Verified
- **Findings**:
  - All file writes use explicit encoding ('utf-8')
  - Binary file operations use 'wb' mode appropriately
  - No unsafe file permissions set

### Security Recommendations

1. **SSRF Protection Enhancement** (Medium Priority)
   - Consider implementing a more robust SSRF protection mechanism
   - Add option to disable localhost access in production environments
   - Implement IP address whitelist/blacklist functionality

2. **Rate Limiting** (Low Priority)
   - Consider adding rate limiting for web requests to prevent abuse
   - Implement request throttling for link traversal

3. **Content Size Limits** (Low Priority)
   - Add maximum content size limits to prevent memory exhaustion
   - Implement streaming for very large files

### Reporting a Vulnerability

If you discover a security vulnerability, please report it via:
- GitHub Security Advisories: https://github.com/GeiserX/Wayback-Diff/security/advisories
- Email: sergio@geiser.cloud

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if available)

### Security Best Practices for Users

1. **Secrets Management**
   - Never commit secrets to the repository
   - Use environment variables or secret management tools
   - Rotate credentials regularly

2. **Network Security**
   - Be cautious when comparing URLs from untrusted sources
   - Use the tool in isolated environments when testing unknown websites
   - Monitor network traffic when using the tool

3. **File System Security**
   - Use dedicated directories for reports and screenshots
   - Review generated files before sharing
   - Clean up generated artifacts regularly

## Security Checklist

- [x] No hardcoded secrets
- [x] URL validation implemented
- [x] SSRF protection (basic)
- [x] Path traversal protection (via Path objects)
- [x] No command injection vectors
- [x] Safe file operations
- [x] Input sanitization
- [x] Proper error handling
- [x] No unsafe deserialization
- [x] Dependencies up to date
