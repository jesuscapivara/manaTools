# -*- coding: utf-8 -*-
"""
LISTA DE PARAMETROS (Raio-X).
FIX: Suporte a Ambientes (Rooms) que não possuem propriedade .Name direta.
"""
from Autodesk.Revit.DB import ElementType, BuiltInParameter
from pyrevit import script, revit, forms

doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

# --- HELPER: NOME ROBUSTO ---
def get_element_name(element):
    """Recupera nome de qualquer coisa (Room, Wall, Type)."""
    # 1. Tenta propriedade padrão
    try:
        if hasattr(element, "Name"): return element.Name
    except: pass
    
    # 2. Tenta parâmetros específicos
    for bip in [BuiltInParameter.ROOM_NAME, BuiltInParameter.SYMBOL_NAME_PARAM]:
        try:
            p = element.get_Parameter(bip)
            if p and p.HasValue: return p.AsString()
        except: pass
        
    return "Elemento ID: {}".format(element.Id)

# --- 1. Seleção ---
selection = revit.get_selection()

if selection:
    element = selection[0]
else:
    # Permite clicar no elemento mesmo sem pré-seleção
    try:
        picked = revit.pick_element(message="Selecione um elemento para inspecionar")
        if not picked:
            script.exit()
        element = picked
    except Exception:
        forms.alert("Nenhum elemento selecionado.", exitscript=True)

# Pega o Tipo se não for Tipo
element_type = doc.GetElement(element.GetTypeId()) if hasattr(element, "GetTypeId") and element.GetTypeId().IntegerValue > 0 else None

# --- HELPER: Extrai dados do parâmetro ---
def get_param_data(param):
    if not param.HasValue:
        val = "(Vazio)"
    else:
        val = param.AsValueString() or param.AsString() or str(param.AsDouble()) or str(param.AsInteger())
    
    definition = param.Definition
    try:
        bip = param.Definition.BuiltInParameter
    except:
        bip = "Custom/Shared"

    return [definition.Name, str(bip), val, str(param.StorageType)]

# --- 2. Coleta Dados ---
data_instance = []
try:
    for p in element.Parameters:
        data_instance.append(get_param_data(p))
except: pass

data_type = []
if element_type:
    try:
        for p in element_type.Parameters:
            data_type.append(get_param_data(p))
    except: pass

# --- 3. Renderiza ---
# AQUI ESTAVA O ERRO: Substituímos element.Name pela função segura
safe_name = get_element_name(element)

output.print_md("### 🕵️‍♂️ Inspector Maná: {}".format(safe_name))
output.print_md("**ID do Elemento:** {}".format(element.Id))
output.print_md("**Categoria:** {}".format(element.Category.Name if element.Category else "Sem Categoria"))

if data_instance:
    output.print_md("#### 📦 Parâmetros de Instância")
    output.print_table(
        table_data=sorted(data_instance, key=lambda x: x[0]),
        columns=["Nome (UI)", "Internal Name (Code)", "Valor Atual", "Tipo de Dado"]
    )

if data_type:
    output.print_md("#### 🏗️ Parâmetros de Tipo")
    output.print_table(
        table_data=sorted(data_type, key=lambda x: x[0]),
        columns=["Nome (UI)", "Internal Name (Code)", "Valor Atual", "Tipo de Dado"]
    )
