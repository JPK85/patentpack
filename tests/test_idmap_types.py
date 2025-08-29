import pytest

from patentpack.idmap.types import (
    Bucket,
    DiscoveryOptions,
    NamePlan,
    NamePlanResult,
    PlanOptions,
    VariantItem,
)


class TestBucket:
    """Test the Bucket literal type."""

    def test_valid_buckets(self):
        """Test that all expected bucket values are valid."""
        valid_buckets = [
            "orig",
            "gleif_legal",
            "gleif_other",
            "gleif_sub",
            "expand_orig",
            "expand_legal",
            "expand_other",
            "expand_sub",
        ]

        for bucket in valid_buckets:
            # This should not raise a type error
            bucket_var: Bucket = bucket  # type: ignore
            assert bucket_var == bucket

    def test_bucket_string_operations(self):
        """Test that buckets can be used in string operations."""
        bucket: Bucket = "orig"

        # String concatenation
        assert bucket + "_test" == "orig_test"

        # String methods
        assert bucket.upper() == "ORIG"
        assert bucket.startswith("or")
        assert bucket.endswith("ig")

        # String formatting
        assert f"bucket_{bucket}" == "bucket_orig"


class TestVariantItem:
    """Test the VariantItem TypedDict."""

    def test_variant_item_creation(self):
        """Test creating VariantItem instances."""
        variant = VariantItem(name="Apple Inc", bucket="orig", kind="seed")

        assert variant["name"] == "Apple Inc"
        assert variant["bucket"] == "orig"
        assert variant["kind"] == "seed"

    def test_variant_item_field_access(self):
        """Test accessing VariantItem fields."""
        variant = VariantItem(
            name="Apple Inc", bucket="gleif_legal", kind="seed"
        )

        # Test field access
        assert variant["name"] == "Apple Inc"
        assert variant["bucket"] == "gleif_legal"
        assert variant["bucket"] in [
            "orig",
            "gleif_legal",
            "gleif_other",
            "gleif_sub",
        ]
        assert variant["kind"] in ["seed", "expand"]

    def test_variant_item_mutation(self):
        """Test that VariantItem can be mutated."""
        variant = VariantItem(name="Apple Inc", bucket="orig", kind="seed")

        # Should be able to change values
        variant["name"] = "Apple Computer Inc"
        variant["bucket"] = "gleif_other"

        assert variant["name"] == "Apple Computer Inc"
        assert variant["bucket"] == "gleif_other"

    def test_variant_item_validation(self):
        """Test that VariantItem enforces correct types."""
        variant = VariantItem(name="Apple Inc", bucket="orig", kind="seed")

        # All fields should be strings
        assert isinstance(variant["name"], str)
        assert isinstance(variant["bucket"], str)
        assert isinstance(variant["kind"], str)


class TestDiscoveryOptions:
    """Test the DiscoveryOptions dataclass."""

    def test_discovery_options_defaults(self):
        """Test DiscoveryOptions default values."""
        options = DiscoveryOptions()

        assert options.run_discovery is True
        assert options.run_eq is False
        assert options.limit_discovery == 120
        assert options.utility_only is False

    def test_discovery_options_custom_values(self):
        """Test DiscoveryOptions with custom values."""
        options = DiscoveryOptions(
            run_discovery=False,
            run_eq=True,
            limit_discovery=60,
            utility_only=True,
        )

        assert options.run_discovery is False
        assert options.run_eq is True
        assert options.limit_discovery == 60
        assert options.utility_only is True

    def test_discovery_options_immutability(self):
        """Test that DiscoveryOptions is immutable."""
        options = DiscoveryOptions()

        with pytest.raises(Exception):
            options.run_discovery = False  # type: ignore

    def test_discovery_options_equality(self):
        """Test DiscoveryOptions equality."""
        options1 = DiscoveryOptions(run_discovery=True, run_eq=False)
        options2 = DiscoveryOptions(run_discovery=True, run_eq=False)
        options3 = DiscoveryOptions(run_discovery=False, run_eq=False)

        assert options1 == options2
        assert options1 != options3

    def test_discovery_options_repr(self):
        """Test DiscoveryOptions string representation."""
        options = DiscoveryOptions(
            run_discovery=True, run_eq=False, limit_discovery=60
        )
        repr_str = repr(options)

        assert "DiscoveryOptions" in repr_str
        assert "run_discovery=True" in repr_str
        assert "run_eq=False" in repr_str
        assert "limit_discovery=60" in repr_str


