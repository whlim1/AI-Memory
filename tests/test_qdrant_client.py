"""Tests for ai_memory_pipeline.qdrant_client (QdrantManager).

The underlying QdrantClient is the stub installed by conftest.py: it records
constructor args and call history, succeeds on recreate_collection/upsert/
delete, returns [] from get_points, and raises RuntimeError from
get_collections/search. Tests monkeypatch instance methods to exercise both
success and failure paths without a live Qdrant server.
"""

from ai_memory_pipeline.qdrant_client_wrapper import QdrantManager


class _FakeHit:
    """Stand-in for a qdrant search result item."""

    def __init__(self, id=None, score=0.0, payload=None):
        self.id = id
        self.score = score
        self.payload = payload


class _FakeCollection:
    def __init__(self, name):
        self.name = name


class _FakeCollectionsResponse:
    def __init__(self, names):
        self.collections = [_FakeCollection(n) for n in names]


def _last_call(manager, method_name):
    """Return the recorded (method, *args) tuple for a client call."""
    calls = [c for c in manager.client.calls if c[0] == method_name]
    assert calls, f"expected at least one '{method_name}' call on stub client"
    return calls[-1]


class TestInit:
    def test_stores_connection_settings(self):
        m = QdrantManager(host="qdrant.local", port=7000)
        assert m.host == "qdrant.local"
        assert m.port == 7000
        assert m.api_key is None

    def test_client_built_without_api_key_by_default(self):
        m = QdrantManager(host="h1", port=6334)
        assert m.client.kwargs == {"host": "h1", "port": 6334}
        assert "api_key" not in m.client.kwargs

    def test_client_built_with_api_key_when_provided(self):
        m = QdrantManager(host="h2", port=6335, api_key="secret")
        assert m.api_key == "secret"
        assert m.client.kwargs.get("api_key") == "secret"
        assert m.client.kwargs["host"] == "h2"
        assert m.client.kwargs["port"] == 6335

    def test_defaults_to_localhost_6333(self):
        m = QdrantManager()
        assert m.host == "localhost"
        assert m.port == 6333


class TestCreateCollection:
    def test_success_returns_true_and_passes_vector_params(self):
        m = QdrantManager()
        assert m.create_collection("docs", vector_size=768, distance="Dot") is True
        call = _last_call(m, "recreate_collection")
        assert call[1] == "docs"
        assert call[2].size == 768
        assert call[2].distance == "Dot"

    def test_defaults_vector_size_1536_cosine(self):
        m = QdrantManager()
        assert m.create_collection("c") is True
        call = _last_call(m, "recreate_collection")
        assert call[2].size == 1536
        assert call[2].distance == "Cosine"

    def test_client_error_returns_false(self):
        m = QdrantManager()
        monkeypatched = []

        def boom(collection_name=None, vectors_config=None, **kw):
            monkeypatched.append(True)
            raise RuntimeError("connection refused")

        m.client.recreate_collection = boom
        assert m.create_collection("docs") is False
        assert monkeypatched


class TestIndexDocument:
    def test_success_returns_true_and_upserts_point(self):
        m = QdrantManager()
        vec = [0.1, 0.2, 0.3]
        assert m.index_document("docs", "doc-1", vec) is True
        call = _last_call(m, "upsert")
        assert call[1] == "docs"
        points = call[2]
        assert len(points) == 1
        point = points[0]
        assert point.id == "doc-1"
        assert point.vector == vec
        assert point.payload == {}

    def test_metadata_stored_as_payload(self):
        m = QdrantManager()
        meta = {"title": "T", "tags": ["a"]}
        assert m.index_document("docs", "d2", [1.0], metadata=meta) is True
        point = _last_call(m, "upsert")[2][0]
        assert point.payload == meta

    def test_client_error_returns_false(self):
        m = QdrantManager()

        def boom(collection_name=None, points=None, **kw):
            raise RuntimeError("server down")

        m.client.upsert = boom
        assert m.index_document("docs", "d3", [1.0]) is False


class TestSearchSimilar:
    def test_stub_error_returns_empty_list(self):
        # Stub search() raises by default -> error path yields [].
        m = QdrantManager()
        assert m.search_similar("docs", [0.5, 0.5]) == []

    def test_success_maps_hits_to_dicts(self):
        m = QdrantManager()
        hits = [
            _FakeHit(id="a", score=0.91, payload={"title": "A"}),
            _FakeHit(id="b", score=0.82, payload=None),  # None -> {}
        ]
        m.client.search = lambda **kw: hits
        results = m.search_similar("docs", [0.5], limit=3)
        assert results == [
            {"id": "a", "score": 0.91, "payload": {"title": "A"}},
            {"id": "b", "score": 0.82, "payload": {}},
        ]

    def test_passes_limit_and_filter_to_client(self):
        m = QdrantManager()
        seen = {}

        def search(collection_name=None, query_vector=None, limit=10, **kw):
            seen["collection"] = collection_name
            seen["vector"] = query_vector
            seen["limit"] = limit
            seen["filter"] = kw.get("filter")
            return []

        m.client.search = search
        flt = object()
        assert m.search_similar("docs", [1.0], limit=5, filter_conditions=flt) == []
        assert seen["collection"] == "docs"
        assert seen["vector"] == [1.0]
        assert seen["limit"] == 5
        assert seen["filter"] is flt


class TestGetDocument:
    def test_missing_document_returns_none(self):
        # Stub get_points() returns [] by default -> not found path.
        m = QdrantManager()
        assert m.get_document("docs", "nope") is None

    def test_found_document_returns_id_and_payload(self):
        m = QdrantManager()
        m.client.get_points = lambda **kw: [_FakeHit(id="d1", payload={"title": "T"})]
        result = m.get_document("docs", "d1")
        assert result == {"id": "d1", "payload": {"title": "T"}}

    def test_found_document_with_none_payload_defaults_to_empty_dict(self):
        m = QdrantManager()
        m.client.get_points = lambda **kw: [_FakeHit(id="d2", payload=None)]
        result = m.get_document("docs", "d2")
        assert result == {"id": "d2", "payload": {}}

    def test_client_error_returns_none(self):
        m = QdrantManager()

        def boom(collection_name=None, ids=None, **kw):
            raise RuntimeError("timeout")

        m.client.get_points = boom
        assert m.get_document("docs", "d3") is None


class TestDeleteDocument:
    def test_success_returns_true_and_deletes_point(self):
        m = QdrantManager()
        assert m.delete_document("docs", "doc-9") is True
        call = _last_call(m, "delete")
        assert call[1] == "docs"
        assert call[2] == ["doc-9"]

    def test_client_error_returns_false(self):
        m = QdrantManager()

        def boom(collection_name=None, points_selector=None, **kw):
            raise RuntimeError("gone")

        m.client.delete = boom
        assert m.delete_document("docs", "doc-10") is False


class TestListCollections:
    def test_stub_error_returns_empty_list(self):
        # Stub get_collections() raises by default -> error path yields [].
        m = QdrantManager()
        assert m.list_collections() == []

    def test_success_returns_collection_names(self):
        m = QdrantManager()
        m.client.get_collections = lambda: _FakeCollectionsResponse(["a", "b"])
        assert m.list_collections() == ["a", "b"]


class TestHealthCheck:
    def test_stub_error_returns_false(self):
        # Stub get_collections() raises by default -> unhealthy.
        m = QdrantManager()
        assert m.health_check() is False

    def test_success_returns_true(self):
        m = QdrantManager()
        m.client.get_collections = lambda: _FakeCollectionsResponse([])
        assert m.health_check() is True
