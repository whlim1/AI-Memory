# AI Memory Pipeline

A Python-based document processing and indexing pipeline with Qdrant vector storage integration.

## Project Structure

```
.
├── docker-compose.yml          # Docker Compose configuration for Qdrant
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── ai_memory_pipeline/         # Core Python package
    ├── __init__.py             # Package initialization
    ├── chunking.py             # Text chunking functionality
    ├── redaction.py            # Sensitive data redaction
    ├── semantic_summary.py     # Semantic summarization
    ├── metadata.py             # Metadata handling
    └── qdrant_client.py        # Qdrant vector database integration
```

## Getting Started

### Prerequisites

- Docker Desktop 29.9.2 or higher
- Python 3.15.2 with pip 26.2.2
- Docker Compose v5.6.1 or higher

### Running Qdrant Vector Database

To start the Qdrant vector database:

```bash
# Navigate to the project root directory
cd D:/AI-Memory

# Start Qdrant service using Docker Compose
docker-compose up -d

# Check if Qdrant is running
docker-compose ps
```

### Stopping Qdrant

To stop the Qdrant service:

```bash
# Stop and remove containers
docker-compose down
```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   ```

2. Activate the virtual environment:
   - On Windows: `.venv\Scripts\activate`
   - On Linux/Mac: `source .venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Install in development mode:
   ```bash
   pip install -e .
   ```

## API Endpoints

- **Health Check**: `http://localhost:6333/readyz` (Qdrant)
- **API Documentation**: Coming soon...

## Configuration

The Qdrant service is configured to run on ports 6333 (HTTP) and 6334 (gRPC). The data will be persisted in the `qdrant_storage` volume.

## License

This project is licensed under the MIT License.