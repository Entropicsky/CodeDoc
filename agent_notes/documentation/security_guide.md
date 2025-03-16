# CodeDoc Pipeline Security Best Practices

This guide outlines security considerations and best practices for using the CodeDoc pipeline securely, with a focus on API key management and data handling.

## API Key Management

### Protecting API Keys

Your API keys grant access to paid services and potentially sensitive data. Follow these best practices:

1. **Never hardcode API keys** in your source code:
   ```python
   # DON'T do this
   api_key = "sk-1234567890abcdef1234567890abcdef"
   
   # DO use environment variables or secure configuration
   api_key = os.environ.get("OPENAI_API_KEY")
   ```

2. **Use environment variables** for API keys:
   ```bash
   # Set in your terminal session
   export OPENAI_API_KEY="your-key-here"
   
   # Or use in a single command
   OPENAI_API_KEY="your-key-here" python3 -m codedoc.pipeline ...
   ```

3. **Use `.env` files** with appropriate permissions:
   ```bash
   # Create a .env file
   echo "OPENAI_API_KEY=your-key-here" > .env
   
   # Set restrictive permissions
   chmod 600 .env
   
   # Add to .gitignore
   echo ".env" >> .gitignore
   ```

4. **Rotate API keys** if you suspect they've been compromised.

5. **Use different API keys** for development and production.

### Using API Key Managers

Consider using a dedicated secret manager:

- **On macOS**: Use Keychain Access
- **On Linux**: Use tools like `pass` or `keyring`
- **In production**: Use AWS Secrets Manager, HashiCorp Vault, or similar

## Data Security Considerations

### Sensitive Code Handling

Be cautious with sensitive code or data:

1. **Scan for credentials** before processing:
   ```bash
   # Search for potential hardcoded secrets
   grep -E "(api_key|password|secret|token)" --include="*.py" -r /path/to/codebase
   ```

2. **Exclude sensitive files** from processing:
   ```bash
   # Using the exclude patterns
   --exclude-dirs "credentials,secrets,private"
   ```

3. **Consider data classification** before processing:
   - Public code repositories are generally safe to process
   - Internal tools containing business logic require careful consideration
   - Security-related code should be handled with extra caution

### Output Data Protection

Protect the generated documentation and vector stores:

1. **Set appropriate permissions** on output directories:
   ```bash
   chmod -R 700 my-project-output
   ```

2. **Encrypt sensitive outputs** if necessary:
   ```bash
   # Compress and encrypt using GPG
   tar -czf - my-project-output | gpg -c > my-project-output.tar.gz.gpg
   ```

3. **Be careful with vector store sharing** as it contains embeddings of your code.

## Network Security

### Secure API Communication

1. **Use HTTPS/TLS** for all API communications (enabled by default).

2. **Consider a VPN** when working with sensitive codebases.

3. **Be aware of proxy configurations** if working in corporate environments:
   ```bash
   # Set HTTP proxy if needed
   export HTTP_PROXY="http://proxy.example.com:8080"
   export HTTPS_PROXY="https://proxy.example.com:8080"
   ```

## Code and Prompt Injection

### Preventing Prompt Injection

The pipeline processes code which could theoretically contain prompt injection attacks:

1. **Treat input code with caution**, especially if processing third-party code.

2. **Use the latest LLM models** which have better safeguards against prompt injection.

3. **Review generated documentation** before deploying or distributing it.

## Operational Security

### Logging and Monitoring

1. **Enable appropriate logging levels**:
   ```bash
   export LOG_LEVEL=INFO  # Avoid DEBUG in production which might log sensitive details
   ```

2. **Monitor API usage** regularly:
   - Check OpenAI dashboard for unusual activity
   - Watch for unexpected usage spikes

3. **Clean up logs** that might contain sensitive information.

### Rate Limiting and Quotas

1. **Set API usage limits** in your OpenAI dashboard.

2. **Implement custom rate limiting** for additional protection.

3. **Monitor costs** to avoid unexpected charges.

## Compliance Considerations

### Data Processing Regulations

1. **Understand data regulations** (GDPR, CCPA, etc.) that apply to your organization.

2. **Consider data residency requirements** when using cloud-based LLMs.

3. **Document data processing activities** involving third-party APIs.

### Intellectual Property

1. **Consider IP implications** of sending code to external APIs.

2. **Review the Terms of Service** of API providers to understand how they handle your data.

3. **Consult legal counsel** if processing code with strict IP protections.

## Recommended Security Configuration

### Minimal Security Configuration

```bash
# Use environment variables for API keys
export OPENAI_API_KEY="your-key-here"

# Set appropriate permissions on output
python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output
chmod -R 700 my-project-output
```

### Enhanced Security Configuration

```bash
# Use a dedicated API key with usage limits
export OPENAI_API_KEY="limited-usage-key-here"

# Process only specific directories, excluding sensitive ones
python3 -m codedoc.pipeline $(pwd)/my-project/src --project-name "My Project" --output-dir my-project-output --exclude-dirs "credentials,secrets,private,vendor"

# Set restricted permissions and encrypt output
chmod -R 700 my-project-output
tar -czf - my-project-output | gpg -c > my-project-output.tar.gz.gpg
rm -rf my-project-output  # Remove unencrypted files
```

## Security Incident Response

If you suspect a security incident:

1. **Revoke compromised API keys** immediately.

2. **Rotate all credentials** even if you're unsure which were affected.

3. **Review API usage logs** for unauthorized activities.

4. **Contact API providers** if you suspect their services were involved.

5. **Document the incident** and improve security measures accordingly. 