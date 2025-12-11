# -*- coding: utf-8 -*-
"""Sinal rápido de carregamento da extensão ManaTools."""
from pyrevit import forms, script


def _notify():
    try:
        forms.toast(
            "ManaTools carregado (startup)",
            title="ManaTools",
            appid="ManaTools",
        )
    except Exception as toast_err:
        print("ManaTools startup: falha ao mostrar toast: {}".format(toast_err))

    try:
        script.get_logger().info("ManaTools startup.py executado.")
    except Exception as log_err:
        print("ManaTools startup: falha ao logar: {}".format(log_err))


_notify()

