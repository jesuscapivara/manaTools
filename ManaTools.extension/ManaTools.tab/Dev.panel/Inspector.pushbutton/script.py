# -*- coding: utf-8 -*-
"""
LISTA DE PARAMETROS (Raio-X).
Mostra Nome Visual vs BuiltInParameter (Essencial para Dev).
"""
from Autodesk.Revit.DB import ElementType
from pyrevit import script, revit, forms

doc = __revit__.ActiveUIDocument.Document
output = script.get_output()

# --- 1. Seleção ---
selection = revit.get_selection()
if not selection:
    forms.alert("Selecione um elemento para inspecionar.", exitscript=True)

element = selection[0]  # Pega o primeiro item
element_type = doc.GetElement(element.GetTypeId()) if not isinstance(element, ElementType) else element

# --- HELPER: Extrai dados do parâmetro ---
def get_param_data(param):
    # 1. Valor Legível
    if not param.HasValue:
        val = "(Vazio)"
    else:
        # Tenta pegar string, se não der, converte valor
        val = param.AsValueString() or param.AsString() or str(param.AsDouble()) or str(param.AsInteger())
    
    # 2. Definição Interna (O Ouro do Dev)
    definition = param.Definition
    
    # Tenta descobrir o BuiltInParameter
    try:
        # Em versões novas do Revit/PyRevit, acessamos assim:
        bip = param.Definition.BuiltInParameter
    except:
        bip = "Custom/Shared"

    return [definition.Name, str(bip), val, str(param.StorageType)]

# --- 2. Coleta Dados de INSTÂNCIA ---
data_instance = []
if not isinstance(element, ElementType):
    for p in element.Parameters:
        data_instance.append(get_param_data(p))

# --- 3. Coleta Dados de TIPO ---
data_type = []
if element_type:
    for p in element_type.Parameters:
        data_type.append(get_param_data(p))

# --- 4. Renderiza Tabelas ---
output.print_md("### 🕵️‍♂️ Inspector Maná: {}".format(element.Name))
output.print_md("**ID do Elemento:** {}".format(element.Id))

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

