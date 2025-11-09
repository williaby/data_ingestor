"""
Hardware and dataset fingerprinting for baseline tracking.

Captures hardware characteristics (CPU, GPU, RAM) and dataset properties
(document types, sizes, complexity) to enable reproducible benchmarking
and performance tracking across different environments.
"""

import hashlib
import logging
import platform
import psutil
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class HardwareProfile:
    """
    Hardware configuration profile.

    Captures system characteristics to ensure comparable baseline measurements
    across different environments.

    Attributes:
        cpu_model: CPU model name
        cpu_cores: Number of physical CPU cores
        cpu_threads: Number of logical CPU threads
        cpu_frequency_mhz: Maximum CPU frequency in MHz
        gpu_model: GPU model name (None if no GPU)
        gpu_memory_gb: GPU memory in GB (None if no GPU)
        cuda_version: CUDA version string (None if no CUDA)
        ram_total_gb: Total system RAM in GB
        ram_available_gb: Available RAM at capture time
        storage_type: Storage type (SSD, HDD, NVMe)
        os_info: Operating system information
        python_version: Python version string
        fingerprint_hash: Unique hash for this hardware configuration
        timestamp: When this profile was captured
    """

    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    cpu_frequency_mhz: float
    gpu_model: Optional[str]
    gpu_memory_gb: Optional[float]
    cuda_version: Optional[str]
    ram_total_gb: float
    ram_available_gb: float
    storage_type: str
    os_info: str
    python_version: str
    fingerprint_hash: str
    timestamp: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "HardwareProfile":
        """Create from dictionary."""
        return cls(**data)


@dataclass
class DocumentCharacteristics:
    """
    Characteristics of a single document.

    Used for document classification and routing optimization.

    Attributes:
        doc_id: Document identifier
        file_size_mb: File size in megabytes
        page_count: Number of pages (for PDFs)
        document_type: Classification (digital, scanned, hybrid)
        complexity_score: Estimated processing complexity (0.0-1.0)
        has_tables: Whether document contains tables
        has_images: Whether document contains images
        language: Primary language (if detectable)
    """

    doc_id: str
    file_size_mb: float
    page_count: Optional[int]
    document_type: str  # "digital", "scanned", "hybrid", "unknown"
    complexity_score: float
    has_tables: bool
    has_images: bool
    language: Optional[str]

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class DatasetProfile:
    """
    Dataset characteristics profile.

    Summarizes document collection properties for baseline comparison.

    Attributes:
        total_documents: Total number of documents
        total_size_gb: Total dataset size in GB
        size_distribution: Distribution by size (small, medium, large)
        type_distribution: Distribution by type (digital, scanned, hybrid)
        page_distribution: Page count statistics
        complexity_stats: Complexity score statistics
        avg_file_size_mb: Average file size
        median_file_size_mb: Median file size
        language_distribution: Distribution by language
        dataset_hash: Unique hash for this dataset
        timestamp: When this profile was created
    """

    total_documents: int
    total_size_gb: float
    size_distribution: Dict[str, int]  # small, medium, large
    type_distribution: Dict[str, int]  # digital, scanned, hybrid
    page_distribution: Dict[str, float]  # mean, median, p95
    complexity_stats: Dict[str, float]  # mean, median, p95
    avg_file_size_mb: float
    median_file_size_mb: float
    language_distribution: Dict[str, int]
    dataset_hash: str
    timestamp: str

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "DatasetProfile":
        """Create from dictionary."""
        return cls(**data)


