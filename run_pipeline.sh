#!/bin/bash
#
# CodeDoc Pipeline Execution Script
# =================================
#
# This script provides a simple way to run the CodeDoc pipeline without dealing with
# PYTHONPATH settings or direct script invocation complexities.
#
# USAGE:
#   ./run_pipeline.sh <input_dir> --project-name "Project Name" [options]
#
# EXAMPLES:
#   ./run_pipeline.sh my_codebase --project-name "My Project" --model gpt-4-turbo
#   ./run_pipeline.sh my_codebase --project-name "My Project" --output-dir custom-output --skip-upload
#
# REQUIRED ARGUMENTS:
#   <input_dir>                 Directory containing source code (first positional argument)
#   --project-name, -p          Name of the project
#
# COMMON OPTIONS:
#   --output-dir, -o            Output directory (default: "codedoc-output")
#   --model                     Model to use for LLM (e.g., "gpt-4-turbo", "gpt-3.5-turbo")
#   --file-patterns             Glob patterns for files to process (e.g., "*.py" "*.js")
#   --exclude-dirs              Directories to exclude (e.g., "tests" "node_modules")
#   --max-files                 Maximum number of files to process
#
# SKIP OPTIONS:
#   --skip-enhancement          Skip code enhancement
#   --skip-analysis             Skip code analysis
#   --skip-supplementary        Skip supplementary content generation
#   --skip-processing           Skip file processing for vectorization
#   --skip-upload               Skip upload to vector store
#
# See README.md for full documentation

# Print a colorful banner
echo -e "\033[1;36m"
echo "╔════════════════════════════════════════╗"
echo "║                                        ║"
echo "║           CodeDoc Pipeline             ║"
echo "║                                        ║"
echo "╚════════════════════════════════════════╝"
echo -e "\033[0m"

# Check if input directory is provided
if [ $# -eq 0 ]; then
    echo -e "\033[1;31mError: Input directory is required\033[0m"
    echo "Usage: ./run_pipeline.sh <input_dir> --project-name \"Project Name\" [options]"
    exit 1
fi

# Check if the input directory exists
if [ ! -d "$1" ]; then
    echo -e "\033[1;31mError: Input directory '$1' does not exist\033[0m"
    exit 1
fi

# Check if project name is specified
if [[ ! "$*" =~ --project-name && ! "$*" =~ -p ]]; then
    echo -e "\033[1;31mError: Project name is required (use --project-name or -p)\033[0m"
    echo "Usage: ./run_pipeline.sh <input_dir> --project-name \"Project Name\" [options]"
    exit 1
fi

# Set up Python environment
export PYTHONPATH=$PWD

# Check for API key in environment variable
if [ -z "$OPENAI_API_KEY" ]; then
    # Check if .env file exists and load API key
    if [ -f .env ]; then
        export OPENAI_API_KEY=$(grep OPENAI_API_KEY .env | cut -d '=' -f2)
        echo -e "\033[0;32mLoaded OpenAI API key from .env file\033[0m"
    else
        echo -e "\033[1;33mWarning: OPENAI_API_KEY not found in environment or .env file\033[0m"
        echo "You'll need to provide an API key to use OpenAI services"
    fi
fi

# Print execution info
echo -e "\033[0;36mRunning CodeDoc pipeline with settings:\033[0m"
echo "  • Input directory: $1"
echo "  • Python path: $PYTHONPATH"
echo "  • API Key: ${OPENAI_API_KEY:0:5}... ${#OPENAI_API_KEY} chars"
echo "  • Command: python3 codedoc/pipeline.py $@"
echo

# Run the pipeline with all arguments passed to this script
echo -e "\033[0;36mStarting pipeline execution...\033[0m"
python3 codedoc/pipeline.py "$@"
EXIT_CODE=$?

# Check exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\033[1;32mPipeline execution completed successfully!\033[0m"
else
    echo -e "\033[1;31mPipeline execution failed with exit code $EXIT_CODE\033[0m"
    echo "Check the logs for details"
fi

exit $EXIT_CODE 