from unittest.mock import Mock, patch

import pytest

from patentpack.idmap.cache import CacheKey, NamePlanCache
from patentpack.idmap.iterator import (
    ALL_BUCKETS,
    EXPAND_BUCKETS,
    SEED_BUCKETS,
    DiscoveryResult,
    EqAttemptResult,
    NameEvent,
    NameResolver,
    ResolveConfig,
    _Cache,
)


class TestResolveConfig:
    """Test the ResolveConfig dataclass."""

    def test_resolve_config_defaults(self):
        """Test ResolveConfig default values."""
        config = ResolveConfig()

        assert config.strategy == "eq_then_discovery"
        assert config.discovery_limit == 120
        assert config.debug is False

    def test_resolve_config_custom_values(self):
        """Test ResolveConfig with custom values."""
        config = ResolveConfig(
            strategy="discovery_first", discovery_limit=60, debug=True
        )

        assert config.strategy == "discovery_first"
        assert config.discovery_limit == 60
        assert config.debug is True


class TestCacheAdapter:
    """Test the _Cache adapter class."""

    def test_cache_adapter_initialization(self, sample_cache: NamePlanCache):
        """Test _Cache initialization."""
        cache_adapter = _Cache(sample_cache)

        assert cache_adapter.store == sample_cache

    def test_cache_adapter_default_store(self):
        """Test _Cache with default store."""
        cache_adapter = _Cache()

        assert cache_adapter.store is not None
        assert isinstance(cache_adapter.store, NamePlanCache)

    def test_cache_adapter_year_conversion(self):
        """Test _Cache year conversion."""
        cache_adapter = _Cache()

        assert cache_adapter._year(2020) == 2020
        assert cache_adapter._year(None) == 0
        assert cache_adapter._year("2020") == 2020

    def test_cache_adapter_get_eq_cached(self, sample_cache: NamePlanCache):
        """Test _Cache get_eq with cached data."""
        cache_adapter = _Cache(sample_cache)

        # Pre-populate cache
        key = CacheKey(provider="uspto", year=2020, op="eq", key="Apple Inc")
        sample_cache.mark_has_hits(key, True)

        result = cache_adapter.get_eq("uspto", 2020, "Apple Inc")

        # Should return placeholder count since we only track has_hits
        assert result == 1

    def test_cache_adapter_get_eq_not_cached(
        self, sample_cache: NamePlanCache
    ):
        """Test _Cache get_eq with no cached data."""
        cache_adapter = _Cache(sample_cache)

        result = cache_adapter.get_eq("uspto", 2020, "Nonexistent")

        assert result is None

    def test_cache_adapter_put_eq(self, sample_cache: NamePlanCache):
        """Test _Cache put_eq."""
        cache_adapter = _Cache(sample_cache)

        cache_adapter.put_eq("uspto", 2020, "Apple Inc", 150)

        # Check that cache was updated
        key = CacheKey(provider="uspto", year=2020, op="eq", key="Apple Inc")
        assert sample_cache.has_hits(key) is True

    def test_cache_adapter_get_discovery_cached(
        self, sample_cache: NamePlanCache
    ):
        """Test _Cache get_discovery with cached data."""
        cache_adapter = _Cache(sample_cache)

        # Pre-populate cache
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(key, True)

        result = cache_adapter.get_discovery("uspto", 2020, "Apple Inc")

        # Should return placeholder list since we only track has_hits
        assert result == ["cached_hit"]

    def test_cache_adapter_get_discovery_not_cached(
        self, sample_cache: NamePlanCache
    ):
        """Test _Cache get_discovery with no cached data."""
        cache_adapter = _Cache(sample_cache)

        result = cache_adapter.get_discovery("uspto", 2020, "Nonexistent")

        assert result is None

    def test_cache_adapter_put_discovery(self, sample_cache: NamePlanCache):
        """Test _Cache put_discovery."""
        cache_adapter = _Cache(sample_cache)

        cache_adapter.put_discovery(
            "uspto", 2020, "Apple Inc", ["Apple Inc", "Apple Computer Inc"]
        )

        # Check that cache was updated
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        assert sample_cache.has_hits(key) is True

    def test_cache_adapter_put_discovery_empty(
        self, sample_cache: NamePlanCache
    ):
        """Test _Cache put_discovery with empty results."""
        cache_adapter = _Cache(sample_cache)

        cache_adapter.put_discovery("uspto", 2020, "Apple Inc", [])

        # Check that cache was updated
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        assert sample_cache.has_hits(key) is False

    def test_cache_adapter_has_hits(self, sample_cache: NamePlanCache):
        """Test _Cache has_hits method."""
        cache_adapter = _Cache(sample_cache)

        # Test with no hits
        assert (
            cache_adapter.has_hits("uspto", 2020, "discover", "Apple Inc")
            is False
        )

        # Test with hits
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(key, True)

        assert (
            cache_adapter.has_hits("uspto", 2020, "discover", "Apple Inc")
            is True
        )


