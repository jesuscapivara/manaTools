# -*- coding: utf-8 -*-
"""
Cria Pisos em Ambientes selecionados.
FIX: Fluxo de seleção robusto (Esc para sair) e validação de janela.
"""
import os
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import BuiltInCategory, BuiltInParameter, Transaction, SpatialElementTag
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException  # <--- Importante para o ESC
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
final_rooms = []
seen_ids = set()

def process_element(elem):
    """Extrai o Room de um Elemento (seja Room ou Tag)."""
    room = None
    if not elem or not elem.Category:
        return
    
    cat_id = elem.Category.Id.IntegerValue
    
    if cat_id == int(BuiltInCategory.OST_Rooms):
        room = elem
    elif cat_id == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            if hasattr(elem, "Room") and elem.Room:
                room = elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"):
                room = elem.GetTaggedLocalElement()

    if room and room.Id not in seen_ids:
        final_rooms.append(room)
        seen_ids.add(room.Id)

# Tenta processar o que já estava selecionado antes de clicar no botão
for s in selection:
    process_element(s)

# Se não tinha nada selecionado, entra no modo "Esperar Seleção"
if not final_rooms:
    try:
        # Prompt visual para o usuário
        with forms.WarningBar(title="Selecione os Ambientes ou Tags e clique em Concluir (ou ESC para cancelar):"):
            # PickObjects permite selecionar vários. O script "pausa" aqui esperando o usuário.
            refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes ou Tags")
            
            for r in refs:
                process_element(doc.GetElement(r))
                
    except OperationCanceledException:
        # Se o usuário der ESC, o script morre aqui silenciosamente.
        script.exit()

# Validação final antes de abrir a janela
if not final_rooms:
    # Se selecionou coisas erradas (ex: paredes) e a lista continuou vazia
    forms.alert("Nenhum ambiente válido foi selecionado.", exitscript=True)

# --- 2. Preparação de Dados UI ---
all_floor_types = flooring.get_floor_types(doc)
all_levels = finishes.get_levels(doc)

dict_floors = {get_name_safe(f): f for f in sorted(all_floor_types, key=lambda x: get_name_safe(x))}
dict_levels = {l.Name: l for l in all_levels}

# --- 3. Janela de Configuração (Com Trava de Cancelamento) ---
class FloorWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_floor_type.ItemsSource = dict_floors.keys()
        self.cb_level.ItemsSource = dict_levels.keys()
        
        if dict_floors:
            self.cb_floor_type.SelectedIndex = 0
        if dict_levels:
            self.cb_level.SelectedIndex = 0
        
        # Flag de Controle: Assume falso até que se clique no botão criar
        self.run_script = False

    def button_create_clicked(self, sender, args):
        # Usuário clicou no botão, podemos rodar
        self.run_script = True
        self.Close()

win = FloorWindow()
win.ShowDialog()

# --- VERIFICAÇÃO DE CANCELAMENTO DA JANELA ---
# Se fechou no X ou deu Alt+F4, run_script será False
if not win.run_script:
    script.exit()

# --- 4. Processamento dos Inputs ---
# Se chegou aqui, é seguro ler os valores
if win.cb_floor_type.SelectedItem:
    sel_floor = dict_floors[win.cb_floor_type.SelectedItem]
else:
    script.exit()

if win.cb_level.SelectedItem:
    sel_level = dict_levels[win.cb_level.SelectedItem]
else:
    forms.alert("Selecione um nível válido.", exitscript=True)

is_merge = win.chk_merge.IsChecked

try:
    val_offset = float(win.tb_offset.Text) / 30.48
except:
    forms.alert("Valor de deslocamento inválido. Use ponto para decimais.", exitscript=True)

# --- 5. Execução (Transação) ---
# Só abre a transação se passou por todas as barreiras acima
count = 0
with revit.Transaction("Criar Pisos Maná"):
    new_floors = flooring.create_floors(
        doc, 
        final_rooms, 
        sel_floor, 
        sel_level, 
        val_offset, 
        merge_all=is_merge
    )
    count = len(new_floors)

if count > 0:
    forms.toast("{} Pisos criados com sucesso!".format(count))
else:
    forms.alert("Nenhum piso criado. Verifique se os ambientes estão fechados corretamente.")
