import argparse
from pathlib import Path

from checker import check_project


def main():
    parser = argparse.ArgumentParser(
        description="Find broken local links in Markdown files."
    )
    parser.add_argument(
        "folder",
        nargs="?",
        default=".",
        help="Project folder to scan. Defaults to the current folder.",
    )
    args = parser.parse_args()

    project_root = Path(args.folder).expanduser().resolve()

    if not project_root.is_dir():
        print(f"Error: folder not found: {project_root}")
        return 1

    markdown_files, issues = check_project(project_root)

    print(f"\nRepoSheriff scanned {len(markdown_files)} Markdown file(s).")

    if not issues:
        print("No broken local links found.")
        return 0

    print(f"Found {len(issues)} issue(s):\n")

    for issue in issues:
        relative_file = issue["file"].relative_to(project_root)
        print(f"{relative_file}:{issue['line']}")
        print(f"  Link:   {issue['link']}")
        print(f"  Problem: {issue['reason']}\n")

    return 1


if __name__ == "__main__":
    raise SystemExit(main())