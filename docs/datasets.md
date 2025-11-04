version: 1
generated: 2025-11-03
maintainer: "Byron Williams"
notes: >
  Dataset metadata below is intentionally conservative on licensing. Confirm each dataset's
  license/version before redistribution. For large corpora, sample_size is a practical starter cut.

categories:
  - id: layout-reading-order
    name: General PDF layout & reading order
  - id: tables
    name: Tables (detection, structure, functional roles)
  - id: forms-semi-structured
    name: Forms, invoices, semi-structured business docs
  - id: classification-heterogeneous
    name: Document variety & classification stress tests
  - id: spreadsheets
    name: Spreadsheets (XLS/XLSX) for parser robustness
  - id: mixed-filetypes
    name: Mixed file types for parser coverage & robustness
  - id: end-to-end-eval
    name: End-to-end PDF→Markdown/HTML evaluators
  - id: rag-evaluation
    name: RAG pipeline evaluation with QA pairs
  - id: quality-assessment
    name: Document quality and OCR accuracy assessment

datasets:

  # ========================================
  # INITIAL BENCHMARKING RECOMMENDATION
  # ========================================
  # For initial PDF benchmarking analysis, use this prioritized sequence:
  #
  # PHASE 1 - CORE VALIDATION (Week 1-2):
  #   1. readoc (500 samples) - Best proxy for RAG pipeline needs
  #   2. doclaynet (1000 samples) - Layout/reading order baseline
  #   3. pubtables-1m (500 samples) - Table extraction validation
  #
  # PHASE 2 - RAG-SPECIFIC (Week 2-3):
  #   4. ragbench (1000 samples) - Industry-specific RAG validation
  #   5. open-rag-benchmark (200 samples) - Multimodal RAG testing
  #
  # PHASE 3 - COVERAGE & EDGE CASES (Week 3-4):
  #   6. docile (500 samples) - Semi-structured forms
  #   7. rvl-cdip (2000 samples) - Document variety stress test
  #
  # RATIONALE: This sequence validates core extraction → RAG use cases → edge cases,
  # providing comprehensive coverage while managing evaluation overhead.
  # ========================================

  # 1) Layout & reading order
  - id: doclaynet
    name: "DocLayNet"
    category: layout-reading-order
    priority: high
    modalities: ["pdf"]
    formats: ["COCO/JSON annotations", "PDF"]
    license: "CC BY 4.0 (verify specific release)"
    source_url: "https://github.com/DS4SD/DocLayNet"
    huggingface_url: "https://huggingface.co/datasets/ds4sd/DocLayNet"
    citation: "DocLayNet: A Large Human-Annotated Document Layout Dataset (2023)"
    size: "80,863 pages (train: 69,375 | val: 6,489 | test: 4,999)"
    recommended_split:
      sample_size: 1000
      rationale: "Representative page diversity for layout/reading-order checks; human-annotated quality"
    use_cases:
      - "Block segmentation (11 classes: text, title, list, table, figure, etc.)"
      - "Reading-order accuracy"
      - "Financial reports, manuals, patents, scientific papers"
    primary_metrics:
      - "mAP (layout classes)"
      - "Reading-order sequence F1 / Kendall tau"
    notes: "Non-scientific, realistic office/administrative content; strong human labels. Includes digital text extraction."

  - id: publaynet
    name: "PubLayNet"
    category: layout-reading-order
    priority: medium
    modalities: ["pdf"]
    formats: ["PDF", "JSON annotations"]
    license: "PMC OA-derived; research use terms—verify"
    source_url: "https://github.com/ibm-aur-nlp/PubLayNet"
    citation: "PubLayNet: Largest Dataset for Document Layout Analysis (2019)"
    size: "360,000+ document images"
    recommended_split:
      sample_size: 5000
      rationale: "High-scale layout detection; academic paper bias"
    use_cases:
      - "High-scale layout detection; complex academic layouts"
      - "5 classes: text, title, list, table, figure"
    primary_metrics: ["mAP (layout classes)"]
    notes: "Labels auto-aligned from XML; great scale, academic bias. Good for training, less ideal for validation due to noise."

  - id: docbank
    name: "DocBank"
    category: layout-reading-order
    priority: medium
    modalities: ["pdf"]
    formats: ["PDF", "Token-level annotations"]
    license: "Apache-2.0"
    source_url: "https://github.com/doc-analysis/DocBank"
    paper_url: "https://arxiv.org/abs/2006.01038"
    citation: "DocBank: A Benchmark Dataset for Document Layout Analysis (COLING 2020)"
    size: "500K pages (train: 400K | val: 50K | test: 50K)"
    recommended_split:
      sample_size: 5000
      rationale: "Token-level granularity useful for fine-grained extraction"
    use_cases:
      - "Token-level structure & reading-order (12 semantic units)"
      - "Abstract, author, caption, equation, figure, footer, list, paragraph, section, table, title"
    primary_metrics: ["Token classification F1", "Order accuracy"]
    notes: "LaTeX-derived alignment provides fine-grained supervision. Good for academic documents."

  - id: readoc
    name: "ReadOC"
    category: layout-reading-order
    priority: critical
    modalities: ["pdf"]
    formats: ["PDF", "Markdown ground truth"]
    license: "Open for research; check repo"
    source_url: "https://github.com/readoc-benchmark/readoc"
    citation: "ReadOC: A Benchmark for PDF-to-Markdown Structure Fidelity"
    recommended_split:
      sample_size: 500
      rationale: "BEST proxy for RAG chunk quality - pairs PDFs with Markdown"
    use_cases:
      - "End-to-end PDF→Markdown structure fidelity close to RAG needs"
      - "Section/heading hierarchy preservation"
      - "List and code block extraction"
      - "Table-to-markdown conversion"
    primary_metrics:
      - "Section/list/code/table scoring suite (project-provided)"
      - "Text fidelity (BLEU/chrF/CER)"
      - "Structure preservation scores"
    notes: "Pairs real PDFs with MD; excellent proxy for chunk/section correctness. RECOMMENDED FOR INITIAL VALIDATION."

  - id: omnidocbench
    name: "OmniDocBench"
    category: quality-assessment
    priority: high
    modalities: ["pdf"]
    formats: ["PDF", "Bounding boxes", "OCR annotations", "Formula annotations"]
    license: "Research use; verify (CVPR 2025)"
    source_url: "https://github.com/opendatalab/OmniDocBench"
    citation: "OmniDocBench: A Comprehensive Benchmark for Document Parsing and Evaluation (CVPR 2025)"
    recommended_split:
      sample_size: 2000
      rationale: "Comprehensive modern benchmark with OCR and formula support"
    use_cases:
      - "OCR text recognition evaluation (block-level and span-level)"
      - "Formula recognition (display and inline equations)"
      - "Comprehensive document parsing assessment"
    primary_metrics: ["Edit distance", "BLEU", "METEOR", "CDM (formula-specific)"]
    notes: "Block-level and span-level annotations; strong for OCR and formula extraction validation. Very recent (2025)."

  # 2) Tables
  - id: pubtables-1m
    name: "PubTables-1M"
    category: tables
    priority: critical
    modalities: ["pdf"]
    formats: ["PDF", "Table structure annotations"]
    license: "Research use; verify"
    source_url: "https://github.com/microsoft/table-transformer"
    citation: "PubTables-1M: Towards Comprehensive Table Recognition (2021)"
    size: "1 million+ tables"
    recommended_split:
      sample_size: 500
      rationale: "Gold standard for table structure - detection + grid + spans"
    use_cases:
      - "Table detection + structure (grid, spans, merged cells)"
      - "Row/column identification"
      - "Header vs. data cell classification"
    primary_metrics: ["TEDS (tree edit distance)", "Cell exact match", "Header role F1"]
    notes: "Careful with over-segmentation; strong for structure metrics. RECOMMENDED FOR TABLE VALIDATION."

  - id: fintabnet
    name: "FinTabNet"
    category: tables
    priority: medium
    modalities: ["pdf", "html"]
    formats: ["PDF↔HTML table alignments"]
    license: "Research use; verify"
    source_url: "https://developer.ibm.com/exchanges/data/all/fintabnet/"
    citation: "FinTabNet: Financial Table Dataset (2020)"
    size: "112,000+ tables"
    recommended_split:
      sample_size: 2000
      rationale: "Financial domain tables with functional roles"
    use_cases:
      - "Financial table structure & functional roles"
      - "Header/stub identification"
      - "Complex spanning cells"
    primary_metrics: ["TEDS", "Header/Stub role F1"]
    notes: "Some label issues reported; test subset is more reliable. Good for financial documents."

  - id: tablebank
    name: "TableBank"
    category: tables
    priority: medium
    modalities: ["docx", "latex", "pdf (derived)"]
    formats: ["Images/PDF with table boxes", "Annotations"]
    license: "Apache-2.0"
    source_url: "https://github.com/doc-analysis/TableBank"
    citation: "TableBank: A Benchmark Dataset for Table Detection and Recognition (LREC 2020)"
    size: "417,234 tables"
    recommended_split:
      sample_size: 3000
      rationale: "Complements PubTables with Word/LaTeX sources"
    use_cases:
      - "Table detection across Word & LaTeX sources"
      - "Simple table boundaries"
    primary_metrics: ["mAP (table class)", "Detection F1"]
    notes: "Useful for DOCX-origin tables; complements PubTables/FinTabNet. Good coverage."

  - id: icdar2013-tables
    name: "ICDAR 2013 Table Competition"
    category: tables
    priority: low
    modalities: ["pdf"]
    formats: ["PDF", "Ground-truth table structure"]
    license: "Competition terms; verify redistribution"
    source_url: "https://www.primaresearch.org/datasets/Table_Competition"
    citation: "ICDAR 2013 Table Competition Dataset"
    size: "238 pages"
    recommended_split:
      sample_size: 200
      rationale: "Small classic benchmark for regression testing"
    use_cases:
      - "Small, hand-curated sanity checks for PDF→HTML table fidelity"
    primary_metrics: ["TEDS", "Cell content/structure exact match"]
    notes: "Classic benchmark; good as a regression test suite. Small but high quality."

  # 3) Forms / Semi-structured
  - id: docile
    name: "DocILE (KILE/LIR)"
    category: forms-semi-structured
    priority: high
    modalities: ["pdf", "image"]
    formats: ["PDF/Images", "Key-value labels", "Line-item labels"]
    license: "Research/competition terms; verify"
    source_url: "https://docile.rossum.ai/"
    citation: "DocILE: Document Information Localization and Extraction Benchmark (2023)"
    size: "6,678 documents"
    recommended_split:
      sample_size: 1000
      rationale: "Invoices and orders - critical for business documents"
    use_cases:
      - "Invoices/orders: key-value and line-item extraction"
      - "Semi-structured business document parsing"
      - "Spatial layout understanding"
    primary_metrics: ["KILE F1 (key information localization)", "LIR F1 (line item recognition)", "AP (average precision)"]
    notes: "Includes synthetic & real docs; public eval server available. RECOMMENDED FOR SEMI-STRUCTURED DOCS."

  - id: funsd
    name: "FUNSD"
    category: forms-semi-structured
    priority: medium
    modalities: ["scan", "pdf"]
    formats: ["Scanned forms", "Key-value/entity labels"]
    license: "Research use; verify"
    source_url: "https://guillaumejaume.github.io/FUNSD/"
    citation: "FUNSD: Form Understanding in Noisy Scanned Documents (ICDAR 2019)"
    size: "199 forms"
    recommended_split:
      sample_size: 199
      rationale: "Small but widely-used baseline for form understanding"
    use_cases:
      - "Form key-value extraction; classic baseline"
      - "Noisy scanned document handling"
    primary_metrics: ["Entity F1", "Relation F1"]
    notes: "Small but widely used; pairs well with DocILE. Good baseline comparison."

  - id: xfund
    name: "XFUND (multilingual FUNSD)"
    category: forms-semi-structured
    priority: low
    modalities: ["scan", "pdf"]
    formats: ["Scanned forms", "Multilingual labels"]
    license: "Research use; verify"
    source_url: "https://github.com/doc-analysis/XFUND"
    citation: "XFUND: A Benchmark for Multilingual Form Understanding (2021)"
    size: "1,393 forms across 7 languages"
    recommended_split:
      sample_size: 500
      rationale: "Multilingual validation if needed"
    use_cases:
      - "Multilingual key-value extraction (Chinese, Japanese, Spanish, French, Italian, German, Portuguese)"
    primary_metrics: ["Entity F1", "Relation F1"]
    notes: "Useful for non-English pipelines. Use only if multilingual support is required."

  # 4) Classification / heterogeneity
  - id: rvl-cdip
    name: "RVL-CDIP"
    category: classification-heterogeneous
    priority: high
    modalities: ["scan", "pdf (derived)"]
    formats: ["Images", "Class labels (16 types)"]
    license: "Research use; special access—verify"
    source_url: "https://adamharley.com/rvl-cdip/"
    citation: "RVL-CDIP: Large-Scale Document Classification (2015)"
    size: "400,000 grayscale images (16 classes)"
    recommended_split:
      sample_size: 2000
      rationale: "Variety stress test - 16 document types"
    use_cases:
      - "Variety stress test across forms, letters, invoices, memos, scientific papers, etc."
      - "Document type classification"
      - "Parser robustness across diverse layouts"
    primary_metrics: ["Top-1 accuracy", "Per-class F1"]
    notes: "Known label noise; still valuable for diversity. RECOMMENDED FOR STRESS TESTING."

  - id: docbench-qa
    name: "DocBench (Multi-domain QA)"
    category: classification-heterogeneous
    priority: medium
    modalities: ["pdf"]
    formats: ["PDF", "QA pairs across 5 domains"]
    license: "Research use; verify"
    source_url: "https://arxiv.org/html/2407.10701v1"
    citation: "DocBench: A Benchmark for Evaluating LLM-based Document Reading Systems (2024)"
    size: "229 PDFs with 1,102 questions"
    recommended_split:
      sample_size: 150
      rationale: "Cross-domain validation: academia, finance, government, law, news"
    use_cases:
      - "Cross-domain document understanding"
      - "Multi-modal QA (text, tables, figures)"
      - "Domain generalization testing"
    primary_metrics: ["Answer correctness", "LLM-as-judge evaluation", "Domain-specific accuracy"]
    notes: "Good for testing domain generalization. 5 diverse domains with human-curated questions."

  # 5) Spreadsheets
  - id: spreadsheetbench
    name: "SpreadsheetBench"
    category: spreadsheets
    priority: critical
    modalities: ["xlsx", "xls"]
    formats: ["Native spreadsheets", "Manipulation instructions", "Test cases"]
    license: "Research use; verify"
    source_url: "https://spreadsheetbench.github.io/"
    huggingface_url: "https://huggingface.co/datasets/KAKA22/SpreadsheetBench"
    citation: "SpreadsheetBench: Towards Challenging Real World Spreadsheet Manipulation (2024)"
    size: "912 instructions with 2,729 test cases"
    recommended_split:
      sample_size: 200
      rationale: "Real-world Excel complexity - multiple tables, non-standard formats"
    use_cases:
      - "Real-world spreadsheet manipulation validation"
      - "Multiple tables per sheet handling"
      - "Non-standard relational tables (missing headers, etc.)"
      - "Cell-level and sheet-level operations"
    primary_metrics: ["Task completion accuracy", "Test case pass rate", "Cell/sheet-level correctness"]
    notes: "2,729 test cases; sourced from Excel forums. RECOMMENDED FOR EXCEL VALIDATION - most realistic."

  - id: euses
    name: "EUSES"
    category: spreadsheets
    priority: medium
    modalities: ["xlsx", "xls"]
    formats: ["Native spreadsheets"]
    license: "Research use; verify"
    source_url: "http://eusesconsortium.org/resources.php"
    citation: "EUSES: A Corpus for Spreadsheet Research (2005+)"
    size: "4,498 spreadsheets"
    recommended_split:
      sample_size: 500
      rationale: "Diverse real-world spreadsheets"
    use_cases:
      - "Real-world spreadsheets for parser correctness"
      - "Mixed domains and complexity levels"
    primary_metrics:
      - "Per-cell type/text preservation"
      - "Formula vs cached-value consistency"
    notes: "Mixed domains; good starting point. Some older Excel formats."

  - id: enron-spreadsheets
    name: "Enron Spreadsheets"
    category: spreadsheets
    priority: medium
    modalities: ["xlsx", "xls"]
    formats: ["Native spreadsheets"]
    license: "Research use; verify host terms"
    source_url: "https://figshare.com/articles/dataset/Enron_Spreadsheets_and_Emails/1222882"
    citation: "Enron Spreadsheet Corpus"
    size: "15,770 spreadsheets"
    recommended_split:
      sample_size: 1000
      rationale: "Enterprise messy sheets - merged cells, complex formulas"
    use_cases:
      - "Enterprise-like messy sheets; merged cells, names, validation"
      - "Edge case coverage"
      - "Complex formula handling"
    primary_metrics: ["Per-cell exact match", "Type preservation", "Formula parsing success"]
    notes: "Excellent for edge-case coverage. Real enterprise complexity."

  - id: fuse
    name: "FUSE (and VFUSE)"
    category: spreadsheets
    priority: low
    modalities: ["xlsx", "xls", "csv"]
    formats: ["Crawled corpus", "Validated subset"]
    license: "Research use; verify"
    source_url: "https://zenodo.org/records/3878063"
    citation: "FUSE: A Large-Scale Spreadsheet Corpus (2020)"
    size: "249,376 spreadsheets"
    recommended_split:
      sample_size: 2000
      rationale: "Scale/stress testing"
    use_cases:
      - "Scale/stress testing of spreadsheet parsers"
      - "Timeout/error handling"
    primary_metrics: ["Parser success rate", "Timeout/error rates", "Memory usage"]
    notes: "Internet-scale; expect corrupt/huge files. Good for robustness testing."

  - id: nist-csf-xlsx
    name: "NIST CSF Worksheets (example public XLSX)"
    category: spreadsheets
    priority: low
    modalities: ["xlsx"]
    formats: ["Native spreadsheets"]
    license: "US Gov works; generally public domain—verify specific file notices"
    source_url: "https://www.nist.gov/cyberframework"
    citation: "NIST Cybersecurity Framework Worksheets"
    recommended_split:
      sample_size: 25
      rationale: "Clean XLSX sanity checks"
    use_cases:
      - "Clean XLSX with validations/merged cells; sanity checks"
      - "Government document format compliance"
    primary_metrics: ["Cell value/type retention", "Sheet order", "Validation preservation"]
    notes: "Swap/augment with other gov XLSX you rely on. Good for baseline validation."

  # 6) Mixed file types
  - id: govdocs1
    name: "GovDocs1 (Digital Corpora)"
    category: mixed-filetypes
    priority: medium
    modalities: ["pdf", "doc", "docx", "xls", "xlsx", "ppt", "images", "archives"]
    formats: ["Native files"]
    license: "Digital Corpora terms; redistribution restrictions—verify"
    source_url: "https://digitalcorpora.org/corpora/govdocs"
    citation: "GovDocs1 Dataset"
    size: "1 million files"
    recommended_split:
      sample_size: 5000
      rationale: "File type coverage and robustness"
    use_cases:
      - "MIME detection, parser coverage, robustness, crash/timeout handling"
      - "File format diversity"
    primary_metrics: ["Parse success rate", "Throughput", "Graceful error handling"]
    notes: "Gold standard for coverage; curate slices by extension. Use for robustness testing."

  # 7) RAG-specific evaluation
  - id: ragbench
    name: "RAGBench"
    category: rag-evaluation
    priority: critical
    modalities: ["pdf", "text"]
    formats: ["Annotated QA pairs", "Industry corpora"]
    license: "Research use; verify"
    source_url: "https://huggingface.co/datasets/rungalileo/ragbench"
    paper_url: "https://arxiv.org/abs/2407.11005"
    citation: "RAGBench: Explainable Benchmark for Retrieval-Augmented Generation Systems (2024)"
    size: "100K examples across 5 domains"
    recommended_split:
      sample_size: 1000
      rationale: "Industry-specific RAG validation - user manuals, customer service"
    use_cases:
      - "End-to-end RAG pipeline evaluation"
      - "Industry-specific domains (customer service, manuals, finance, healthcare, legal)"
      - "Token-level attribution validation"
    primary_metrics: 
      - "TRACe: uTilization (context usage)"
      - "Relevance (retrieved context quality)"
      - "Adherence (factual grounding)"
      - "Completeness (answer coverage)"
    notes: "Real-world RAG examples from user manuals. RECOMMENDED FOR RAG VALIDATION - most comprehensive."

  - id: open-rag-benchmark
    name: "Open RAG Benchmark (Vectara)"
    category: rag-evaluation
    priority: high
    modalities: ["pdf"]
    formats: ["Multimodal QA pairs", "PDF with text/tables/images"]
    license: "Apache-2.0"
    source_url: "https://huggingface.co/datasets/vectara/open-rag-benchmark"
    blog_url: "https://www.vectara.com/blog/open-rag-benchmark-a-new-frontier-for-multimodal-pdf-understanding-in-rag"
    citation: "Open RAG Benchmark: Multimodal PDF Understanding (2024)"
    size: "3,000+ QA pairs from arXiv papers"
    recommended_split:
      sample_size: 200
      rationale: "Multimodal RAG testing - text + tables + images"
    use_cases:
      - "Multimodal RAG evaluation (text + tables + images)"
      - "Scientific/technical domain documents from arXiv"
      - "Abstractive and extractive query types"
    primary_metrics: 
      - "UMBRELA (answer quality)"
      - "Hallucination detection"
      - "Answer accuracy by modality (text-only vs. multimodal)"
    notes: "Specifically designed for multimodal PDF understanding. RECOMMENDED FOR MULTIMODAL RAG."

  - id: financebench
    name: "FinanceBench"
    category: rag-evaluation
    priority: medium
    modalities: ["pdf"]
    formats: ["10-K filings", "Earnings reports", "QA pairs with evidence strings"]
    license: "Apache-2.0"
    source_url: "https://github.com/patronus-ai/financebench"
    huggingface_url: "https://huggingface.co/datasets/PatronusAI/financebench"
    citation: "FinanceBench: Financial Document RAG Benchmark (2024)"
    size: "360 PDFs (150-250 pages each) with 150 questions"
    recommended_split:
      sample_size: 150
      rationale: "Large document RAG validation - financial domain"
    use_cases:
      - "Financial document RAG evaluation"
      - "Complex multi-page document retrieval (150-250 pages)"
      - "Structured + unstructured data handling"
      - "Dense table-heavy documents"
    primary_metrics: 
      - "Single-store retrieval accuracy"
      - "Shared-store retrieval accuracy (cross-document)"
      - "Answer correctness with evidence validation"
    notes: "50,000+ pages total; excellent for testing large document handling. Use if financial docs in scope."

  - id: legalbench-rag
    name: "LegalBench-RAG"
    category: rag-evaluation
    priority: low
    modalities: ["pdf"]
    formats: ["Legal documents", "Query-span pairs"]
    license: "Research use; verify"
    source_url: "https://arxiv.org/html/2408.10343v1"
    citation: "LegalBench-RAG: Benchmark for Retrieval-Augmented Generation in Legal Domain (2024)"
    size: "6,858 query-answer pairs over 79M+ characters"
    recommended_split:
      sample_size: 1000
      rationale: "Legal domain RAG - precise span extraction"
    use_cases:
      - "Legal document retrieval evaluation"
      - "Precise span extraction (character-level accuracy)"
      - "Domain-specific RAG performance"
    primary_metrics: 
      - "Retrieval precision/recall at various k"
      - "Span-level F1"
      - "Character-level accuracy"
    notes: "Emphasizes precise snippet retrieval over full documents. Use if legal docs in scope."

  # 8) End-to-end evaluators / harnesses
  - id: docling-eval
    name: "Docling-eval"
    category: end-to-end-eval
    type: benchmark_framework
    priority: high
    modalities: ["pdf"]
    formats: ["Evaluation code", "Benchmark adapters"]
    license: "MIT"
    source_url: "https://github.com/DS4SD/docling-eval"
    citation: "Docling-eval (IBM): Unified evaluation for document conversion"
    recommended_split:
      sample_size: "N/A (framework)"
    use_cases:
      - "Plug-in scoring for layout, reading order, tables"
      - "Adapters for multiple datasets (DocLayNet, PubTables, etc.)"
      - "Standardized metric computation"
    primary_metrics:
      - "Dataset-specific (mAP, TEDS, text fidelity, etc.)"
    notes: "Use as your primary harness; wire your converter outputs. Supports multiple datasets."

  - id: marker-bench
    name: "Marker benchmarks"
    category: end-to-end-eval
    type: benchmark_framework
    priority: medium
    modalities: ["pdf"]
    formats: ["Evaluation scripts", "Pointers to test PDFs/MD"]
    license: "Apache-2.0"
    source_url: "https://github.com/VikParuchuri/marker"
    citation: "Marker: PDF-to-Markdown conversion (open source)"
    recommended_split:
      sample_size: "N/A (scripts + data pointers)"
    use_cases:
      - "Quick local bake-offs for PDF→MD quality"
      - "Conversion speed benchmarking"
    primary_metrics:
      - "Project-provided text/structure scores"
      - "Processing time"
    notes: "Good complement to Docling-eval; easy to run. Good for comparative analysis."

  - id: pdf-extraction-benchmark
    name: "PDF Data Extraction Benchmark (Procycons)"
    category: end-to-end-eval
    type: benchmark_framework
    priority: low
    modalities: ["pdf"]
    formats: ["Corporate reports", "Comparative metrics"]
    license: "Research use; verify source PDFs"
    source_url: "https://procycons.com/en/blogs/pdf-data-extraction-benchmark/"
    citation: "PDF Data Extraction Benchmark 2025: Comparing Docling, Unstructured, and LlamaParse (2025)"
    size: "Variable (corporate reports 4,500-34,000 words)"
    recommended_split:
      sample_size: 50
      rationale: "Competitive benchmarking context"
    use_cases:
      - "Benchmarking against Docling, Unstructured, LlamaParse"
      - "Performance scalability testing (1-50 page documents)"
      - "Real corporate document formats (financial reports)"
    primary_metrics: 
      - "Processing time (per page and total)"
      - "Accuracy (table and text extraction)"
      - "Scalability (linear vs. non-linear performance)"
    notes: "Uses real corporate reports (Pfizer, Bayer, DHL, etc.); good for comparative analysis."

  # 9) Quality assessment
  - id: diqa-5000
    name: "DIQA-5000"
    category: quality-assessment
    priority: low
    modalities: ["pdf", "image"]
    formats: ["Document images", "Subjective quality ratings"]
    license: "Research use; verify"
    source_url: "https://arxiv.org/html/2509.17012"
    citation: "DocIQ: Document Image Quality Assessment Dataset (2025)"
    size: "5,000 enhanced document images with 15 annotators each"
    recommended_split:
      sample_size: 1000
      rationale: "Quality assessment validation"
    use_cases:
      - "Document enhancement evaluation"
      - "Quality assessment across distortion types (blur, shadow, wrinkle, occlusion, moiré)"
      - "OCR preprocessing validation"
    primary_metrics: 
      - "Overall quality (1-5 scale)"
      - "Sharpness (1-5 scale)"
      - "Color fidelity (1-5 scale)"
      - "SRCC (Spearman correlation)"
      - "PLCC (Pearson correlation)"
    notes: "5 distortion types; useful for evaluating preprocessing steps. Use if OCR quality is critical."

