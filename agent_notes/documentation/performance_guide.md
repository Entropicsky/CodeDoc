# CodeDoc Pipeline Performance Optimization Guide

This guide provides strategies for optimizing the performance of the CodeDoc pipeline, especially when working with large codebases.

## Performance Benchmarks

For reference, here are typical performance metrics:

| Operation | Approximate Time | Notes |
|-----------|------------------|-------|
| File Enhancement | 1 minute per file | Varies with file size and complexity |
| Supplementary Doc Generation | 3-5 minutes per document | Depends on project size |
| Vector Store Upload | 1-2 minutes per 100 files | Depends on file size and network speed |

## Key Performance Factors

The pipeline's performance is primarily affected by:

1. **LLM API Throughput**: Rate limits and processing time for API requests
2. **File Size and Complexity**: Larger, more complex files take longer to process
3. **Number of Files**: More files means more API calls and longer processing time
4. **Network Conditions**: API latency affects overall performance
5. **Hardware Resources**: Memory and CPU usage during processing

## Optimization Strategies

### 1. Selective Processing

Process only the files that need enhancement:

```bash
# Process only Python files
--file-patterns "*.py"

# Exclude test directories
--exclude-dirs "tests,__tests__,test"

# Process only specific directories
python3 -m codedoc.pipeline $(pwd)/my-project/src/core --project-name "Core Module" --output-dir core-output
```

### 2. Batched Processing

Break down large projects into smaller batches:

```bash
# Process first 20 files
python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project Batch 1" --output-dir my-project-output-batch1 --max-files 20

# Skip already processed files in subsequent runs
# (This requires custom implementation or manual tracking)
```

### 3. Model Selection

Choose the most efficient model for your needs:

```bash
# Use a faster, smaller model
--model gpt-3.5-turbo

# Use a more powerful model for complex code
--model gpt-4-turbo-preview

# Use Gemini for potentially different performance characteristics
--llm-provider gemini
```

### 4. Chunking Optimization

Adjust chunking parameters based on your codebase:

```bash
# Smaller chunks for faster processing
--chunk-size 1000 --chunk-overlap 100

# Larger chunks for better coherence (but slower processing)
--chunk-size 2000 --chunk-overlap 300
```

### 5. Pipeline Phases

Run the pipeline in phases to manage resources better:

```bash
# Phase 1: Process files without uploading to vector store
python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output --skip-upload

# Phase 2: Upload to vector store (after reviewing output)
# (This would require a separate command or custom script)
```

### 6. Parallel Processing

For very large codebases, consider parallel processing:

```bash
# Process different directories in parallel (on different terminals)
python3 -m codedoc.pipeline $(pwd)/my-project/src/module1 --project-name "Module 1" --output-dir module1-output

python3 -m codedoc.pipeline $(pwd)/my-project/src/module2 --project-name "Module 2" --output-dir module2-output
```

### 7. Resource Allocation

Ensure your system has adequate resources:

- **Memory**: 4GB+ recommended, 8GB+ for large codebases
- **CPU**: Multi-core processor recommended
- **Network**: Stable, high-speed internet connection
- **Disk Space**: At least 3x the size of your codebase for output files

## Configuring for Different Scenarios

### Small Projects (< 50 files)

```bash
# Process everything at once with default settings
python3 -m codedoc.pipeline $(pwd)/small-project --project-name "Small Project" --output-dir small-project-output
```

### Medium Projects (50-200 files)

```bash
# Use a faster model with optimized chunking
python3 -m codedoc.pipeline $(pwd)/medium-project --project-name "Medium Project" --output-dir medium-project-output --model gpt-3.5-turbo --chunk-size 1200 --chunk-overlap 150
```

### Large Projects (200+ files)

```bash
# Process in batches of directories
python3 -m codedoc.pipeline $(pwd)/large-project/src/core --project-name "Large Project Core" --output-dir large-project-output-core --model gpt-3.5-turbo --skip-upload

python3 -m codedoc.pipeline $(pwd)/large-project/src/utils --project-name "Large Project Utils" --output-dir large-project-output-utils --model gpt-3.5-turbo --skip-upload

# After processing all directories, create a combined vector store
# (This would require a separate custom script)
```

## Monitoring Performance

### Tracking Processing Time

Add timing to your command to track performance:

```bash
time python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output --max-files 10
```

### Logging API Usage

Monitor your API usage to optimize costs:

1. Set logging to DEBUG level
2. Track the number of tokens used from the logs
3. Analyze which files are consuming the most tokens

### Memory Usage Monitoring

For large projects, monitor memory usage:

```bash
# Linux
watch -n 1 'ps -o pid,user,%mem,command ax | grep python3'

# macOS
top -pid $(pgrep -f "python3 -m codedoc.pipeline")
```

## Advanced Optimization Tips

### 1. Preprocess Files

If your codebase has extremely large files, consider preprocessing them:

- Split files larger than 5MB into smaller components
- Remove binary files, logs, or temporary files
- Exclude generated code or vendor libraries

### 2. Optimize Network Conditions

- Use a wired connection instead of Wi-Fi when possible
- Consider running the pipeline on a cloud instance with high-speed internet
- Avoid processing during peak usage hours for OpenAI API

### 3. Custom File Filters

Create custom filtering for more targeted processing:

- Process only recently modified files
- Focus on files with low test coverage or documentation
- Prioritize core modules over utility functions

### 4. Schedule During Off-Hours

For very large projects, schedule processing during off-hours:

```bash
# Using at command
echo "cd $(pwd) && OPENAI_API_KEY=your_key python3 -m codedoc.pipeline $(pwd)/my-project --project-name 'My Project' --output-dir my-project-output" | at midnight
```

## Troubleshooting Performance Issues

### Problem: Processing Slows Down Over Time

**Possible causes**:
- Rate limiting from the API provider
- Memory leaks or resource exhaustion
- Network congestion

**Solutions**:
- Add delays between batches of files
- Restart the process after a certain number of files
- Run during off-peak hours

### Problem: Some Files Take Much Longer Than Others

**Possible causes**:
- File size or complexity
- Context window limitations
- Special characters or encoding issues

**Solutions**:
- Process outlier files separately with adjusted parameters
- Split very large files before processing
- Check for unusual content patterns that might confuse the LLM 