# CodeDoc Pipeline - Quick Reference

This quick reference guide provides common commands and examples for using the CodeDoc pipeline.

## Basic Usage

```bash
# Process a codebase
./run_pipeline.sh my_codebase --project-name "My Project"

# Process with a specific model
./run_pipeline.sh my_codebase --project-name "My Project" --model gpt-4-turbo

# Process with custom output directory
./run_pipeline.sh my_codebase --project-name "My Project" --output-dir custom-output
```

## File Selection

```bash
# Only process Python and JavaScript files
./run_pipeline.sh my_codebase --project-name "My Project" --file-patterns "*.py" "*.js"

# Exclude certain directories
./run_pipeline.sh my_codebase --project-name "My Project" --exclude-dirs "tests" "docs" "examples"

# Limit the number of files processed
./run_pipeline.sh my_codebase --project-name "My Project" --max-files 50
```

## Pipeline Customization

```bash
# Skip code enhancement
./run_pipeline.sh my_codebase --project-name "My Project" --skip-enhancement

# Skip uploading to vector store (offline mode)
./run_pipeline.sh my_codebase --project-name "My Project" --skip-upload

# Only generate supplementary docs (skip enhancement, analysis, and upload)
./run_pipeline.sh my_codebase --project-name "My Project" --skip-enhancement --skip-analysis --skip-processing --skip-upload
```

## Real-World Examples

```bash
# Process a Python SDK with GPT-4 Turbo
./run_pipeline.sh s2rh_pythonsdk-main --project-name "S2RH Python SDK" --model gpt-4-turbo --output-dir s2rh_pythonsdk-main-output

# Process a large codebase with limits
./run_pipeline.sh large-repo --project-name "Large Repository" --model gpt-3.5-turbo --max-files 100 --file-patterns "*.py" "*.md" --exclude-dirs "tests" "docs" "examples" "node_modules"

# Generate only supplementary docs for an existing project
./run_pipeline.sh my_codebase --project-name "My Project" --skip-enhancement --skip-analysis --skip-processing --skip-upload
```

## Troubleshooting

- If you get API key errors, check that your `.env` file contains `OPENAI_API_KEY=your_api_key_here`
- If the script fails with "No module named 'codedoc'", ensure you're running from the root directory of the project
- To view logs, check `codedoc_pipeline.log` in the project root

See the full README.md for detailed documentation. 