"""
src/ui/widgets/notebook_utils.py — Smooth Drag-and-Drop & Anti-Jitter for ttk.Notebook
"""

from typing import Any, Callable, List, Optional
import tkinter as tk
from tkinter import ttk


def enable_smooth_tab_drag(
    notebook: ttk.Notebook,
    tabs_getter: Optional[Callable[[], List[Any]]] = None,
    on_reorder_callback: Optional[Callable[[int, int], None]] = None,
) -> None:
    """
    Enables fluid, flicker-free drag-and-drop tab reordering for a ttk.Notebook
    and suppresses Tkinter's default glitchy/jittery <B1-Motion> tearing box on Windows.

    :param notebook: The ttk.Notebook instance.
    :param tabs_getter: Optional callable returning the underlying Python list of tab widgets.
    :param on_reorder_callback: Optional callback receiving (from_idx, to_idx).
    """
    drag_data: dict[str, Any] = {
        "x": 0,
        "y": 0,
        "idx": -1,
        "dragging": False,
    }

    def _on_press(event: tk.Event) -> None:  # type: ignore[type-arg]
        try:
            idx = notebook.index(f"@{event.x},{event.y}")
            drag_data["x"] = event.x
            drag_data["y"] = event.y
            drag_data["idx"] = idx
            drag_data["dragging"] = False
        except Exception:
            drag_data["x"] = event.x
            drag_data["y"] = event.y
            drag_data["idx"] = -1
            drag_data["dragging"] = False

    def _on_motion(event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        if drag_data.get("idx", -1) < 0:
            return None

        curr_from_idx = drag_data["idx"]
        dx = abs(event.x - drag_data["x"])
        dy = abs(event.y - drag_data["y"])

        # 5px threshold to separate clicks from drag actions
        if not drag_data["dragging"]:
            if dx > 5 or dy > 5:
                drag_data["dragging"] = True

        if drag_data["dragging"]:
            tab_names = notebook.tabs()
            num_tabs = len(tab_names)
            if num_tabs <= 1:
                return "break"

            target_idx = None
            # Probe multiple heights in tab header to ensure tracking even if user tilts mouse vertically
            for test_y in (event.y, 10, 15, 5, 20):
                try:
                    t_idx = notebook.index(f"@{event.x},{test_y}")
                    if isinstance(t_idx, int) and 0 <= t_idx < num_tabs:
                        target_idx = t_idx
                        break
                except Exception:
                    continue

            if (
                target_idx is not None
                and target_idx != curr_from_idx
                and 0 <= target_idx < num_tabs
                and 0 <= curr_from_idx < num_tabs
            ):
                # Retrieve the widget at curr_from_idx
                if tabs_getter is not None:
                    tab_list = tabs_getter()
                    tab_widget = tab_list[curr_from_idx]
                else:
                    tab_widget = notebook.nametowidget(tab_names[curr_from_idx])

                # Move tab in ttk.Notebook
                notebook.insert(target_idx, tab_widget)

                # Keep backing list in sync
                if tabs_getter is not None:
                    tab_list = tabs_getter()
                    tab_list.insert(target_idx, tab_list.pop(curr_from_idx))

                notebook.select(target_idx)
                old_idx = curr_from_idx
                drag_data["idx"] = target_idx
                drag_data["x"] = event.x

                if on_reorder_callback is not None:
                    try:
                        on_reorder_callback(old_idx, target_idx)
                    except Exception:
                        pass

            # Suppress default Tkinter ttk::notebook::Drag which creates the jerky dashed outline
            return "break"
        return None

    def _on_release(_event: tk.Event) -> Optional[str]:  # type: ignore[type-arg]
        was_dragging = bool(drag_data and drag_data.get("dragging", False))
        drag_data["x"] = 0
        drag_data["y"] = 0
        drag_data["idx"] = -1
        drag_data["dragging"] = False
        if was_dragging:
            return "break"
        return None

    notebook.bind("<ButtonPress-1>", _on_press, add="+")
    notebook.bind("<B1-Motion>", _on_motion)
    notebook.bind("<ButtonRelease-1>", _on_release)
