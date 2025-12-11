# -*- coding: utf-8 -*-
import json
import os
from pyrevit import forms
from manalib import bim_utils

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
    # 0) Confirmação visual de que o hook rodou
    try:
        forms.toast("ManaTools hook ativo", title="ManaTools", appid="ManaTools")
    except Exception as e:
        print("Aviso: falha ao mostrar toast inicial: {}".format(e))

    # 1) Checagem de atualização (com toast de debug temporário)
    try:
        try:
            from manalib import update_checker
        except Exception as imp_err:
            forms.toast(
                "Erro ao carregar update_checker: {}".format(imp_err),
                title="ManaTools Update Check",
                appid="ManaTools",
            )
            return

        local_ver = get_local_version()
        remote = update_checker.get_remote_version_info()

        def _version_gt(remote_v, local_v):
            def to_tuple(v):
                try:
                    return tuple(int(x) for x in v.split("."))
                except:
                    return (0,)
            return to_tuple(remote_v) > to_tuple(local_v)

        if not remote:
            forms.toast(
                "Falha ao consultar versão em /version",
                title="ManaTools Update Check",
                appid="ManaTools",
            )
        else:
            remote_ver = remote.get("latest_version", "0.0.0")
            # Toast de debug: sempre mostra local vs remoto
            forms.toast(
                "Versão local: {}\nVersão remota: {}".format(local_ver, remote_ver),
                title="ManaTools Update Check",
                appid="ManaTools",
                click=remote.get("download_url", ""),
            )

            if _version_gt(remote_ver, local_ver):
                forms.toast(
                    "Versão {} disponível!\n{}".format(
                        remote_ver, remote.get("message", "")
                    ),
                    title="ManaTools Update",
                    appid="ManaTools",
                    click=remote.get("download_url", ""),
                )
    except Exception as e:
        # Falha silenciosa para não atrapalhar abertura do arquivo
        print("Aviso: falha ao checar atualização: {}".format(e))

    # 2) Checagem de licença (já existente)
    check_license_startup()


if __name__ == '__main__':
    check_license_startup()
