import sys
from pathlib import Path

try:
    import tomllib  # py3.11+
except ModuleNotFoundError:  # py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def read_version(pyproject_path: Path) -> str:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    # New Poetry (PEP 621)
    proj = data.get("project") or {}
    if "version" in proj:
        return str(proj["version"]).strip()
    # Legacy Poetry
    tool = data.get("tool") or {}
    poetry = tool.get("poetry") or {}
    if "version" in poetry:
        return str(poetry["version"]).strip()
    raise KeyError("version not found in [project] or [tool.poetry]")


def update_version_in_init():
    repo_root = Path(__file__).resolve().parent.parent
    pyproject_path = repo_root / "pyproject.toml"
    init_file_path = repo_root / "src" / "patentpack" / "__init__.py"

    if not pyproject_path.exists():
        print(f"pyproject.toml not found at {pyproject_path}", file=sys.stderr)
        sys.exit(1)
    if not init_file_path.exists():
        print(f"__init__.py not found at {init_file_path}", file=sys.stderr)
        sys.exit(1)

    version = read_version(pyproject_path)

    init_text = init_file_path.read_text(encoding="utf-8")
    lines = init_text.splitlines()
    out_lines = []
    replaced = False
    for line in lines:
        if line.strip().startswith("__version__"):
            out_lines.append(f"__version__ = '{version}'")
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        # Ensure a trailing newline, then append
        if out_lines and out_lines[-1] != "":
            out_lines.append("")
        out_lines.append(f"__version__ = '{version}'")

    new_text = "\n".join(out_lines).rstrip() + "\n"
    init_file_path.write_text(new_text, encoding="utf-8")
    print(f"Updated __version__ in {init_file_path} to {version}")


if __name__ == "__main__":
    update_version_in_init()
