# -*- coding: utf-8 -*-
"""
Cria Rodapés (Line Based) em Ambientes.
ENGINE V4.2: Seleção Interativa (Rooms/Tags) + Correção de Cantos + UI Flow.
"""
import clr
import math
import os
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
logger = script.get_logger()

CMD_ID = "manatools_criarrodape_line"

# --- 1. FILTRO DE SELEÇÃO VISUAL ---
class RoomSelectionFilter(ISelectionFilter):
    """
    Permite selecionar apenas Ambientes e Tags.
    As portas são detectadas automaticamente pela engine, não precisam ser selecionadas.
    """
    def AllowElement(self, elem):
        if not elem.Category: return False
        cid = elem.Category.Id.IntegerValue
        if cid == int(BuiltInCategory.OST_Rooms): return True
        if cid == int(BuiltInCategory.OST_RoomTags): return True
        return False

    def AllowReference(self, reference, position):
        return False

# --- 2. SELEÇÃO INTERATIVA ---
def get_user_selection():
    rooms = []
    seen_ids = set()
    
    # Verifica seleção prévia
    pre_selection = uidoc.Selection.GetElementIds()
    if pre_selection:
        filter_instance = RoomSelectionFilter()
        for eid in pre_selection:
            elem = doc.GetElement(eid)
            if filter_instance.AllowElement(elem):
                r = resolve_room(elem)
                if r and r.Id not in seen_ids:
                    rooms.append(r)
                    seen_ids.add(r.Id)
        if rooms: return rooms

    # Pede nova seleção
    try:
        with forms.WarningBar(title="Clique nos Ambientes para criar Rodapé (ESC para concluir):"):
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element, 
                RoomSelectionFilter(), 
                "Selecione Ambientes"
            )
            for r in refs:
                elem = doc.GetElement(r)
                room = resolve_room(elem)
                if room and room.Id not in seen_ids:
                    rooms.append(room)
                    seen_ids.add(room.Id)
    except OperationCanceledException: pass
    return rooms

def resolve_room(elem):
    cid = elem.Category.Id.IntegerValue
    if cid == int(BuiltInCategory.OST_Rooms): return elem
    elif cid == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            if elem.Room: return elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"): return elem.GetTaggedLocalElement()
    return None

# --- 3. HELPER: FILTROS E NOMES ---
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

def get_name(element):
    if not element: return ""
    try: return Element.Name.GetValue(element)
    except: return getattr(element, "Name", str(element.Id))

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
    try:
        lc = wall.Location
        if isinstance(lc, LocationCurve):
            curve = lc.Curve
            if isinstance(curve, Line):
                return (curve.GetEndPoint(1) - curve.GetEndPoint(0)).Normalize()
    except: pass
    return None

def is_parallel(vec1, vec2):
    if not vec1 or not vec2: return False
    cross_prod = vec1.CrossProduct(vec2)
    return cross_prod.GetLength() < 0.1

