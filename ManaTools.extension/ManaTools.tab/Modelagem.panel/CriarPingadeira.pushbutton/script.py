# -*- coding: utf-8 -*-
"""
Cria Pingadeiras (Floors) sob janelas selecionadas.
Versão Simplificada: Sem inclinação (Flat).
"""
import os
import clr
import math
from System.Collections.Generic import List

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import forms, script, revit
from manalib import config_manager, bim_utils

# --- SECURITY CHECK ---
if not bim_utils.calculate_vector_matrix()[0]:
    forms.alert("ACESSO NEGADO: " + bim_utils.calculate_vector_matrix()[1] + "\n\nPor favor, faça Login na aba 'Gestão'.", exitscript=True)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_criarpingadeira"

# --- 1. HELPERS ---
def get_name_hardcore(element):
    if not element: return "Nulo"
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.HasValue: return p.AsString()
    except: pass
    try: return Element.Name.GetValue(element)
    except: return "Elemento ID:{}".format(element.Id)

# --- 2. SELEÇÃO ---
def get_selected_windows():
    selection = revit.get_selection()
    windows = []
    seen = set()
    
    def add(w):
        if w and w.Id not in seen:
            windows.append(w)
            seen.add(w.Id)

    for elem in selection:
        if not elem.Category: continue
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Windows):
            add(elem)
            
    if not windows:
        try:
            with forms.WarningBar(title="Selecione Janelas (ESC para sair):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Janelas")
                for r in refs: 
                    e = doc.GetElement(r)
                    if e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Windows):
                        add(e)
        except: pass
    return windows

# --- 3. GEOMETRIA ---
def get_window_width(window):
    params = [BuiltInParameter.WINDOW_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM, BuiltInParameter.FURNITURE_WIDTH]
    for pid in params:
        p = window.get_Parameter(pid)
        if not p: p = window.Symbol.get_Parameter(pid)
        if p and p.HasValue: return p.AsDouble()
    for pid in params:
        p = window.Symbol.get_Parameter(pid)
        if p and p.HasValue: return p.AsDouble()
    return 1.0

def get_wall_thickness(wall):
    return wall.Width

def is_external_room(room):
    """
    Verifica se um ambiente parece ser externo baseado no nome.
    """
    if not room: return True
    
    try:
        room_name = room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
        room_number = room.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
        
        # Lista de termos que indicam área externa
        external_terms = [
            "calcada", "calçada", "rua", "exterior", "externo", "externa",
            "varanda", "sacada", "area externa", "área externa", 
            "passeio", "logradouro", "jardim externo"
        ]
        
        name_lower = (room_name or "").lower()
        number_lower = (room_number or "").lower()
        
        for term in external_terms:
            if term in name_lower or term in number_lower:
                return True
                
    except: pass
    
    return False

def get_room_area(room):
    """Retorna a área do ambiente em pés quadrados."""
    if not room: return 0
    try:
        p_area = room.get_Parameter(BuiltInParameter.ROOM_AREA)
        if p_area and p_area.HasValue:
            return p_area.AsDouble()
    except: pass
    return 0

def detect_external_face(window, wall):
    """
    Detecta qual lado da parede é externo, baseado na presença de ambientes.
    Considera múltiplos critérios para decidir o lado correto.
    """
    pt_center = window.Location.Point
    wall_thick = get_wall_thickness(wall)
    vec_orientation = wall.Orientation
    
    # Offset para testar (metade da espessura + um pouco mais)
    test_distance = (wall_thick / 2.0) + 0.5  # +0.5 pés (~15cm) para ter certeza
    
    # Testa os dois lados
    pt_side_A = pt_center + (vec_orientation * test_distance)
    pt_side_B = pt_center - (vec_orientation * test_distance)
    
    # Verifica se existe Room em cada lado
    room_side_A = doc.GetRoomAtPoint(pt_side_A)
    room_side_B = doc.GetRoomAtPoint(pt_side_B)
    
    # CASO 1: Só tem Room em um lado -> Pingadeira vai para o lado sem Room
    if room_side_A and not room_side_B:
        return vec_orientation  # Pingadeira vai para o lado B (externo)
    
    if room_side_B and not room_side_A:
        return -vec_orientation  # Pingadeira vai para o lado A (externo)
    
    # CASO 2: Tem Room nos dois lados (janela interna)
    if room_side_A and room_side_B:
        # 2.1: Verifica se algum tem nome indicando área externa
        is_A_external = is_external_room(room_side_A)
        is_B_external = is_external_room(room_side_B)
        
        if is_A_external and not is_B_external:
            return vec_orientation  # A é externo, pingadeira vai para A
        
        if is_B_external and not is_A_external:
            return -vec_orientation  # B é externo, pingadeira vai para B
        
        # 2.2: Se ambos parecem internos, compara áreas
        # Área muito grande pode indicar área externa mal configurada
        area_A = get_room_area(room_side_A)
        area_B = get_room_area(room_side_B)
        
        # Se um ambiente é significativamente maior (>3x), provavelmente é externo
        if area_A > 0 and area_B > 0:
            if area_A > area_B * 3:
                return vec_orientation  # A é muito maior, provavelmente externo
            if area_B > area_A * 3:
                return -vec_orientation  # B é muito maior, provavelmente externo
    
    # CASO 3: Sem Room em nenhum lado, ou casos indeterminados
    # Usa orientação padrão da parede (geralmente aponta para fora)
    return vec_orientation

