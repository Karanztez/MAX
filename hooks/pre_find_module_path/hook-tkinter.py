"""Keep tkinter discoverable when PyInstaller's Tcl probe cannot initialize."""


def pre_find_module_path(_hook_api):
    pass
