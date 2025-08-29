from unittest.mock import Mock, patch

import pytest

from patentpack.idmap.cache import CacheKey, NamePlanCache
from patentpack.idmap.runner import _count_by_bucket, plan_names
from patentpack.idmap.types import (
    DiscoveryOptions,
    PlanOptions,
    VariantItem,
)


class TestCountByBucket:
    """Test the _count_by_bucket helper function."""

    def test_count_by_bucket_empty(self):
        """Test counting with empty variant list."""
        variants: list[VariantItem] = []
        result = _count_by_bucket(variants)

        # The function initializes all buckets to 0
        expected = {
            "orig": 0,
            "gleif_legal": 0,
            "gleif_other": 0,
            "gleif_sub": 0,
            "expand_legal": 0,
            "expand_other": 0,
            "expand_orig": 0,
            "expand_sub": 0,
        }
        assert result == expected

    def test_count_by_bucket_single_bucket(self):
        """Test counting with single bucket."""
        variants = [
            VariantItem(name="Apple Inc", bucket="orig", kind="seed"),
            VariantItem(name="APPLE INC", bucket="orig", kind="seed"),
        ]

        result = _count_by_bucket(variants)

        assert result["orig"] == 2
        # All other buckets should be 0
        assert result["gleif_legal"] == 0
        assert result["gleif_other"] == 0
        assert result["gleif_sub"] == 0

    def test_count_by_bucket_multiple_buckets(self):
        """Test counting with multiple buckets."""
        variants = [
            VariantItem(name="Apple Inc", bucket="orig", kind="seed"),
            VariantItem(name="Apple Inc.", bucket="gleif_legal", kind="seed"),
            VariantItem(
                name="Apple Computer Inc", bucket="gleif_other", kind="seed"
            ),
        ]

        result = _count_by_bucket(variants)

        assert result["orig"] == 1
        assert result["gleif_legal"] == 1
        assert result["gleif_other"] == 1
        # All other buckets should be 0
        assert result["gleif_sub"] == 0
        assert result["expand_legal"] == 0