class HardwareFingerprint:
    """
    Hardware fingerprinting utility.

    Captures current hardware configuration for baseline tracking
    and performance comparison across environments.
    """

    @staticmethod
    def capture() -> HardwareProfile:
        """
        Capture current hardware configuration.

        Returns:
            HardwareProfile with current system characteristics

        Example:
            >>> profile = HardwareFingerprint.capture()
            >>> print(f"CPU: {profile.cpu_model}, RAM: {profile.ram_total_gb}GB")
        """
        logger.info("Capturing hardware profile...")

        # CPU information
        cpu_model = platform.processor() or "Unknown"
        cpu_cores = psutil.cpu_count(logical=False) or 1
        cpu_threads = psutil.cpu_count(logical=True) or 1

        # CPU frequency
        try:
            cpu_freq = psutil.cpu_freq()
            cpu_frequency = cpu_freq.max if cpu_freq else 0.0
        except Exception:
            cpu_frequency = 0.0

        # RAM information
        mem = psutil.virtual_memory()
        ram_total_gb = mem.total / (1024**3)
        ram_available_gb = mem.available / (1024**3)

        # GPU information (requires additional libraries)
        gpu_model, gpu_memory_gb, cuda_version = HardwareFingerprint._get_gpu_info()

        # Storage type (estimate based on disk stats)
        storage_type = HardwareFingerprint._estimate_storage_type()

        # OS information
        os_info = f"{platform.system()} {platform.release()} ({platform.machine()})"

        # Python version
        python_version = platform.python_version()

        # Generate fingerprint hash
        fingerprint_data = {
            "cpu_model": cpu_model,
            "cpu_cores": cpu_cores,
            "gpu_model": gpu_model or "none",
            "ram_total_gb": round(ram_total_gb, 1),
        }
        fingerprint_hash = HardwareFingerprint._generate_hash(fingerprint_data)

        profile = HardwareProfile(
            cpu_model=cpu_model,
            cpu_cores=cpu_cores,
            cpu_threads=cpu_threads,
            cpu_frequency_mhz=cpu_frequency,
            gpu_model=gpu_model,
            gpu_memory_gb=gpu_memory_gb,
            cuda_version=cuda_version,
            ram_total_gb=round(ram_total_gb, 2),
            ram_available_gb=round(ram_available_gb, 2),
            storage_type=storage_type,
            os_info=os_info,
            python_version=python_version,
            fingerprint_hash=fingerprint_hash,
            timestamp=datetime.now().isoformat(),
        )

        logger.info(f"Hardware profile captured: {fingerprint_hash}")
        logger.info(f"  CPU: {cpu_model} ({cpu_cores} cores)")
        logger.info(f"  RAM: {ram_total_gb:.1f} GB")
        logger.info(f"  GPU: {gpu_model or 'None'}")

        return profile

    @staticmethod
    def _get_gpu_info() -> tuple[Optional[str], Optional[float], Optional[str]]:
        """
        Get GPU information if available.

        Returns:
            Tuple of (gpu_model, gpu_memory_gb, cuda_version)
        """
        # #EDGE: GPU detection may fail on systems without GPU libraries
        # #VERIFY: Graceful fallback to None values

        try:
            import torch

            if torch.cuda.is_available():
                gpu_model = torch.cuda.get_device_name(0)
                gpu_memory_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                cuda_version = torch.version.cuda
                return gpu_model, round(gpu_memory_gb, 2), cuda_version
        except ImportError:
            logger.debug("PyTorch not available, skipping GPU detection")
        except Exception as e:
            logger.debug(f"GPU detection failed: {e}")

        return None, None, None

    @staticmethod
    def _estimate_storage_type() -> str:
        """
        Estimate storage type based on disk characteristics.

        Returns:
            Storage type string ("SSD", "HDD", "NVMe", "Unknown")
        """
        # #ASSUME: Storage type estimation may not be accurate
        # #EDGE: May require platform-specific detection methods

        try:
            # Check if /proc/diskstats exists (Linux)
            if platform.system() == "Linux" and Path("/sys/block").exists():
                # Check for rotational disk (0 = SSD, 1 = HDD)
                for disk in Path("/sys/block").iterdir():
                    rotational_file = disk / "queue" / "rotational"
                    if rotational_file.exists():
                        rotational = rotational_file.read_text().strip()
                        if rotational == "0":
                            # Check if NVMe
                            if "nvme" in str(disk):
                                return "NVMe"
                            return "SSD"
                        else:
                            return "HDD"
        except Exception as e:
            logger.debug(f"Storage type detection failed: {e}")

        return "Unknown"

    @staticmethod
    def _generate_hash(data: Dict) -> str:
        """
        Generate stable hash for hardware configuration.

        Args:
            data: Configuration data to hash

        Returns:
            Hex string hash
        """
        # Sort keys for stable hashing
        sorted_data = {k: data[k] for k in sorted(data.keys())}
        hash_input = str(sorted_data).encode()
        return hashlib.sha256(hash_input).hexdigest()[:16]


