# -*- coding: utf-8 -*-
"""Exibe informações básicas do ManaTools."""
import json
import os
from pyrevit import forms


def _find_extension_root():
    """Sobe diretórios até achar o extension.json."""
    cur = os.path.dirname(__file__)
    for _ in range(6):
        if os.path.isfile(os.path.join(cur, "extension.json")):
            return cur
        cur = os.path.dirname(cur)
    return None


def get_local_version():
    try:
        ext_root = _find_extension_root()
        if not ext_root:
            return "0.0.0"
        json_path = os.path.join(ext_root, "extension.json")
        with open(json_path, "r") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except Exception:
        return "0.0.0"


def main():
    ver = get_local_version()
    
    # Caminho para o XAML
    xaml_path = os.path.join(os.path.dirname(__file__), "window.xaml")
    window = forms.WPFWindow(xaml_path)
    
    # Atualiza versão
    window.version_text.Text = "Versão {}".format(ver)
    
    # Handlers
    window.close_btn.Click += lambda s, e: window.Close()
    window.ShowDialog()


if __name__ == "__main__":
    main()