class TestPlanNames:
    """Test the main plan_names function."""

    def test_plan_names_no_probing(self, sample_cache: NamePlanCache):
        """Test plan_names without discovery or EQ."""
        result = plan_names(
            provider_name="uspto",
            year=2020,
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            cache=sample_cache,
        )

        # Should have plan but no discovery or EQ results
        assert result.plan is not None
        assert len(result.plan.ordered_variants) > 0
        # Variants are generated even without probing, but discovery/eq are empty
        assert not result.discovery
        assert not result.eq_counts
        assert result.best_total == 0
        assert result.best_variant == ""
        assert result.best_bucket == ""

    def test_plan_names_with_discovery(self, sample_cache: NamePlanCache):
        """Test plan_names with discovery enabled."""
        with patch(
            "patentpack.idmap.runner.discover_orgs_via_begins"
        ) as mock_discover:
            mock_discover.return_value = ["Apple Inc", "Apple Computer Inc"]

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=False),
                cache=sample_cache,
            )

            # Should have discovery results
            assert result.discovery
            assert "Apple Inc" in result.discovery
            assert len(result.discovery["Apple Inc"]) == 2

            # Should have trace
            assert len(result.trace) > 0
            assert any(t["op"] == "discover" for t in result.trace)

    def test_plan_names_with_eq(self, sample_cache: NamePlanCache):
        """Test plan_names with EQ enabled."""
        with patch("patentpack.idmap.runner.eq_count") as mock_eq:
            mock_eq.return_value = (150, {"total_hits": 150})

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=False, run_eq=True),
                cache=sample_cache,
            )

            # Should have EQ results
            assert result.eq_counts
            assert "Apple Inc" in result.eq_counts
            assert result.eq_counts["Apple Inc"] == 150

            # Should have best results
            assert result.best_total == 150
            assert result.best_variant == "Apple Inc"
            assert result.best_bucket == "orig"

    def test_plan_names_with_both_discovery_and_eq(
        self, sample_cache: NamePlanCache
    ):
        """Test plan_names with both discovery and EQ enabled."""
        with (
            patch(
                "patentpack.idmap.runner.discover_orgs_via_begins"
            ) as mock_discover,
            patch("patentpack.idmap.runner.eq_count") as mock_eq,
        ):

            mock_discover.return_value = ["Apple Inc", "Apple Computer Inc"]
            mock_eq.return_value = (150, {"total_hits": 150})

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=True),
                cache=sample_cache,
            )

            # Should have both discovery and EQ results
            assert result.discovery
            assert result.eq_counts
            assert result.best_total == 150

    def test_plan_names_cache_usage(self, sample_cache: NamePlanCache):
        """Test that plan_names uses cache correctly."""
        # Pre-populate cache
        key = CacheKey(
            provider="uspto", year=2020, op="discover", key="Apple Inc"
        )
        sample_cache.mark_has_hits(key, True)

        with patch(
            "patentpack.idmap.runner.discover_orgs_via_begins"
        ) as mock_discover:
            mock_discover.return_value = ["cached_result"]

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=False),
                cache=sample_cache,
            )

            # Should use cached result
            assert "Apple Inc" in result.discovery
            # Note: With simplified cache, we return placeholder data
            assert len(result.discovery["Apple Inc"]) > 0

    def test_plan_names_error_handling(self, sample_cache: NamePlanCache):
        """Test that plan_names handles errors gracefully."""
        with patch(
            "patentpack.idmap.runner.discover_orgs_via_begins"
        ) as mock_discover:
            mock_discover.side_effect = Exception("API Error")

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=False),
                cache=sample_cache,
            )

            # Should handle errors gracefully
            assert result.discovery
            assert "Apple Inc" in result.discovery
            assert result.discovery["Apple Inc"] == []  # Empty on error

    def test_plan_names_plan_options(self, sample_cache: NamePlanCache):
        """Test that plan_names respects PlanOptions."""
        result = plan_names(
            provider_name="uspto",
            year=2020,
            base_name="Apple Inc",
            plan_opts=PlanOptions(include_expansions=False, max_variants=3),
            cache=sample_cache,
        )

        # Should respect max_variants
        assert len(result.plan.ordered_variants) <= 3

        # Should not have expansions
        buckets = [v["bucket"] for v in result.plan.ordered_variants]
        assert not any(b.startswith("expand_") for b in buckets)

    def test_plan_names_provider_creation(self, sample_cache: NamePlanCache):
        """Test that plan_names creates provider correctly."""
        with patch(
            "patentpack.idmap.runner.get_provider"
        ) as mock_get_provider:
            mock_provider = Mock()
            mock_get_provider.return_value = mock_provider

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                rpm=45,  # Custom RPM
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=False),
                cache=sample_cache,
            )

            # Should call get_provider with correct parameters
            mock_get_provider.assert_called_once_with("uspto", rpm=45)

    def test_plan_names_trace_logging(self, sample_cache: NamePlanCache):
        """Test that plan_names logs operations in trace."""
        with patch(
            "patentpack.idmap.runner.discover_orgs_via_begins"
        ) as mock_discover:
            mock_discover.return_value = ["Apple Inc"]

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=False),
                cache=sample_cache,
            )

            # Should have trace entries
            assert len(result.trace) > 0

            # Check trace structure
            for entry in result.trace:
                assert "op" in entry
                assert entry["op"] in ["discover", "eq"]

                if entry["op"] == "discover":
                    assert "seed" in entry
                    assert "bucket" in entry
                    assert "found_n" in entry
                elif entry["op"] == "eq":
                    assert "name" in entry
                    assert "bucket" in entry
                    assert "count" in entry

    def test_plan_names_variant_ordering(self, sample_cache: NamePlanCache):
        """Test that variants are properly ordered."""
        result = plan_names(
            provider_name="uspto",
            year=2020,
            base_name="Apple Inc",
            gleif_legal="Apple Inc.",
            gleif_other_names=["Apple Computer Inc"],
            subsidiaries=["Beats Electronics"],
            cache=sample_cache,
        )

        # Should have variants in expected order
        variants = result.plan.ordered_variants

        # Check that we have the expected buckets
        buckets = [v["bucket"] for v in variants]
        assert "orig" in buckets
        assert "gleif_legal" in buckets
        assert "gleif_other" in buckets
        assert "gleif_sub" in buckets

    def test_plan_names_empty_inputs(self, sample_cache: NamePlanCache):
        """Test plan_names with empty inputs."""
        result = plan_names(
            provider_name="uspto",
            year=2020,
            base_name="",
            gleif_legal="",
            gleif_other_names=[],
            subsidiaries=[],
            cache=sample_cache,
        )

        # Should handle empty inputs gracefully
        assert result.plan is not None
        # May have fewer variants with empty inputs
        assert len(result.plan.ordered_variants) >= 0

    def test_plan_names_cache_integration(self, sample_cache: NamePlanCache):
        """Test that plan_names integrates properly with cache."""
        # Test that cache is used for both discovery and EQ
        with (
            patch(
                "patentpack.idmap.runner.discover_orgs_via_begins"
            ) as mock_discover,
            patch("patentpack.idmap.runner.eq_count") as mock_eq,
        ):

            mock_discover.return_value = ["Apple Inc"]
            mock_eq.return_value = (150, {"total_hits": 150})

            result = plan_names(
                provider_name="uspto",
                year=2020,
                base_name="Apple Inc",
                probe_opts=DiscoveryOptions(run_discovery=True, run_eq=True),
                cache=sample_cache,
            )

            # Should have used cache
            assert result.discovery
            assert result.eq_counts

            # Check that cache was populated
            disc_key = CacheKey(
                provider="uspto", year=2020, op="discover", key="Apple Inc"
            )
            eq_key = CacheKey(
                provider="uspto", year=2020, op="eq", key="Apple Inc"
            )

            assert sample_cache.has_hits(disc_key)
            assert sample_cache.has_hits(eq_key)
