# CodeDoc: Code Enhancement and Vector Store Integration Platform

CodeDoc is a comprehensive platform for enhancing codebases with improved documentation, generating supplementary content, and preparing everything for vector search. It leverages Large Language Models (LLMs) to analyze code, improve documentation, and create a rich ecosystem of materials that can be uploaded to vector stores for semantic code search.

## Features

- **Code Enhancement**: Automatically improve code documentation with AI-generated insights
- **Code Analysis**: Extract patterns, complexity metrics, and other insights from your codebase
- **Supplementary Content**: Generate FAQs, tutorials, architecture diagrams, and more
- **Vector Store Preparation**: Process files with sophisticated chunking strategies
- **OpenAI Vector Store Integration**: Upload enhanced content to OpenAI's vector store
- **Flexible Pipeline**: Configure workflows to suit your specific needs

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/codedoc.git
cd codedoc

# Install dependencies
pip install -r requirements.txt
```

## Quick Start

To analyze and enhance a codebase:

```bash
# Make sure the script is executable
chmod +x run_pipeline.sh

# Run the pipeline
./run_pipeline.sh path/to/your/codebase --project-name "My Project"
```

That's it! The script will:

1. Set up the necessary environment variables
2. Load your OpenAI API key from the `.env` file (if available)
3. Enhance documentation in all source files
4. Analyze the code for patterns and complexity
5. Generate supplementary documentation like FAQs, tutorials, and architecture diagrams
6. Process the files for vector storage using OpenAI's Files API
7. Upload the processed files to OpenAI's vector store

## Detailed Usage

### Pipeline Configuration

The pipeline can be customized with various options:

```bash
./run_pipeline.sh path/to/codebase \
    --project-name "My Project" \
    --output-dir output-folder \
    --model gpt-4-turbo \
    --file-patterns "*.py" "*.js" "*.md" \
    --exclude-dirs "tests" "node_modules" \
    --max-files 50 \
    --skip-upload
```

### Example Real-World Usage

Here's an example of processing a Python SDK project:

```bash
./run_pipeline.sh s2rh_pythonsdk-main \
    --project-name "S2RH Python SDK" \
    --output-dir s2rh_pythonsdk-main-output \
    --model gpt-4-turbo
```

### Skip Steps

You can skip specific steps in the pipeline:

```bash
./run_pipeline.sh path/to/codebase \
    --project-name "My Project" \
    --skip-enhancement \
    --skip-analysis \
    --skip-supplementary \
    --skip-processing \
    --skip-upload
```

For more examples and detailed usage, see the [Quick Reference Guide](QUICK_REFERENCE.md).

### Vector Store Operations

Upload a file to OpenAI's vector store:

```bash
PYTHONPATH=$PWD python3 codedoc/vectorstore/openai_vectorstore.py upload-file \
    --file-path "path/to/your/file.md" \
    --purpose "assistants"
```

Create a vector store from files:

```bash
PYTHONPATH=$PWD python3 codedoc/vectorstore/openai_vectorstore.py create-vector-store \
    --name "my-codebase" \
    --file-ids "file-abc123,file-def456"
```

Search the vector store:

```bash
PYTHONPATH=$PWD python3 codedoc/vectorstore/openai_vectorstore.py search \
    --vector-store-id "vs-123456" \
    --query "How do I implement authentication?"
```

## Core Components

### File Enhancement Pipeline

The file enhancement pipeline leverages LLMs to improve documentation in your code files:

```python
from codedoc.enhancers.file_enhancer import FileEnhancer
from codedoc.llm.openai_client import OpenAIClient

# Initialize the LLM client
llm_client = OpenAIClient()

# Initialize the file enhancer
enhancer = FileEnhancer(
    llm_client=llm_client,
    output_dir="enhanced-code",
    model="gpt-4o"
)

# Enhance a single file
result = enhancer.enhance_file("path/to/file.py")

# Enhance a directory
results = enhancer.enhance_directory(
    input_dir="my_project",
    file_patterns=["*.py", "*.js"],
    recursive=True
)
```

### Vector Store Preprocessing

Process files directly for OpenAI's vector store using the DirectFileProcessor:

```python
from codedoc.preprocessors.direct_file_processor import DirectFileProcessor
from codedoc.integrations.openai_vector import OpenAIVectorClient

# Initialize the OpenAI client
openai_client = OpenAIVectorClient()

# Initialize the direct file processor
processor = DirectFileProcessor(
    openai_client=openai_client,
    output_dir="vector-ready"
)

# Process a single file
file_id = processor.process_file(
    file_path="path/to/file.py",
    purpose="assistants"  # Valid values: 'assistants', 'fine-tune', etc.
)

# Process a directory
file_ids = processor.process_directory(
    input_dir="enhanced-code",
    file_patterns=["*.py", "*.md"],
    purpose="assistants",
    recursive=True
)
```

### OpenAI Vector Store Integration

Create and search vector stores using OpenAI's Files API:

```python
from codedoc.vectorstore.openai_vectorstore import OpenAIVectorStore

# Initialize the vector store client
vector_store = OpenAIVectorStore()

# Create a vector store from file IDs
vector_store_id = vector_store.create_vector_store(
    name="my-codebase",
    file_ids=["file-abc123", "file-def456"]
)

# Search the vector store
search_results = vector_store.search(
    vector_store_id="vs-123456",
    query="How do I implement authentication?",
    max_results=10
)
```

## Environment Variables

The following environment variables can be used:

- `OPENAI_API_KEY`: Your OpenAI API key
- `GEMINI_API_KEY`: Your Google Gemini API key
- `OPENAI_ORG_ID`: Your OpenAI organization ID (optional)

## Output Structure

The default output structure is:

```
project-output/
├── enhanced-codebase/    # Enhanced code files
├── supplementary-docs/   # Generated FAQs, tutorials, etc.
│   ├── tutorials/        # Tutorial documents
│   ├── project_faq.md    # Frequently asked questions
│   └── architecture.md   # Architecture documentation
├── metadata/             # Analysis results and metrics
│   ├── file_patterns.md  # Pattern analysis for each file
│   └── file_complexity.md # Complexity analysis for each file
└── vector-store/         # Vector store information
    └── file_ids.json     # Mapping of files to OpenAI file IDs
```

## Requirements

- Python 3.8+
- OpenAI API key for vector store and LLM functionality
- Google Gemini API key (optional, for alternative LLM provider)

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request 