class DatasetFingerprint:
    """
    Dataset fingerprinting utility.

    Analyzes document collections to characterize dataset properties
    for baseline comparison and routing optimization.
    """

    @staticmethod
    def analyze_dataset(
        documents: List[Path],
        sample_size: Optional[int] = None,
    ) -> DatasetProfile:
        """
        Analyze document collection and create profile.

        Args:
            documents: List of document file paths
            sample_size: Optionally sample N documents for analysis

        Returns:
            DatasetProfile with collection characteristics

        Example:
            >>> docs = list(Path("data/benchmarks").glob("*.pdf"))
            >>> profile = DatasetFingerprint.analyze_dataset(docs)
            >>> print(f"Dataset: {profile.total_documents} docs, {profile.total_size_gb:.2f} GB")
        """
        logger.info(f"Analyzing dataset: {len(documents)} documents")

        # Sample if requested
        if sample_size and sample_size < len(documents):
            import random
            documents = random.sample(documents, sample_size)
            logger.info(f"  Sampled {sample_size} documents for analysis")

        # Analyze each document
        doc_characteristics = []
        for doc_path in documents:
            try:
                char = DatasetFingerprint.classify_document(doc_path)
                doc_characteristics.append(char)
            except Exception as e:
                logger.warning(f"Failed to analyze {doc_path}: {e}")

        if not doc_characteristics:
            raise ValueError("No documents could be analyzed")

        # Calculate statistics
        total_documents = len(doc_characteristics)
        file_sizes = [c.file_size_mb for c in doc_characteristics]
        page_counts = [c.page_count for c in doc_characteristics if c.page_count is not None]
        complexity_scores = [c.complexity_score for c in doc_characteristics]

        total_size_gb = sum(file_sizes) / 1024
        avg_file_size_mb = sum(file_sizes) / len(file_sizes)
        median_file_size_mb = sorted(file_sizes)[len(file_sizes) // 2]

        # Size distribution (small < 1MB, medium 1-10MB, large > 10MB)
        size_distribution = {
            "small": sum(1 for s in file_sizes if s < 1.0),
            "medium": sum(1 for s in file_sizes if 1.0 <= s < 10.0),
            "large": sum(1 for s in file_sizes if s >= 10.0),
        }

        # Type distribution
        type_distribution = {}
        for char in doc_characteristics:
            doc_type = char.document_type
            type_distribution[doc_type] = type_distribution.get(doc_type, 0) + 1

        # Page distribution
        if page_counts:
            page_distribution = {
                "mean": sum(page_counts) / len(page_counts),
                "median": sorted(page_counts)[len(page_counts) // 2],
                "p95": sorted(page_counts)[int(len(page_counts) * 0.95)] if len(page_counts) > 20 else max(page_counts),
            }
        else:
            page_distribution = {"mean": 0.0, "median": 0.0, "p95": 0.0}

        # Complexity distribution
        complexity_stats = {
            "mean": sum(complexity_scores) / len(complexity_scores),
            "median": sorted(complexity_scores)[len(complexity_scores) // 2],
            "p95": sorted(complexity_scores)[int(len(complexity_scores) * 0.95)] if len(complexity_scores) > 20 else max(complexity_scores),
        }

        # Language distribution
        language_distribution = {}
        for char in doc_characteristics:
            lang = char.language or "unknown"
            language_distribution[lang] = language_distribution.get(lang, 0) + 1

        # Generate dataset hash
        dataset_hash = DatasetFingerprint._generate_dataset_hash(doc_characteristics)

        profile = DatasetProfile(
            total_documents=total_documents,
            total_size_gb=round(total_size_gb, 2),
            size_distribution=size_distribution,
            type_distribution=type_distribution,
            page_distribution=page_distribution,
            complexity_stats=complexity_stats,
            avg_file_size_mb=round(avg_file_size_mb, 2),
            median_file_size_mb=round(median_file_size_mb, 2),
            language_distribution=language_distribution,
            dataset_hash=dataset_hash,
            timestamp=datetime.now().isoformat(),
        )

        logger.info(f"Dataset profile created: {dataset_hash}")
        logger.info(f"  {total_documents} documents, {total_size_gb:.2f} GB")
        logger.info(f"  Types: {type_distribution}")

        return profile

    @staticmethod
    def classify_document(doc_path: Path) -> DocumentCharacteristics:
        """
        Classify single document characteristics.

        Args:
            doc_path: Path to document file

        Returns:
            DocumentCharacteristics for this document
        """
        # #ASSUME: Basic file-based classification is sufficient for Phase 1
        # #TODO: Phase 2 could add content-based classification

        doc_id = doc_path.stem
        file_size_mb = doc_path.stat().st_size / (1024**2)

        # Initialize with defaults
        page_count = None
        document_type = "unknown"
        complexity_score = 0.5  # Default medium complexity
        has_tables = False
        has_images = False
        language = None

        # Try to get PDF-specific information
        if doc_path.suffix.lower() == ".pdf":
            try:
                import pymupdf

                doc = pymupdf.open(doc_path)
                page_count = len(doc)

                # Estimate document type based on text extraction
                # Sample first few pages
                sample_pages = min(3, page_count)
                total_text_len = 0
                total_image_count = 0

                for page_num in range(sample_pages):
                    page = doc[page_num]
                    text = page.get_text()
                    total_text_len += len(text)

                    # Check for images
                    images = page.get_images()
                    total_image_count += len(images)

                avg_text_per_page = total_text_len / sample_pages if sample_pages > 0 else 0

                # Classify document type
                if avg_text_per_page > 500:
                    document_type = "digital"
                    complexity_score = 0.3
                elif avg_text_per_page > 100:
                    document_type = "hybrid"
                    complexity_score = 0.6
                else:
                    document_type = "scanned"
                    complexity_score = 0.9

                has_images = total_image_count > 0

                # Rough table detection (simplified)
                # #ASSUME: Tables indicated by many short text blocks
                # #TODO: Proper table detection in Phase 2

                doc.close()

            except Exception as e:
                logger.debug(f"Could not analyze PDF {doc_path}: {e}")

        return DocumentCharacteristics(
            doc_id=doc_id,
            file_size_mb=round(file_size_mb, 2),
            page_count=page_count,
            document_type=document_type,
            complexity_score=round(complexity_score, 2),
            has_tables=has_tables,
            has_images=has_images,
            language=language,
        )

    @staticmethod
    def _generate_dataset_hash(characteristics: List[DocumentCharacteristics]) -> str:
        """
        Generate stable hash for dataset.

        Args:
            characteristics: List of document characteristics

        Returns:
            Hex string hash
        """
        # Use sorted doc IDs and total count for hash
        doc_ids = sorted([c.doc_id for c in characteristics])
        hash_input = f"{len(doc_ids)}:{':'.join(doc_ids[:100])}".encode()  # First 100 docs
        return hashlib.sha256(hash_input).hexdigest()[:16]
