# -*- coding: utf-8 -*-
"""
Automação de Cotas V17.0 (Reach Expansion).
Correção: Expande a área de validação das paredes intersectantes.
Resolve: Paredes internas que param na face do núcleo e não alcançavam o eixo da parede principal.
"""
import os
import clr
import math

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script, revit
from manalib import config_manager

# --- SETUP ---
doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_cotas_v17"

# --- CONSTANTES ---
MIN_THICKNESS_FT = 0.05 / 0.3048 # 5cm

# --- CLASSES ---
class RefItem:
    def __init__(self, ref, distance):
        self.ref = ref
        self.dist = distance

# --- UTILS ---
def get_name_safe(element):
    if not element: return ""
    try:
        p = element.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.HasValue: return p.AsString()
    except: pass
    try: return element.Name
    except: return str(element.Id)

def get_wall_curve(wall):
    lc = wall.Location
    if isinstance(lc, LocationCurve): return lc.Curve
    return None

def is_parallel(vec1, vec2):
    return abs(vec1.DotProduct(vec2)) > 0.995

# --- MATH ---
def intersect_line_plane(line_origin, line_dir, plane_origin, plane_normal):
    denom = line_dir.DotProduct(plane_normal)
    if abs(denom) < 0.05: return None 
    vec_dist = plane_origin - line_origin
    t = vec_dist.DotProduct(plane_normal) / denom
    return t

def get_smart_direction(wall, view, selection_centroid=None):
    """Lógica de repulsão de ambientes e centróide."""
    try: normal = wall.Orientation.Normalize()
    except: normal = XYZ.BasisY
    curve = get_wall_curve(wall)
    if not curve: return normal
    p0 = curve.GetEndPoint(0)
    p1 = curve.GetEndPoint(1)
    mid_pt = (p0 + p1) / 2.0
    
    wall_level_id = wall.LevelId
    z_offset = 0.0
    if wall_level_id != ElementId.InvalidElementId:
        level = doc.GetElement(wall_level_id)
        if level: z_offset = level.Elevation
    test_z = z_offset + (1.5 / 0.3048)
    mid_pt_3d = XYZ(mid_pt.X, mid_pt.Y, test_z)
    
    offset_dist = (wall.Width / 2.0) + 1.0 
    pt_A = mid_pt_3d + (normal * offset_dist)
    pt_B = mid_pt_3d - (normal * offset_dist)
    
    phase = doc.GetElement(view.get_Parameter(BuiltInParameter.VIEW_PHASE).AsElementId())
    room_A = doc.GetRoomAtPoint(pt_A, phase)
    room_B = doc.GetRoomAtPoint(pt_B, phase)
    
    has_A = room_A is not None
    has_B = room_B is not None
    
    if has_A and not has_B: return normal.Negate()
    elif not has_A and has_B: return normal
    
    if selection_centroid:
        centroid_vec = (mid_pt - selection_centroid).Normalize()
        if centroid_vec.DotProduct(normal) > 0: return normal
        else: return normal.Negate()
            
    return normal

# --- COLETORES ---
def get_ends_strict(wall, start_pt, wall_dir):
    refs = []
    opt = Options()
    opt.ComputeReferences = True
    opt.DetailLevel = ViewDetailLevel.Fine
    opt.IncludeNonVisibleObjects = True
    geom = wall.get_Geometry(opt)
    if not geom: return []
    length = get_wall_curve(wall).Length
    for obj in geom:
        if isinstance(obj, Solid) and obj.Volume > 0:
            for face in obj.Faces:
                if is_parallel(face.FaceNormal, wall_dir):
                    dist = (face.Origin - start_pt).DotProduct(wall_dir)
                    if dist < 0.05 or dist > (length - 0.05):
                        refs.append(RefItem(face.Reference, dist))
    return refs

