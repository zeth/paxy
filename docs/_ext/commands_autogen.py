from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections import defaultdict, OrderedDict
from pathlib import Path
from typing import Iterable, Tuple, List

# Paths
DOCS_DIR = Path(__file__).resolve().parents[1]
GEN_DIR = DOCS_DIR / "commands"
GEN_DIR.mkdir(parents=True, exist_ok=True)


# -------------------------
# Discovery & docstring utils
# -------------------------


def _iter_command_classes() -> Iterable[Tuple[str, type]]:
    """
    Yield (module_name, classobj) for Command-like classes in paxy.commands.*,
    skipping base module and re-exports.
    """
    try:
        import paxy.commands as root  # type: ignore
    except Exception:
        return []

    seen: set[str] = set()

    for modinfo in pkgutil.walk_packages(root.__path__, root.__name__ + "."):
        mod_name = modinfo.name
        tail = mod_name.rsplit(".", 1)[-1]
        if tail.startswith("__"):
            continue
        if mod_name == "paxy.commands.base":
            continue

        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue

        for _, obj in inspect.getmembers(mod, inspect.isclass):
            if obj.__module__ != mod.__name__:
                continue
            if not obj.__module__.startswith("paxy.commands."):
                continue
            if not getattr(obj, "COMMAND", None):
                continue
            if not hasattr(obj, "make_ops"):
                continue

            fq = f"{obj.__module__}.{obj.__name__}"
            if fq in seen:
                continue
            seen.add(fq)
            yield mod_name, obj


def _infer_category_from_module(cls: type) -> str:
    modname = getattr(cls, "__module__", "")
    if not modname.startswith("paxy.commands."):
        return "misc"
    parts = modname.split(".")
    if len(parts) >= 3:
        return parts[2]  # 'core','std','data','web','ui',...
    return "core"


def _get_category(cls: type) -> str:
    return getattr(cls, "CATEGORY", None) or _infer_category_from_module(cls)


def _split_docstring(cls: type) -> tuple[str, str]:
    """
    Return (summary, details) from class docstring:
      - summary = first non-empty line (or default)
      - details = remaining lines, skipping a single blank separator
    """
    doc = (inspect.getdoc(cls) or "").strip()
    if not doc:
        return "_No documentation_", ""
    lines = doc.splitlines()
    summary = lines[0].strip() if lines else "_No documentation_"
    body = lines[1:]
    if body and not body[0].strip():
        body = body[1:]
    details = "\n".join(body).strip()
    return summary or "_No documentation_", details


# -------------------------
# Per-command page generation
# -------------------------


def _write_command_page(name: str, category: str, summary: str, details: str) -> str:
    """
    Write docs/commands/<slug>.md and return slug.
    """
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(name)).strip("-")
    out_path = GEN_DIR / f"{slug}.md"

    parts: List[str] = [
        f"# {name}",
        "",
        f"**Category:** `{category}`",
        "",
        summary,
        "",
        "---",
        "",
        details if details else "_No detailed documentation yet._",
        "",
    ]
    out_path.write_text("\n".join(parts), encoding="utf-8")
    return slug


def _generate_commands_index(pages: Iterable[Tuple[str, str, str]]) -> None:
    """
    Write docs/commands.md (grouped listing + one hidden toctree).
    """
    by_cat: dict[str, list[Tuple[str, str]]] = defaultdict(list)
    slug_order: "OrderedDict[str, None]" = OrderedDict()

    for slug, name, cat in pages:
        by_cat[cat].append((slug, name))
        if slug not in slug_order:
            slug_order[slug] = None

    lines: list[str] = ["# Commands Reference", ""]
    order = ["core", "std", "data", "web", "ui", "misc"]
    cats = sorted(by_cat, key=lambda c: (order.index(c) if c in order else 999, c))

    # Human-friendly grouped list
    for cat in cats:
        lines += [f"## {cat.title()}", ""]
        for slug, name in sorted(by_cat[cat], key=lambda x: x[1].lower()):
            lines.append(f"- [{name}](commands/{slug}.md)")
        lines.append("")

    # Hidden toctree with explicit entries
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


# -------------------------
# Orchestration
# -------------------------


def _generate_all_commands(_app=None) -> None:
    """
    Generate per-command pages + grouped index.
    """
    collected: list[
        tuple[str, str, str, str]
    ] = []  # (name, category, summary, details)
    for _, cls in _iter_command_classes():
        name = getattr(cls, "COMMAND", cls.__name__)
        category = _get_category(cls)
        summary, details = _split_docstring(cls)
        collected.append((name, category, summary, details))

    # Write per-command pages and index
    pages: list[Tuple[str, str, str]] = []
    for name, category, summary, details in collected:
        slug = _write_command_page(name, category, summary, details)
        pages.append((slug, name, category))
    _generate_commands_index(pages)


def setup(app):
    app.connect("builder-inited", _generate_all_commands)
