# -*- coding: utf-8 -*-
"""
Renomeia Marcas de Tipo (P1, J1...) baseado na quantidade de instâncias (Curva ABC).
O Tipo com mais cópias no projeto vira o número 1.
"""
from collections import defaultdict
from Autodesk.Revit.DB import FilteredElementCollector, BuiltInCategory, BuiltInParameter, Transaction
from pyrevit import forms, script, revit

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

def get_types_sorted_by_count(category_id):
    """
    Retorna uma lista de Tipos (ElementTypes) ordenados pela quantidade de uso no modelo.
    Mais usados primeiro.
    """
    # 1. Coletar todas as INSTÂNCIAS (Portas/Janelas físicas)
    instances = FilteredElementCollector(doc)\
                .OfCategory(category_id)\
                .WhereElementIsNotElementType()\
                .ToElements()
    
    if not instances: return []

    # 2. Contar frequência dos Tipos
    # Dicionário: { TypeId : Contagem }
    type_counts = defaultdict(int)
    
    # Dicionário para recuperar o Elemento Tipo pelo ID depois
    type_map = {} 

    for inst in instances:
        try:
            tid = inst.GetTypeId()
            if tid.IntegerValue > 0:  # Ignora elementos sem tipo válido
                type_counts[tid] += 1
                
                # Guarda o objeto do tipo se ainda não guardou
                if tid not in type_map:
                    type_map[tid] = doc.GetElement(tid)
        except: pass

    # 3. Ordenar (Do maior para o menor)
    # Retorna uma lista de tuplas [(TypeId, Count), ...]
    sorted_ids = sorted(type_counts, key=type_counts.get, reverse=True)
    
    # Retorna a lista de objetos Type ordenados
    return [type_map[tid] for tid in sorted_ids]

def rename_marks(category_name, types_list, prefix):
    """Aplica P1, P2... J1, J2..."""
    count = 0
    
    for i, el_type in enumerate(types_list):
        new_mark = "{}{}".format(prefix, i + 1)  # Ex: P1
        
        # Pega o parâmetro "Marca de Tipo"
        p_mark = el_type.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_MARK)
        
        if p_mark and not p_mark.IsReadOnly:
            current = p_mark.AsString()
            
            # Só muda se for diferente para evitar processamento inútil
            if current != new_mark:
                p_mark.Set(new_mark)
                print("✅ {} -> {} ({} un.)".format(el_type.FamilyName, new_mark, "??")) 
                # Nota: Para performance, não recutamos a contagem aqui no print
                count += 1
        else:
            print("⚠️ Travado: " + el_type.FamilyName)

    return count

# --- UI ---
options = ["Portas (P1, P2...)", "Janelas (J1, J2...)", "Ambas"]
res = forms.CommandSwitchWindow.show(options, message="Renomear Marcas de Tipo por Quantidade:")

if not res: script.exit()

# --- EXECUÇÃO ---
with revit.Transaction("Renomear Marcas de Tipo"):
    
    # >> PORTAS
    if res in ["Portas (P1, P2...)", "Ambas"]:
        print("--- PROCESSANDO PORTAS ---")
        sorted_doors = get_types_sorted_by_count(BuiltInCategory.OST_Doors)
        
        if sorted_doors:
            # Passada de Limpeza (Opcional, mas evita aviso de duplicidade do Revit)
            # Renomeia tudo para um GUID temporário antes? 
            # R: O Revit aceita duplicata em Mark com aviso. Vamos direto para simplicidade.
            
            count = rename_marks("Portas", sorted_doors, "P")
            print("Total Portas Renomeadas: {}".format(count))
        else:
            print("Nenhuma porta encontrada.")
            
    # >> JANELAS
    if res in ["Janelas (J1, J2...)", "Ambas"]:
        print("\n--- PROCESSANDO JANELAS ---")
        sorted_windows = get_types_sorted_by_count(BuiltInCategory.OST_Windows)
        
        if sorted_windows:
            count = rename_marks("Janelas", sorted_windows, "J")
            print("Total Janelas Renomeadas: {}".format(count))
        else:
            print("Nenhuma janela encontrada.")

forms.alert("Processo Finalizado! Confira o console.", title="Maná Type Marks")