def get_intersecting_walls_hybrid(host_wall, start_pt, wall_dir):
    refs = []
    host_curve = get_wall_curve(host_wall)
    host_len = host_curve.Length
    
    # SCANNER
    bb = host_wall.get_BoundingBox(None)
    if not bb: return []
    
    # Expansão para pegar paredes encostadas
    outline = Outline(bb.Min - XYZ(0.5,0.5,0.5), bb.Max + XYZ(0.5,0.5,0.5))
    bb_filter = BoundingBoxIntersectsFilter(outline)
    collector = FilteredElementCollector(doc, doc.ActiveView.Id).OfClass(Wall).WherePasses(bb_filter)
    
    # [V17 FIX] Define margem de expansão baseada na parede HOST
    # Garante que o BBox da parede T alcance o eixo da parede Host
    reach_margin = max(host_wall.Width * 1.5, 2.0) # Pelo menos 2 pés ou 1.5x a largura
    
    for j_wall in collector:
        if j_wall.Id == host_wall.Id: continue 
        if j_wall.Width < MIN_THICKNESS_FT: continue 

        j_curve = get_wall_curve(j_wall)
        if not j_curve: continue
        j_dir = (j_curve.GetEndPoint(1) - j_curve.GetEndPoint(0)).Normalize()
        if abs(wall_dir.DotProduct(j_dir)) > 0.2: continue 
        
        try:
            sides_ext = HostObjectUtils.GetSideFaces(j_wall, ShellLayerType.Exterior)
            sides_int = HostObjectUtils.GetSideFaces(j_wall, ShellLayerType.Interior)
            all_sides = list(sides_ext) + list(sides_int)
            
            j_bb = j_wall.get_BoundingBox(None)
            if not j_bb: continue
            
            # [V17 FIX] EXPANSÃO AGRESSIVA DO BBOX DA PAREDE T
            # Expandimos o BBox da parede T em todas as direções para garantir que ele "cubra"
            # o ponto de intersecção no eixo da parede Host.
            j_outline = Outline(
                j_bb.Min - XYZ(reach_margin, reach_margin, reach_margin), 
                j_bb.Max + XYZ(reach_margin, reach_margin, reach_margin)
            )
            
            for ref in all_sides:
                face = j_wall.GetGeometryObjectFromReference(ref)
                if isinstance(face, PlanarFace):
                    if is_parallel(face.FaceNormal, wall_dir):
                        dist = intersect_line_plane(start_pt, wall_dir, face.Origin, face.FaceNormal)
                        if dist is not None:
                            pt_on_axis = start_pt + (wall_dir * dist)
                            
                            # Validação relaxada: Agora o BBox da parede T é gigante
                            if j_outline.Contains(pt_on_axis, 0): 
                                if 0.01 < dist < (host_len - 0.01):
                                    refs.append(RefItem(ref, dist))
        except: pass
    return refs

def get_openings_refs(wall, start_pt, wall_dir):
    refs = []
    inserts = wall.FindInserts(True, False, False, False)
    for eid in inserts:
        inst = doc.GetElement(eid)
        try:
            r_left = inst.GetReferences(FamilyInstanceReferenceType.Left)
            r_right = inst.GetReferences(FamilyInstanceReferenceType.Right)
            loc_pt = inst.Location.Point
            center_dist = (loc_pt - start_pt).DotProduct(wall_dir)
            w_p = inst.Symbol.get_Parameter(BuiltInParameter.DOOR_WIDTH) or \
                  inst.Symbol.get_Parameter(BuiltInParameter.WINDOW_WIDTH)
            hw = w_p.AsDouble()/2 if w_p else 1.0
            if r_left: refs.append(RefItem(r_left[0], center_dist - hw))
            if r_right: refs.append(RefItem(r_right[0], center_dist + hw))
        except: pass
    return refs

