# -*- coding: utf-8 -*-
"""
Cria Rodapés (Line Based) em Ambientes.
ENGINE V4: Correção do "Corte Fantasma" em cantos (Filtro de Paralelismo).
"""
import clr
import math
import os
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import forms, script, revit
from manalib import config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
logger = script.get_logger()

CMD_ID = "manatools_criarrodape_line"

# --- 1. SELEÇÃO ---
def get_selected_rooms():
    selection = revit.get_selection()
    rooms = []
    seen_ids = set()

    def process(elem):
        r = None
        if not elem or not elem.Category: return
        cat_id = elem.Category.Id.IntegerValue
        if cat_id == int(BuiltInCategory.OST_Rooms): r = elem
        elif cat_id == int(BuiltInCategory.OST_RoomTags):
            if isinstance(elem, SpatialElementTag):
                if hasattr(elem, "Room") and elem.Room: r = elem.Room
                elif hasattr(elem, "GetTaggedLocalElement"): r = elem.GetTaggedLocalElement()
        if r and r.Id not in seen_ids:
            rooms.append(r)
            seen_ids.add(r.Id)

    for s in selection: process(s)
    if not rooms:
        try:
            with forms.WarningBar(title="Selecione Ambientes (ESC para sair):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes")
                for r in refs: process(doc.GetElement(r))
        except: pass
    return rooms

# --- 2. FILTRO DE FAMÍLIAS ---
def get_line_based_families():
    symbols = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_GenericModel).ToElements()
    valid = []
    for s in symbols:
        try:
            if s.Family.FamilyPlacementType == FamilyPlacementType.CurveDrivenStructural or \
               s.Family.FamilyPlacementType == FamilyPlacementType.CurveBased:
                valid.append(s)
        except: pass
    return valid

def get_name(e):
    try: return Element.Name.GetValue(e)
    except: return e.Name

# --- 3. HELPER: LARGURA ---
def get_element_width(element):
    for param_id in [BuiltInParameter.DOOR_WIDTH, BuiltInParameter.WINDOW_WIDTH, BuiltInParameter.FAMILY_WIDTH_PARAM]:
        p = element.get_Parameter(param_id)
        if not p: p = element.Symbol.get_Parameter(param_id)
        if p and p.HasValue: return p.AsDouble()
    
    for name in ["Width", "Largura", "Largura Aproximada", "Vão Luz", "Rough Width"]:
        p = element.LookupParameter(name)
        if not p: p = element.Symbol.LookupParameter(name)
        if p and p.HasValue: return p.AsDouble()
    return 0.9

# --- 4. MATH ENGINE: CORTE INTELIGENTE (V4) ---
def get_wall_orientation(wall):
    """Retorna o vetor de direção da parede."""
    try:
        lc = wall.Location
        if isinstance(lc, LocationCurve):
            curve = lc.Curve
            if isinstance(curve, Line):
                return (curve.GetEndPoint(1) - curve.GetEndPoint(0)).Normalize()
    except: pass
    return None

def is_parallel(vec1, vec2):
    """Verifica se dois vetores são paralelos (mesma direção ou opostos)."""
    if not vec1 or not vec2: return False
    cross_prod = vec1.CrossProduct(vec2)
    # Se produto vetorial é zero (ou quase), são paralelos
    return cross_prod.GetLength() < 0.1

