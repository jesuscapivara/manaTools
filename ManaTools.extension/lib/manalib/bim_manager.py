# -*- coding: utf-8 -*-
"""
Gerenciador BIM - Lógica para manipulação de elementos BIM.
"""
from manalib import utils


class BIMManager:
    """Classe para gerenciar operações BIM."""
    
    def __init__(self, doc):
        """
        Inicializa o gerenciador BIM.
        
        Args:
            doc: Documento do Revit
        """
        self.doc = doc
    
    def rename_elements(self, elements, standard="MANA_2025"):
        """
        Renomeia elementos BIM usando convenção de nomenclatura.
        
        Args:
            elements: Lista de elementos a renomear
            standard (str): Padrão de nomenclatura a aplicar
            
        Returns:
            int: Número de elementos renomeados com sucesso
        """
        count = 0
        for element in elements:
            if utils.apply_naming_convention(element, standard):
                count += 1
        return count