class TestPlanOptions:
    """Test the PlanOptions dataclass."""

    def test_plan_options_defaults(self):
        """Test PlanOptions default values."""
        options = PlanOptions()

        assert options.include_expansions is True
        assert options.max_variants == 0

    def test_plan_options_custom_values(self):
        """Test PlanOptions with custom values."""
        options = PlanOptions(include_expansions=False, max_variants=10)

        assert options.include_expansions is False
        assert options.max_variants == 10

    def test_plan_options_immutability(self):
        """Test that PlanOptions is immutable."""
        options = PlanOptions()

        with pytest.raises(Exception):
            options.include_expansions = False  # type: ignore

    def test_plan_options_equality(self):
        """Test PlanOptions equality."""
        options1 = PlanOptions(include_expansions=True, max_variants=0)
        options2 = PlanOptions(include_expansions=True, max_variants=0)
        options3 = PlanOptions(include_expansions=False, max_variants=0)

        assert options1 == options2
        assert options1 != options3

    def test_plan_options_repr(self):
        """Test PlanOptions string representation."""
        options = PlanOptions(include_expansions=False, max_variants=5)
        repr_str = repr(options)

        assert "PlanOptions" in repr_str
        assert "include_expansions=False" in repr_str
        assert "max_variants=5" in repr_str


class TestNamePlan:
    """Test the NamePlan dataclass."""

    def test_name_plan_creation(self):
        """Test creating NamePlan instances."""
        variants = [
            VariantItem(name="Apple Inc", bucket="orig", kind="seed"),
            VariantItem(name="Apple Inc.", bucket="gleif_legal", kind="seed"),
        ]

        plan = NamePlan(ordered_variants=variants)

        assert len(plan.ordered_variants) == 2
        assert plan.ordered_variants[0]["name"] == "Apple Inc"
        assert plan.ordered_variants[1]["name"] == "Apple Inc."

    def test_name_plan_defaults(self):
        """Test NamePlan default values."""
        plan = NamePlan()

        assert plan.ordered_variants == []
        assert plan.counts_by_bucket == {}

    def test_name_plan_counts_by_bucket(self):
        """Test NamePlan counts_by_bucket field."""
        variants = [
            VariantItem(name="Apple Inc", bucket="orig", kind="seed"),
            VariantItem(name="APPLE INC", bucket="orig", kind="seed"),
            VariantItem(name="Apple Inc.", bucket="gleif_legal", kind="seed"),
        ]

        plan = NamePlan(ordered_variants=variants)

        # counts_by_bucket should be populated with the actual counts
        # The function counts by bucket, so orig should have 2, gleif_legal should have 1
        assert plan.counts_by_bucket["orig"] == 2
        assert plan.counts_by_bucket["gleif_legal"] == 1

    def test_name_plan_immutability(self):
        """Test that NamePlan is immutable."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)

        # NamePlan is a dataclass with frozen=True, so it should be immutable
        with pytest.raises(Exception):
            # Try to modify a field - this should raise an error
            plan.ordered_variants = []  # type: ignore

    def test_name_plan_equality(self):
        """Test NamePlan equality."""
        variants1 = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        variants2 = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        variants3 = [VariantItem(name="Microsoft", bucket="orig", kind="seed")]

        plan1 = NamePlan(ordered_variants=variants1)
        plan2 = NamePlan(ordered_variants=variants2)
        plan3 = NamePlan(ordered_variants=variants3)

        assert plan1 == plan2
        assert plan1 != plan3

    def test_name_plan_repr(self):
        """Test NamePlan string representation."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)
        repr_str = repr(plan)

        assert "NamePlan" in repr_str
        assert "ordered_variants=" in repr_str


