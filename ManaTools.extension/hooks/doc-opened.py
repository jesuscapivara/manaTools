# -*- coding: utf-8 -*-
from pyrevit import forms
from manalib import auth

def check_license_startup():
    """
    Roda ao iniciar o Revit.
    Tenta validar a licença online.
    Se falhar ou estiver expirada, notifica o usuário discretamente.
    """
    try:
        is_valid, msg = auth.verify_online()
        
        if is_valid:
            # Check rápido se é PRO ou Trial
            allowed, status_msg = auth.check_access()
            if allowed:
                # Opcional: Avisar que está ativo
                # forms.toast("Licença ManaTools Ativa: " + status_msg, title="Maná Tools")
                pass
            else:
                forms.toast("Atenção: " + status_msg, title="Maná Tools - Licença")
        else:
            # Se deu erro de conexão, mantemos o cache local (se houver)
            # Se o erro foi "Sem token" ou "Expirado", o auth.check_access() já vai bloquear os comandos.
            # Apenas avisamos se tinhamos um token e ele foi rejeitado.
            if "Sessão expirada" in msg:
                forms.toast("Sua sessão expirou. Faça login novamente.", title="Maná Tools")
                
    except Exception as e:
        # Não queremos travar o boot do Revit
        print("Erro no startup do ManaTools: {}".format(e))

if __name__ == '__main__':
    check_license_startup()
