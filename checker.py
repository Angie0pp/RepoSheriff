import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


LINK_PATTERN = re.compile(
    r"!?\[[^\]]*\]\(\s*(?:<([^>]+)>|([^\s)]+))"
)

SKIP_FOLDERS = {".git", ".venv", "venv", "node_modules"}


HEADING_PUNCTUATION = re.compile(r"[^\w\- ]", re.UNICODE)
INLINE_MARKDOWN = re.compile(r"[*_~`]")


def find_markdown_files(root):
    """Find Markdown files while skipping common dependency and Git folders."""
    files = []

    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".md", ".markdown"}:
            continue

        if any(part in SKIP_FOLDERS for part in path.parts):
            continue

        files.append(path)

    return sorted(files)


def read_text(path):
    """Read a text file, replacing invalid characters if necessary."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def heading_anchors(markdown_text):
    """Create GitHub-style anchors from Markdown headings."""
    anchors = set()
    counts = {}
    inside_code_block = False

    for line in markdown_text.splitlines():
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            inside_code_block = not inside_code_block
            continue

        if inside_code_block:
            continue

        match = re.match(r"^#{1,6}\s+(.+?)\s*#*\s*$", stripped)
        if not match:
            continue

        heading = INLINE_MARKDOWN.sub("", match.group(1)).strip()
        slug = HEADING_PUNCTUATION.sub("", heading.lower())
        slug = re.sub(r"\s+", "-", slug)

        
        number = counts.get(slug, 0)
        counts[slug] = number + 1

        if number:
            slug = f"{slug}-{number}"

        anchors.add(slug)

    return anchors


def check_markdown_file(markdown_file, project_root):
    """Return broken local links found in one Markdown file."""
    issues = []
    content = read_text(markdown_file)
    inside_code_block = False

    for line_number, line in enumerate(content.splitlines(), start=1):
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            inside_code_block = not inside_code_block
            continue

        # Links inside code examples are not treated as real links.
        if inside_code_block:
            continue

        for match in LINK_PATTERN.finditer(line):
            destination = match.group(1) or match.group(2)
            destination = destination.strip()

            if not destination:
                continue

            parts = urlsplit(destination)

           
            if parts.scheme or parts.netloc:
                continue

            path_text = unquote(parts.path)
            anchor = unquote(parts.fragment)

            if path_text:
                if path_text.startswith("/"):
                    target = project_root / path_text.lstrip("/")
                else:
                    target = markdown_file.parent / path_text

                target = target.resolve()

                if not target.exists():
                    issues.append({
                        "file": markdown_file,
                        "line": line_number,
                        "link": destination,
                        "reason": "target file or folder does not exist",
                    })
                    continue
            else:
                
                target = markdown_file

            if anchor and target.suffix.lower() in {".md", ".markdown"}:
                target_anchors = heading_anchors(read_text(target))

                if anchor not in target_anchors:
                    issues.append({
                        "file": markdown_file,
                        "line": line_number,
                        "link": destination,
                        "reason": f"heading anchor #{anchor} was not found",
                    })

    return issues


def check_project(project_root):
    """Check every Markdown file beneath the project folder."""
    markdown_files = find_markdown_files(project_root)
    issues = []

    for markdown_file in markdown_files:
        issues.extend(check_markdown_file(markdown_file, project_root))

    return markdown_files, issues