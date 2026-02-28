"""Wiki knowledge system for organizing RLM findings."""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class WikiPage:
    """A single wiki page."""
    title: str
    content: str
    tags: Set[str] = field(default_factory=set)
    links: Set[str] = field(default_factory=set)
    created_at: int = 0
    updated_at: int = 0

    def __repr__(self) -> str:
        tags_str = ", ".join(sorted(self.tags)) if self.tags else "none"
        return f"WikiPage({self.title!r}, tags=[{tags_str}], updated={self.updated_at})"


class Wiki:
    """Wiki knowledge base with BM25 search.

    Provides structured knowledge storage for RLM agents.
    Pages can be created, updated, linked, tagged, and searched.
    """

    def __init__(self) -> None:
        self._pages: Dict[str, WikiPage] = {}
        self._iteration: int = 0

        # BM25 index internals
        self._inverted_index: Dict[str, Set[str]] = defaultdict(set)
        self._doc_lengths: Dict[str, int] = {}
        self._avg_doc_length: float = 0.0

    # -- CRUD --

    def create(self, title: str, content: str, tags: Optional[Set[str]] = None) -> WikiPage:
        """Create a new wiki page.

        Args:
            title: Unique page title (e.g. "revenue/q1").
            content: Free-form text body.
            tags: Optional set of labels like "finding", "todo".

        Returns:
            The created WikiPage.

        Raises:
            KeyError: If a page with this title already exists.
        """
        if title in self._pages:
            raise KeyError(f"Page {title!r} already exists. Use update() to modify it.")
        page = WikiPage(
            title=title,
            content=content,
            tags=set(tags) if tags else set(),
            created_at=self._iteration,
            updated_at=self._iteration,
        )
        self._pages[title] = page
        self._index_page(title, content)
        return page

    def update(
        self,
        title: str,
        content: Optional[str] = None,
        append: Optional[str] = None,
        tags: Optional[Set[str]] = None,
    ) -> WikiPage:
        """Modify an existing wiki page.

        Args:
            title: Page title to update.
            content: Replace entire content (mutually exclusive with append).
            append: Append text to existing content.
            tags: Replace tags entirely if provided.

        Returns:
            The updated WikiPage.

        Raises:
            KeyError: If the page does not exist.
        """
        page = self._get_or_raise(title)
        if content is not None:
            page.content = content
        elif append is not None:
            page.content += append
        if tags is not None:
            page.tags = set(tags)
        page.updated_at = self._iteration
        self._index_page(title, page.content)
        return page

    def get(self, title: str) -> WikiPage:
        """Retrieve a page by title.

        Raises:
            KeyError: If the page does not exist.
        """
        return self._get_or_raise(title)

    def delete(self, title: str) -> None:
        """Remove a page and clean up references.

        Raises:
            KeyError: If the page does not exist.
        """
        self._get_or_raise(title)
        # Remove from other pages' link sets
        for other in self._pages.values():
            other.links.discard(title)
        # Remove from index
        self._remove_from_index(title)
        del self._pages[title]

    def link(self, from_title: str, to_title: str) -> None:
        """Add a cross-reference from one page to another.

        Both pages must exist.
        """
        self._get_or_raise(from_title)
        self._get_or_raise(to_title)
        self._pages[from_title].links.add(to_title)

    # -- Listings --

    def titles(self) -> List[str]:
        """Return all page titles, sorted."""
        return sorted(self._pages.keys())

    def toc(self) -> str:
        """Formatted table of contents.

        Returns a string table with title, tags, and updated_at for each page.
        """
        if not self._pages:
            return "(wiki is empty)"
        lines = []
        for title in sorted(self._pages):
            page = self._pages[title]
            tags_str = ", ".join(sorted(page.tags)) if page.tags else "-"
            lines.append(f"  {title:<40s} [{tags_str}]  (iter {page.updated_at})")
        header = f"Wiki: {len(self._pages)} pages"
        return header + "\n" + "\n".join(lines)

    def backlinks(self, title: str) -> List[str]:
        """Return titles of pages that link TO this page."""
        return sorted(
            t for t, p in self._pages.items() if title in p.links
        )

    # -- Search --

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """BM25-ranked search over page contents.

        Args:
            query: Search query string.
            top_k: Number of results to return.

        Returns:
            List of (title, score, snippet) tuples, highest score first.
        """
        tokens = self._tokenize(query)
        if not tokens or not self._pages:
            return []

        scores: Dict[str, float] = defaultdict(float)
        n = len(self._pages)
        k1, b = 1.5, 0.75

        for term in tokens:
            if term not in self._inverted_index:
                continue
            doc_set = self._inverted_index[term]
            idf = math.log((n - len(doc_set) + 0.5) / (len(doc_set) + 0.5) + 1.0)
            for title in doc_set:
                page = self._pages[title]
                tf = Counter(self._tokenize(page.content))[term]
                dl = self._doc_lengths.get(title, 1)
                avg_dl = self._avg_doc_length or 1.0
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * dl / avg_dl)
                scores[title] += idf * numerator / denominator

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        results = []
        for title, score in ranked:
            snippet = self._make_snippet(self._pages[title].content, tokens)
            results.append((title, round(score, 3), snippet))
        return results

    def search_tags(self, tag: str) -> List[str]:
        """Return titles of pages that have the given tag."""
        return sorted(t for t, p in self._pages.items() if tag in p.tags)

    # -- Serialization --

    def export(self) -> dict:
        """JSON-serializable snapshot of the entire wiki."""
        return {
            "pages": {
                title: {
                    "title": page.title,
                    "content": page.content,
                    "tags": sorted(page.tags),
                    "links": sorted(page.links),
                    "created_at": page.created_at,
                    "updated_at": page.updated_at,
                }
                for title, page in self._pages.items()
            },
            "page_count": len(self._pages),
        }

    def __repr__(self) -> str:
        return self.toc()

    # -- Iteration tracking (called by RLM core) --

    def set_iteration(self, iteration: int) -> None:
        """Update the current iteration counter."""
        self._iteration = iteration

    # -- Internal helpers --

    def _get_or_raise(self, title: str) -> WikiPage:
        if title not in self._pages:
            raise KeyError(f"Page {title!r} not found. Existing pages: {self.titles()}")
        return self._pages[title]

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Lowercase and split on non-word characters."""
        return re.findall(r'\w+', text.lower())

    def _index_page(self, title: str, content: str) -> None:
        """Update inverted index for a page."""
        # Remove old entries first
        self._remove_from_index(title)
        tokens = self._tokenize(content)
        self._doc_lengths[title] = len(tokens)
        for token in set(tokens):
            self._inverted_index[token].add(title)
        # Recompute average doc length
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)

    def _remove_from_index(self, title: str) -> None:
        """Remove a page from the inverted index."""
        self._doc_lengths.pop(title, None)
        empty_terms = []
        for term, titles in self._inverted_index.items():
            titles.discard(title)
            if not titles:
                empty_terms.append(term)
        for term in empty_terms:
            del self._inverted_index[term]
        if self._doc_lengths:
            self._avg_doc_length = sum(self._doc_lengths.values()) / len(self._doc_lengths)
        else:
            self._avg_doc_length = 0.0

    @staticmethod
    def _make_snippet(content: str, query_tokens: List[str], max_len: int = 120) -> str:
        """Extract a snippet around the first query term match."""
        lower = content.lower()
        best_pos = len(content)
        for token in query_tokens:
            pos = lower.find(token)
            if pos != -1 and pos < best_pos:
                best_pos = pos
        if best_pos == len(content):
            # No match found, return start of content
            return content[:max_len].replace("\n", " ") + ("..." if len(content) > max_len else "")
        start = max(0, best_pos - 30)
        end = start + max_len
        snippet = content[start:end].replace("\n", " ")
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet += "..."
        return snippet