def get_wall_segments_minus_openings(room, gap_margin):
    final_curves = []
    
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish 
    
    segments_list = room.GetBoundarySegments(opt)
    if not segments_list: return []

    print("Processando Sala: {}".format(room.Number))

    for segments in segments_list:
        for seg in segments:
            curve = seg.GetCurve()
            p_start = curve.GetEndPoint(0)
            p_end = curve.GetEndPoint(1)
            
            p_start_2d = XYZ(p_start.X, p_start.Y, 0)
            p_end_2d = XYZ(p_end.X, p_end.Y, 0)
            
            try: line_vec = (p_end_2d - p_start_2d).Normalize()
            except: continue
            
            seg_length = p_start_2d.DistanceTo(p_end_2d)
            wall = doc.GetElement(seg.ElementId)
            cuts = [] 
            
            if isinstance(wall, Wall):
                inserts_ids = list(wall.FindInserts(True, False, False, False))
                
                # --- FIX V4: FILTRO DE PAREDES UNIDAS ---
                try:
                    joined_ids = JoinGeometryUtils.GetJoinedElements(doc, wall)
                    for j_id in joined_ids:
                        j_wall = doc.GetElement(j_id)
                        if isinstance(j_wall, Wall):
                            # VERIFICA PARALELISMO
                            # Se a parede unida for perpendicular (canto), ignoramos os inserts dela
                            # Se for paralela (parede cebola), aceitamos.
                            j_vec = get_wall_orientation(j_wall)
                            
                            if is_parallel(line_vec, j_vec):
                                j_inserts = j_wall.FindInserts(True, False, False, False)
                                for ji in j_inserts:
                                    if ji not in inserts_ids: inserts_ids.append(ji)
                            # else: print("Ignorando parede perpendicular ID: {}".format(j_id))
                except: pass

                for ins_id in inserts_ids:
                    elem = doc.GetElement(ins_id)
                    if not elem: continue
                    cat_id = elem.Category.Id.IntegerValue
                    
                    is_door = (cat_id == int(BuiltInCategory.OST_Doors))
                    is_window = (cat_id == int(BuiltInCategory.OST_Windows))
                    
                    if not (is_door or is_window): continue
                    
                    if is_window:
                        sill_p = elem.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                        if sill_p and sill_p.HasValue:
                            if sill_p.AsDouble() > 0.5: continue 
                    
                    pt_elem = elem.Location.Point
                    pt_elem_2d = XYZ(pt_elem.X, pt_elem.Y, 0)
                    
                    vec_to_elem = pt_elem_2d - p_start_2d
                    dot = vec_to_elem.DotProduct(line_vec)
                    
                    # Distância lateral (validação extra)
                    # Se a porta projetada está muito longe do eixo da parede atual, é fantasma
                    perp_dist = abs((p_end_2d.X - p_start_2d.X) * (p_start_2d.Y - pt_elem_2d.Y) - (p_start_2d.X - pt_elem_2d.X) * (p_end_2d.Y - p_start_2d.Y)) / seg_length
                    if perp_dist > 1.0: # Se projetado a mais de 30cm, ignora
                        continue

                    width = get_element_width(elem)
                    
                    current_gap = gap_margin 
                    
                    start_dist = dot - (width / 2.0) - current_gap
                    end_dist = dot + (width / 2.0) + current_gap
                    
                    cut_s = max(0, start_dist)
                    cut_e = min(seg_length, end_dist)
                    
                    if cut_s < cut_e:
                        cuts.append((cut_s, cut_e))

            # Merge Cuts
            cuts.sort(key=lambda x: x[0])
            merged_cuts = []
            if cuts:
                curr_s, curr_e = cuts[0]
                for i in range(1, len(cuts)):
                    next_s, next_e = cuts[i]
                    if next_s < curr_e: 
                        curr_e = max(curr_e, next_e)
                    else:
                        merged_cuts.append((curr_s, curr_e))
                        curr_s, curr_e = next_s, next_e
                merged_cuts.append((curr_s, curr_e))
            
            # Gera Linhas
            current_pos = 0.0
            for c_start, c_end in merged_cuts:
                if c_start - current_pos > 0.02: 
                    p1 = p_start + (line_vec * current_pos)
                    p2 = p_start + (line_vec * c_start)
                    final_curves.append(Line.CreateBound(p1, p2))
                current_pos = max(current_pos, c_end)
            
            if seg_length - current_pos > 0.02:
                p1 = p_start + (line_vec * current_pos)
                p2 = p_start + (line_vec * seg_length)
                final_curves.append(Line.CreateBound(p1, p2))
                
    return final_curves