# --- BUILDER ---
def execute_dimensions(wall, view, dim_type, options, centroid=None):
    curve = get_wall_curve(wall)
    p0 = curve.GetEndPoint(0)
    p1 = curve.GetEndPoint(1)
    wall_dir = (p1 - p0).Normalize()
    
    ends = get_ends_strict(wall, p0, wall_dir)
    intersects = get_intersecting_walls_hybrid(wall, p0, wall_dir)
    openings = get_openings_refs(wall, p0, wall_dir)
    
    def clean(ref_list):
        if not ref_list: return []
        ref_list.sort(key=lambda x: x.dist)
        unique = [ref_list[0]]
        for i in range(1, len(ref_list)):
            if abs(ref_list[i].dist - ref_list[i-1].dist) > 0.003:
                unique.append(ref_list[i])
        return unique

    refs_L1 = clean(ends + intersects + openings)
    refs_L2 = clean(ends + intersects)
    
    if len(refs_L2) >= 2:
        refs_L3 = [refs_L2[0], refs_L2[-1]]
    else:
        refs_L3 = clean(ends)

    orient = get_smart_direction(wall, view, centroid)
    if options['side_inverted']: orient = orient.Negate()
    base_dist = options['dist_mm'] / 304.8 * view.Scale
    
    def create_dim(refs, tier):
        if len(refs) < 2: return
        arr = ReferenceArray()
        for r in refs: arr.Append(r.ref)
        offset = orient * (base_dist * tier)
        line = Line.CreateBound(p0 + offset, p1 + offset)
        try: doc.Create.NewDimension(view, line, arr, dim_type)
        except: pass

    tier = 1
    if options['do_L1'] and len(refs_L1) > 2:
        create_dim(refs_L1, tier)
        tier += 1
    if options['do_L2']:
        if len(refs_L2) > 2:
            create_dim(refs_L2, tier)
            tier += 1
        elif len(refs_L2) == 2 and not options['do_L3']:
             create_dim(refs_L2, tier)
             tier += 1
    if options['do_L3']:
        create_dim(refs_L3, tier)

# --- UI ---
class WallFilter(ISelectionFilter):
    def AllowElement(self, e): return e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Walls)
    def AllowReference(self, r, p): return False

dim_types = FilteredElementCollector(doc).OfClass(DimensionType).ToElements()
dim_names = sorted([n for n in (get_name_safe(d) for d in dim_types) if n and n.strip()])

class CotasWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        self.run_script = False
        self.cb_dim_style.ItemsSource = dim_names
        
        cfg = config_manager.get_config(CMD_ID)
        idx = 0
        if getattr(cfg, "style", None) in dim_names: idx = dim_names.index(cfg.style)
        self.cb_dim_style.SelectedIndex = idx
        self.tb_dist.Text = getattr(cfg, "dist", "10")
        if getattr(cfg, "side", "A") == "B": self.rb_side_int.IsChecked = True
        self.chk_line_1.IsChecked = getattr(cfg, "L1", True)
        self.chk_line_2.IsChecked = getattr(cfg, "L2", True)
        self.chk_line_3.IsChecked = getattr(cfg, "L3", True)

    def cb_dim_style_changed(self, s, a): pass
    def button_run_clicked(self, s, a):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "style": self.cb_dim_style.SelectedItem,
            "dist": self.tb_dist.Text,
            "side": "B" if self.rb_side_int.IsChecked else "A",
            "L1": self.chk_line_1.IsChecked,
            "L2": self.chk_line_2.IsChecked,
            "L3": self.chk_line_3.IsChecked
        })
        self.Close()

# --- RUN ---
win = CotasWindow()
win.ShowDialog()

if win.run_script:
    try:
        sel = uidoc.Selection.PickObjects(ObjectType.Element, WallFilter(), "Selecione Paredes")
        walls = [doc.GetElement(r) for r in sel]
    except: walls = []

    if walls:
        s_name = win.cb_dim_style.SelectedItem
        d_type = next((d for d in dim_types if get_name_safe(d) == s_name), None)
        
        opts = {
            'dist_mm': float(win.tb_dist.Text),
            'side_inverted': win.rb_side_int.IsChecked,
            'do_L1': win.chk_line_1.IsChecked,
            'do_L2': win.chk_line_2.IsChecked,
            'do_L3': win.chk_line_3.IsChecked
        }
        
        centroid = XYZ.Zero
        valid_count = 0
        for w in walls:
            c = get_wall_curve(w)
            if c:
                mid = (c.GetEndPoint(0) + c.GetEndPoint(1)) / 2.0
                centroid += mid
                valid_count += 1
        if valid_count > 0: centroid = centroid / valid_count
        
        count = 0
        with revit.Transaction("Maná Cotas V17"):
            for w in walls:
                execute_dimensions(w, doc.ActiveView, d_type, opts, centroid)
                count += 1
        forms.toast("Feito: {} paredes cotadas.".format(count))