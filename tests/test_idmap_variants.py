import pytest

from patentpack.idmap.cache import CacheKey, NamePlanCache
from patentpack.idmap.types import Bucket, VariantItem
from patentpack.idmap.variants import (
    _add_uc_variant,
    _has_designator,
    _squash_ws,
    build_bucketed_variants,
    build_cache_aware_variants,
)


class TestUtilityFunctions:
    """Test utility functions in variants module."""

    def test_squash_ws(self):
        """Test whitespace squashing function."""
        assert _squash_ws("  hello   world  ") == "hello world"
        assert _squash_ws("no_spaces") == "no_spaces"
        assert _squash_ws("") == ""
        assert _squash_ws("   ") == ""
        assert _squash_ws("single") == "single"

    def test_has_designator(self):
        """Test corporate designator detection."""
        # Should have designators
        assert _has_designator("Apple Inc") is True
        assert _has_designator("Microsoft Corporation") is True
        assert _has_designator("Google LLC") is True
        assert _has_designator("Tesla GmbH") is True
        assert _has_designator("Samsung S.p.A.") is True

        # Should not have designators
        assert _has_designator("Apple") is False
        assert _has_designator("Microsoft") is False
        assert _has_designator("Google") is False
        assert _has_designator("Tesla") is False
        assert _has_designator("Samsung") is False

        # Test edge cases
        assert _has_designator("") is False
        assert _has_designator("   ") is False
        assert _has_designator("Apple Inc.") is True  # With period
        assert _has_designator("Apple, Inc") is True  # With comma

    def test_add_uc_variant(self):
        """Test uppercase variant addition."""
        out: list[VariantItem] = []
        seen: set[str] = set()

        # Add UC variant
        _add_uc_variant("Apple Inc", "orig", out, seen)

        assert len(out) == 1
        assert out[0]["name"] == "APPLE INC"
        assert out[0]["bucket"] == "orig"
        assert out[0]["kind"] == "seed"
        assert "APPLE INC" in seen

    def test_add_uc_variant_duplicate(self):
        """Test that duplicate UC variants are not added."""
        out: list[VariantItem] = []
        seen: set[str] = set()

        # Add same UC variant twice
        _add_uc_variant("Apple Inc", "orig", out, seen)
        _add_uc_variant("Apple Inc", "orig", out, seen)

        assert len(out) == 1  # Should only add once
        assert "APPLE INC" in seen

    def test_add_uc_variant_already_uc(self):
        """Test that already uppercase names don't create duplicates."""
        out: list[VariantItem] = []
        seen: set[str] = set()

        # Add the UC variant first
        _add_uc_variant("APPLE INC", "orig", out, seen)

        # The name should be in seen set
        assert "APPLE INC" in seen
        # But no variants should be added since it's already UC
        assert len(out) == 0


class TestBuildBucketedVariants:
    """Test the main variant building function."""

    def test_basic_variants_no_expansions(self):
        """Test basic variant generation without expansions."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc"],
            subsidiaries=["Beats Electronics"],
            include_expansions=False,
        )

        # Should have seeds but no expansions
        assert len(variants) > 0

        # Check that we have the expected buckets
        buckets = [v["bucket"] for v in variants]
        assert "orig" in buckets
        assert "gleif_legal" in buckets
        assert "gleif_other" in buckets
        assert "gleif_sub" in buckets

        # Check that we don't have expansions
        assert "expand_orig" not in buckets
        assert "expand_legal" not in buckets

    def test_variants_with_expansions(self):
        """Test variant generation with expansions."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            include_expansions=True,
        )

        # Should have more variants due to expansions
        assert len(variants) > 0

        # Check that we have expansion buckets
        buckets = [v["bucket"] for v in variants]
        assert "expand_orig" in buckets or "expand_legal" in buckets

    def test_variants_max_limit(self):
        """Test that max_variants limit is respected."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc", "Apple Computer"],
            subsidiaries=["Beats Electronics", "Shazam"],
            include_expansions=True,
            max_variants=5,
        )

        assert len(variants) <= 5

    def test_variants_empty_inputs(self):
        """Test variant generation with empty inputs."""
        variants = build_bucketed_variants(
            base_name="",
            gleif_legal="",
            gleif_other_names=[],
            subsidiaries=[],
            include_expansions=False,
        )

        # Should handle empty inputs gracefully
        assert isinstance(variants, list)

    def test_variants_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        variants = build_bucketed_variants(
            base_name="  Apple   Inc  ",
            gleif_legal="  Apple   Inc.  ",
            include_expansions=False,
        )

        # Should normalize whitespace in variant names
        for variant in variants:
            name = variant["name"]
            # Should not have leading/trailing whitespace
            assert name == name.strip()
            # Should not have multiple consecutive spaces
            assert "  " not in name
            # Should have single spaces between words
            assert " " in name  # At least one space between words

    def test_variants_bucket_ordering(self):
        """Test that variants are generated in the expected bucket order."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc"],
            subsidiaries=["Beats Electronics"],
            include_expansions=True,
        )

        # Check that seeds come before expansions
        seed_buckets = ["orig", "gleif_legal", "gleif_other", "gleif_sub"]
        expansion_buckets = [
            "expand_orig",
            "expand_legal",
            "expand_other",
            "expand_sub",
        ]

        # Find first occurrence of each bucket type
        seed_indices = []
        expansion_indices = []

        for i, variant in enumerate(variants):
            if variant["bucket"] in seed_buckets:
                seed_indices.append(i)
            elif variant["bucket"] in expansion_buckets:
                expansion_indices.append(i)

        # All seeds should come before expansions
        if seed_indices and expansion_indices:
            assert max(seed_indices) < min(expansion_indices)


