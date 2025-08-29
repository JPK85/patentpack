import json
import tempfile
from pathlib import Path

import pytest

from patentpack.idmap.cache import CacheKey, NamePlanCache
from patentpack.idmap.variants import build_cache_aware_variants


def test_cache_location():
    """Test that cache is now stored in data/cache/ instead of data/"""
    print("Testing cache location...")

    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        data_dir = temp_path / "data"
        cache_dir = data_dir / "cache"

        # Create the directories
        data_dir.mkdir()
        cache_dir.mkdir()

        # Test that cache uses CACHE_DIR
        cache = NamePlanCache(path=cache_dir / "test_cache.jsonl")
        expected_path = cache_dir / "test_cache.jsonl"

        assert str(cache.path) == str(
            expected_path
        ), f"Expected {expected_path}, got {cache.path}"
        print("✓ Cache location test passed")


def test_simplified_cache_structure():
    """Test that cache now stores has_hits instead of detailed results"""
    print("Testing simplified cache structure...")

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "test_cache.jsonl"
        cache = NamePlanCache(path=cache_path)

        # Test discovery cache
        disc_key = CacheKey(
            provider="uspto", year=2020, op="discover", key="test_company"
        )
        cache.mark_has_hits(disc_key, True)

        # Check that we stored has_hits
        cached = cache.get(disc_key)
        assert cached is not None, "Cache should have stored the key"
        assert (
            cached.get("has_hits") is True
        ), "Should have stored has_hits=True"

        # Test EQ cache
        eq_key = CacheKey(
            provider="uspto", year=2020, op="eq", key="test_company"
        )
        cache.mark_has_hits(eq_key, False)

        cached = cache.get(eq_key)
        assert cached is not None, "Cache should have stored the key"
        assert (
            cached.get("has_hits") is False
        ), "Should have stored has_hits=False"

        print("✓ Simplified cache structure test passed")


def test_cache_aware_variants():
    """Test that variant generation respects cache hits"""
    print("Testing cache-aware variant generation...")

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "test_cache.jsonl"
        cache = NamePlanCache(path=cache_path)

        # Test 1: No cache hits - should generate all variants
        variants_no_hits = build_cache_aware_variants(
            base_name="Test Company Inc",
            cache=cache,
            provider_name="uspto",
            year=2020,
        )

        # Should generate multiple variants when no hits
        assert (
            len(variants_no_hits) > 1
        ), "Should generate multiple variants when no cache hits"
        print(
            f"✓ Generated {len(variants_no_hits)} variants when no cache hits"
        )

        # Test 2: Mark original as having hits
        orig_key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Test Company Inc"
        )
        cache.mark_has_hits(orig_key, True)

        # Test 3: With cache hits - should return only variants with hits
        variants_with_hits = build_cache_aware_variants(
            base_name="Test Company Inc",
            cache=cache,
            provider_name="uspto",
            year=2020,
        )

        # Should return only the original since it has hits
        assert (
            len(variants_with_hits) == 1
        ), "Should return only variants with hits"
        assert (
            variants_with_hits[0]["name"] == "Test Company Inc"
        ), "Should return the original name"
        print(
            f"✓ Generated {len(variants_with_hits)} variants when original has cache hits"
        )

        print("✓ Cache-aware variant generation test passed")


def test_cache_persistence():
    """Test that cache persists data correctly"""
    print("Testing cache persistence...")

    with tempfile.TemporaryDirectory() as temp_dir:
        cache_path = Path(temp_dir) / "test_cache.jsonl"

        # Create cache and add data
        cache1 = NamePlanCache(path=cache_path)
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="persistent_test"
        )
        cache1.mark_has_hits(key, True)

        # Create new cache instance and verify data persists
        cache2 = NamePlanCache(path=cache_path)
        assert cache2.has_hits(
            key
        ), "Cache data should persist between instances"

        print("✓ Cache persistence test passed")


