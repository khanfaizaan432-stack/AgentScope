import math
import re
from collections import Counter


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _tfidf_vectors(texts: list[str]) -> list[dict[str, float]]:
    if not texts:
        return []

    tokenized = [_tokenize(t) for t in texts]
    n_docs = len(texts)

    df: Counter[str] = Counter()
    for tokens in tokenized:
        for term in set(tokens):
            df[term] += 1

    idf = {term: math.log((1 + n_docs) / (1 + count)) + 1 for term, count in df.items()}

    vectors: list[dict[str, float]] = []
    for tokens in tokenized:
        tf = Counter(tokens)
        total = len(tokens) or 1
        vec = {term: (count / total) * idf.get(term, 0) for term, count in tf.items()}
        vectors.append(vec)

    return vectors


def cosine_similarity(vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
    if not vec_a or not vec_b:
        return 0.0

    common = set(vec_a) & set(vec_b)
    dot = sum(vec_a[t] * vec_b[t] for t in common)

    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot / (norm_a * norm_b)


def jaccard_similarity(text_a: str, text_b: str) -> float:
    set_a = set(_tokenize(text_a))
    set_b = set(_tokenize(text_b))
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def combined_similarity(
    text_a: str, text_b: str, vec_a: dict[str, float], vec_b: dict[str, float]
) -> float:
    return max(cosine_similarity(vec_a, vec_b), jaccard_similarity(text_a, text_b))
