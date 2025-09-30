# docs/_ext/commands_autogen.py
from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Tuple, List

# Where to write generated pages (under docs/)
DOCS_DIR = Path(__file__).resolve().parents[1]
GEN_DIR = DOCS_DIR / "commands"
GEN_DIR.mkdir(parents=True, exist_ok=True)


def _iter_command_classes() -> Iterable[Tuple[str, type]]:
    """
    Yield (module_name, classobj) for public Command-like classes in paxy.commands.*.

    Heuristic:
      - module starts with 'paxy.commands.'
      - class has attribute 'COMMAND' (public name)
      - class has method 'make_ops' (your BaseCommand API)
    """
    try:
        import paxy.commands as root  # type: ignore
    except Exception:
        return []

    for modinfo in pkgutil.walk_packages(root.__path__, root.__name__ + "."):
        mod_tail = modinfo.name.rsplit(".", 1)[-1]
        if mod_tail.startswith("__"):
            continue
        try:
            mod = importlib.import_module(modinfo.name)
        except Exception:
            # Don't fail the docs build because a command module can't import
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__.startswith("paxy.commands."):
                if getattr(obj, "COMMAND", None) and hasattr(obj, "make_ops"):
                    yield modinfo.name, obj


def _infer_category_from_module(cls: type) -> str:
    """
    Infer category from module path.
      paxy.commands.core.let -> "core"
      paxy.commands.std.jsonop -> "std"
      paxy.commands.par (top-level) -> "core" (fallback)
    """
    modname = getattr(cls, "__module__", "")
    if not modname.startswith("paxy.commands."):
        return "misc"
    parts = modname.split(".")
    if len(parts) >= 3:
        return parts[2]  # 'core', 'std', 'data', 'web', 'ui', ...
    return "core"


def _get_category(cls: type) -> str:
    # Prefer explicit CATEGORY, else infer from module path
    return getattr(cls, "CATEGORY", None) or _infer_category_from_module(cls)


def _write_command_page(cls: type) -> Tuple[str, str, str]:
    """
    Emit one Markdown page for a command class.
    Returns (slug, display_name, category).
    """
    name = getattr(cls, "COMMAND", cls.__name__)
    summary = (getattr(cls, "SUMMARY", "") or "").strip()
    category = _get_category(cls)
    doc = (inspect.getdoc(cls) or "").strip()

    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(name)).strip("-")
    out_path = GEN_DIR / f"{slug}.md"

    parts: List[str] = [
        f"# {name}",
        "",
        f"**Category:** `{category}`",
        "",
        (summary if summary else "_No summary provided._"),
        "",
        "---",
        "",
        (doc if doc else "_No detailed documentation yet._"),
        "",
    ]
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return slug, name, category


def _generate_commands_index(pages: Iterable[Tuple[str, str, str]]) -> None:
    from collections import defaultdict, OrderedDict

    by_cat: dict[str, list[Tuple[str, str]]] = defaultdict(list)
    slug_order: "OrderedDict[str, None]" = OrderedDict()  # keep first occurrence only

    for slug, name, cat in pages:
        by_cat[cat].append((slug, name))
        if slug not in slug_order:
            slug_order[slug] = None

    lines: list[str] = ["# Commands Reference", ""]
    order = ["core", "std", "data", "web", "ui", "misc"]
    cats = sorted(by_cat, key=lambda c: (order.index(c) if c in order else 999, c))

    # Human-friendly grouped listing (not a toctree)
    for cat in cats:
        lines.append(f"## {cat.title()}")
        lines.append("")
        for slug, name in sorted(by_cat[cat], key=lambda x: x[1].lower()):
            lines.append(f"- [{name}](commands/{slug}.md)")
        lines.append("")

    # Single hidden toctree, explicit unique entries (no .md extension)
    lines += [
        "```{toctree}",
        ":maxdepth: 1",
        ":hidden:",
        "",
    ]
    lines += [f"commands/{slug}" for slug in slug_order.keys()]
    lines += [
        "```",
        "",
    ]

    (DOCS_DIR / "commands.md").write_text("\n".join(lines), encoding="utf-8")


def _generate_all_commands(_app=None) -> None:
    """
    Generate per-command pages and the grouped index before Sphinx reads sources.
    """
    pages: List[Tuple[str, str, str]] = []
    for _, cls in _iter_command_classes():
        pages.append(_write_command_page(cls))
    _generate_commands_index(pages)


def setup(app):
    """
    Sphinx extension entry point.
    Runs the generator at 'builder-inited' so files exist before reading sources.
    """
    app.connect("builder-inited", _generate_all_commands)