class TestBuildCacheAwareVariants:
    """Test the cache-aware variant building function."""

    def test_cache_aware_no_cache_provided(self):
        """Test that function falls back to regular variant generation when no cache."""
        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            cache=None,
        )

        # Should generate variants as usual
        assert len(variants) > 0
        assert any(v["bucket"] == "orig" for v in variants)

    def test_cache_aware_no_hits(self, sample_cache: NamePlanCache):
        """Test cache-aware generation when no hits in cache."""
        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            cache=sample_cache,
            provider_name="uspto",
            year=2020,
        )

        # Should generate all variants when no cache hits
        assert len(variants) > 1  # More than just the original

    def test_cache_aware_with_hits(self, sample_cache: NamePlanCache):
        """Test cache-aware generation when hits exist in cache."""
        # Mark the original as having hits
        orig_key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(orig_key, True)

        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            cache=sample_cache,
            provider_name="uspto",
            year=2020,
        )

        # Should return only variants with hits (currently just the original)
        assert len(variants) == 1
        assert variants[0]["name"] == "Apple Inc"
        assert variants[0]["bucket"] == "orig"

    def test_cache_aware_different_provider(self, sample_cache: NamePlanCache):
        """Test that cache keys are provider-specific."""
        # Mark hit for one provider
        orig_key_uspto = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(orig_key_uspto, True)

        # Try with different provider
        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            cache=sample_cache,
            provider_name="epo",  # Different provider
            year=2020,
        )

        # Should generate all variants since different provider
        assert len(variants) > 1

    def test_cache_aware_different_year(self, sample_cache: NamePlanCache):
        """Test that cache keys are year-specific."""
        # Mark hit for one year
        orig_key_2020 = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(orig_key_2020, True)

        # Try with different year
        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            cache=sample_cache,
            provider_name="uspto",
            year=2021,  # Different year
        )

        # Should generate all variants since different year
        assert len(variants) > 1

    def test_cache_aware_edge_cases(self, sample_cache: NamePlanCache):
        """Test cache-aware generation with edge cases."""
        # Test with empty base name
        variants = build_cache_aware_variants(
            base_name="",
            cache=sample_cache,
            provider_name="uspto",
            year=2020,
        )

        # Should handle gracefully
        assert isinstance(variants, list)

        # Test with None year
        variants = build_cache_aware_variants(
            base_name="Apple Inc",
            cache=sample_cache,
            provider_name="uspto",
            year=None,
        )

        # Should handle None year (converts to 0)
        assert isinstance(variants, list)


class TestVariantItemStructure:
    """Test that generated variants have the correct structure."""

    def test_variant_item_structure(self):
        """Test that all variants have the required fields."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            include_expansions=True,
        )

        for variant in variants:
            # Check required fields
            assert "name" in variant
            assert "bucket" in variant
            assert "kind" in variant

            # Check field types
            assert isinstance(variant["name"], str)
            assert isinstance(variant["bucket"], str)
            assert isinstance(variant["kind"], str)

            # Check field values
            assert variant["name"].strip() != ""
            assert variant["bucket"] in [
                "orig",
                "gleif_legal",
                "gleif_other",
                "gleif_sub",
                "expand_orig",
                "expand_legal",
                "expand_other",
                "expand_sub",
            ]
            assert variant["kind"] in ["seed", "expand"]

    def test_variant_uniqueness(self):
        """Test that variants are unique."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc"],
            subsidiaries=["Beats Electronics"],
            include_expansions=True,
        )

        # Check for duplicates
        names = [v["name"] for v in variants]
        assert len(names) == len(set(names)), "Variants should be unique"

    def test_variant_bucket_distribution(self):
        """Test that variants are distributed across expected buckets."""
        variants = build_bucketed_variants(
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc"],
            subsidiaries=["Beats Electronics"],
            include_expansions=True,
        )

        buckets = [v["bucket"] for v in variants]

        # Should have seeds
        assert "orig" in buckets
        assert "gleif_legal" in buckets

        # Should have some expansions if enabled
        expansion_buckets = [b for b in buckets if b.startswith("expand_")]
        assert len(expansion_buckets) > 0
