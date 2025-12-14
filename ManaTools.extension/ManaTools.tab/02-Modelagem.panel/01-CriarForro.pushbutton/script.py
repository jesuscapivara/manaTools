# -*- coding: utf-8 -*-
"""
Cria Forros (Ceilings) e Tabicas.
V2.1: Seleção de Nível Explícita + Seleção Interativa Filtrada.
"""
import os
import math
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_criarforro"

# --- 1. FILTRO DE SELEÇÃO VISUAL ---
class RoomSelectionFilter(ISelectionFilter):
    def AllowElement(self, elem):
        if not elem.Category: return False
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms): return True
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_RoomTags): return True
        return False
    def AllowReference(self, reference, position): return False

# --- 2. SELEÇÃO INTERATIVA ---
def get_user_selection():
    rooms = []
    seen_ids = set()
    
    pre_selection = uidoc.Selection.GetElementIds()
    if pre_selection:
        for eid in pre_selection:
            elem = doc.GetElement(eid)
            if RoomSelectionFilter().AllowElement(elem):
                r = resolve_room(elem)
                if r and r.Id not in seen_ids:
                    rooms.append(r)
                    seen_ids.add(r.Id)
        if rooms: return rooms

    try:
        with forms.WarningBar(title="Clique nos Ambientes para o Forro (ESC para concluir):"):
            refs = uidoc.Selection.PickObjects(
                ObjectType.Element, 
                RoomSelectionFilter(), 
                "Selecione os Ambientes"
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
    if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms): return elem
    elif elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            if elem.Room: return elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"): return elem.GetTaggedLocalElement()
    return None

# --- HELPER: GEOMETRIA ---
def flatten_loop_to_z(curve_loop, z_val=0.0):
    curves = []
    iterator = curve_loop
    if isinstance(curve_loop, CurveLoop): iterator = curve_loop
    for curve in iterator:
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        new_p0 = XYZ(p0.X, p0.Y, z_val)
        new_p1 = XYZ(p1.X, p1.Y, z_val)
        try:
            if isinstance(curve, Line):
                curves.append(Line.CreateBound(new_p0, new_p1))
            else:
                trans = XYZ(0, 0, z_val - p0.Z)
                curves.append(curve.CreateTransformed(Transform.CreateTranslation(trans)))
        except: pass
    try: return CurveLoop.Create(curves)
    except: return None

# --- CORE LOGIC ---
def create_ceiling_geometry(room, offset_dist):
    loops = []
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    segments_list = room.GetBoundarySegments(opt)
    if not segments_list: return None
    for segments in segments_list:
        curves = []
        for seg in segments: curves.append(seg.GetCurve())
        try:
            original_loop = flatten_loop_to_z(curves, 0.0)
            if not original_loop: continue
            if abs(offset_dist) > 0.001:
                try:
                    offset_loops = CurveLoop.CreateViaOffset(original_loop, -offset_dist, XYZ.BasisZ)
                    if isinstance(offset_loops, CurveLoop): loops.append(offset_loops)
                    else: 
                        for ol in offset_loops: loops.append(ol)
                except: loops.append(original_loop)
            else: loops.append(original_loop)
        except: pass
    return loops

def get_tabica_curves(room, offset_dist):
    tabica_curves = []
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    segments_list = room.GetBoundarySegments(opt)
    if not segments_list: return []
    for segments in segments_list:
        curves = []
        for seg in segments: curves.append(seg.GetCurve())
        original_loop = flatten_loop_to_z(curves, 0.0)
        if not original_loop: continue
        try:
            if abs(offset_dist) > 0.001:
                offset_loops = CurveLoop.CreateViaOffset(original_loop, -offset_dist, XYZ.BasisZ)
            else: offset_loops = [original_loop]
            loops_to_proc = [offset_loops] if isinstance(offset_loops, CurveLoop) else offset_loops
            for ol in loops_to_proc:
                for c in ol: tabica_curves.append(c)
        except: pass
    return tabica_curves

def create_tabica_instance(doc, curve, symbol, level, force_invert_h, force_invert_z):
    try:
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        final_curve = Line.CreateBound(p1, p0) if force_invert_h else curve
        instance = doc.Create.NewFamilyInstance(final_curve, symbol, level, Structure.StructuralType.NonStructural)
        if force_invert_z and instance:
            doc.Regenerate()
            plane_z = level.Elevation
            mirror_plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0,0, plane_z))
            new_ids = ElementTransformUtils.MirrorElement(doc, instance.Id, mirror_plane)
            doc.Delete(instance.Id)
            if new_ids: return doc.GetElement(new_ids[0])
        return instance
    except: return None

# --- PREP DADOS ---
all_ceilings = sorted(FilteredElementCollector(doc).OfClass(CeilingType).ToElements(), key=lambda x: Element.Name.GetValue(x))
all_tabicas = sorted(FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_GenericModel).ToElements(), key=lambda x: Element.Name.GetValue(x))
all_tabicas = [t for t in all_tabicas if t.Family.FamilyPlacementType == FamilyPlacementType.CurveBased]
all_levels = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda l: l.Elevation)

dict_levels = {l.Name: l for l in all_levels}
def get_name(e): return Element.Name.GetValue(e)

