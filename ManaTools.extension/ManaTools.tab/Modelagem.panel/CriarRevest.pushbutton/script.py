# -*- coding: utf-8 -*-
"""
Cria revestimentos (cebola) em Ambientes.
FIX: UI Nativa (WPF/XAML) e leitura correta de nomes (ALL_MODEL_TYPE_NAME).
"""
import os
import clr
clr.AddReference("System.Windows.Forms")
clr.AddReference("System.Drawing")

from Autodesk.Revit.DB import BuiltInCategory, BuiltInParameter, Transaction, Element, SpatialElementTag
from pyrevit import forms, script, revit
from manalib import finishes, config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

CMD_ID = "manatools_criarrevest"

# --- HELPER: NOME SEGURO (Baseado nos seus HTMLs) ---
def get_name_safe(element):
    """Lê o nome correto dependendo se é Tipo, Instância ou Ambiente."""
    # 1. Tenta Parâmetros BuiltIn Específicos (Prioridade)
    for bip in [
        BuiltInParameter.ALL_MODEL_TYPE_NAME, # Para Tipos de Parede
        BuiltInParameter.ROOM_NAME,           # Para Ambientes
        BuiltInParameter.SYMBOL_NAME_PARAM    # Fallback
    ]:
        try:
            p = element.get_Parameter(bip)
            if p and p.HasValue:
                v = p.AsString()
                if v: return v
        except: pass

    # 2. Tenta Propriedade .Name padrão
    try:
        if hasattr(element, "Name") and element.Name:
            return element.Name
    except: pass
        
    return "Elemento <{}>".format(element.Id)

# --- 1. Seleção ---
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
        ref = uidoc.Selection.PickObject(Autodesk.Revit.UI.Selection.ObjectType.Element, "Selecione um Ambiente ou Tag")
        elem = doc.GetElement(ref)
        process_element(elem)
        
        if not final_rooms:
            forms.alert("O elemento selecionado não é um Ambiente nem uma Tag válida.", exitscript=True)
    except:
        script.exit() # Sai silenciosamente no ESC

# --- 2. Dados para UI ---
all_wall_types = finishes.get_wall_types(doc)
all_levels = finishes.get_levels(doc)

# Dicionários (Nome -> Objeto)
# Usamos o get_name_safe para garantir que apareça "Interior - Assentar blocos..."
dict_walls = {get_name_safe(w): w for w in sorted(all_wall_types, key=lambda x: get_name_safe(x))}
dict_levels = {l.Name: l for l in all_levels}

# --- 3. UI WINDOW (XAML EMBUTIDO) ---
class RevestWindow(forms.WPFWindow):
    def __init__(self):
        # Carrega o arquivo .xaml que está na mesma pasta deste script
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        # Popula Combos
        self.cb_wall_type.ItemsSource = dict_walls.keys()
        self.cb_base_level.ItemsSource = dict_levels.keys()
        
        # Adiciona opção Desconectado no Topo
        top_opts = list(dict_levels.keys())
        top_opts.insert(0, "(Desconectado)")
        self.cb_top_level.ItemsSource = top_opts

        # Load Config
        cfg = config_manager.get_config(CMD_ID)
        
        # Defaults
        self.cb_wall_type.SelectedIndex = 0
        self.cb_base_level.SelectedIndex = 0
        self.cb_top_level.SelectedIndex = 0 
        
        # Restore
        if getattr(cfg, "last_wall_type", None) in dict_walls:
            self.cb_wall_type.SelectedItem = cfg.last_wall_type
            
        if getattr(cfg, "last_base_level", None) in dict_levels:
            self.cb_base_level.SelectedItem = cfg.last_base_level
            
        if getattr(cfg, "last_top_level", None):
            # Procura item (pode ser (Desconectado))
            for i, item in enumerate(top_opts):
                if item == cfg.last_top_level:
                    self.cb_top_level.SelectedIndex = i
                    break
                    
        self.tb_base_offset.Text = getattr(cfg, "last_base_offset", "0")
        self.tb_height.Text = getattr(cfg, "last_height", "280")

    def button_create_clicked(self, sender, args):
        # Save Config
        config_manager.save_config(CMD_ID, {
            "last_wall_type": self.cb_wall_type.SelectedItem,
            "last_base_level": self.cb_base_level.SelectedItem,
            "last_top_level": self.cb_top_level.SelectedItem,
            "last_base_offset": self.tb_base_offset.Text,
            "last_height": self.tb_height.Text
        })
        self.Close()

# Abre Janela
win = RevestWindow()
win.ShowDialog()

# --- 4. Processamento ---
# Se o usuário fechou sem clicar, wall_type será None ou vazio
if not win.cb_wall_type.SelectedItem:
    script.exit()

# Recupera Inputs
sel_wall_name = win.cb_wall_type.SelectedItem
sel_base_name = win.cb_base_level.SelectedItem
sel_top_name = win.cb_top_level.SelectedItem

selected_wall_type = dict_walls[sel_wall_name]
selected_base_level = dict_levels[sel_base_name]

# Lógica do Topo (Se for desconectado, passa None)
selected_top_level = None
if sel_top_name != "(Desconectado)":
    selected_top_level = dict_levels[sel_top_name]

# Conversão CM -> Feet
try:
    h_cm = float(win.tb_height.Text)
    off_cm = float(win.tb_base_offset.Text)
    val_height = h_cm / 30.48
    val_offset = off_cm / 30.48
except:
    forms.alert("Valores numéricos inválidos. Use ponto para decimais.", exitscript=True)

# --- 5. Execução ---
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
