# -*- coding: utf-8 -*-
from pyrevit import forms
from manalib import bim_utils

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

if __name__ == '__main__':
    check_license_startup()
