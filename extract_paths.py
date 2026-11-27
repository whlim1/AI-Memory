import sys, re, json, urllib.request

url = "http://192.168.0.16:8081/api/docs/static/swagger-ui-bundle.js"
resp = urllib.request.urlopen(url)
data = resp.read().decode("utf-8", errors="replace")
print(f"Bundled size: {len(data)} chars, {len(data.splitlines())} lines")

# Method 1: Search for any /api/ path patterns (quoted strings containing /api/)
paths_found = re.findall(r'["\'](/api/[^\s"\']{3,})["\']', data)
unique_paths = sorted(set(paths_found))
print(f"\n=== ALL /api/ PATHS FOUND ({len(unique_paths)} total) ===")
for p in unique_paths:
    print(f"  {p}")

# Method 2: Look for the swagger spec object by finding "swagger": or "openapi": 
# followed eventually by "paths"
print("\n=== SEARCHING FOR SWAGGER SPEC OBJECTS ===")
spec_markers = re.finditer(r'"(swagger|openapi)"\s*:\s*"([^"]+)"', data)
for m in spec_markers:
    print(f"  Found {m.group(1)} version {m.group(2)} at pos {m.start()}")

# Method 3: Look for the paths object by finding a large JSON block with "paths" key
# The bundle might have it as part of a larger object. Let's find all objects containing "paths"
print("\n=== SEARCHING FOR 'paths' KEY IN OBJECTS ===")
for m in re.finditer(r'"paths"\s*:', data):
    pos = m.start()
    # Look at context around this position
    ctx_start = max(0, pos - 200)
    ctx_end = min(len(data), pos + 500)
    ctx = data[ctx_start:ctx_end]
    print(f"\n  Context at pos {pos}:")
    # Print the surrounding text with visible quotes
    for i in range(0, len(ctx), 80):
        chunk = ctx[i:i+80].replace('"', '["]').replace("'", "[']")
        print(f"    {chunk}")

# Method 4: If it's a Swagger UI bundle, the spec might be loaded from an external URL
# Look for URLs that point to OpenAPI/Swagger specs
print("\n=== LOOKING FOR EXTERNAL SPEC URLs ===")
url_patterns = re.findall(r'(https?://[^\s"\']+/api/[^/\s"\']+)', data)
for u in url_patterns:
    print(f"  {u}")

# Method 5: Check if there's a /api/docs/static/swagger.json or similar
print("\n=== CHECKING COMMON SWAGGER JSON PATHS ===")
common_paths = [
    "/api/docs/static/swagger.json",
    "/api/v1/docs/openapi.json", 
    "/docs/api-reference/openapi.json",
    "/openapi.json",
]
for p in common_paths:
    try:
        resp2 = urllib.request.urlopen(url.replace("swagger-ui-bundle.js", p.lstrip("/")))
        print(f"  {p} -> {resp2.status}")
    except Exception as e:
        pass