class TestNameResolver:
    """Test the NameResolver class."""

    def test_name_resolver_initialization(
        self, mock_provider, sample_cache: NamePlanCache
    ):
        """Test NameResolver initialization."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        assert resolver.provider == mock_provider
        assert resolver.cache.store == sample_cache
        assert resolver.provider_label == "test_provider"

    def test_name_resolver_default_cache(self, mock_provider):
        """Test NameResolver with default cache."""
        resolver = NameResolver(mock_provider)

        assert resolver.cache is not None
        assert isinstance(resolver.cache, _Cache)

    def test_name_resolver_default_provider_label(self, mock_provider):
        """Test NameResolver with default provider label."""
        resolver = NameResolver(mock_provider)

        assert resolver.provider_label == "provider"

    def test_name_resolver_resolve_eq_then_discovery(
        self, mock_provider, sample_cache: NamePlanCache
    ):
        """Test NameResolver with eq_then_discovery strategy."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        candidates = [("Apple Inc", "orig"), ("Apple Inc.", "gleif_legal")]

        events = list(
            resolver.resolve(
                base_query="Apple Inc",
                year=2020,
                candidates=candidates,
                strategy="eq_then_discovery",
                discovery_limit=60,
                debug=False,
            )
        )

        # Should have events
        assert len(events) > 0

        # Check event types
        for event in events:
            assert isinstance(event, (EqAttemptResult, DiscoveryResult))

    def test_name_resolver_resolve_discovery_first(
        self, mock_provider, sample_cache: NamePlanCache
    ):
        """Test NameResolver with discovery_first strategy."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        candidates = [("Apple Inc", "orig"), ("Apple Inc.", "gleif_legal")]

        events = list(
            resolver.resolve(
                base_query="Apple Inc",
                year=2020,
                candidates=candidates,
                strategy="discovery_first_for_seeds",
                discovery_limit=60,
                debug=False,
            )
        )

        # Should have events
        assert len(events) > 0

    def test_name_resolver_unknown_strategy(
        self, mock_provider, sample_cache: NamePlanCache
    ):
        """Test NameResolver with unknown strategy."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        candidates = [("Apple Inc", "orig")]

        with pytest.raises(ValueError, match="Unknown strategy"):
            list(
                resolver.resolve(
                    base_query="Apple Inc",
                    year=2020,
                    candidates=candidates,
                    strategy="unknown_strategy",
                )
            )

    def test_name_resolver_debug_output(
        self, mock_provider, sample_cache: NamePlanCache, capsys
    ):
        """Test NameResolver debug output."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        candidates = [("Apple Inc", "orig"), ("Apple Inc.", "gleif_legal")]

        list(
            resolver.resolve(
                base_query="Apple Inc",
                year=2020,
                candidates=candidates,
                strategy="eq_then_discovery",
                debug=True,
            )
        )

        # Check that debug output was produced
        captured = capsys.readouterr()
        assert "variants-plan" in captured.out
        assert "Apple Inc" in captured.out

    def test_name_resolver_cache_integration(
        self, mock_provider, sample_cache: NamePlanCache
    ):
        """Test that NameResolver integrates with cache."""
        resolver = NameResolver(mock_provider, sample_cache, "test_provider")

        candidates = [("Apple Inc", "orig")]

        # First run - should populate cache
        events1 = list(
            resolver.resolve(
                base_query="Apple Inc",
                year=2020,
                candidates=candidates,
                strategy="eq_then_discovery",
            )
        )

        # Second run - should use cache
        events2 = list(
            resolver.resolve(
                base_query="Apple Inc",
                year=2020,
                candidates=candidates,
                strategy="eq_then_discovery",
            )
        )

        # Both should produce events
        assert len(events1) > 0
        assert len(events2) > 0


class TestEventTypes:
    """Test the event type dataclasses."""

    def test_eq_attempt_result(self):
        """Test EqAttemptResult creation and attributes."""
        event = EqAttemptResult(
            base_query="Apple Inc",
            year=2020,
            variant="Apple Inc",
            bucket="orig",
            total=150,
            meta={"source": "test"},
        )

        assert event.base_query == "Apple Inc"
        assert event.year == 2020
        assert event.variant == "Apple Inc"
        assert event.bucket == "orig"
        assert event.total == 150
        assert event.meta["source"] == "test"

    def test_discovery_result(self):
        """Test DiscoveryResult creation and attributes."""
        event = DiscoveryResult(
            base_query="Apple Inc",
            year=2020,
            seed="Apple Inc",
            bucket="orig",
            harvested=["Apple Inc", "Apple Computer Inc"],
            meta={"limit": 120},
        )

        assert event.base_query == "Apple Inc"
        assert event.year == 2020
        assert event.seed == "Apple Inc"
        assert event.bucket == "orig"
        assert len(event.harvested) == 2
        assert event.meta["limit"] == 120

    def test_name_event_union(self):
        """Test that NameEvent can be either type."""
        eq_event = EqAttemptResult(
            base_query="Apple Inc",
            year=2020,
            variant="Apple Inc",
            bucket="orig",
            total=150,
            meta={},
        )

        disc_event = DiscoveryResult(
            base_query="Apple Inc",
            year=2020,
            seed="Apple Inc",
            bucket="orig",
            harvested=["Apple Inc"],
            meta={},
        )

        events: list[NameEvent] = [eq_event, disc_event]

        assert len(events) == 2
        assert isinstance(events[0], EqAttemptResult)
        assert isinstance(events[1], DiscoveryResult)


class TestBucketConstants:
    """Test the bucket constant definitions."""

    def test_seed_buckets(self):
        """Test SEED_BUCKETS constant."""
        assert "orig" in SEED_BUCKETS
        assert "gleif_legal" in SEED_BUCKETS
        assert "gleif_other" in SEED_BUCKETS
        assert "gleif_sub" in SEED_BUCKETS

        # Should not contain expansion buckets
        assert "expand_orig" not in SEED_BUCKETS

    def test_expand_buckets(self):
        """Test EXPAND_BUCKETS constant."""
        assert "expand_orig" in EXPAND_BUCKETS
        assert "expand_legal" in EXPAND_BUCKETS
        assert "expand_other" in EXPAND_BUCKETS
        assert "expand_sub" in EXPAND_BUCKETS

        # Should not contain seed buckets
        assert "orig" not in EXPAND_BUCKETS

    def test_all_buckets(self):
        """Test ALL_BUCKETS constant."""
        # Should contain all buckets
        for bucket in SEED_BUCKETS:
            assert bucket in ALL_BUCKETS

        for bucket in EXPAND_BUCKETS:
            assert bucket in ALL_BUCKETS

        # Should be the union
        assert len(ALL_BUCKETS) == len(SEED_BUCKETS) + len(EXPAND_BUCKETS)
