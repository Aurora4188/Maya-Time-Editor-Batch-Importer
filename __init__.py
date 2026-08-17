"""Maya Time Editor batch FBX importer."""


def show():
    """Open the tool UI."""
    from .main import show as show_window

    return show_window()


__all__ = ["show"]