# --- GUI ---
class ForroWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.run_script = False
        
        self.cb_level.ItemsSource = dict_levels.keys()
        self.cb_ceiling_type.ItemsSource = [get_name(c) for c in all_ceilings]
        self.cb_tabica_type.ItemsSource = ["(Nenhum)"] + [get_name(t) for t in all_tabicas]
        
        # Config Recovery
        cfg = config_manager.get_config(CMD_ID)
        
        # --- Nível Smart Select ---
        active_view = doc.ActiveView
        active_level = getattr(active_view, "GenLevel", None)
        
        target_level = None
        if active_level and active_level.Name in dict_levels:
            target_level = active_level.Name
        elif getattr(cfg, "last_level", None) in dict_levels:
            target_level = cfg.last_level
        else:
            if dict_levels: target_level = list(dict_levels.keys())[0]
            
        if target_level: self.cb_level.SelectedItem = target_level

        # --- Outros Defaults ---
        self.cb_ceiling_type.SelectedIndex = 0
        if getattr(cfg, "last_ceiling_type", None): self.cb_ceiling_type.SelectedItem = cfg.last_ceiling_type
            
        self.cb_tabica_type.SelectedIndex = 0 
        if getattr(cfg, "last_tabica_type", None): self.cb_tabica_type.SelectedItem = cfg.last_tabica_type
        
        self.tb_height.Text = getattr(cfg, "last_height", "260")
        self.tb_gesso_gap.Text = getattr(cfg, "last_gesso_gap", "2.5")
        self.tb_tabica_gap.Text = getattr(cfg, "last_tabica_gap", "0")
        self.tb_tabica_z_offset.Text = getattr(cfg, "last_tabica_z_offset", "0")
        self.chk_create_tabica.IsChecked = getattr(cfg, "last_create_tabica", True)
        self.chk_invert_tabica.IsChecked = getattr(cfg, "last_invert_tabica", False)
        self.chk_invert_z_tabica.IsChecked = getattr(cfg, "last_invert_z_tabica", False)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_level": self.cb_level.SelectedItem, # Salva o nível usado
            "last_ceiling_type": self.cb_ceiling_type.SelectedItem,
            "last_tabica_type": self.cb_tabica_type.SelectedItem,
            "last_height": self.tb_height.Text,
            "last_gesso_gap": self.tb_gesso_gap.Text,
            "last_tabica_gap": self.tb_tabica_gap.Text,
            "last_tabica_z_offset": self.tb_tabica_z_offset.Text,
            "last_create_tabica": self.chk_create_tabica.IsChecked,
            "last_invert_tabica": self.chk_invert_tabica.IsChecked,
            "last_invert_z_tabica": self.chk_invert_z_tabica.IsChecked
        })
        self.Close()

win = ForroWindow()
win.ShowDialog()

if not win.run_script: script.exit()

rooms = get_user_selection()
if not rooms: script.exit()

# --- RECUPERA INPUTS ---
sel_level = dict_levels[win.cb_level.SelectedItem] # Nível escolhido na UI

sel_ceil_name = win.cb_ceiling_type.SelectedItem
ceil_type = next((x for x in all_ceilings if get_name(x) == sel_ceil_name), None)

sel_tab_name = win.cb_tabica_type.SelectedItem
tab_symbol = None
if sel_tab_name != "(Nenhum)":
    tab_symbol = next((x for x in all_tabicas if get_name(x) == sel_tab_name), None)

do_tabica = win.chk_create_tabica.IsChecked
do_invert_h = win.chk_invert_tabica.IsChecked
do_invert_z = win.chk_invert_z_tabica.IsChecked

try:
    gesso_gap_ft = float(win.tb_gesso_gap.Text) / 30.48
    tabica_gap_ft = float(win.tb_tabica_gap.Text) / 30.48
    tabica_z_offset_ft = float(win.tb_tabica_z_offset.Text) / 30.48
    height_ft = float(win.tb_height.Text) / 30.48
except:
    forms.alert("Valores inválidos.", exitscript=True)

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Forro e Tabica")
t.Start()

count_forros = 0
count_tabicas = 0

try:
    if do_tabica and tab_symbol and not tab_symbol.IsActive:
        tab_symbol.Activate()
        doc.Regenerate()

    for room in rooms:
        # USA O NÍVEL SELECIONADO NA UI, NÃO O DO QUARTO
        level_id = sel_level.Id
        
        loops = create_ceiling_geometry(room, gesso_gap_ft)
        
        if loops:
            try:
                valid_loops = []
                for l in loops:
                    if isinstance(l, CurveLoop) and not l.IsOpen():
                        valid_loops.append(l)
                
                if valid_loops:
                    c = Ceiling.Create(doc, valid_loops, ceil_type.Id, level_id)
                    p_off = c.get_Parameter(BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM)
                    if p_off: p_off.Set(height_ft)
                    count_forros += 1
            except: pass

        if do_tabica and tab_symbol:
            curves = get_tabica_curves(room, tabica_gap_ft)
            for c in curves:
                # CRIA TABICA NO NÍVEL SELECIONADO
                inst = create_tabica_instance(doc, c, tab_symbol, sel_level, do_invert_h, do_invert_z)
                if inst:
                    final_z = height_ft + tabica_z_offset_ft
                    p_elev = inst.get_Parameter(BuiltInParameter.INSTANCE_ELEVATION_PARAM) or inst.get_Parameter(BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM)
                    if p_elev: p_elev.Set(final_z)
                    else:
                        for n in ["Elevação", "Offset", "Altura"]:
                            p = inst.LookupParameter(n)
                            if p: p.Set(final_z); break
                    count_tabicas += 1

    t.Commit()
    msg = "Sucesso: {} Forros".format(count_forros)
    if do_tabica: msg += " | {} Tabicas".format(count_tabicas)
    forms.toast(msg)

except Exception as e:
    t.RollBack()
    forms.alert("Erro: {}".format(e))