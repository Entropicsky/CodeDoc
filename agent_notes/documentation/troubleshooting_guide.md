# CodeDoc Pipeline Troubleshooting Guide

This guide helps you diagnose and resolve common issues with the CodeDoc pipeline.

## API Authentication Issues

### Problem: "Authentication Error" or "Invalid API Key"

**Symptoms**:
- Error message: "Authentication error with OpenAI API"
- Error message: "Invalid API key provided"

**Solutions**:
1. Check that your API key is correctly set in the environment:
   ```bash
   echo $OPENAI_API_KEY
   ```
2. Ensure your API key is valid by testing it with a simple API call:
   ```bash
   curl https://api.openai.com/v1/models \
     -H "Authorization: Bearer $OPENAI_API_KEY"
   ```
3. If using a `.env` file, verify the file is properly formatted and the key is being read correctly:
   ```bash
   cat .env | grep OPENAI_API_KEY
   ```

### Problem: "Organization Not Found"

**Symptoms**:
- Error message: "Organization not found" or "The organization ID provided does not exist"

**Solutions**:
1. Verify your organization ID:
   ```bash
   echo $OPENAI_ORG_ID
   ```
2. Check that your account is properly set up with the organization in the OpenAI dashboard.
3. If you don't need to specify an organization, remove the `OPENAI_ORG_ID` environment variable.

## File Processing Issues

### Problem: Files Are Skipped or Not Processed

**Symptoms**:
- The pipeline completes but fewer files than expected are processed
- Specific files you expected to be processed are missing from the output

**Solutions**:
1. Check your file patterns to ensure they match the files you want to process:
   ```bash
   # Use more inclusive patterns
   --file-patterns "*.py,*.md,*.js,*.ts,*.java"
   ```
2. Verify that excluded directories aren't containing files you want to process:
   ```bash
   # Be more specific with excluded directories
   --exclude-dirs "node_modules,venv,__pycache__"
   ```
3. Check if the files are readable by the current user:
   ```bash
   ls -la path/to/files
   ```

### Problem: Processing Takes Too Long

**Symptoms**:
- The pipeline runs very slowly (much slower than ~1 minute per file)
- The process seems to hang with no output

**Solutions**:
1. Use a smaller model or faster provider:
   ```bash
   --llm-provider openai --model gpt-3.5-turbo
   ```
2. Limit the number of files for testing:
   ```bash
   --max-files 10
   ```
3. Check for very large files that might be causing issues:
   ```bash
   find path/to/codebase -type f -size +1M | grep -v "node_modules" | grep -v "venv"
   ```
4. Consider splitting the process into smaller batches:
   ```bash
   # Process one directory at a time
   python3 -m codedoc.pipeline $(pwd)/my-project/src/module1 --project-name "Module 1" --output-dir module1-output
   ```

## LLM Request Issues

### Problem: "Rate Limit Exceeded"

**Symptoms**:
- Error message: "Rate limit exceeded" or "Too many requests"
- The pipeline stops with an API error

**Solutions**:
1. Reduce the concurrent requests by processing fewer files:
   ```bash
   --max-files 5
   ```
2. Implement a delay between API calls:
   ```bash
   # Not directly supported, but you can modify the code to add delays
   # In the meantime, you can run with fewer files
   ```
3. Upgrade your API tier for higher rate limits.
4. Switch to a different model with higher rate limits:
   ```bash
   --model gpt-3.5-turbo
   ```

### Problem: "Context Length Exceeded"

**Symptoms**:
- Error message: "This model's maximum context length is X tokens"
- The pipeline fails when processing specific files

**Solutions**:
1. Reduce the chunk size:
   ```bash
   --chunk-size 1000 --chunk-overlap 100
   ```
2. Use a model with a larger context window:
   ```bash
   --model gpt-4-turbo-preview
   ```
3. Skip problematic files and process them separately with special handling.

## Vector Store Issues

### Problem: "Failed to Create Vector Store"

**Symptoms**:
- Error message: "Failed to create vector store"
- The pipeline completes file enhancement but fails at the vector store step

**Solutions**:
1. Verify your OpenAI API key has access to the vector store endpoints.
2. Check if you've reached your quota limit for vector stores.
3. Skip the vector store upload during testing:
   ```bash
   --skip-upload
   ```
4. Try creating a vector store with a smaller number of files first.

### Problem: "Timeout During Vector Store Creation"

**Symptoms**:
- Error message: "Timeout waiting for vector store creation"
- The pipeline hangs during the vector store creation step

**Solutions**:
1. Increase the timeout value in the code.
2. Process fewer files to create smaller vector stores.
3. Check your internet connection stability.
4. Skip the upload step and try later:
   ```bash
   --skip-upload
   ```

## Environment and Setup Issues

### Problem: "Module Not Found"

**Symptoms**:
- Error message: "ModuleNotFoundError: No module named 'X'"
- The pipeline fails to start

**Solutions**:
1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Check your Python environment:
   ```bash
   which python
   python --version
   ```
3. Verify you're using the correct Python interpreter with the installed packages.

### Problem: "Permission Denied"

**Symptoms**:
- Error message: "Permission denied" when reading files or writing output
- The pipeline fails with file access errors

**Solutions**:
1. Check the permissions of input files:
   ```bash
   ls -la path/to/codebase
   ```
2. Verify write permissions for the output directory:
   ```bash
   ls -la path/to/output-dir
   ```
3. Run the command with appropriate permissions.

## Advanced Troubleshooting

### Enabling Debug Logging

For more detailed logs to diagnose issues:

```bash
export LOG_LEVEL=DEBUG
python3 -m codedoc.pipeline ...
```

### Monitoring API Usage

To check your API usage and remaining credits:

1. Go to the OpenAI dashboard: https://platform.openai.com/usage
2. Check your current usage and limits.

### Handling Large Codebases

For very large codebases:

1. Process subdirectories separately
2. Use a configuration file instead of command-line arguments
3. Consider running on a more powerful machine with more memory
4. Set up a dedicated environment with stable internet connection

### What to Include in Bug Reports

If you encounter a bug that you can't resolve, include the following information in your report:

1. Full command you were running
2. Your environment details:
   ```bash
   python --version
   pip list
   ```
3. The error message and relevant logs
4. Description of the codebase (size, language, structure)
5. Steps to reproduce the issue 