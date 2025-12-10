# -*- coding: utf-8 -*-
"""
Cria revestimentos (cebola) em Ambientes.
FIX: Interface separada (script.xaml) e Suporte a Tags de Ambiente.
"""
import os
from Autodesk.Revit.DB import BuiltInCategory, BuiltInParameter, Transaction, Element, SpatialElementTag
from Autodesk.Revit.UI import Selection
from pyrevit import forms, script, revit
from manalib import finishes

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# --- HELPER: NOME SEGURO ---
def get_name_safe(element):
    """Lê o nome correto dependendo se é Tipo, Instância ou Ambiente."""
    # Tenta Parâmetros BuiltIn
    for bip in [BuiltInParameter.ALL_MODEL_TYPE_NAME, BuiltInParameter.ROOM_NAME, BuiltInParameter.SYMBOL_NAME_PARAM]:
        try:
            p = element.get_Parameter(bip)
            if p and p.HasValue: return p.AsString()
        except: pass
    
    # Tenta Propriedade .Name
    try:
        if hasattr(element, "Name") and element.Name: return element.Name
    except: pass
        
    return "Elemento <{}>".format(element.Id)

# --- 1. Seleção Inteligente (Rooms + Tags) ---
selection = revit.get_selection()
final_rooms = []
seen_ids = set()

def process_element(elem):
    """Extrai o Room de um Elemento (seja Room ou Tag)."""
    room = None
    if not elem.Category: return

    cat_id = elem.Category.Id.IntegerValue
    
    # Caso 1: É o próprio Ambiente
    if cat_id == int(BuiltInCategory.OST_Rooms):
        room = elem
        
    # Caso 2: É uma Tag de Ambiente (A novidade!)
    elif cat_id == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            # Tenta pegar o ambiente associado (Sem link, modelo atual)
            if elem.Room: 
                room = elem.Room
            # Nota: Se for Tag de Link, a lógica é mais complexa, focando no local agora.

    # Adiciona se válido e não duplicado
    if room and room.Id not in seen_ids:
        final_rooms.append(room)
        seen_ids.add(room.Id)

# Processa Seleção Atual
for s in selection: process_element(s)

# Se nada selecionado, pede seleção manual
if not final_rooms:
    try:
        ref = uidoc.Selection.PickObject(Selection.ObjectType.Element, "Selecione um Ambiente ou Tag")
        elem = doc.GetElement(ref)
        process_element(elem)
        
        if not final_rooms:
            forms.alert("O elemento selecionado não é um Ambiente nem uma Tag válida.", exitscript=True)
    except:
        forms.alert("Selecione pelo menos um Ambiente ou Tag.", exitscript=True)

# --- 2. Dados para UI ---
all_wall_types = finishes.get_wall_types(doc)
all_levels = finishes.get_levels(doc)

dict_walls = {get_name_safe(w): w for w in sorted(all_wall_types, key=lambda x: get_name_safe(x))}
dict_levels = {l.Name: l for l in all_levels}

# --- 3. UI WINDOW (Carrega do arquivo script.xaml) ---
class RevestWindow(forms.WPFWindow):
    def __init__(self):
        # Carrega o arquivo .xaml que está na mesma pasta deste script
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        # Popula Combos
        self.cb_wall_type.ItemsSource = dict_walls.keys()
        self.cb_base_level.ItemsSource = dict_levels.keys()
        
        top_opts = list(dict_levels.keys())
        top_opts.insert(0, "(Desconectado)")
        self.cb_top_level.ItemsSource = top_opts

        # Defaults
        if dict_walls: self.cb_wall_type.SelectedIndex = 0
        if dict_levels: self.cb_base_level.SelectedIndex = 0
        self.cb_top_level.SelectedIndex = 0 

    def button_create_clicked(self, sender, args):
        self.Close()

# Abre Janela
win = RevestWindow()
win.ShowDialog()

if not win.cb_wall_type.SelectedItem: script.exit()

# Recupera Inputs
selected_wall_type = dict_walls[win.cb_wall_type.SelectedItem]
selected_base_level = dict_levels[win.cb_base_level.SelectedItem]
selected_top_level = None

sel_top_name = win.cb_top_level.SelectedItem
if sel_top_name != "(Desconectado)":
    selected_top_level = dict_levels[sel_top_name]

try:
    val_height = float(win.tb_height.Text) / 30.48
    val_offset = float(win.tb_base_offset.Text) / 30.48
except:
    forms.alert("Valores numéricos inválidos.", exitscript=True)

# --- 4. Execução ---
count = 0
with revit.Transaction("Criar Revestimentos"):
    for room in final_rooms:
        walls = finishes.create_finishes_in_room(
            doc, 
            room, 
            selected_wall_type, 
            selected_base_level, 
            selected_top_level, 
            val_height, 
            val_offset
        )
        count += len(walls)

if count > 0:
    forms.toast("{} paredes criadas em {} ambiente(s).".format(count, len(final_rooms)))
else:
    forms.alert("Nenhuma parede criada. Verifique os limites do ambiente.")
