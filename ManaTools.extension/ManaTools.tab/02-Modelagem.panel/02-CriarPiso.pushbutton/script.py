# -*- coding: utf-8 -*-
"""
Cria Pisos em Ambientes e Portas selecionados.
V2.0: Seleção Interativa Filtrada (Ambientes + Portas).
"""
import os
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import flooring, finishes, config_manager, bim_utils

# --- SECURITY CHECK ---
if not bim_utils.calculate_vector_matrix()[0]:
    forms.alert("ACESSO NEGADO: " + bim_utils.calculate_vector_matrix()[1] + "\n\nPor favor, faça Login na aba 'Gestão'.", exitscript=True)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_criarpiso"

# --- 1. FILTRO DE SELEÇÃO VISUAL ---
class FloorSelectionFilter(ISelectionFilter):
    """
    Permite selecionar Ambientes (para o piso principal) e Portas (para soleiras/transições).
    """
    def AllowElement(self, elem):
        if not elem.Category: return False
        cid = elem.Category.Id.IntegerValue
        
        # Aceita Ambientes
        if cid == int(BuiltInCategory.OST_Rooms): return True
        # Aceita Tags de Ambiente
        if cid == int(BuiltInCategory.OST_RoomTags): return True
        # Aceita Portas (para gerar o 'bridge' do piso)
        if cid == int(BuiltInCategory.OST_Doors): return True
        
        return False

    def AllowReference(self, reference, position):
        return False

# --- 2. SELEÇÃO INTERATIVA ---
def get_user_selection():
    elements = []
    seen_ids = set()
    
    # Verifica seleção prévia
    pre_selection = uidoc.Selection.GetElementIds()
    if pre_selection:
        filter_instance = FloorSelectionFilter()
        for eid in pre_selection:
            elem = doc.GetElement(eid)
            if filter_instance.AllowElement(elem):
                processed = process_element(elem)
                if processed and processed.Id not in seen_ids:
                    elements.append(processed)
                    seen_ids.add(processed.Id)
        
        if elements: return elements

    # Se não, pede nova
    try:
        with forms.WarningBar(title="Clique em Ambientes e Portas (ESC para concluir):"):
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element, 
                FloorSelectionFilter(), 
                "Selecione Ambientes e Portas"
            )
            for r in refs:
                elem = doc.GetElement(r)
                processed = process_element(elem)
                if processed and processed.Id not in seen_ids:
                    elements.append(processed)
                    seen_ids.add(processed.Id)
    except OperationCanceledException:
        pass
        
    return elements

def process_element(elem):
    """Normaliza o elemento para Room ou Door."""
    if not elem or not elem.Category: return None
    cid = elem.Category.Id.IntegerValue
    
    if cid == int(BuiltInCategory.OST_Rooms):
        return elem
    elif cid == int(BuiltInCategory.OST_Doors):
        return elem
    elif cid == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            if elem.Room: return elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"): return elem.GetTaggedLocalElement()
    return None

def get_name_safe(element):
    for bip in [BuiltInParameter.ALL_MODEL_TYPE_NAME, BuiltInParameter.ROOM_NAME, BuiltInParameter.SYMBOL_NAME_PARAM]:
        p = element.get_Parameter(bip)
        if p and p.HasValue: return p.AsString()
    return getattr(element, "Name", "Elemento <{}>".format(element.Id))

# --- PREP DADOS ---
all_floor_types = flooring.get_floor_types(doc)
all_levels = finishes.get_levels(doc)

dict_floors = {get_name_safe(f): f for f in sorted(all_floor_types, key=get_name_safe)}
dict_levels = {l.Name: l for l in all_levels}

# --- GUI ---
class FloorWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.run_script = False
        
        self.cb_floor_type.ItemsSource = dict_floors.keys()
        self.cb_level.ItemsSource = dict_levels.keys()
        
        # Config Recovery
        cfg = config_manager.get_config(CMD_ID)
        
        self.cb_floor_type.SelectedIndex = 0
        last_floor = getattr(cfg, "last_floor_type", None)
        if last_floor and last_floor in dict_floors:
            self.cb_floor_type.SelectedItem = last_floor
            
        self.cb_level.SelectedIndex = 0
        last_level = getattr(cfg, "last_level", None)
        if last_level and last_level in dict_levels:
            self.cb_level.SelectedItem = last_level
        
        self.tb_offset.Text = getattr(cfg, "last_offset", "0")
        self.tb_overlap.Text = getattr(cfg, "last_overlap", "5")
        self.chk_merge.IsChecked = getattr(cfg, "last_merge", False)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_floor_type": self.cb_floor_type.SelectedItem,
            "last_level": self.cb_level.SelectedItem,
            "last_offset": self.tb_offset.Text,
            "last_overlap": self.tb_overlap.Text,
            "last_merge": self.chk_merge.IsChecked
        })
        self.Close()

win = FloorWindow()
win.ShowDialog()

# --- SÓ RODA SE CLICOU ---
if not win.run_script: script.exit()

# --- AGORA PEDE SELEÇÃO ---
final_elements = get_user_selection()

if not final_elements:
    script.exit()

# Tenta ser inteligente com o nível se o usuário não escolheu bem
# (Se o usuário deixou no default, mas selecionou coisas no Nível 2)
# Mas como já fechamos a janela, vamos confiar no input da GUI.

sel_floor = dict_floors.get(win.cb_floor_type.SelectedItem)
sel_level = dict_levels.get(win.cb_level.SelectedItem)

if not sel_floor or not sel_level:
    forms.alert("Configuração inválida.", exitscript=True)

try:
    val_offset = float(win.tb_offset.Text) / 30.48
    val_overlap = float(win.tb_overlap.Text) / 30.48
except:
    forms.alert("Valores numéricos inválidos.", exitscript=True)

# --- EXECUÇÃO ---
with revit.Transaction("Criar Pisos"):
    try:
        new_floors = flooring.create_floors(
            doc, 
            final_elements, # Lista mista de Rooms e Doors
            sel_floor, 
            sel_level, 
            val_offset, 
            door_overlap=val_overlap,
            merge_all=win.chk_merge.IsChecked
        )
        
        if new_floors:
            forms.toast("{} Pisos criados com sucesso!".format(len(new_floors)))
        else:
            forms.alert("Nenhum piso criado. Verifique se os ambientes estão fechados.")
            
    except Exception as e:
        forms.alert("Erro ao criar pisos: {}".format(e))