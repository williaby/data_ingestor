"""
Baseline management and comparative analysis.

Manages versioned performance baselines and provides statistical
comparison tools for tracking performance across code changes.
"""

import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np
from scipy import stats

from data_ingestor.benchmarking.config_tester import ConfigurationResult
from data_ingestor.benchmarking.fingerprint import HardwareProfile, DatasetProfile

logger = logging.getLogger(__name__)


@dataclass
class Baseline:
    """
    Versioned performance baseline.

    Stores configuration test results along with hardware/dataset
    fingerprints for reproducible comparisons.

    Attributes:
        name: Baseline identifier
        version: Baseline version number
        hardware_profile: Hardware configuration
        dataset_profile: Dataset characteristics
        results: List of configuration test results
        created_at: Creation timestamp
        metadata: Additional metadata dictionary
    """

    name: str
    version: int
    hardware_profile: HardwareProfile
    dataset_profile: DatasetProfile
    results: List[ConfigurationResult]
    created_at: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "name": self.name,
            "version": self.version,
            "hardware_profile": self.hardware_profile.to_dict(),
            "dataset_profile": self.dataset_profile.to_dict(),
            "results": [r.to_dict() for r in self.results],
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Baseline":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            version=data["version"],
            hardware_profile=HardwareProfile.from_dict(data["hardware_profile"]),
            dataset_profile=DatasetProfile.from_dict(data["dataset_profile"]),
            results=[ConfigurationResult.from_dict(r) for r in data["results"]],
            created_at=data["created_at"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class ComparisonReport:
    """
    Statistical comparison between two baselines.

    Contains detailed metrics comparisons and statistical significance tests.
    """

    baseline1_name: str
    baseline1_version: int
    baseline2_name: str
    baseline2_version: int
    comparisons: List[Dict[str, Any]]
    statistical_tests: Dict[str, Any]
    summary: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ConfigurationRecommendation:
    """
    Configuration recommendation for a document type.

    Based on performance analysis, recommends optimal parser configuration.
    """

    document_type: str
    optimization_target: str  # "speed", "accuracy", "balanced"
    recommended_parser: str
    recommended_config: Dict[str, Any]
    expected_performance: Dict[str, float]
    confidence: float
    rationale: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class BaselineManager:
    """
    Manages versioned performance baselines.

    Stores baselines with automatic versioning and provides retrieval
    and comparison capabilities.

    Example:
        >>> manager = BaselineManager(Path("data/baselines"))
        >>> baseline = manager.create_baseline(
        ...     name="phase1d_initial",
        ...     hardware_profile=hw_profile,
        ...     dataset_profile=ds_profile,
        ...     results=config_results,
        ... )
        >>> loaded = manager.load_baseline("phase1d_initial", version=1)
    """

    def __init__(self, storage_path: Path):
        """
        Initialize baseline manager.

        Args:
            storage_path: Directory for baseline storage
        """
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        (self.storage_path / "baselines").mkdir(exist_ok=True)
        (self.storage_path / "hardware_profiles").mkdir(exist_ok=True)
        (self.storage_path / "dataset_profiles").mkdir(exist_ok=True)

        logger.info(f"Baseline manager initialized: {self.storage_path}")

    def create_baseline(
        self,
        name: str,
        hardware_profile: HardwareProfile,
        dataset_profile: DatasetProfile,
        results: List[ConfigurationResult],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Baseline:
        """
        Create new baseline with automatic versioning.

        Args:
            name: Baseline identifier
            hardware_profile: Hardware configuration
            dataset_profile: Dataset characteristics
            results: Configuration test results
            metadata: Optional additional metadata

        Returns:
            Created Baseline object
        """
        # Determine next version number
        version = self._get_next_version(name)

        baseline = Baseline(
            name=name,
            version=version,
            hardware_profile=hardware_profile,
            dataset_profile=dataset_profile,
            results=results,
            created_at=datetime.now().isoformat(),
            metadata=metadata or {},
        )

        # Save baseline
        self._save_baseline(baseline)

        # Save hardware and dataset profiles separately for reuse
        self._save_hardware_profile(hardware_profile)
        self._save_dataset_profile(dataset_profile)

        logger.info(f"Created baseline: {name} v{version}")
        return baseline

    def load_baseline(
        self,
        name: str,
        version: Optional[int] = None,
    ) -> Baseline:
        """
        Load baseline (latest or specific version).

        Args:
            name: Baseline identifier
            version: Specific version (None for latest)

        Returns:
            Loaded Baseline object

        Raises:
            FileNotFoundError: If baseline not found
        """
        if version is None:
            version = self._get_latest_version(name)
            if version is None:
                raise FileNotFoundError(f"No baselines found with name: {name}")

        baseline_path = self._get_baseline_path(name, version)

        if not baseline_path.exists():
            raise FileNotFoundError(f"Baseline not found: {name} v{version}")

        with open(baseline_path) as f:
            data = json.load(f)

        baseline = Baseline.from_dict(data)
        logger.info(f"Loaded baseline: {name} v{version}")
        return baseline

    def list_baselines(self) -> List[Dict[str, Any]]:
        """
        List all available baselines.

        Returns:
            List of baseline info dictionaries
        """
        baselines = []
        baseline_dir = self.storage_path / "baselines"

        for baseline_file in baseline_dir.glob("*.json"):
            try:
                with open(baseline_file) as f:
                    data = json.load(f)
                baselines.append({
                    "name": data["name"],
                    "version": data["version"],
                    "created_at": data["created_at"],
                    "num_results": len(data["results"]),
                })
            except Exception as e:
                logger.warning(f"Could not load baseline {baseline_file}: {e}")

        # Sort by name, then version
        baselines.sort(key=lambda x: (x["name"], x["version"]))
        return baselines

    def compare_baselines(
        self,
        baseline1: Baseline,
        baseline2: Baseline,
        significance_level: float = 0.05,
    ) -> ComparisonReport:
        """
        Compare two baselines with statistical tests.

        Args:
            baseline1: First baseline
            baseline2: Second baseline
            significance_level: p-value threshold for significance

        Returns:
            ComparisonReport with detailed comparison
        """
        logger.info(f"Comparing baselines: {baseline1.name} v{baseline1.version} vs {baseline2.name} v{baseline2.version}")

        # Compare each configuration that appears in both baselines
        comparisons = []

        for result1 in baseline1.results:
            # Find matching result in baseline2
            matching_result = None
            for result2 in baseline2.results:
                if (result1.parser_type == result2.parser_type and
                    result1.configuration_name == result2.configuration_name):
                    matching_result = result2
                    break

            if matching_result:
                comparison = self._compare_configuration_results(
                    result1,
                    matching_result,
                    significance_level,
                )
                comparisons.append(comparison)

        # Statistical tests across all configurations
        statistical_tests = self._run_global_statistical_tests(
            baseline1,
            baseline2,
            significance_level,
        )

        # Generate summary
        summary = self._generate_comparison_summary(comparisons, statistical_tests)

        report = ComparisonReport(
            baseline1_name=baseline1.name,
            baseline1_version=baseline1.version,
            baseline2_name=baseline2.name,
            baseline2_version=baseline2.version,
            comparisons=comparisons,
            statistical_tests=statistical_tests,
            summary=summary,
            timestamp=datetime.now().isoformat(),
        )

        logger.info("Baseline comparison complete")
        return report

    def find_compatible_baselines(
        self,
        hardware_profile: HardwareProfile,
        dataset_profile: DatasetProfile,
        tolerance: float = 0.2,
    ) -> List[Baseline]:
        """
        Find baselines with similar hardware and dataset.

        Args:
            hardware_profile: Hardware configuration to match
            dataset_profile: Dataset characteristics to match
            tolerance: Tolerance for matching (0.0-1.0)

        Returns:
            List of compatible baselines
        """
        compatible = []

        for baseline_info in self.list_baselines():
            try:
                baseline = self.load_baseline(
                    baseline_info["name"],
                    baseline_info["version"],
                )

                # Check hardware compatibility
                hw_compatible = self._check_hardware_compatibility(
                    hardware_profile,
                    baseline.hardware_profile,
                    tolerance,
                )

                # Check dataset compatibility
                ds_compatible = self._check_dataset_compatibility(
                    dataset_profile,
                    baseline.dataset_profile,
                    tolerance,
                )

                if hw_compatible and ds_compatible:
                    compatible.append(baseline)

            except Exception as e:
                logger.warning(f"Could not check compatibility for {baseline_info}: {e}")

        logger.info(f"Found {len(compatible)} compatible baselines")
        return compatible

    def _save_baseline(self, baseline: Baseline):
        """Save baseline to JSON file."""
        baseline_path = self._get_baseline_path(baseline.name, baseline.version)
        with open(baseline_path, "w") as f:
            json.dump(baseline.to_dict(), f, indent=2)

    def _save_hardware_profile(self, profile: HardwareProfile):
        """Save hardware profile for reuse."""
        profile_path = self.storage_path / "hardware_profiles" / f"{profile.fingerprint_hash}.json"
        with open(profile_path, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def _save_dataset_profile(self, profile: DatasetProfile):
        """Save dataset profile for reuse."""
        profile_path = self.storage_path / "dataset_profiles" / f"{profile.dataset_hash}.json"
        with open(profile_path, "w") as f:
            json.dump(profile.to_dict(), f, indent=2)

    def _get_baseline_path(self, name: str, version: int) -> Path:
        """Get path to baseline file."""
        return self.storage_path / "baselines" / f"{name}_v{version}.json"

    def _get_next_version(self, name: str) -> int:
        """Get next version number for baseline name."""
        latest = self._get_latest_version(name)
        return 1 if latest is None else latest + 1

    def _get_latest_version(self, name: str) -> Optional[int]:
        """Get latest version number for baseline name."""
        baseline_dir = self.storage_path / "baselines"
        versions = []

        for baseline_file in baseline_dir.glob(f"{name}_v*.json"):
            try:
                version_str = baseline_file.stem.split("_v")[-1]
                versions.append(int(version_str))
            except ValueError:
                continue

        return max(versions) if versions else None

    def _compare_configuration_results(
        self,
        result1: ConfigurationResult,
        result2: ConfigurationResult,
        significance_level: float,
    ) -> Dict[str, Any]:
        """
        Compare two configuration results statistically.

        Returns dictionary with comparison metrics and statistical tests.
        """
        agg1 = result1.aggregated_metrics
        agg2 = result2.aggregated_metrics

        # Calculate percentage changes
        time_change_pct = ((agg2["mean_total_time"] - agg1["mean_total_time"]) /
                           agg1["mean_total_time"] * 100) if agg1["mean_total_time"] > 0 else 0

        memory_change_pct = ((agg2["mean_peak_memory_mb"] - agg1["mean_peak_memory_mb"]) /
                             agg1["mean_peak_memory_mb"] * 100) if agg1["mean_peak_memory_mb"] > 0 else 0

        quality_change_pct = ((agg2["mean_quality_score"] - agg1["mean_quality_score"]) /
                              agg1["mean_quality_score"] * 100) if agg1["mean_quality_score"] > 0 else 0

        # Extract time measurements for t-test
        times1 = [d["metrics"]["total_time_seconds"] for d in result1.document_results
                  if d["metrics"]["success"]]
        times2 = [d["metrics"]["total_time_seconds"] for d in result2.document_results
                  if d["metrics"]["success"]]

        # Perform t-test if we have enough data
        t_test_result = None
        if len(times1) >= 2 and len(times2) >= 2:
            try:
                t_stat, p_value = stats.ttest_ind(times1, times2)
                t_test_result = {
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": p_value < significance_level,
                }
            except Exception as e:
                logger.debug(f"T-test failed: {e}")

        return {
            "configuration_name": result1.configuration_name,
            "parser_type": result1.parser_type,
            "baseline1_mean_time": agg1["mean_total_time"],
            "baseline2_mean_time": agg2["mean_total_time"],
            "time_change_pct": round(time_change_pct, 2),
            "baseline1_mean_memory": agg1["mean_peak_memory_mb"],
            "baseline2_mean_memory": agg2["mean_peak_memory_mb"],
            "memory_change_pct": round(memory_change_pct, 2),
            "baseline1_quality": agg1["mean_quality_score"],
            "baseline2_quality": agg2["mean_quality_score"],
            "quality_change_pct": round(quality_change_pct, 2),
            "t_test": t_test_result,
        }

    def _run_global_statistical_tests(
        self,
        baseline1: Baseline,
        baseline2: Baseline,
        significance_level: float,
    ) -> Dict[str, Any]:
        """Run statistical tests across all configurations."""
        # Collect all times from both baselines
        all_times1 = []
        all_times2 = []

        for result in baseline1.results:
            times = [d["metrics"]["total_time_seconds"] for d in result.document_results
                     if d["metrics"]["success"]]
            all_times1.extend(times)

        for result in baseline2.results:
            times = [d["metrics"]["total_time_seconds"] for d in result.document_results
                     if d["metrics"]["success"]]
            all_times2.extend(times)

        tests = {}

        # T-test for overall time difference
        if len(all_times1) >= 2 and len(all_times2) >= 2:
            try:
                t_stat, p_value = stats.ttest_ind(all_times1, all_times2)
                tests["overall_time_ttest"] = {
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "significant": p_value < significance_level,
                }
            except Exception as e:
                logger.debug(f"Overall t-test failed: {e}")

        return tests

    def _generate_comparison_summary(
        self,
        comparisons: List[Dict[str, Any]],
        statistical_tests: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate summary statistics for comparison."""
        if not comparisons:
            return {"note": "No comparable configurations found"}

        # Count improvements and regressions
        time_improvements = sum(1 for c in comparisons if c["time_change_pct"] < 0)
        time_regressions = sum(1 for c in comparisons if c["time_change_pct"] > 0)

        quality_improvements = sum(1 for c in comparisons if c["quality_change_pct"] > 0)
        quality_regressions = sum(1 for c in comparisons if c["quality_change_pct"] < 0)

        # Average changes
        avg_time_change = sum(c["time_change_pct"] for c in comparisons) / len(comparisons)
        avg_quality_change = sum(c["quality_change_pct"] for c in comparisons) / len(comparisons)

        return {
            "total_comparisons": len(comparisons),
            "time_improvements": time_improvements,
            "time_regressions": time_regressions,
            "quality_improvements": quality_improvements,
            "quality_regressions": quality_regressions,
            "avg_time_change_pct": round(avg_time_change, 2),
            "avg_quality_change_pct": round(avg_quality_change, 2),
        }

    def _check_hardware_compatibility(
        self,
        profile1: HardwareProfile,
        profile2: HardwareProfile,
        tolerance: float,
    ) -> bool:
        """Check if two hardware profiles are compatible within tolerance."""
        # Simple check: same GPU presence and similar CPU cores
        gpu_match = (profile1.gpu_model is None) == (profile2.gpu_model is None)

        cpu_diff = abs(profile1.cpu_cores - profile2.cpu_cores) / max(profile1.cpu_cores, profile2.cpu_cores)
        cpu_match = cpu_diff <= tolerance

        return gpu_match and cpu_match

    def _check_dataset_compatibility(
        self,
        profile1: DatasetProfile,
        profile2: DatasetProfile,
        tolerance: float,
    ) -> bool:
        """Check if two dataset profiles are compatible within tolerance."""
        # Check document count similarity
        count_diff = abs(profile1.total_documents - profile2.total_documents) / max(profile1.total_documents, profile2.total_documents)

        return count_diff <= tolerance


class ComparativeAnalyzer:
    """
    Performs comparative analysis and generates recommendations.

    Analyzes configuration test results to identify optimal configurations
    for different document types and optimization targets.
    """

    def __init__(self):
        """Initialize comparative analyzer."""
        logger.info("Comparative analyzer initialized")

    def analyze_results(
        self,
        results: List[ConfigurationResult],
    ) -> Dict[str, Any]:
        """
        Perform statistical analysis on configuration results.

        Args:
            results: List of configuration test results

        Returns:
            Analysis report dictionary
        """
        if not results:
            return {"error": "No results to analyze"}

        # Speed vs accuracy trade-offs
        trade_offs = self._analyze_tradeoffs(results)

        # Best configurations by metric
        best_configs = self._find_best_configurations(results)

        # Statistical significance tests
        significance = self._test_significance(results)

        return {
            "trade_offs": trade_offs,
            "best_configurations": best_configs,
            "statistical_significance": significance,
            "timestamp": datetime.now().isoformat(),
        }

    def recommend_configuration(
        self,
        results: List[ConfigurationResult],
        document_type: str,
        optimization_target: str = "balanced",
    ) -> ConfigurationRecommendation:
        """
        Recommend optimal configuration for document type.

        Args:
            results: Configuration test results
            document_type: Document type ("digital", "scanned", "hybrid")
            optimization_target: Optimization goal ("speed", "accuracy", "balanced")

        Returns:
            ConfigurationRecommendation
        """
        logger.info(f"Generating recommendation for {document_type} documents, target: {optimization_target}")

        # Filter results relevant to document type
        # #ASSUME: For Phase 1, use all results (document type filtering in Phase 2)

        # Score configurations based on optimization target
        scored_configs = []

        for result in results:
            agg = result.aggregated_metrics

            if optimization_target == "speed":
                # Prioritize speed
                score = 1.0 / (agg["mean_total_time"] + 0.1)  # Avoid division by zero
            elif optimization_target == "accuracy":
                # Prioritize quality
                score = agg.get("mean_quality_score", 0.5)
            else:  # balanced
                # Balance speed and quality
                time_score = 1.0 / (agg["mean_total_time"] + 0.1)
                quality_score = agg.get("mean_quality_score", 0.5)
                score = (time_score * quality_score) ** 0.5  # Geometric mean

            scored_configs.append({
                "result": result,
                "score": score,
            })

        # Sort by score
        scored_configs.sort(key=lambda x: x["score"], reverse=True)

        if not scored_configs:
            raise ValueError("No configurations to recommend")

        # Best configuration
        best = scored_configs[0]
        result = best["result"]
        agg = result.aggregated_metrics

        # Calculate confidence based on success rate and sample size
        confidence = agg["success_rate"] * min(1.0, agg["total_documents"] / 100.0)

        # Generate rationale
        rationale = f"{result.parser_type} with {result.configuration_name} "
        rationale += f"achieves {agg['mean_total_time']:.2f}s avg processing time "

        if agg.get("mean_quality_score"):
            rationale += f"with {agg['mean_quality_score']:.2f} quality score"

        return ConfigurationRecommendation(
            document_type=document_type,
            optimization_target=optimization_target,
            recommended_parser=result.parser_type,
            recommended_config=result.configuration,
            expected_performance={
                "mean_time": agg["mean_total_time"],
                "mean_quality": agg.get("mean_quality_score", 0.0),
                "success_rate": agg["success_rate"],
            },
            confidence=round(confidence, 2),
            rationale=rationale,
        )

    def _analyze_tradeoffs(self, results: List[ConfigurationResult]) -> Dict[str, Any]:
        """Analyze speed vs accuracy trade-offs."""
        trade_offs = []

        for result in results:
            agg = result.aggregated_metrics
            trade_offs.append({
                "configuration": result.configuration_name,
                "parser": result.parser_type,
                "speed": agg["mean_total_time"],
                "quality": agg.get("mean_quality_score", 0.0),
                "memory": agg["mean_peak_memory_mb"],
            })

        return {"points": trade_offs}

    def _find_best_configurations(self, results: List[ConfigurationResult]) -> Dict[str, Any]:
        """Find best configurations by different metrics."""
        best = {}

        # Fastest
        fastest = min(results, key=lambda r: r.aggregated_metrics["mean_total_time"])
        best["fastest"] = {
            "configuration": fastest.configuration_name,
            "parser": fastest.parser_type,
            "time": fastest.aggregated_metrics["mean_total_time"],
        }

        # Most accurate (if quality scores available)
        configs_with_quality = [r for r in results if r.aggregated_metrics.get("mean_quality_score", 0) > 0]
        if configs_with_quality:
            most_accurate = max(configs_with_quality, key=lambda r: r.aggregated_metrics["mean_quality_score"])
            best["most_accurate"] = {
                "configuration": most_accurate.configuration_name,
                "parser": most_accurate.parser_type,
                "quality": most_accurate.aggregated_metrics["mean_quality_score"],
            }

        # Most memory efficient
        most_efficient = min(results, key=lambda r: r.aggregated_metrics["mean_peak_memory_mb"])
        best["most_memory_efficient"] = {
            "configuration": most_efficient.configuration_name,
            "parser": most_efficient.parser_type,
            "memory": most_efficient.aggregated_metrics["mean_peak_memory_mb"],
        }

        return best

    def _test_significance(self, results: List[ConfigurationResult]) -> Dict[str, Any]:
        """Test statistical significance between configurations."""
        # #TODO: Implement pairwise comparisons with Bonferroni correction
        return {"note": "Statistical significance testing to be implemented in Phase 2"}
