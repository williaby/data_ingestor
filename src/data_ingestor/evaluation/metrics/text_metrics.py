"""
Text fidelity metrics.

Implements standard metrics for comparing extracted text against ground truth:
- CER (Character Error Rate): Levenshtein distance at character level
- BLEU: Bilingual Evaluation Understudy Score
- chrF: Character n-gram F-score
"""

import re
from collections import Counter


def calculate_cer(prediction: str, reference: str) -> float:
    """
    Calculate Character Error Rate (CER).

    CER is the Levenshtein (edit) distance normalized by reference length.
    Lower values are better (0.0 = perfect match).

    Args:
        prediction: Predicted text
        reference: Reference (ground truth) text

    Returns:
        CER score (0.0 = perfect, higher = more errors)

    Formula:
        CER = (S + D + I) / N
        where S=substitutions, D=deletions, I=insertions, N=reference length
    """
    if not reference:
        return 1.0 if prediction else 0.0

    # #ASSUME: Dynamic programming approach is efficient for typical document lengths
    # #VERIFY: Performance is acceptable for documents < 100K characters

    # Levenshtein distance using dynamic programming
    m, n = len(prediction), len(reference)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # Initialize base cases
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if prediction[i - 1] == reference[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j] + 1,  # deletion
                    dp[i][j - 1] + 1,  # insertion
                    dp[i - 1][j - 1] + 1,  # substitution
                )

    edit_distance = dp[m][n]
    return edit_distance / len(reference)


def calculate_bleu(
    prediction: str,
    reference: str,
    max_n: int = 4,
) -> float:
    """
    Calculate BLEU score.

    BLEU (Bilingual Evaluation Understudy) measures n-gram overlap between
    prediction and reference. Higher values are better (1.0 = perfect match).

    Args:
        prediction: Predicted text
        reference: Reference (ground truth) text
        max_n: Maximum n-gram size (default: 4)

    Returns:
        BLEU score (0.0-1.0, higher = better)

    Note:
        Uses simplified BLEU without smoothing. For production use, consider
        using NLTK's BLEU implementation with smoothing.
    """
    if not prediction or not reference:
        return 0.0

    # Tokenize (simple whitespace split)
    pred_tokens = prediction.lower().split()
    ref_tokens = reference.lower().split()

    if not pred_tokens or not ref_tokens:
        return 0.0

    # Calculate brevity penalty
    bp = _brevity_penalty(len(pred_tokens), len(ref_tokens))

    # Calculate n-gram precisions
    precisions = []
    for n in range(1, max_n + 1):
        p_n = _ngram_precision(pred_tokens, ref_tokens, n)
        precisions.append(p_n)

    # #ASSUME: Geometric mean is appropriate for BLEU aggregation
    # #VERIFY: All precisions are non-zero (use smoothing if needed)
    if any(p == 0 for p in precisions):
        return 0.0

    # Geometric mean of precisions
    import math

    geo_mean = math.exp(sum(math.log(p) for p in precisions) / len(precisions))

    return bp * geo_mean


def _brevity_penalty(pred_len: int, ref_len: int) -> float:
    """Calculate BLEU brevity penalty."""
    import math

    if pred_len >= ref_len:
        return 1.0
    return math.exp(1 - ref_len / pred_len)


def _ngram_precision(
    pred_tokens: list[str],
    ref_tokens: list[str],
    n: int,
) -> float:
    """Calculate n-gram precision."""
    if len(pred_tokens) < n:
        return 0.0

    # Extract n-grams
    pred_ngrams = [tuple(pred_tokens[i : i + n]) for i in range(len(pred_tokens) - n + 1)]
    ref_ngrams = [tuple(ref_tokens[i : i + n]) for i in range(len(ref_tokens) - n + 1)]

    if not pred_ngrams:
        return 0.0

    # Count matches (with clipping)
    pred_counts = Counter(pred_ngrams)
    ref_counts = Counter(ref_ngrams)

    matches = sum(min(pred_counts[ngram], ref_counts[ngram]) for ngram in pred_counts)

    return matches / len(pred_ngrams)


def calculate_chrf(
    prediction: str,
    reference: str,
    beta: float = 2.0,
    max_n: int = 6,
) -> float:
    """
    Calculate chrF (Character n-gram F-score).

    chrF measures character-level n-gram overlap with F-beta score.
    Higher values are better (1.0 = perfect match).

    Args:
        prediction: Predicted text
        reference: Reference (ground truth) text
        beta: Beta parameter for F-score (default: 2.0, favors recall)
        max_n: Maximum character n-gram size (default: 6)

    Returns:
        chrF score (0.0-1.0, higher = better)

    Reference:
        Popović, M. (2015). chrF: character n-gram F-score for automatic MT evaluation.
    """
    if not prediction or not reference:
        return 0.0

    # Remove whitespace for character-level comparison
    pred_chars = prediction.replace(" ", "")
    ref_chars = reference.replace(" ", "")

    if not pred_chars or not ref_chars:
        return 0.0

    # Calculate character n-gram F-scores
    f_scores = []
    for n in range(1, max_n + 1):
        f_n = _char_ngram_fscore(pred_chars, ref_chars, n, beta)
        if f_n is not None:
            f_scores.append(f_n)

    if not f_scores:
        return 0.0

    # Average F-scores across all n-gram sizes
    return sum(f_scores) / len(f_scores)


def _char_ngram_fscore(
    pred: str,
    ref: str,
    n: int,
    beta: float,
) -> float | None:
    """Calculate character n-gram F-score."""
    if len(pred) < n or len(ref) < n:
        return None

    # Extract character n-grams
    pred_ngrams = [pred[i : i + n] for i in range(len(pred) - n + 1)]
    ref_ngrams = [ref[i : i + n] for i in range(len(ref) - n + 1)]

    # Count matches
    pred_counts = Counter(pred_ngrams)
    ref_counts = Counter(ref_ngrams)

    matches = sum(min(pred_counts[ngram], ref_counts[ngram]) for ngram in pred_counts)

    if not matches:
        return 0.0

    # Calculate precision and recall
    precision = matches / len(pred_ngrams) if pred_ngrams else 0.0
    recall = matches / len(ref_ngrams) if ref_ngrams else 0.0

    if precision + recall == 0:
        return 0.0

    # Calculate F-beta score
    beta_squared = beta * beta
    return (1 + beta_squared) * precision * recall / (beta_squared * precision + recall)


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    Applies standard normalization:
    - Lowercase
    - Remove extra whitespace
    - Remove punctuation (optional)

    Args:
        text: Input text

    Returns:
        Normalized text
    """
    # Lowercase
    text = text.lower()

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()
