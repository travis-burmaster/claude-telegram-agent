"""Memory selection and formatting for prompt injection."""

from pathlib import Path
from typing import Any

from .manager import MemoryManager


def select_memories(
    mgr: MemoryManager,
    context: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Search memories by context string, returning up to max_results."""
    # Split context into keywords and search each, dedup by name+type
    keywords = context.lower().split()
    seen: set[tuple[str, str]] = set()
    results: list[dict[str, Any]] = []

    for keyword in keywords:
        if len(keyword) < 2:
            continue
        for entry in mgr.search(keyword):
            key = (entry.get("name", ""), entry.get("type", ""))
            if key not in seen:
                seen.add(key)
                results.append(entry)
            if len(results) >= max_results:
                return results

    return results[:max_results]


def format_memories_for_prompt(
    memories: list[dict[str, Any]],
    memory_dir: Path,
) -> str:
    """Format selected memories into a string suitable for Claude prompt injection."""
    if not memories:
        return ""

    sections: list[str] = []
    sections.append("## Relevant Memories\n")

    for mem in memories:
        fp = memory_dir / mem.get("file", "")
        content = ""
        if fp.exists():
            # Read just the content (skip frontmatter)
            from .manager import _parse_frontmatter
            _, content = _parse_frontmatter(fp.read_text())

        tags_str = ", ".join(mem.get("tags", []))
        header = f"### {mem.get('name', 'Unknown')} ({mem.get('type', '?')})"
        if tags_str:
            header += f"  [tags: {tags_str}]"
        sections.append(header)
        if content.strip():
            sections.append(content.strip())
        sections.append("")

    return "\n".join(sections)
