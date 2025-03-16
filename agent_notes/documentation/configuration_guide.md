# CodeDoc Pipeline Configuration Guide

This guide provides detailed information about configuring the CodeDoc pipeline for generating enhanced documentation and creating a searchable vector store.

## Environment Variables

The pipeline uses several environment variables for configuration:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | Yes | None |
| `OPENAI_ORG_ID` | Your OpenAI organization ID | No | None |
| `GEMINI_API_KEY` | Your Google Gemini API key (if using Gemini) | No | None |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No | INFO |

## Command-Line Arguments

The pipeline can be configured through various command-line arguments:

### Required Arguments

| Argument | Description | Example |
|----------|-------------|---------|
| `input_dir` | Path to the codebase to process | `$(pwd)/my-project` |
| `--project-name` | Name of the project | `--project-name "My Project"` |
| `--output-dir` | Directory where output will be stored | `--output-dir my-project-output` |

### Optional Arguments

| Argument | Description | Default | Example |
|----------|-------------|---------|---------|
| `--max-files` | Maximum number of files to process | No limit | `--max-files 20` |
| `--skip-upload` | Skip vector store upload | False | `--skip-upload` |
| `--llm-provider` | LLM provider to use (openai or gemini) | openai | `--llm-provider gemini` |
| `--model` | Model to use for the LLM | gpt-4-turbo-preview (OpenAI) or gemini-1.0-pro (Gemini) | `--model gpt-4` |
| `--chunk-strategy` | Chunking strategy for documents (semantic, fixed, or hybrid) | hybrid | `--chunk-strategy semantic` |
| `--chunk-size` | Size of chunks in tokens | 1500 | `--chunk-size 2000` |
| `--chunk-overlap` | Overlap between chunks in tokens | 200 | `--chunk-overlap 300` |
| `--temperature` | Temperature for LLM requests | 0.2 | `--temperature 0.5` |
| `--vector-name` | Name for the vector store | Project name | `--vector-name "My Project Vectors"` |
| `--file-patterns` | File patterns to include (comma-separated) | *.py,*.md,*.txt,*.js,*.html | `--file-patterns "*.py,*.java"` |
| `--exclude-dirs` | Directories to exclude (comma-separated) | .git,__pycache__,venv | `--exclude-dirs "tests,examples"` |

## Configuration File

Instead of using command-line arguments, you can also use a configuration file:

```bash
python3 -m codedoc.pipeline --config-file my_config.yaml
```

The configuration file should be in YAML format and can include all the same options as the command-line arguments:

```yaml
# Pipeline configuration
input_dir: /path/to/my-project
project_name: My Project
output_dir: my-project-output

# LLM Configuration
llm_provider: openai
model: gpt-4-turbo-preview
temperature: 0.2

# Processing Configuration
max_files: 100
skip_upload: false
chunk_strategy: hybrid
chunk_size: 1500
chunk_overlap: 200

# File Selection
file_patterns:
  - "*.py"
  - "*.md"
  - "*.txt"
exclude_dirs:
  - .git
  - __pycache__
  - venv
```

## Environment Setup

### OpenAI API Configuration

To use the OpenAI API, you need to:

1. Create an account on [OpenAI](https://platform.openai.com/)
2. Generate an API key in your account settings
3. Set the `OPENAI_API_KEY` environment variable:

```bash
export OPENAI_API_KEY=your_api_key_here
```

Or create a `.env` file in your project root:

```
OPENAI_API_KEY=your_api_key_here
```

### Gemini API Configuration

To use the Google Gemini API, you need to:

1. Set up a Google Cloud account
2. Enable the Gemini API
3. Create an API key
4. Set the `GEMINI_API_KEY` environment variable:

```bash
export GEMINI_API_KEY=your_api_key_here
```

## Chunking Strategy

The chunking strategy determines how documents are split for processing and vector store embedding:

- **semantic**: Chunks documents based on semantic boundaries (paragraphs, sections)
- **fixed**: Chunks documents into fixed-size chunks regardless of content
- **hybrid**: Combines semantic and fixed strategies for optimal results

## Advanced Configuration

### Fine-tuning LLM Behavior

You can adjust the LLM's behavior by changing the `temperature` parameter:

- Lower temperatures (0.0-0.3) produce more deterministic, focused outputs
- Higher temperatures (0.7-1.0) produce more creative, varied outputs

### Handling Large Codebases

For large codebases, consider:

1. Using `--max-files` for initial testing
2. Using `--exclude-dirs` to skip test directories or external dependencies
3. Running the pipeline on subsets of your codebase with specific `--file-patterns`
4. Using a more efficient model like `gpt-3.5-turbo` for faster processing (with some quality trade-off)

### Debugging

Set the `LOG_LEVEL` environment variable to `DEBUG` for more detailed logging:

```bash
export LOG_LEVEL=DEBUG
```

## Example Configurations

### Minimal Configuration

```bash
OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2) python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output
```

### Full Configuration

```bash
OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2) python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output --max-files 100 --llm-provider openai --model gpt-4-turbo-preview --temperature 0.2 --chunk-strategy hybrid --chunk-size 1500 --chunk-overlap 200 --file-patterns "*.py,*.md" --exclude-dirs "tests,examples" --vector-name "My Project Vectors"
```

### Testing Configuration

```bash
OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2) python3 -m codedoc.pipeline $(pwd)/my-project --project-name "My Project" --output-dir my-project-output --max-files 10 --skip-upload
``` 