import re
import hashlib
from typing import List, Dict, Any, Tuple

def normalize_text(text: str) -> str:
    """Normalizes text by lowercasing, removing non-alphanumeric chars, and collapsing whitespace."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

def generate_canonical_id(title: str, url: str = "") -> str:
    """Generates a stable deterministic hash for a headline and optional canonical URL."""
    norm_title = normalize_text(title)
    # Strip URL query parameters for cleaner comparison
    clean_url = url.split("?")[0].strip().lower() if url else ""
    seed = f"{norm_title}::{clean_url}" if clean_url else norm_title
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]

def jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates word-token Jaccard similarity between two texts."""
    words1 = set(normalize_text(text1).split())
    words2 = set(normalize_text(text2).split())
    if not words1 or not words2:
        return 0.0
    intersection = words1.intersection(words2)
    union = words1.union(words2)
    return len(intersection) / len(union)

class DeduplicationService:
    SIMILARITY_THRESHOLD = 0.82  # Near-duplicate threshold

    @classmethod
    def process_articles(cls, raw_articles: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
        """
        Marks duplicates while preserving distinct articles.
        Returns:
            processed_articles: List with `is_duplicate` and `duplicate_of` fields
            duplicate_count: Number of duplicate articles found
        """
        seen_canonical_ids = {}  # id -> master_id
        seen_urls = {}           # clean_url -> master_id
        canonical_masters = []   # list of (master_article, normalized_title)
        
        duplicate_count = 0
        processed = []

        for article in raw_articles:
            art_copy = dict(article)
            title = art_copy.get("title", "")
            url = art_copy.get("url", "")
            clean_url = url.split("?")[0].strip().lower() if url else ""
            
            canonical_id = generate_canonical_id(title, clean_url)
            art_copy["canonical_id"] = canonical_id
            
            is_dup = False
            dup_of = None

            # 1. Exact canonical ID check
            if canonical_id in seen_canonical_ids:
                is_dup = True
                dup_of = seen_canonical_ids[canonical_id]
            # 2. Exact URL match
            elif clean_url and clean_url in seen_urls:
                is_dup = True
                dup_of = seen_urls[clean_url]
            else:
                # 3. Near-duplicate text similarity check against masters
                norm_title = normalize_text(title)
                for master, m_norm in canonical_masters:
                    # Same company or closely related
                    sim = jaccard_similarity(norm_title, m_norm)
                    if sim >= cls.SIMILARITY_THRESHOLD:
                        is_dup = True
                        dup_of = master.get("id") or master.get("canonical_id")
                        break

            art_copy["is_duplicate"] = is_dup
            art_copy["duplicate_of"] = dup_of

            if is_dup:
                duplicate_count += 1
            else:
                seen_canonical_ids[canonical_id] = art_copy.get("id") or canonical_id
                if clean_url:
                    seen_urls[clean_url] = art_copy.get("id") or canonical_id
                canonical_masters.append((art_copy, normalize_text(title)))

            processed.append(art_copy)

        return processed, duplicate_count

deduplication_service = DeduplicationService()
