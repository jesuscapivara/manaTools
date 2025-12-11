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
from manalib import config_manager, auth

# --- SECURITY CHECK ---
if not auth.check_access()[0]:
    forms.alert("ACESSO NEGADO: " + auth.check_access()[1] + "\n\nPor favor, faça Login na aba 'Gestão'.", exitscript=True)

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

def create_sill_geometry(window, wall, side_offset, overhang, internal_depth):
    # Geometria base
    pt_center = window.Location.Point
    
    lc = wall.Location
    if not isinstance(lc, LocationCurve): return None
    line = lc.Curve
    
    vec_wall = (line.GetEndPoint(1) - line.GetEndPoint(0)).Normalize()
    vec_out = wall.Orientation # Vetor que aponta para fora
    
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
            print("Janela {} sem parede hospedeira.".format(win_elem.Id))
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
                print("Erro na janela {}: {}".format(win_elem.Id, ex))
                
    t.Commit()
    forms.toast("Sucesso: {} pingadeiras criadas (Flat).".format(count))

except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))