class TestCacheKey:
    """Test the CacheKey dataclass."""

    def test_cache_key_creation(self):
        """Test creating CacheKey instances."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")

        assert key.provider == "uspto"
        assert key.year == 2020
        assert key.op == "discover"
        assert key.key == "test"

    def test_cache_key_immutability(self):
        """Test that CacheKey is immutable."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")

        with pytest.raises(Exception):
            key.provider = "epo"  # type: ignore

    def test_cache_key_equality(self):
        """Test CacheKey equality."""
        key1 = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        key2 = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        key3 = CacheKey(provider="epo", year=2020, op="discover", key="test")

        assert key1 == key2
        assert key1 != key3

    def test_cache_key_hashable(self):
        """Test that CacheKey is hashable."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        key_dict = {key: "value"}

        assert key in key_dict
        assert key_dict[key] == "value"


class TestNamePlanCache:
    """Test the NamePlanCache class."""

    def test_cache_initialization(self, temp_cache_dir: Path):
        """Test cache initialization."""
        cache_path = temp_cache_dir / "test_cache.jsonl"
        cache = NamePlanCache(path=cache_path)

        assert cache.path == cache_path
        assert not cache._loaded
        assert cache._mem == {}

    def test_cache_default_path(self):
        """Test that cache uses default path when none specified."""
        cache = NamePlanCache()

        # Should use the CACHE_DIR from config
        assert "cache" in str(cache.path)

    def test_cache_load_nonexistent_file(self, temp_cache_dir: Path):
        """Test loading cache when file doesn't exist."""
        cache_path = temp_cache_dir / "nonexistent.jsonl"
        cache = NamePlanCache(path=cache_path)

        # Should not raise error
        cache._load()
        assert cache._loaded

    def test_cache_load_empty_file(self, temp_cache_dir: Path):
        """Test loading cache from empty file."""
        cache_path = temp_cache_dir / "empty.jsonl"
        cache_path.write_text("")

        cache = NamePlanCache(path=cache_path)
        cache._load()

        assert cache._loaded
        assert cache._mem == {}

    def test_cache_load_valid_data(self, temp_cache_dir: Path):
        """Test loading cache from valid JSONL file."""
        cache_path = temp_cache_dir / "valid.jsonl"

        # Create test data
        test_data = [
            {
                "provider": "uspto",
                "year": 2020,
                "op": "discover",
                "key": "test1",
                "val": {"has_hits": True},
            },
            {
                "provider": "uspto",
                "year": 2020,
                "op": "eq",
                "key": "test2",
                "val": {"has_hits": False},
            },
        ]

        with cache_path.open("w") as f:
            for record in test_data:
                f.write(json.dumps(record) + "\n")

        cache = NamePlanCache(path=cache_path)
        cache._load()

        assert cache._loaded
        assert len(cache._mem) == 2

        # Check first record
        key1 = CacheKey(
            provider="uspto", year=2020, op="discover", key="test1"
        )
        assert cache._mem[(key1.provider, key1.year, key1.op, key1.key)] == {
            "has_hits": True
        }

        # Check second record
        key2 = CacheKey(provider="uspto", year=2020, op="eq", key="test2")
        assert cache._mem[(key2.provider, key2.year, key2.op, key2.key)] == {
            "has_hits": False
        }

    def test_cache_load_invalid_data(self, temp_cache_dir: Path):
        """Test loading cache from file with an invalid JSON line followed by a valid schema line."""
        import json

        cache_path = temp_cache_dir / "invalid.jsonl"

        # 1) invalid JSON line (should be skipped)
        bad = "invalid json\n"
        # 2) valid schema line (should be loaded)
        good = (
            json.dumps(
                {
                    "provider": "uspto",
                    "year": 2020,
                    "op": "discover",
                    "key": "Apple Inc",
                    "val": {"has_hits": True},
                }
            )
            + "\n"
        )

        cache_path.write_text(bad + good, encoding="utf-8")

        cache = NamePlanCache(path=cache_path)
        cache._load()

        assert cache._loaded
        # Should skip the bad line and keep the good one
        assert len(cache._mem) == 1

        # And the record should be accessible via the key helpers
        k = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        assert cache.has_hits(k) is True

    def test_cache_get_nonexistent(self, sample_cache: NamePlanCache):
        """Test getting non-existent cache entry."""
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="nonexistent"
        )

        result = sample_cache.get(key)
        assert result is None

    def test_cache_get_existing(self, sample_cache: NamePlanCache):
        """Test getting existing cache entry."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        value = {"has_hits": True}

        # Put value first
        sample_cache.put(key, value)

        # Get it back
        result = sample_cache.get(key)
        assert result == value

    def test_cache_put_new(self, sample_cache: NamePlanCache):
        """Test putting new cache entry."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        value = {"has_hits": True}

        sample_cache.put(key, value)

        # Check memory
        key_tuple = (key.provider, key.year, key.op, key.key)
        assert sample_cache._mem[key_tuple] == value

        # Check file
        assert sample_cache.path.exists()

        # Read file content
        with sample_cache.path.open("r") as f:
            lines = f.readlines()
            assert len(lines) == 1

            record = json.loads(lines[0])
            assert record["provider"] == key.provider
            assert record["year"] == key.year
            assert record["op"] == key.op
            assert record["key"] == key.key
            assert record["val"] == value

    def test_cache_put_existing(self, sample_cache: NamePlanCache):
        """Test updating existing cache entry."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        value1 = {"has_hits": False}
        value2 = {"has_hits": True}

        # Put first value
        sample_cache.put(key, value1)

        # Put second value (should update)
        sample_cache.put(key, value2)

        # Check memory
        key_tuple = (key.provider, key.year, key.op, key.key)
        assert sample_cache._mem[key_tuple] == value2

        # Check file has both records (append-only)
        with sample_cache.path.open("r") as f:
            lines = f.readlines()
            assert len(lines) == 2

    def test_cache_has_hits_true(self, sample_cache: NamePlanCache):
        """Test has_hits method when entry has hits."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        value = {"has_hits": True}

        sample_cache.put(key, value)

        assert sample_cache.has_hits(key) is True

    def test_cache_has_hits_false(self, sample_cache: NamePlanCache):
        """Test has_hits method when entry has no hits."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        value = {"has_hits": False}

        sample_cache.put(key, value)

        assert sample_cache.has_hits(key) is False

    def test_cache_has_hits_nonexistent(self, sample_cache: NamePlanCache):
        """Test has_hits method for non-existent entry."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")

        assert sample_cache.has_hits(key) is False

    def test_cache_mark_has_hits(self, sample_cache: NamePlanCache):
        """Test mark_has_hits method."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")

        # Mark as having hits
        sample_cache.mark_has_hits(key, True)
        assert sample_cache.has_hits(key) is True

        # Mark as not having hits
        sample_cache.mark_has_hits(key, False)
        assert sample_cache.has_hits(key) is False

    def test_cache_thread_safety(self, temp_cache_dir: Path):
        """Test that cache operations are thread-safe."""
        import threading
        import time

        cache_path = temp_cache_dir / "thread_test.jsonl"
        cache = NamePlanCache(path=cache_path)

        def worker(worker_id: int):
            """Worker function that performs cache operations."""
            for i in range(10):
                key = CacheKey(
                    provider="uspto",
                    year=2020,
                    op="discover",
                    key=f"worker_{worker_id}_key_{i}",
                )
                cache.mark_has_hits(key, i % 2 == 0)
                time.sleep(
                    0.001
                )  # Small delay to increase chance of race conditions

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all operations completed
        assert cache_path.exists()

        # Check that we can read the cache without errors
        cache._load()
        assert cache._loaded

    def test_cache_directory_creation(self, temp_cache_dir: Path):
        """Test that cache creates parent directories if they don't exist."""
        deep_cache_path = temp_cache_dir / "deep" / "nested" / "cache.jsonl"
        cache = NamePlanCache(path=deep_cache_path)

        # This should create the directories
        key = CacheKey(provider="uspto", year=2020, op="discover", key="test")
        cache.mark_has_hits(key, True)

        # Check directories were created
        assert deep_cache_path.parent.exists()
        assert deep_cache_path.exists()

    def test_cache_unicode_support(self, sample_cache: NamePlanCache):
        """Test that cache supports Unicode characters."""
        key = CacheKey(provider="uspto", year=2020, op="discover", key="café")
        value = {"has_hits": True, "note": "café avec accent"}

        sample_cache.put(key, value)

        # Read back
        result = sample_cache.get(key)
        assert result == value
        assert result["note"] == "café avec accent"

    def test_cache_large_data(self, sample_cache: NamePlanCache):
        """Test cache with large amounts of data."""
        # Add many entries
        for i in range(1000):
            key = CacheKey(
                provider="uspto", year=2020, op="discover", key=f"key_{i}"
            )
            sample_cache.mark_has_hits(key, i % 2 == 0)

        # Verify all entries are accessible
        for i in range(1000):
            key = CacheKey(
                provider="uspto", year=2020, op="discover", key=f"key_{i}"
            )
            expected_hits = i % 2 == 0
            assert sample_cache.has_hits(key) == expected_hits


def main():
    """Run all tests"""
    print("Running cache logic tests...\n")

    try:
        test_cache_location()
        test_simplified_cache_structure()
        test_cache_aware_variants()
        test_cache_persistence()

        print(
            "\n🎉 All tests passed! The new caching logic is working correctly."
        )

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0