# ========================================
# INITIAL BENCHMARKING ANALYSIS RECOMMENDATION
# ========================================

initial_benchmark_plan:
  objective: "Validate PDF→Markdown/embedding pipeline for RAG applications"
  
  phase_1_core_validation:
    duration: "Week 1-2"
    focus: "Core extraction capabilities"
    datasets:
      - dataset: readoc
        sample_size: 500
        priority: critical
        rationale: "Best end-to-end proxy for RAG. Tests structure preservation (headings, lists, tables, code blocks)."
        metrics: ["Section F1", "List F1", "Table F1", "Text CER"]
        
      - dataset: doclaynet
        sample_size: 1000
        priority: critical
        rationale: "Layout and reading order baseline. Human-annotated, diverse document types."
        metrics: ["mAP (11 classes)", "Reading order accuracy"]
        
      - dataset: pubtables-1m
        sample_size: 500
        priority: critical
        rationale: "Table extraction validation. Tests structure detection and cell extraction."
        metrics: ["TEDS", "Cell exact match", "Header F1"]
    
    success_criteria:
      readoc: "Section F1 > 0.85, Table F1 > 0.75"
      doclaynet: "mAP > 0.80, Reading order > 0.90"
      pubtables: "TEDS > 0.85"

  phase_2_rag_specific:
    duration: "Week 2-3"
    focus: "RAG pipeline validation with QA pairs"
    datasets:
      - dataset: ragbench
        sample_size: 1000
        priority: critical
        rationale: "Industry-specific RAG validation. Tests real-world document types (manuals, customer service)."
        metrics: ["TRACe (Utilization, Relevance, Adherence, Completeness)"]
        
      - dataset: open-rag-benchmark
        sample_size: 200
        priority: high
        rationale: "Multimodal RAG testing. Validates text + table + image handling."
        metrics: ["UMBRELA", "Hallucination rate", "Accuracy by modality"]
    
    success_criteria:
      ragbench: "Utilization > 0.80, Adherence > 0.90"
      open_rag: "UMBRELA > 0.75, Hallucination < 0.15"

  phase_3_coverage_edge_cases:
    duration: "Week 3-4"
    focus: "Document variety and edge case handling"
    datasets:
      - dataset: docile
        sample_size: 500
        priority: high
        rationale: "Semi-structured forms (invoices, orders). Tests key-value and line-item extraction."
        metrics: ["KILE F1", "LIR F1"]
        
      - dataset: rvl-cdip
        sample_size: 2000
        priority: high
        rationale: "Document variety stress test. 16 document types (forms, letters, memos, scientific, etc.)."
        metrics: ["Parser success rate", "Per-class extraction quality"]
        
      - dataset: spreadsheetbench
        sample_size: 100
        priority: medium
        rationale: "Excel validation if XLSX in scope. Tests real-world complexity."
        metrics: ["Cell extraction accuracy", "Table structure preservation"]
    
    success_criteria:
      docile: "KILE F1 > 0.75, LIR F1 > 0.70"
      rvl_cdip: "Success rate > 0.95, Quality variance < 0.20"
      spreadsheetbench: "Cell accuracy > 0.90"

  total_samples: "~5,800 documents"
  estimated_time: "3-4 weeks"
  estimated_cost: "Low (all open-source datasets)"

  evaluation_framework:
    primary: "docling-eval (unified metrics)"
    secondary: "marker-bench (comparative analysis)"
    custom: "RAG-specific chunking quality metrics"

  rationale: >
    This phased approach validates: (1) Core PDF extraction quality against human-annotated
    benchmarks, (2) End-to-end RAG pipeline performance with actual QA pairs, (3) Robustness
    across document variety and edge cases. The ~5,800 sample total provides statistical
    significance while remaining manageable for iterative development.

# ========================================
# DEFAULTS AND CONFIGURATION
# ========================================

defaults:
  download:
    retry: 3
    timeout_seconds: 1800
    parallel_downloads: 4
  storage:
    root_dir: "data/raw"
    annotations_dir: "data/annotations"
    cache_dir: ".cache/datasets"
    processed_dir: "data/processed"
  evaluation:
    primary_harness: "docling-eval"
    secondary_harness: "marker-bench"
    output_dir: "eval/outputs"
    metrics_report: "eval/reports/summary.json"
    per_dataset_reports: true
    save_predictions: true
  governance:
    verify_licenses: true
    log_dataset_versions: true
    keep_origin_checksums: true
    pii_scan_before_commit: true
    track_data_lineage: true
  performance:
    batch_size: 32
    max_workers: 8
    timeout_per_doc: 120
    memory_limit_gb: 16