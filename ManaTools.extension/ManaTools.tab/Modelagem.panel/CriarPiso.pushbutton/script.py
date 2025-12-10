# -*- coding: utf-8 -*-
"""
Cria Pisos em Ambientes selecionados.
FIX: Fluxo de seleção robusto e suporte a Portas.
"""
import os
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import BuiltInCategory, BuiltInParameter, Transaction, SpatialElementTag
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import flooring, finishes

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# --- HELPER: NOME SEGURO ---
def get_name_safe(element):
    """Leitura de nome à prova de falhas."""
    for bip in [BuiltInParameter.ALL_MODEL_TYPE_NAME, BuiltInParameter.ROOM_NAME, BuiltInParameter.SYMBOL_NAME_PARAM]:
        try:
            p = element.get_Parameter(bip)
            if p and p.HasValue:
                return p.AsString()
        except:
            pass
    try:
        if hasattr(element, "Name") and element.Name:
            return element.Name
    except:
        pass
    return "Elemento <{}>".format(element.Id)

# --- 1. LÓGICA DE SELEÇÃO ROBUSTA ---
selection = revit.get_selection()
final_elements = [] # Rooms + Doors
seen_ids = set()

def process_element(elem):
    """Adiciona Room ou Door à lista de processamento."""
    if not elem or not elem.Category: return
    
    cat_id = elem.Category.Id.IntegerValue
    
    # Ambientes
    if cat_id == int(BuiltInCategory.OST_Rooms):
        if elem.Id not in seen_ids:
            final_elements.append(elem)
            seen_ids.add(elem.Id)
            
    # Portas (Novidade!)
    elif cat_id == int(BuiltInCategory.OST_Doors):
        if elem.Id not in seen_ids:
            final_elements.append(elem)
            seen_ids.add(elem.Id)

    # Tags de Ambiente
    elif cat_id == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            room = None
            if hasattr(elem, "Room") and elem.Room: room = elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"): room = elem.GetTaggedLocalElement()
            
            if room and room.Id not in seen_ids:
                final_elements.append(room)
                seen_ids.add(room.Id)

# Tenta processar seleção atual
for s in selection: process_element(s)

# Se nada selecionado, pede seleção manual
if not final_elements:
    try:
        with forms.WarningBar(title="Selecione Ambientes, Tags ou Portas (ESC para sair):"):
            refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes, Tags ou Portas")
            for r in refs:
                process_element(doc.GetElement(r))
    except OperationCanceledException:
        script.exit()

if not final_elements:
    forms.alert("Nada selecionado.", exitscript=True)

# --- 2. Preparação de Dados UI ---
all_floor_types = flooring.get_floor_types(doc)
all_levels = finishes.get_levels(doc)

dict_floors = {get_name_safe(f): f for f in sorted(all_floor_types, key=lambda x: get_name_safe(x))}
dict_levels = {l.Name: l for l in all_levels}

# --- 3. Janela de Configuração ---
class FloorWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_floor_type.ItemsSource = dict_floors.keys()
        self.cb_level.ItemsSource = dict_levels.keys()
        
        if dict_floors: self.cb_floor_type.SelectedIndex = 0
        if dict_levels: self.cb_level.SelectedIndex = 0
        
        self.run_script = False

    def button_create_clicked(self, sender, args):
        self.run_script = True
        self.Close()

win = FloorWindow()
win.ShowDialog()

if not win.run_script: script.exit()

# --- 4. Processamento dos Inputs ---
sel_floor = dict_floors[win.cb_floor_type.SelectedItem] if win.cb_floor_type.SelectedItem else None
if not sel_floor: script.exit()

sel_level = dict_levels[win.cb_level.SelectedItem] if win.cb_level.SelectedItem else None
if not sel_level: forms.alert("Nível inválido.", exitscript=True)

is_merge = win.chk_merge.IsChecked

try:
    val_offset = float(win.tb_offset.Text) / 30.48
    val_overlap = float(win.tb_overlap.Text) / 30.48 # CM -> Feet
except:
    forms.alert("Valores numéricos inválidos.", exitscript=True)

# --- 5. Execução ---
count = 0
with revit.Transaction("Criar Pisos Maná"):
    new_floors = flooring.create_floors(
        doc, 
        final_elements, 
        sel_floor, 
        sel_level, 
        val_offset,
        door_overlap=val_overlap,
        merge_all=is_merge
    )
    count = len(new_floors)

if count > 0:
    forms.toast("{} Pisos criados!".format(count))
else:
    forms.alert("Nenhum piso criado.")
