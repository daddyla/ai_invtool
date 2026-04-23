"""Cross-platform prompt helpers — falls back to simple input() if questionary fails."""

from rich.console import Console

console = Console()

# Try questionary first, fall back to basic input
_USE_QUESTIONARY = False
try:
    import questionary
    # Test if it actually works in this terminal
    questionary.select("test", choices=["a"], instruction="").skip_if(True, default="a").ask()
    _USE_QUESTIONARY = True
except Exception:
    pass


def select(message: str, choices: list, **kwargs) -> str:
    """Show a selection menu. choices = list of (label, value) tuples or Choice objects."""
    # Normalize choices to (label, value) pairs
    items = []
    for c in choices:
        if hasattr(c, "title") and hasattr(c, "value"):
            items.append((c.title, c.value))
        elif isinstance(c, tuple):
            items.append(c)
        elif isinstance(c, dict):
            items.append((c.get("name", c.get("label", "")), c.get("value", "")))
        elif isinstance(c, str):
            items.append((c, c))
        else:
            # questionary.Choice or similar
            try:
                items.append((str(c.title), c.value))
            except Exception:
                items.append((str(c), str(c)))

    # Filter out separators
    items = [(label, val) for label, val in items if val and label and label.strip("─-") != ""]

    if _USE_QUESTIONARY:
        try:
            q_choices = [questionary.Choice(label, value=val) for label, val in items]
            result = questionary.select(message, choices=q_choices, **kwargs).ask()
            return result
        except Exception:
            pass

    # Fallback: numbered menu
    console.print(f"\n[bold]{message}[/]")
    for i, (label, val) in enumerate(items, 1):
        console.print(f"  [cyan]{i}.[/] {label}")
    console.print()

    while True:
        try:
            raw = input("  > ").strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not raw:
            continue
        # Accept number or value text
        try:
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return items[idx][1]
        except ValueError:
            # Try matching by value or label
            raw_lower = raw.lower()
            for label, val in items:
                if raw_lower == val.lower() or raw_lower == label.lower() or raw_lower in label.lower():
                    return val
        console.print(f"  [yellow]Enter 1-{len(items)}[/]")


def text(message: str, default: str = "") -> str:
    """Prompt for text input."""
    if _USE_QUESTIONARY:
        try:
            result = questionary.text(message, default=default).ask()
            return result if result is not None else default
        except Exception:
            pass

    # Fallback
    prompt = f"  {message}"
    if default:
        prompt += f" [{default}]"
    prompt += " "
    try:
        raw = input(prompt).strip()
        return raw if raw else default
    except (EOFError, KeyboardInterrupt):
        return default


def confirm(message: str, default: bool = True) -> bool:
    """Yes/no confirmation."""
    if _USE_QUESTIONARY:
        try:
            return questionary.confirm(message, default=default).ask()
        except Exception:
            pass

    # Fallback
    yn = "Y/n" if default else "y/N"
    try:
        raw = input(f"  {message} [{yn}] ").strip().lower()
        if not raw:
            return default
        return raw in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default
