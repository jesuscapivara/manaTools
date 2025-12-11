# -*- coding: utf-8 -*-
"""Checa manualmente se há atualização do ManaTools."""
import json
import os
import webbrowser
from pyrevit import forms
from System.Windows import Visibility
from System.Windows.Media import SolidColorBrush, ColorConverter


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


def _version_gt(remote_v, local_v):
    def to_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except Exception:
            return (0,)
    return to_tuple(remote_v) > to_tuple(local_v)


def main():
    try:
        from manalib import update_checker
    except Exception as imp_err:
        forms.alert(
            "Erro ao carregar update_checker:\n{}".format(imp_err),
            title="Checar Update",
        )
        return

    # Loader
    with forms.ProgressBar(title="Checando atualização...", cancellable=False, step=1) as pb:
        local_ver = get_local_version()
        pb.update_progress(1, 2)
        remote = update_checker.get_remote_version_info()
        pb.update_progress(2, 2)

    if not remote:
        forms.alert("Falha ao consultar /version.", title="Checar Update")
        return

    remote_ver = remote.get("latest_version", "0.0.0")
    download_url = remote.get("download_url", "")
    msg = remote.get("message", "")
    has_update = _version_gt(remote_ver, local_ver)

    # Carrega XAML
    xaml_path = os.path.join(os.path.dirname(__file__), "window.xaml")
    window = forms.WPFWindow(xaml_path)
    
    # Preenche dados
    window.local_ver.Text = local_ver
    window.remote_ver.Text = remote_ver
    
    if msg:
        window.msg_text.Text = msg
        window.msg_border.Visibility = Visibility.Visible
    
    converter = ColorConverter()
    if has_update:
        window.status_text.Text = "✓ Nova versão disponível!"
        window.status_text.Foreground = SolidColorBrush(converter.ConvertFromString("#27AE60"))
        if download_url:
            window.download_btn.Visibility = Visibility.Visible
    else:
        window.status_text.Text = "✓ Você já está na versão mais recente"
        window.status_text.Foreground = SolidColorBrush(converter.ConvertFromString("#3498DB"))
    
    # Handlers
    def on_download(sender, args):
        try:
            webbrowser.open(download_url)
            window.Close()
        except Exception:
            forms.alert("Não foi possível abrir:\n{}".format(download_url), title="Erro")
    
    if has_update and download_url:
        window.download_btn.Click += on_download
    
    window.close_btn.Click += lambda s, e: window.Close()
    window.ShowDialog()


if __name__ == "__main__":
    main()

