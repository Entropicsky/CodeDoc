#!/bin/bash
#
# File Uploader Utility Wrapper
# A utility for uploading files to OpenAI and creating vector stores
#

# Set default directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Display usage instructions
function show_usage {
    echo "OpenAI File Uploader and Vector Store Creator"
    echo ""
    echo "Usage: $(basename $0) [OPTIONS] --input-dir <directory> --vector-store-name <name>"
    echo ""
    echo "Options:"
    echo "  -i, --input-dir <dir>       Directory containing files to process (required)"
    echo "  -n, --vector-store-name <name>  Name for the vector store (required)"
    echo "  -o, --output-dir <dir>      Output directory for logs and state"
    echo "  -b, --batch-size <size>     Batch size (max 100, default: 100)"
    echo "  -k, --api-key <key>         OpenAI API key (defaults to env var)"
    echo "  -p, --purpose <purpose>     Purpose for file uploads (default: assistants)"
    echo "  -f, --file-patterns <pat>   File patterns to include (space-separated, quoted)"
    echo "  -e, --exclude-dirs <dirs>   Directories to exclude (space-separated, quoted)"
    echo "  -t, --test                  Run in test mode with smaller directory"
    echo "  -c, --create-test-files     Create test files (use with -t)"
    echo "  --no-recursive              Disable recursive directory traversal"
    echo "  --reset-state               Reset state before processing"
    echo "  --debug                     Enable debug logging"
    echo "  -h, --help                  Show this help message"
    echo ""
    echo "Examples:"
    echo "  $(basename $0) -i ./my_code -n \"My Project Vector Store\""
    echo "  $(basename $0) -i ./src -n \"Source Code\" -o ./output -b 50 -f \"*.py *.js *.md\""
    echo "  $(basename $0) --test --create-test-files --debug"
}

# Default values
INPUT_DIR=""
VECTOR_STORE_NAME=""
OUTPUT_DIR=""
BATCH_SIZE=100
API_KEY=""
PURPOSE="assistants"
FILE_PATTERNS=""
EXCLUDE_DIRS=""
TEST_MODE=false
CREATE_TEST_FILES=false
RECURSIVE=true
RESET_STATE=false
DEBUG=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        -i|--input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        -n|--vector-store-name)
            VECTOR_STORE_NAME="$2"
            shift 2
            ;;
        -o|--output-dir)
            OUTPUT_DIR="$2"
            shift 2
            ;;
        -b|--batch-size)
            BATCH_SIZE="$2"
            shift 2
            ;;
        -k|--api-key)
            API_KEY="$2"
            shift 2
            ;;
        -p|--purpose)
            PURPOSE="$2"
            shift 2
            ;;
        -f|--file-patterns)
            FILE_PATTERNS="$2"
            shift 2
            ;;
        -e|--exclude-dirs)
            EXCLUDE_DIRS="$2"
            shift 2
            ;;
        -t|--test)
            TEST_MODE=true
            shift
            ;;
        -c|--create-test-files)
            CREATE_TEST_FILES=true
            shift
            ;;
        --no-recursive)
            RECURSIVE=false
            shift
            ;;
        --reset-state)
            RESET_STATE=true
            shift
            ;;
        --debug)
            DEBUG=true
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Load API key from .env file if it exists
if [ -f "$SCRIPT_DIR/.env" ]; then
    source "$SCRIPT_DIR/.env"
fi

# Set API key if provided
if [ -n "$API_KEY" ]; then
    export OPENAI_API_KEY="$API_KEY"
fi

# Check if API key is set
if [ -z "$OPENAI_API_KEY" ]; then
    echo "Error: OpenAI API key not set. Please set OPENAI_API_KEY environment variable or use --api-key."
    exit 1
fi

# Run in test mode if requested
if [ "$TEST_MODE" = true ]; then
    echo "Running in test mode..."
    
    # Set test parameters
    TEST_DIR="$SCRIPT_DIR/test_files"
    TEST_VECTOR_STORE_NAME="Test Vector Store"
    
    # Create test files if requested
    if [ "$CREATE_TEST_FILES" = true ]; then
        echo "Creating test files..."
        ARGS=""
        if [ "$DEBUG" = true ]; then
            ARGS="$ARGS --debug"
        fi
        python3 "$SCRIPT_DIR/codedoc/tools/test_file_uploader.py" --create-files --test-dir "$TEST_DIR" $ARGS
    fi
    
    # Run test
    CMD="python3 $SCRIPT_DIR/codedoc/tools/test_file_uploader.py --test-dir $TEST_DIR --vector-store-name \"$TEST_VECTOR_STORE_NAME\""
    if [ "$DEBUG" = true ]; then
        CMD="$CMD --debug"
    fi
    if [ "$BATCH_SIZE" -ne 100 ]; then
        CMD="$CMD --batch-size $BATCH_SIZE"
    fi
    
    echo "Running: $CMD"
    eval $CMD
    exit $?
fi

# Check required arguments
if [ -z "$INPUT_DIR" ] || [ -z "$VECTOR_STORE_NAME" ]; then
    echo "Error: --input-dir and --vector-store-name are required."
    show_usage
    exit 1
fi

# Build command
CMD="python3 $SCRIPT_DIR/codedoc/tools/file_uploader.py --input-dir \"$INPUT_DIR\" --vector-store-name \"$VECTOR_STORE_NAME\""

if [ -n "$OUTPUT_DIR" ]; then
    CMD="$CMD --output-dir \"$OUTPUT_DIR\""
fi

if [ "$BATCH_SIZE" -ne 100 ]; then
    CMD="$CMD --batch-size $BATCH_SIZE"
fi

if [ -n "$PURPOSE" ]; then
    CMD="$CMD --purpose \"$PURPOSE\""
fi

if [ -n "$FILE_PATTERNS" ]; then
    CMD="$CMD --patterns $FILE_PATTERNS"
fi

if [ -n "$EXCLUDE_DIRS" ]; then
    CMD="$CMD --exclude-dirs $EXCLUDE_DIRS"
fi

if [ "$RECURSIVE" = false ]; then
    CMD="$CMD --no-recursive"
fi

if [ "$RESET_STATE" = true ]; then
    CMD="$CMD --reset-state"
fi

if [ "$DEBUG" = true ]; then
    CMD="$CMD --debug"
fi

# Run the command
echo "Running: $CMD"
eval $CMD
exit $? 