def get_wall_segments_minus_openings(room, gap_margin):
    final_curves = []
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish 
    segments_list = room.GetBoundarySegments(opt)
    if not segments_list: return []

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
                # Filtro de Paredes Unidas
                try:
                    joined_ids = JoinGeometryUtils.GetJoinedElements(doc, wall)
                    for j_id in joined_ids:
                        j_wall = doc.GetElement(j_id)
                        if isinstance(j_wall, Wall):
                            j_vec = get_wall_orientation(j_wall)
                            if is_parallel(line_vec, j_vec):
                                j_inserts = j_wall.FindInserts(True, False, False, False)
                                for ji in j_inserts:
                                    if ji not in inserts_ids: inserts_ids.append(ji)
                except: pass

                for ins_id in inserts_ids:
                    elem = doc.GetElement(ins_id)
                    if not elem: continue
                    cat_id = elem.Category.Id.IntegerValue
                    if cat_id not in [int(BuiltInCategory.OST_Doors), int(BuiltInCategory.OST_Windows)]: continue
                    
                    if cat_id == int(BuiltInCategory.OST_Windows):
                        sill_p = elem.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)
                        if sill_p and sill_p.HasValue and sill_p.AsDouble() > 0.5: continue 
                    
                    pt_elem = elem.Location.Point
                    pt_elem_2d = XYZ(pt_elem.X, pt_elem.Y, 0)
                    vec_to_elem = pt_elem_2d - p_start_2d
                    dot = vec_to_elem.DotProduct(line_vec)
                    
                    # Validação lateral
                    perp_dist = abs((p_end_2d.X - p_start_2d.X) * (p_start_2d.Y - pt_elem_2d.Y) - (p_start_2d.X - pt_elem_2d.X) * (p_end_2d.Y - p_start_2d.Y)) / seg_length
                    if perp_dist > 1.0: continue

                    width = get_element_width(elem)
                    start_dist = dot - (width / 2.0) - gap_margin
                    end_dist = dot + (width / 2.0) + gap_margin
                    
                    cut_s = max(0, start_dist)
                    cut_e = min(seg_length, end_dist)
                    
                    if cut_s < cut_e: cuts.append((cut_s, cut_e))

            # Merge Cuts
            cuts.sort(key=lambda x: x[0])
            merged_cuts = []
            if cuts:
                curr_s, curr_e = cuts[0]
                for i in range(1, len(cuts)):
                    next_s, next_e = cuts[i]
                    if next_s < curr_e: curr_e = max(curr_e, next_e)
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
        line = Line.CreateBound(XYZ(p1.X, p1.Y, z_level), XYZ(p0.X, p0.Y, z_level)) if do_flip else Line.CreateBound(XYZ(p0.X, p0.Y, z_level), XYZ(p1.X, p1.Y, z_level))
        inst = doc.Create.NewFamilyInstance(line, symbol, level, Structure.StructuralType.NonStructural)
        
        # Seta offset
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
                if p: p.Set(offset); break
        return inst
    except: return None

def auto_join_elements(doc, elements):
    count = 0
    for i in range(len(elements)):
        for j in range(i + 1, len(elements)):
            try:
                JoinGeometryUtils.JoinGeometry(doc, elements[i], elements[j])
                count += 1
            except: pass 
    return count

# --- GUI ---
all_families = sorted(get_line_based_families(), key=get_name)
if not all_families:
    forms.alert("Nenhuma família Line Based encontrada.", exitscript=True)

class RodapeLineWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        self.run_script = False
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
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_family": self.cb_sweep_type.SelectedItem,
            "last_offset": self.tb_offset.Text,
            "last_invert_flip": self.chk_invert_flip.IsChecked 
        })
        self.Close()

win = RodapeLineWindow()
win.ShowDialog()

# --- SÓ RODA SE CLICOU ---
if not win.run_script: script.exit()

# --- AGORA PEDE SELEÇÃO (AMBIENTES) ---
rooms = get_user_selection()
if not rooms: script.exit()

if not win.cb_sweep_type.SelectedItem: script.exit()

# Recarrega Inputs
sel_name = win.cb_sweep_type.SelectedItem
family_symbol = next((f for f in all_families if get_name(f) == sel_name), None)
do_flip = win.chk_invert_flip.IsChecked 

try: offset_ft = float(win.tb_offset.Text) / 30.48
except: forms.alert("Valor inválido.", exitscript=True)

# Prompt adicional para a folga
gap_input = forms.ask_for_string(
    default="3",
    prompt="Folga Extra do Batente (cm):\n(Valor será descontado de CADA lado do vão)",
    title="Ajuste de Vão de Porta"
)
try: gap_margin_ft = float(gap_input.replace(',', '.')) / 30.48 if gap_input else 0.001
except: gap_margin_ft = 0.001

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Rodapés V4.2")
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
    forms.toast("Sucesso: {} rodapés criados!".format(total_created))

except Exception as e:
    t.RollBack()
    forms.alert("Erro: {}".format(e))