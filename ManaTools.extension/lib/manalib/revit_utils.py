# -*- coding: utf-8 -*-
"""
Wrappers da API do Revit para operações performáticas.
"""
from Autodesk.Revit.DB import (FilteredElementCollector, ViewSheet, 
                               PDFExportOptions, ExportRange, BuiltInCategory)


def get_all_walls(doc):
    """Retorna todas as paredes do projeto de forma performática."""
    return FilteredElementCollector(doc)\
        .OfCategory(BuiltInCategory.OST_Walls)\
        .WhereElementIsNotElementType()\
        .ToElements()


def get_all_sheets(doc):
    """
    Retorna todas as pranchas do projeto, ordenadas pelo número.
    
    Args:
        doc: Documento do Revit
        
    Returns:
        list: Lista de pranchas ordenadas por número
    """
    sheets = FilteredElementCollector(doc)\
             .OfClass(ViewSheet)\
             .ToElements()
    
    # Sort lambda para garantir ordem visual correta
    return sorted(sheets, key=lambda s: s.SheetNumber)


def create_pdf_options(doc, hide_scope_boxes=True):
    """
    Configurações padrão de exportação PDF (Revit 2022+ API).
    
    Args:
        doc: Documento do Revit
        hide_scope_boxes (bool): Se True, oculta scope boxes na exportação
        
    Returns:
        PDFExportOptions: Opções de exportação configuradas
    """
    options = PDFExportOptions()
    options.FileName = "temp"  # Será sobrescrito no loop
    # Na API 2022+, o ExportRange não é setado no options quando exportamos via lista de IDs
    # options.ExportRange = ExportRange.CurrentView  <-- REMOVIDO
    options.HideScopeBoxes = hide_scope_boxes
    # options.ViewId = doc.ActiveView.Id  <-- REMOVIDO (não necessário para batch)
    
    # Adicione aqui configurações de Zoom/PaperSize se necessário
    return options


def get_selected_elements(doc):
    """
    Obtém elementos selecionados no documento ativo.
    
    Args:
        doc: Documento do Revit
        
    Returns:
        list: Lista de elementos selecionados
    """
    from pyrevit import revit
    selection = revit.get_selection()
    element_ids = selection.element_ids
    
    if not element_ids:
        return []
    
    return [doc.GetElement(eid) for eid in element_ids if doc.GetElement(eid) is not None]


def setup_transaction(doc, name):
    """
    Context manager para transações (Boilerplate reduction).
    
    Args:
        doc: Documento do Revit
        name (str): Nome da transação
        
    Returns:
        Transaction: Context manager de transação
    """
    from pyrevit import revit
    return revit.Transaction(name, doc)

