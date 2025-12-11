# -*- coding: utf-8 -*-
"""Lógica de manipulação de Esquadrias (Portas e Janelas)."""
import re
from Autodesk.Revit.DB import BuiltInParameter


def sanitize_name(text):
    """
    Limpeza Militar: Permite apenas Letras, Números, Espaço, Hífen, Ponto e Underline.
    Remove qualquer caractere especial que possa causar o erro 'Name'.
    """
    if not text: return ""
    # Substitui qualquer coisa que NÃO seja (a-z, 0-9, -, _, ., espaço) por vazio
    # Isso elimina caracteres invisíveis, quebras de linha ou símbolos ilegais.
    return re.sub(r'[^a-zA-Z0-9 \-\_\.]', '', text).strip()


def to_cm(value_internal):
    """Converte pés para cm arredondado."""
    if value_internal is None: return 0
    return int(round(value_internal * 30.48))


def get_dimensions(element_type):
    """
    Busca Largura e Altura em cm.
    Inclui suporte a FURNITURE_WIDTH (identificado no seu Inspector).
    """
    # 1. Parâmetros BuiltIn
    w = element_type.get_Parameter(BuiltInParameter.FAMILY_WIDTH_PARAM)
    h = element_type.get_Parameter(BuiltInParameter.FAMILY_HEIGHT_PARAM)
    
    # Fallbacks (Janelas / Mobiliário)
    if not w: w = element_type.get_Parameter(BuiltInParameter.WINDOW_WIDTH)
    if not h: h = element_type.get_Parameter(BuiltInParameter.WINDOW_HEIGHT)
    if not w: w = element_type.get_Parameter(BuiltInParameter.FURNITURE_WIDTH)  # <--- O segredo da sua porta
    
    # 2. Busca por Nome
    if not w: w = element_type.LookupParameter("Largura") or element_type.LookupParameter("Width")
    if not h: h = element_type.LookupParameter("Altura") or element_type.LookupParameter("Height")

    val_w = to_cm(w.AsDouble()) if w and w.HasValue else 0
    val_h = to_cm(h.AsDouble()) if h and h.HasValue else 0
    
    return val_w, val_h


def generate_new_name(element_type):
    """Gera: MARCA - LxH (Sanitizado)"""
    # Marca de Tipo
    p_mark = element_type.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK)
    if not p_mark: p_mark = element_type.get_Parameter(BuiltInParameter.WINDOW_TYPE_ID)

    if p_mark and p_mark.HasValue and p_mark.AsString():
        prefix = p_mark.AsString()
    else:
        prefix = element_type.FamilyName

    w, h = get_dimensions(element_type)
    if w == 0 or h == 0: return None 

    raw_name = "{} - {}x{}".format(prefix, w, h)
    return sanitize_name(raw_name)
