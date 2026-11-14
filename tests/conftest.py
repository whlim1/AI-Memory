"""Shared pytest fixtures and module stubs for ai_memory_pipeline tests.

The real ``qdrant_client`` package is not installed in the test environment,
so we inject lightweight stub modules into ``sys.modules`` *before* any test
imports ``ai_memory_pipeline.qdrant_client`` (or the package itself, whose
``__init__.py`` imports that submodule).
"""

import sys
import types


class _StubVectorParams:
    def __init__(self, size=None, distance=None):
        self.size = size
        self.distance = distance


class _StubFilter:
    def __init__(self, must=None, should=None, must_not=None):
        self.must = must or []
        self.should = should or []
        self.must_not = must_not or []


class _StubFieldCondition:
    def __init__(self, key=None, match=None):
        self.key = key
        self.match = match


class _StubMatchValue:
    def __init__(self, value=None):
        self.value = value


class _StubPointStruct:
    def __init__(self, id=None, vector=None, payload=None):
        self.id = id
        self.vector = vector
        self.payload = payload or {}


class _StubScoredPoint:
    """Stub for qdrant_client.models.ScoredPoint."""
    def __init__(self, id=None, score=0.0, version=None, payload=None, vector=None, shard_key=None, payload_bytes=None):
        self.id = id
        self.score = score
        self.version = version
        self.payload = payload or {}
        self.vector = vector
        self.shard_key = shard_key
        self.payload_bytes = payload_bytes


class _StubDistance:
    """Stub for qdrant_client.models.Distance enum."""
    pass


def _install_qdrant_stubs():
    if "qdrant_client" in sys.modules and getattr(
        sys.modules["qdrant_client"], "_is_stub", False
    ):
        return

    models_mod = types.ModuleType("qdrant_client.models")
    models_mod.VectorParams = _StubVectorParams
    models_mod.Filter = _StubFilter
    models_mod.FieldCondition = _StubFieldCondition
    models_mod.MatchValue = _StubMatchValue
    models_mod.PointStruct = _StubPointStruct
    models_mod.ScoredPoint = _StubScoredPoint
    models_mod.Distance = _StubDistance

    client_mod = types.ModuleType("qdrant_client")
    client_mod.models = models_mod
    client_mod._is_stub = True  # marker so we don't clobber a real install

    class QdrantClient:
        """Minimal stand-in for qdrant_client.QdrantClient.

        Records constructor args and call history; individual tests can
        monkeypatch methods on instances as needed.
        """

        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.calls = []

        # -- collection ops -------------------------------------------------
        def recreate_collection(self, collection_name=None, vectors_config=None, **kw):
            self.calls.append(("recreate_collection", collection_name, vectors_config))
            return True

        def get_collections(self):
            self.calls.append(("get_collections",))
            raise RuntimeError("stub: no collections")

        # -- point ops ------------------------------------------------------
        def upsert(self, collection_name=None, points=None, **kw):
            self.calls.append(("upsert", collection_name, points))
            return True

        def search(
            self,
            collection_name=None,
            query_vector=None,
            limit=10,
            with_payload=True,
            **kw,
        ):
            self.calls.append(("search", collection_name, query_vector, limit))
            return []  # Return empty list instead of raising

        def query_points(
            self,
            collection_name=None,
            query=None,
            limit=10,
            with_payload=True,
            **kw,
        ):
            self.calls.append(("query_points", collection_name, query, limit))
            return []  # Return empty list for similar search

        def get_points(self, collection_name=None, ids=None, with_payload=True, **kw):
            self.calls.append(("get_points", collection_name, ids))
            return []

        def delete(self, collection_name=None, points_selector=None, **kw):
            self.calls.append(("delete", collection_name, points_selector))
            return True

    client_mod.QdrantClient = QdrantClient

    sys.modules["qdrant_client"] = client_mod
    sys.modules["qdrant_client.models"] = models_mod


_install_qdrant_stubs()
