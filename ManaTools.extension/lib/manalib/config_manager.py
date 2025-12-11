# -*- coding: utf-8 -*-
"""
Gerenciador de configurações persistentes para os comandos da Maná Tools.
Salva e recupera preferências do usuário (inputs de UI).
"""
from pyrevit import script

def get_config(command_id):
    """Recupera o objeto de configuração para um comando específico."""
    return script.get_config(command_id)

def save_config(command_id, data_dict):
    """
    Salva dicionário de dados na configuração do comando.
    Args:
        command_id (str): Identificador único do comando (ex: 'manatools_criarforro')
        data_dict (dict): Pares chave-valor a salvar.
    """
    cfg = script.get_config(command_id)
    for key, value in data_dict.items():
        setattr(cfg, key, value)
    script.save_config()