def create_sill_geometry(window, wall, side_offset, overhang, internal_depth):
    # Geometria base
    pt_center = window.Location.Point
    
    lc = wall.Location
    if not isinstance(lc, LocationCurve): return None
    line = lc.Curve
    
    vec_wall = (line.GetEndPoint(1) - line.GetEndPoint(0)).Normalize()
    vec_out = detect_external_face(window, wall)  # Usa detecção inteligente
    
    w_width = get_window_width(window)
    wall_thick = get_wall_thickness(wall)
    
    length = w_width + (side_offset * 2)
    # total_depth = internal_depth + overhang # Não usado no retorno, apenas para cálculo interno
    
    dist_axis_to_ext_face = wall_thick / 2.0
    pt_ext_face_center = pt_center + (vec_out * dist_axis_to_ext_face)
    
    pt_start_center = pt_ext_face_center - (vec_out * internal_depth) 
    pt_end_center = pt_ext_face_center + (vec_out * overhang)         
    
    v_long = vec_wall * (length / 2.0)
    
    def flat(pt): return XYZ(pt.X, pt.Y, 0)
    
    p1 = flat(pt_start_center - v_long)
    p2 = flat(pt_start_center + v_long)
    p3 = flat(pt_end_center + v_long)
    p4 = flat(pt_end_center - v_long)
    
    loops = []
    lines = [
        Line.CreateBound(p1, p2),
        Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4),
        Line.CreateBound(p4, p1)
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

# --- GUI ---
windows = get_selected_windows()
if not windows: script.exit()

if not sorted_names:
    forms.alert("Nenhum Tipo de Piso encontrado.", exitscript=True)

class PingadeiraWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.run_script = False
        
        self.cb_floor_type.ItemsSource = sorted_names
        self.cb_floor_type.SelectedIndex = 0
        
        for i, name in enumerate(sorted_names):
            if "Granito" in name or "Pingadeira" in name or "Soleira" in name:
                self.cb_floor_type.SelectedIndex = i
                break
                
        cfg = config_manager.get_config(CMD_ID)
        self.tb_side_offset.Text = getattr(cfg, "side_offset", "5")
        self.tb_overhang.Text = getattr(cfg, "overhang", "3")
        self.tb_internal_depth.Text = getattr(cfg, "internal_depth", "9") 
        self.chk_join.IsChecked = getattr(cfg, "do_join", True)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_floor": self.cb_floor_type.SelectedItem,
            "side_offset": self.tb_side_offset.Text,
            "overhang": self.tb_overhang.Text,
            "internal_depth": self.tb_internal_depth.Text,
            "do_join": self.chk_join.IsChecked
        })
        self.Close()

win = PingadeiraWindow()
win.ShowDialog()

if not win.run_script: script.exit()

if not win.cb_floor_type.SelectedItem: script.exit()

floor_type = sorted_elements[win.cb_floor_type.SelectedIndex]
do_join = win.chk_join.IsChecked

try:
    side_off = float(win.tb_side_offset.Text) / 30.48
    overhang = float(win.tb_overhang.Text) / 30.48
    internal_depth = float(win.tb_internal_depth.Text) / 30.48
except:
    forms.alert("Valores inválidos.", exitscript=True)

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Pingadeiras")
t.Start()

try:
    count = 0
    for win_elem in windows:
        wall = win_elem.Host
        if not wall or not isinstance(wall, Wall):
            continue
            
        loops = create_sill_geometry(win_elem, wall, side_off, overhang, internal_depth)
        
        if loops:
            try:
                # 1. Cria Piso
                level_id = win_elem.LevelId
                sill = Floor.Create(doc, loops, floor_type.Id, level_id)
                
                # Ajuste de Altura (Peitoril)
                p_sill_win = win_elem.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                if p_sill_win:
                    h_val = p_sill_win.AsDouble()
                    p_off_floor = sill.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
                    if p_off_floor: p_off_floor.Set(h_val)
                
                # 2. Join
                if do_join:
                    try: JoinGeometryUtils.JoinGeometry(doc, sill, wall)
                    except: pass
                    
                count += 1
            except Exception as ex:
                pass
                
    t.Commit()
    forms.toast("Sucesso: {} pingadeiras criadas (Flat).".format(count))

except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))