# -*- coding: utf-8 -*-
# manalib/utils.py
"""
Utilitários gerais para ManaTools.
Funções auxiliares para nomenclatura e convenções.
"""
from manalib import text_utils


def apply_naming_convention(element, standard="MANA_2025"):
    """
    Aplica convenção de nomenclatura a um elemento.
    
    Args:
        element: Elemento do Revit
        standard (str): Padrão de nomenclatura a aplicar
        
    Returns:
        bool: True se a renomeação foi bem-sucedida
    """
    try:
        # Verifica se o elemento tem parâmetro Name
        param = element.LookupParameter("Name")
        if param and not param.IsReadOnly:
            # Lógica de nomenclatura baseada no padrão
            current_name = param.AsString() or ""
            new_name = _generate_name_by_convention(element, current_name, standard)
            param.Set(new_name)
            return True
    except Exception as e:
        print("Erro ao renomear elemento {}: {}".format(element.Id, str(e)))
        return False
    
    return False


def _generate_name_by_convention(element, current_name, standard):
    """
    Gera nome baseado na convenção especificada.
    
    Args:
        element: Elemento do Revit
        current_name (str): Nome atual
        standard (str): Padrão a seguir
        
    Returns:
        str: Novo nome gerado
    """
    # Implementação básica - pode ser expandida
    element_type = element.GetType().Name if hasattr(element, 'GetType') else "Element"
    
    if standard == "MANA_2025":
        # Exemplo: MANA_2025_Wall_001
        prefix = "MANA_2025"
        category = element.Category.Name if element.Category else "Unknown"
        suffix = str(element.Id.IntegerValue)[-3:]  # Últimos 3 dígitos do ID
        return "{}_{}_{}".format(prefix, category, suffix)
    
    return current_name

