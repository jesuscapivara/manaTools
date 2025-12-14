# -*- coding: utf-8 -*-
"""
Cria Soleiras (Floors) sob portas selecionadas.
V2.1: Correção de Largura (Leitura Robusta) + Seleção Interativa.
"""
import os
import clr
import math
from System.Collections.Generic import List

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import config_manager, bim_utils

# --- SECURITY CHECK ---
if not bim_utils.calculate_vector_matrix()[0]:
    forms.alert("ACESSO NEGADO: " + bim_utils.calculate_vector_matrix()[1] + "\n\nPor favor, faça Login na aba 'Gestão'.", exitscript=True)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_criarsoleira"

# --- 1. FILTRO DE SELEÇÃO VISUAL ---
class DoorSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        if not elem.Category: return False
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Doors): return True
        return False
    def AllowReference(self, reference, position): return False

# --- 2. SELEÇÃO INTERATIVA ---
def get_user_selection():
    doors = []
    seen_ids = set()
    
    pre_selection = uidoc.Selection.GetElementIds()
    if pre_selection:
        filter_instance = DoorSelectionFilter()
        for eid in pre_selection:
            elem = doc.GetElement(eid)
            if filter_instance.AllowElement(elem):
                if elem.Id not in seen_ids:
                    doors.append(elem)
                    seen_ids.add(elem.Id)
        if doors: return doors

    try:
        with forms.WarningBar(title="Clique nas Portas para criar Soleira (ESC para concluir):"):
            refs = uidoc.Selection.PickObjects(ObjectType.Element, DoorSelectionFilter(), "Selecione Portas")
            for r in refs: 
                elem = doc.GetElement(r)
                if elem.Id not in seen_ids:
                    doors.append(elem)
                    seen_ids.add(elem.Id)
    except OperationCanceledException: pass
    return doors

# --- 3. HELPER: NOMES ---
def get_name_hardcore(element):
    if not element: return "Nulo"
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.HasValue: return p.AsString()
    except: pass
    try: return Element.Name.GetValue(element)
    except: return "Elemento ID:{}".format(element.Id)

# --- 4. GEOMETRIA ROBUSTA ---
def get_door_width(door):
    """
    Tenta obter a largura do vão da porta de todas as formas possíveis.
    """
    # 1. Tenta Parâmetros de Instância e Tipo (Prioridade)
    params_to_check = [
        BuiltInParameter.DOOR_WIDTH,           # Largura Nativa
        BuiltInParameter.FURNITURE_WIDTH,      # Largura Mobiliário
        BuiltInParameter.FAMILY_WIDTH_PARAM,   # Largura Família
        BuiltInParameter.GENERIC_WIDTH         # Largura Genérica
    ]
    
    # Check Instance
    for pid in params_to_check:
        p = door.get_Parameter(pid)
        if p and p.HasValue:
            val = p.AsDouble()
            if val > 0.1: return val # Ignora valores zerados
            
    # Check Type
    symbol = door.Symbol
    if symbol:
        for pid in params_to_check:
            p = symbol.get_Parameter(pid)
            if p and p.HasValue:
                val = p.AsDouble()
                if val > 0.1: return val
                
    # 2. Tenta parâmetros por nome (String) - Caso seja parâmetro compartilhado
    for name in ["Width", "Largura", "Vão Luz", "Rough Width", "Largura Aproximada"]:
        p = door.LookupParameter(name)
        if not p: p = symbol.LookupParameter(name)
        if p and p.HasValue:
            val = p.AsDouble()
            if val > 0.1: return val

    return 0.8 # Fallback final (80cm)

def get_wall_width(wall):
    return wall.Width