# --- 5. ENGINE: INSTANCIAÇÃO ---
def create_skirting(doc, curve, symbol, level, offset, do_flip=False):
    try:
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        z_level = 0 
        
        if do_flip:
            line = Line.CreateBound(XYZ(p1.X, p1.Y, z_level), XYZ(p0.X, p0.Y, z_level))
        else:
            line = Line.CreateBound(XYZ(p0.X, p0.Y, z_level), XYZ(p1.X, p1.Y, z_level))
            
        inst = doc.Create.NewFamilyInstance(line, symbol, level, Structure.StructuralType.NonStructural)
        
        params = [BuiltInParameter.INSTANCE_ELEVATION_PARAM, BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM]
        done = False
        for bp in params:
            p = inst.get_Parameter(bp)
            if p and not p.IsReadOnly:
                p.Set(offset)
                done = True
                break
        
        if not done:
            for n in ["Elevação", "Offset", "Deslocamento", "Altura"]:
                p = inst.LookupParameter(n)
                if p: 
                    p.Set(offset)
                    break
        return inst
    except: return None

# --- 6. AUTO-JOIN ---
def auto_join_elements(doc, elements):
    count = 0
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            try:
                e1 = elements[i]
                e2 = elements[j]
                bb1 = e1.get_BoundingBox(None)
                bb2 = e2.get_BoundingBox(None)
                JoinGeometryUtils.JoinGeometry(doc, e1, e2)
                count += 1
            except: 
                pass 
    return count

# --- GUI ---
rooms = get_selected_rooms()
if not rooms: script.exit()

all_families = sorted(get_line_based_families(), key=get_name)
if not all_families:
    forms.alert("Nenhuma família Line Based encontrada.", exitscript=True)

class RodapeLineWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_sweep_type.ItemsSource = [get_name(t) for t in all_families]
        self.cb_sweep_type.SelectedIndex = 0
        
        cfg = config_manager.get_config(CMD_ID)
        if getattr(cfg, "last_family", None):
            for i, name in enumerate(self.cb_sweep_type.ItemsSource):
                if name == cfg.last_family:
                    self.cb_sweep_type.SelectedIndex = i
                    break
        
        self.tb_offset.Text = getattr(cfg, "last_offset", "0")
        self.chk_invert_flip.IsChecked = getattr(cfg, "last_invert_flip", False)
        
        self.chk_force_cut.Content = "Corte Automático (V4)"
        self.chk_force_cut.IsEnabled = False
        self.chk_force_cut.IsChecked = True

    def button_create_clicked(self, sender, args):
        config_manager.save_config(CMD_ID, {
            "last_family": self.cb_sweep_type.SelectedItem,
            "last_offset": self.tb_offset.Text,
            "last_invert_flip": self.chk_invert_flip.IsChecked 
        })
        self.Close()

win = RodapeLineWindow()
win.ShowDialog()

if not win.cb_sweep_type.SelectedItem: script.exit()

sel_name = win.cb_sweep_type.SelectedItem
family_symbol = next((f for f in all_families if get_name(f) == sel_name), None)
do_flip = win.chk_invert_flip.IsChecked 

try:
    offset_ft = float(win.tb_offset.Text) / 30.48
except:
    forms.alert("Valor inválido.", exitscript=True)

gap_input = forms.ask_for_string(
    default="3",
    prompt="Folga Extra do Batente (cm):\n(Valor será descontado de CADA lado do vão)",
    title="Ajuste de Vão de Porta"
)

try:
    if gap_input:
        gap_margin_ft = float(gap_input.replace(',', '.')) / 30.48
    else:
        gap_margin_ft = 0.03 / 30.48
except:
    gap_margin_ft = 0.03 / 30.48

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Rodapés V4")
t.Start()

try:
    if not family_symbol.IsActive: family_symbol.Activate()
    
    total_created = 0
    
    for room in rooms:
        curves = get_wall_segments_minus_openings(room, gap_margin_ft)
        
        room_instances = []
        for c in curves:
            inst = create_skirting(doc, c, family_symbol, room.Level, offset_ft, do_flip)
            if inst:
                room_instances.append(inst)
                total_created += 1
        
        doc.Regenerate()
        auto_join_elements(doc, room_instances)
                
    t.Commit()
    forms.toast("Sucesso: {} rodapés criados com união automática!".format(total_created))

except Exception as e:
    t.RollBack()
    forms.alert("Erro: {}".format(e))
