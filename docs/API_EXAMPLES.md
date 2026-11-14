# LM Studio API Examples

## Quick Start

```python
import requests

# Test connection
response = requests.get("http://localhost:1234/v1/models")
print(response.json())

# Generate embeddings
response = requests.post(
    "http://localhost:1234/v1/embeddings",
    json={
        "model": "text-embedding-qwen3-embedding-8b",
        "input": "Your text here",
        "encoding_format": "float"
    }
)
print(response.json())
```

## Complete Examples

### Example 1: Embedding Generation

```python
import requests

def generate_embeddings(texts, model="text-embedding-qwen3-embedding-8b"):
    """Generate embeddings for multiple texts."""
    response = requests.post(
        f"http://localhost:1234/v1/embeddings",
        json={
            "model": model,
            "input": texts,
            "encoding_format": "float"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return [item['embedding'] for item in data['data']]
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

# Usage
embeddings = generate_embeddings(["First text", "Second text"])
print(f"Generated {len(embeddings)} embeddings")
```

### Example 2: Chat Completion

```python
import requests

def chat_completion(messages, model="qwen3-coder-next"):
    """Send a chat completion request."""
    response = requests.post(
        f"http://localhost:1234/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "temperature": 0.7
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        return data['choices'][0]['message']['content']
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

# Usage
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is Python?"}
]
response = chat_completion(messages)
print(response)
```

### Example 3: List Available Models

```python
import requests

def list_models():
    """List all available models in LM Studio."""
    response = requests.get(
        "http://localhost:1234/v1/models"
    )
    
    if response.status_code == 200:
        data = response.json()
        return [model['id'] for model in data['data']]
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

# Usage
models = list_models()
print("Available models:")
for model in models:
    print(f"  - {model}")
```

### Example 4: Get Current Loaded Model

```python
import requests

def get_loaded_model():
    """Get the currently loaded model ID."""
    response = requests.get(
        "http://localhost:1234/v1/models"
    )
    
    if response.status_code == 200:
        data = response.json()
        # The first model in the list is typically the active one
        return data['data'][0]['id'] if data['data'] else None
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

# Usage
current_model = get_loaded_model()
print(f"Current model: {current_model}")
```

## Advanced Examples

### Example 5: Batch Embedding with Error Handling

```python
import requests
import time

def batch_embeddings(texts, model="text-embedding-qwen3-embedding-8b", batch_size=10):
    """Process embeddings in batches with retry logic."""
    all_embeddings = []
    
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        try:
            response = requests.post(
                f"http://localhost:1234/v1/embeddings",
                json={
                    "model": model,
                    "input": batch,
                    "encoding_format": "float"
                },
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                embeddings = [item['embedding'] for item in data['data']]
                all_embeddings.extend(embeddings)
                print(f"Batch {i//batch_size + 1}: Generated {len(embeddings)} embeddings")
            else:
                print(f"Batch failed: {response.status_code}")
                
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            time.sleep(2)  # Wait before retry
            continue
    
    return all_embeddings

# Usage
texts = [f"Text number {i}" for i in range(100)]
embeddings = batch_embeddings(texts)
```

### Example 6: Streaming Chat (Python)

```python
import requests

def stream_chat(messages, model="qwen3-coder-next"):
    """Stream chat completions."""
    response = requests.post(
        f"http://localhost:1234/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "stream": True
        },
        stream=True
    )
    
    if response.status_code == 200:
        full_response = ""
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode('utf-8')
                if 'data: ' in decoded_line:
                    data = decoded_line.replace('data: ', '').strip()
                    if data and data != '[DONE]':
                        try:
                            import json
                            chunk = json.loads(data)
                            content = chunk['choices'][0]['delta'].get('content', '')
                            full_response += content
                            print(content, end='', flush=True)
                        except:
                            pass
        print()  # New line at end
        return full_response
    else:
        raise Exception(f"API error: {response.status_code} - {response.text}")

# Usage
messages = [{"role": "user", "content": "Explain quantum computing"}]
response = stream_chat(messages)
```

### Example 7: Model Switching (Python)

```python
import requests

class LMStudioManager:
    def __init__(self, host="localhost", port=1234):
        self.base_url = f"http://{host}:{port}/v1"
    
    def switch_model(self, model_id):
        """Switch to a specific model."""
        # Note: LM Studio doesn't have an explicit switch endpoint
        # You need to ensure the model is loaded before use
        models_response = requests.get(f"{self.base_url}/models")
        available_models = [m['id'] for m in models_response.json()['data']]
        
        if model_id not in available_models:
            print(f"Warning: {model_id} is not loaded. Loading it now...")
            # In LM Studio, loading happens through the UI
            return False
        
        self.current_model = model_id
        return True
    
    def get_loaded_models(self):
        """Get list of loaded models."""
        response = requests.get(f"{self.base_url}/models")
        if response.status_code == 200:
            data = response.json()
            # Models that have 'loaded' in their details are currently loaded
            return [m['id'] for m in data['data']]
        return []

# Usage
manager = LMStudioManager()
print("Available models:", manager.get_loaded_models())
```

## Integration with Qdrant

### Example 8: Ingestion Pipeline

```python
import requests
from qdrant_client import QdrantClient

def ingest_document(document_text, collection_name="documents"):
    """Ingest a document into Qdrant with embeddings."""
    
    # Generate embedding using LM Studio
    embed_response = requests.post(
        "http://localhost:1234/v1/embeddings",
        json={
            "model": "text-embedding-qwen3-embedding-8b",
            "input": document_text,
            "encoding_format": "float"
        }
    )
    
    if embed_response.status_code != 200:
        raise Exception(f"Embedding failed: {embed_response.status_code}")
    
    embedding = embed_response.json()['data'][0]['embedding']
    
    # Store in Qdrant
    client = QdrantClient(host="localhost", port=6333)
    
    point = {
        "id": len(list(client.get_points(collection_name=collection_name))) + 1,
        "vector": embedding,
        "payload": {"text": document_text}
    }
    
    client.upsert(collection_name=collection_name, points=[point])
    print(f"Document ingested with vector dimension: {len(embedding)}")

# Usage
ingest_document("This is a sample document to ingest into the knowledge base.")
```

## Error Handling

### Common Errors and Solutions

```python
import requests
import time

def safe_api_call(endpoint, method="GET", json_data=None, max_retries=3):
    """Make API calls with retry logic for transient errors."""
    
    base_url = "http://localhost:1234/v1"
    url = f"{base_url}/{endpoint}"
    
    for attempt in range(max_retries):
        try:
            if method == "GET":
                response = requests.get(url, timeout=30)
            elif method == "POST":
                response = requests.post(url, json=json_data, timeout=60)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code in [503, 504]:
                print(f"Server busy (attempt {attempt + 1}/{max_retries})")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                raise Exception(f"HTTP {response.status_code}: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("Connection error - is LM Studio running?")
            return None
        except requests.exceptions.Timeout:
            print("Request timeout")
            continue
    
    return None

# Usage
result = safe_api_call("models")
if result:
    print(f"Retrieved {len(result['data'])} models")
```