def create_threshold_geometry(door, wall, side_offset, width_offset):
    pt_center = door.Location.Point
    lc = wall.Location
    if not isinstance(lc, LocationCurve): return None
    line = lc.Curve
    
    # Vetores da Parede
    # Normalizamos para garantir precisão
    vec_wall = (line.GetEndPoint(1) - line.GetEndPoint(0)).Normalize()
    
    # Vetor Perpendicular (Espessura)
    # Rotação 90 graus em Z: (x, y) -> (-y, x)
    vec_thick = XYZ(-vec_wall.Y, vec_wall.X, 0).Normalize()
    
    # Dimensões Reais
    d_width = get_door_width(door)
    w_thick = get_wall_width(wall)
    
    # Comprimento Total (Largura Porta + Folgas Laterais)
    length = d_width + (side_offset * 2)
    
    # Espessura Total (Espessura Parede + Folgas Transversais)
    thickness = w_thick + (width_offset * 2)
    
    # Vetores de Deslocamento (Metade para cada lado a partir do centro)
    v_long = vec_wall * (length / 2.0)
    v_trans = vec_thick * (thickness / 2.0)
    
    # Centro achatado (Z=0 relativo ao nível)
    center_flat = XYZ(pt_center.X, pt_center.Y, 0)
    
    # Vértices do Retângulo
    p1 = center_flat + v_long + v_trans
    p2 = center_flat - v_long + v_trans
    p3 = center_flat - v_long - v_trans
    p4 = center_flat + v_long - v_trans
    
    # Cria Loop
    loops = []
    lines = [
        Line.CreateBound(p1, p2), Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4), Line.CreateBound(p4, p1)
    ]
    loops.append(CurveLoop.Create(lines))
    return loops

# --- PREP DADOS ---
raw_floors = FilteredElementCollector(doc).OfClass(FloorType).ToElements()
floor_data = []
for f in raw_floors:
    floor_data.append((get_name_hardcore(f), f))
floor_data.sort(key=lambda x: x[0])
sorted_names = [x[0] for x in floor_data]
sorted_elements = [x[1] for x in floor_data]

if not sorted_names:
    forms.alert("Nenhum Tipo de Piso encontrado.", exitscript=True)

# --- GUI ---
class SoleiraWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.run_script = False
        
        self.cb_floor_type.ItemsSource = sorted_names
        self.cb_floor_type.SelectedIndex = 0
        
        for i, name in enumerate(sorted_names):
            if "Soleira" in name or "Granito" in name:
                self.cb_floor_type.SelectedIndex = i
                break
                
        cfg = config_manager.get_config(CMD_ID)
        self.tb_side_offset.Text = getattr(cfg, "side_offset", "5")
        self.tb_width_offset.Text = getattr(cfg, "width_offset", "0")
        self.chk_join.IsChecked = getattr(cfg, "do_join", True)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_floor": self.cb_floor_type.SelectedItem,
            "side_offset": self.tb_side_offset.Text,
            "width_offset": self.tb_width_offset.Text,
            "do_join": self.chk_join.IsChecked
        })
        self.Close()

win = SoleiraWindow()
win.ShowDialog()

# --- SÓ RODA SE CLICOU ---
if not win.run_script: script.exit()

# --- AGORA PEDE SELEÇÃO (PORTAS) ---
doors = get_user_selection()
if not doors: script.exit()

if not win.cb_floor_type.SelectedItem: script.exit()

sel_index = win.cb_floor_type.SelectedIndex
floor_type = sorted_elements[sel_index]
do_join = win.chk_join.IsChecked

try:
    side_off = float(win.tb_side_offset.Text) / 30.48
    width_off = float(win.tb_width_offset.Text) / 30.48
except:
    forms.alert("Valores inválidos.", exitscript=True)

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Soleiras")
t.Start()

try:
    created_count = 0
    for door in doors:
        wall = door.Host
        if not wall or not isinstance(wall, Wall): continue
            
        loops = create_threshold_geometry(door, wall, side_off, width_off)
        if loops:
            try:
                soleira = Floor.Create(doc, loops, floor_type.Id, door.LevelId)
                
                sill_p = door.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if sill_p and sill_p.HasValue:
                    z_val = sill_p.AsDouble()
                    p_off = soleira.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
                    if p_off: p_off.Set(z_val)
                
                if do_join:
                    try: JoinGeometryUtils.JoinGeometry(doc, soleira, wall)
                    except: pass 
                    
                created_count += 1
            except: pass

    t.Commit()
    forms.toast("Sucesso: {} soleiras criadas.".format(created_count))

except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))