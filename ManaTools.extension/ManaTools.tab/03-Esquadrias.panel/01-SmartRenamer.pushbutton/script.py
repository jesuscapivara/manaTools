# -*- coding: utf-8 -*-
"""
Renomeia Tipos de Esquadrias.
FIX CRÍTICO: Substituída a leitura de .Name por SYMBOL_NAME_PARAM para evitar AttributeError.
"""
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter, Element, ElementType
from pyrevit import forms, script, revit
from manalib import joinery, revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# --- HELPER: LEITURA SEGURA DO NOME ---
def get_name_safe(element):
    """
    Tenta ler o nome do tipo de todas as formas possíveis.
    Evita o AttributeError: Name em ambientes instáveis.
    """
    # 1. Tenta pelo Parâmetro Interno (Mais robusto)
    try:
        p = element.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.HasValue:
            return p.AsString()
    except: pass

    # 2. Tenta pelo BuiltIn genérico de Tipo
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.HasValue:
            return p.AsString()
    except: pass

    # 3. Tenta pela propriedade Python (que estava falhando)
    try:
        return element.Name
    except: pass

    return ""  # Desiste

# --- 1. Seleção Inteligente ---
selection = revit_utils.get_selected_elements(doc)
target_types = set() 

def add_to_targets(elem):
    if isinstance(elem, Element):
        try:
            if not elem.Category: return
            cid = elem.Category.Id.IntegerValue
            if cid in [int(BuiltInCategory.OST_Doors), int(BuiltInCategory.OST_Windows)]:
                if isinstance(elem, ElementType): 
                    target_types.add(elem)
                else:
                    tid = elem.GetTypeId()
                    if tid.IntegerValue > 0:
                        target_types.add(doc.GetElement(tid))
        except: pass

if not selection:
    if forms.alert("Renomear TODAS as Portas e Janelas do projeto?", options=["Sim", "Não"]) == "Não":
        script.exit()
    
    doors = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Doors).WhereElementIsElementType().ToElements()
    wins = FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Windows).WhereElementIsElementType().ToElements()
    for d in doors: target_types.add(d)
    for w in wins: target_types.add(w)

else:
    for s in selection: add_to_targets(s)

if not target_types: forms.alert("Nada encontrado.", exitscript=True)

# --- 2. Execução ---
count_ok = 0
count_err = 0

with revit_utils.setup_transaction(doc, "Smart Rename"):
    
    sorted_elements = sorted(list(target_types), key=lambda x: x.FamilyName)
    
    with forms.ProgressBar(title='Padronizando...', cancellable=True) as pb:
        for i, el_type in enumerate(sorted_elements):
            if pb.cancelled: break
            
            try:
                # 1. Gera nome ideal
                new_name = joinery.generate_new_name(el_type)
                
                if not new_name:
                    continue
                
                # LEITURA SEGURA AQUI (Substitui el_type.Name)
                current_name = get_name_safe(el_type)
                
                if current_name == new_name:
                    continue

                # 2. Tenta Renomear
                try:
                    el_type.Name = new_name
                    count_ok += 1

                except Exception as e_rename:
                    # Se falhar (ex: duplicidade ou AttributeError no Setter), tenta ID
                    error_msg = str(e_rename)

                    unique_name = "{} (ID:{})".format(new_name, el_type.Id)
                    try:
                        el_type.Name = unique_name
                        count_ok += 1
                    except Exception as e_final:
                        count_err += 1

            except Exception as e:
                count_err += 1
            
            pb.update_progress(i+1, len(sorted_elements))

# --- 3. Relatório ---
if count_ok > 0:
    forms.toast("{} Tipos renomeados!".format(count_ok))
elif count_err > 0:
    forms.alert("Erros detectados. Veja o console (Shift+Click).")
else:
    forms.alert("Nenhuma alteração necessária.")