class TestNamePlanResult:
    """Test the NamePlanResult dataclass."""

    def test_name_plan_result_creation(self):
        """Test creating NamePlanResult instances."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)

        result = NamePlanResult(plan=plan)

        assert result.plan == plan
        assert result.discovery == {}
        assert result.eq_counts == {}
        assert result.best_variant == ""
        assert result.best_bucket == ""
        assert result.best_total == 0
        assert result.trace == []

    def test_name_plan_result_with_data(self):
        """Test NamePlanResult with populated data."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)

        discovery = {"Apple Inc": ["Apple Inc", "Apple Computer Inc"]}
        eq_counts = {"Apple Inc": 150}

        result = NamePlanResult(
            plan=plan,
            discovery=discovery,
            eq_counts=eq_counts,
            best_variant="Apple Inc",
            best_bucket="orig",
            best_total=150,
            trace=[{"op": "discover", "seed": "Apple Inc"}],
        )

        assert result.discovery == discovery
        assert result.eq_counts == eq_counts
        assert result.best_variant == "Apple Inc"
        assert result.best_bucket == "orig"
        assert result.best_total == 150
        assert len(result.trace) == 1

    def test_name_plan_result_defaults(self):
        """Test NamePlanResult default values."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)

        result = NamePlanResult(plan=plan)

        assert result.discovery == {}
        assert result.eq_counts == {}
        assert result.best_variant == ""
        assert result.best_bucket == ""
        assert result.best_total == 0
        assert result.trace == []

    def test_name_plan_result_immutability(self):
        """Test that NamePlanResult is immutable."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)
        result = NamePlanResult(plan=plan)

        # NamePlanResult is a dataclass with frozen=True, so it should be immutable
        with pytest.raises(Exception):
            # Try to modify a field - this should raise an error
            result.best_total = 100  # type: ignore

    def test_name_plan_result_equality(self):
        """Test NamePlanResult equality."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)

        result1 = NamePlanResult(plan=plan, best_total=150)
        result2 = NamePlanResult(plan=plan, best_total=150)
        result3 = NamePlanResult(plan=plan, best_total=200)

        assert result1 == result2
        assert result1 != result3

    def test_name_plan_result_repr(self):
        """Test NamePlanResult string representation."""
        variants = [VariantItem(name="Apple Inc", bucket="orig", kind="seed")]
        plan = NamePlan(ordered_variants=variants)
        result = NamePlanResult(plan=plan, best_total=150)

        repr_str = repr(result)
        assert "NamePlanResult" in repr_str
        assert "best_total=150" in repr_str


class TestTypeIntegration:
    """Test integration between different types."""

    def test_variant_item_in_name_plan(self):
        """Test that VariantItem works correctly in NamePlan."""
        variants = [
            VariantItem(name="Apple Inc", bucket="orig", kind="seed"),
            VariantItem(name="Apple Inc.", bucket="gleif_legal", kind="seed"),
        ]

        plan = NamePlan(ordered_variants=variants)

        assert len(plan.ordered_variants) == 2
        assert all(isinstance(v, dict) for v in plan.ordered_variants)
        assert all("name" in v for v in plan.ordered_variants)
        assert all("bucket" in v for v in plan.ordered_variants)
        assert all("kind" in v for v in plan.ordered_variants)

    def test_bucket_values_in_variant_items(self):
        """Test that all bucket values can be used in VariantItem."""
        valid_buckets = [
            "orig",
            "gleif_legal",
            "gleif_other",
            "gleif_sub",
            "expand_orig",
            "expand_legal",
            "expand_other",
            "expand_sub",
        ]

        for bucket in valid_buckets:
            variant = VariantItem(name="Test", bucket=bucket, kind="seed")
            assert variant["bucket"] == bucket

    def test_discovery_options_in_runner_context(self):
        """Test that DiscoveryOptions can be used in runner context."""
        options = DiscoveryOptions(run_discovery=True, run_eq=False)

        # Should be able to access all fields
        assert options.run_discovery is True
        assert options.run_eq is False
        assert options.limit_discovery == 120
        assert options.utility_only is False

    def test_plan_options_in_runner_context(self):
        """Test that PlanOptions can be used in runner context."""
        options = PlanOptions(include_expansions=False, max_variants=5)

        # Should be able to access all fields
        assert options.include_expansions is False
        assert options.max_variants == 5
