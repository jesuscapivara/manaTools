# -*- coding: utf-8 -*-
"""
Hook executado quando um documento é aberto no Revit.
"""
from pyrevit import script

logger = script.get_logger()

def doc_opened(doc):
    """
    Event listener para quando um documento é aberto.
    
    Args:
        doc: Documento do Revit
    """
    logger.info("Documento aberto: {}".format(doc.Title))
