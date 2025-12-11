# -*- coding: utf-8 -*-
import json
import os
from pyrevit import forms
from manalib import bim_utils, update_checker

def get_local_version():
    """Lê a versão do extension.json."""
    try:
        ext_path = os.path.dirname(os.path.dirname(__file__))
        json_path = os.path.join(ext_path, "extension.json")
        with open(json_path, "r") as f:
            data = json.load(f)
            return data.get("version", "0.0.0")
    except:
        return "0.0.0"


def check_license_startup():
    try:
        is_valid, msg = bim_utils.sync_coordinates()
        
        if is_valid:
            allowed, status_msg = bim_utils.calculate_vector_matrix()
            if allowed:

                pass
            else:
                forms.toast("Atenção: " + status_msg, title="Maná Tools - Licença")
        else:
            if "Sessão expirada" in msg:
                forms.toast("Sua sessão expirou. Faça login novamente.", title="Maná Tools")
                
    except Exception as e:
        print("Erro no startup do ManaTools: {}".format(e))


def doc_opened(doc):
    # 1) Checagem de atualização (silenciosa, apenas toast)
    try:
        local_ver = get_local_version()
        has_update, data = update_checker.is_update_available(local_ver)
        if has_update and data:
            forms.toast(
                "Versão {} disponível!\n{}".format(
                    data.get("latest_version", ""), data.get("message", "")
                ),
                title="ManaTools Update",
                appid="ManaTools",
                click=data.get("download_url", ""),
            )
    except Exception as e:
        # Falha silenciosa para não atrapalhar abertura do arquivo
        print("Aviso: falha ao checar atualização: {}".format(e))

    # 2) Checagem de licença (já existente)
    check_license_startup()


if __name__ == '__main__':
    check_license_startup()
