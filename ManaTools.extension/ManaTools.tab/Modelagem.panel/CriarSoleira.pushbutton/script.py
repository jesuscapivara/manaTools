# -*- coding: utf-8 -*-
"""
Cria Soleiras (Floors) sob portas selecionadas.
Abordagem direta: Seleciona Porta -> Lê Hospedeiro (Parede) -> Cria Piso.
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
CMD_ID = "manatools_criarsoleira"

# --- 1. FUNÇÃO DE NOME INFALÍVEL ---
def get_name_hardcore(element):
    if not element: return "Nulo"
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.HasValue:
            val = p.AsString()
            if val: return val
    except: pass
    try:
        p = element.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.HasValue:
            val = p.AsString()
            if val: return val
    except: pass
    try:
        return Element.Name.GetValue(element)
    except: pass
    return "Elemento ID:{}".format(element.Id)

# --- 2. PREPARAÇÃO DE DADOS (SAFE SORT) ---
raw_floors = FilteredElementCollector(doc).OfClass(FloorType).ToElements()
floor_data = []
for f in raw_floors:
    safe_name = get_name_hardcore(f)
    floor_data.append((safe_name, f))
floor_data.sort(key=lambda x: x[0])
sorted_names = [x[0] for x in floor_data]
sorted_elements = [x[1] for x in floor_data]

# --- 3. SELEÇÃO DE PORTAS (DIRETA) ---
def get_selected_doors():
    selection = revit.get_selection()
    doors = []
    seen = set()
    
    def add(d):
        if d and d.Id not in seen:
            doors.append(d)
            seen.add(d.Id)

    for elem in selection:
        if not elem.Category: continue
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Doors):
            add(elem)
            
    if not doors:
        try:
            with forms.WarningBar(title="Selecione Portas (ESC para sair):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Portas")
                for r in refs: 
                    e = doc.GetElement(r)
                    if e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Doors):
                        add(e)
        except: pass
    return doors

# --- 4. GEOMETRIA ---
def get_door_width(door):
    # Tenta ler largura real, priorizando FURNITURE_WIDTH (Inspector Maná)
    # Lista de prioridade baseada no HTML do usuário
    params_to_check = [
        BuiltInParameter.FURNITURE_WIDTH, # Largura (0.92) - Mais preciso
        BuiltInParameter.DOOR_WIDTH,      # Largura Padrão
        BuiltInParameter.FAMILY_WIDTH_PARAM
    ]
    
    # 1. Instância
    for pid in params_to_check:
        p = door.get_Parameter(pid)
        if p and p.HasValue:
            val = p.AsDouble()
            if val > 0: return val
            
    # 2. Tipo (Symbol)
    for pid in params_to_check:
        p = door.Symbol.get_Parameter(pid)
        if p and p.HasValue:
            val = p.AsDouble()
            if val > 0: return val
            
    return 0.8 # Fallback 

def get_wall_width(wall):
    return wall.Width

def create_threshold_geometry(door, wall, side_offset, width_offset):
    pt_center = door.Location.Point
    
    lc = wall.Location
    if not isinstance(lc, LocationCurve): return None
    line = lc.Curve
    
    vec_wall = (line.GetEndPoint(1) - line.GetEndPoint(0)).Normalize()
    vec_thick = XYZ(-vec_wall.Y, vec_wall.X, 0)
    
    d_width = get_door_width(door)
    print("DEBUG: Porta ID {} - Largura Detectada: {:.2f}m".format(door.Id, d_width * 0.3048))
    w_thick = get_wall_width(wall)
    
    length = d_width + (side_offset * 2)
    thickness = w_thick + (width_offset * 2)
    
    v_long = vec_wall * (length / 2.0)
    v_trans = vec_thick * (thickness / 2.0)
    
    center_flat = XYZ(pt_center.X, pt_center.Y, 0)
    
    p1 = center_flat + v_long + v_trans
    p2 = center_flat - v_long + v_trans
    p3 = center_flat - v_long - v_trans
    p4 = center_flat + v_long - v_trans
    
    loops = []
    lines = [
        Line.CreateBound(p1, p2),
        Line.CreateBound(p2, p3),
        Line.CreateBound(p3, p4),
        Line.CreateBound(p4, p1)
    ]
    loops.append(CurveLoop.Create(lines))
    return loops

# --- GUI ---
doors = get_selected_doors()
if not doors: script.exit()

if not sorted_names:
    forms.alert("Nenhum Tipo de Piso encontrado.", exitscript=True)

class SoleiraWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
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
        config_manager.save_config(CMD_ID, {
            "last_floor": self.cb_floor_type.SelectedItem,
            "side_offset": self.tb_side_offset.Text,
            "width_offset": self.tb_width_offset.Text,
            "do_join": self.chk_join.IsChecked
        })
        self.Close()

win = SoleiraWindow()
win.ShowDialog()

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
        # Pega a parede hospedeira
        wall = door.Host
        if not wall or not isinstance(wall, Wall):
            print("Aviso: Porta {} não tem parede hospedeira válida.".format(door.Id))
            continue
            
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
                    try:
                        JoinGeometryUtils.JoinGeometry(doc, soleira, wall)
                    except: pass 
                    
                created_count += 1
            except Exception as ex:
                print("Erro porta {}: {}".format(door.Id, ex))

    t.Commit()
    forms.toast("Sucesso: {} soleiras criadas.".format(created_count))

except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))
