# -*- coding: utf-8 -*-
"""
Gerador de Elevações V5.5 (Correção Geométrica).
Author: Lucas Rossetti | Maná Arquitetura
Fixes:
- Cota: Adicionada Cota Vertical (Pé-Direito).
- Tag Janela: Usa o centro do BoundingBox (evita deslocamento).
- Tag Room: Força posição Z+50cm via translação.
"""
import os
import clr
import traceback

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from pyrevit import forms, script, revit
from manalib import config_manager, dimensions 
from System.Collections.Generic import List 

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_elevacoes_v5"

# --- HELPER: NOME SEGURO ---
def get_safe_name(element):
    if not element: return "None"
    try:
        p = element.get_Parameter(BuiltInParameter.SYMBOL_NAME_PARAM)
        if p and p.AsString(): return p.AsString()
    except: pass
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.AsString(): return p.AsString()
    except: pass
    try: return element.Name
    except: return "Elemento {}".format(element.Id)

def get_rich_name(element):
    type_name = get_safe_name(element)
    try:
        if hasattr(element, "FamilyName") and element.FamilyName:
            return "{} : {}".format(element.FamilyName, type_name)
    except: pass
    return type_name

# --- HELPER: SELEÇÃO ---
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter

class RoomFilter(ISelectionFilter):
    def AllowElement(self, e): return e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)
    def AllowReference(self, r, p): return False

def get_rooms():
    ids = uidoc.Selection.GetElementIds()
    rooms = [doc.GetElement(id) for id in ids if doc.GetElement(id).Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)]
    if not rooms:
        try:
            refs = uidoc.Selection.PickObjects(ObjectType.Element, RoomFilter(), "Selecione os Ambientes")
            rooms = [doc.GetElement(r) for r in refs]
        except: return []
    return rooms

# --- COLLECTORS ---
def get_view_templates():
    col = FilteredElementCollector(doc).OfClass(View)
    templates = [v for v in col if v.IsTemplate and v.ViewType == ViewType.Elevation]
    return sorted(templates, key=get_safe_name)

def get_3d_view(doc):
    col = FilteredElementCollector(doc).OfClass(View3D)
    for v in col:
        if not v.IsTemplate and not v.IsAssemblyView: return v
    return None

def get_tags_of_category(built_in_cat):
    col = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(built_in_cat)
    return sorted(list(col.ToElements()), key=get_rich_name)

# --- ENGINE: GEOMETRIA & CROP ---
def get_ceiling_info_fixed(doc, center, view3d):
    cats = [BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs]
    # Sobe 1.5m para garantir que está dentro do ambiente e atira pra cima
    origin = XYZ(center.X, center.Y, center.Z + 1.5) 
    pt, ref = dimensions.raytrace_generic(view3d, origin, XYZ.BasisZ, cats)
    if pt: return pt.Z, ref
    return None, None

def get_floor_info(doc, center, view3d):
    cats = [BuiltInCategory.OST_Floors]
    # Sobe 0.5m e atira pra baixo
    origin = XYZ(center.X, center.Y, center.Z + 0.5)
    pt, ref = dimensions.raytrace_generic(view3d, origin, XYZ.BasisZ.Negate(), cats)
    if pt: return pt.Z, ref
    return None, None

def apply_precise_crop(view, room, offsets, ceiling_z):
    bb = room.get_BoundingBox(None)
    if not bb: return
    room_level_z = bb.Min.Z
    default_height = 2.80 / 0.3048
    max_z = ceiling_z if ceiling_z else (room_level_z + default_height)
    
    view_transform = view.CropBox.Transform
    inverse_transform = view_transform.Inverse
    
    corners = [
        XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z), XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z),
        XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z), XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z),
        XYZ(bb.Min.X, bb.Min.Y, max_z),    XYZ(bb.Max.X, bb.Max.Y, max_z),
        XYZ(bb.Max.X, bb.Min.Y, max_z),    XYZ(bb.Min.X, bb.Max.Y, max_z)
    ]
    pts_view = [inverse_transform.OfPoint(p) for p in corners]
    v_min_x = min(p.X for p in pts_view)
    v_max_x = max(p.X for p in pts_view)
    v_min_y = min(p.Y for p in pts_view)
    v_max_y = max(p.Y for p in pts_view)
    
    cb = view.CropBox
    cb.Min = XYZ(v_min_x - offsets['left'], v_min_y - offsets['bottom'], cb.Min.Z)
    cb.Max = XYZ(v_max_x + offsets['right'], v_max_y + offsets['top'], cb.Max.Z)
    view.CropBox = cb
    view.CropBoxActive = True
    view.CropBoxVisible = True

def get_wall_thickness_at_vector(room, center, vec):
    opt = SpatialElementBoundaryOptions()
    segs = room.GetBoundarySegments(opt)
    if not segs: return 0.5
    center_2d = XYZ(center.X, center.Y, 0)
    ray = Line.CreateUnbound(center_2d, XYZ(vec.X, vec.Y, 0))
    target_w = None
    for sl in segs:
        for s in sl:
            res = ray.Intersect(s.GetCurve())
            if res == SetComparisonResult.Overlap:
                elem = doc.GetElement(s.ElementId)
                if isinstance(elem, Wall): target_w = elem
    if target_w: return target_w.Width
    return 0.5

# --- ANNOTATION ---
def annotate_elevation(doc, view, room, view3d, ceiling_z, ceiling_ref, options):
    dim_style_id = options.get("dim_style_id")
    
    # 1. COTA VERTICAL (Pé Direito) - CORRIGIDO
    if options.get("do_dims", False) and ceiling_ref:
        try:
            # Precisa achar o piso também
            bbox = view.CropBox
            center_room = room.Location.Point
            
            floor_z, floor_ref = get_floor_info(doc, center_room, view3d)
            
            if floor_ref and ceiling_ref:
                # Cria linha de cota Vertical
                # X = Perto da borda direita do crop
                dim_x = bbox.Max.X - (0.5 / 0.3048) # Recua 50cm da borda
                
                # Z na vista = Y na vista
                # Precisamos projetar os pontos Z do mundo para Y da vista
                # Mas para NewDimension na vista, usamos coordenadas do mundo na linha?
                # Sim, Line deve ser paralela ao plano da cota.
                
                # Para uma cota vertical em elevação, a linha deve ser vertical (Z)
                pt_bot = XYZ(center_room.X, center_room.Y, floor_z)
                pt_top = XYZ(center_room.X, center_room.Y, ceiling_z)
                
                line = Line.CreateBound(pt_bot, pt_top)
                dimensions.create_linear_dimension(doc, view, line, [floor_ref, ceiling_ref], dim_style_id)
        except Exception as e: print("Erro Cota Vertical: {}".format(e))

    # 2. TAG AMBIENTE (Forçada 50cm acima)
    if options.get("do_room_tag", False):
        try:
            loc = room.Location.Point
            # Ponto 3D Exato: Piso + 50cm
            target_pt = XYZ(loc.X, loc.Y, loc.Z + (0.50 / 0.3048))
            
            # Projeta no plano da vista
            v_inv = view.CropBox.Transform.Inverse
            pt_view = v_inv.OfPoint(target_pt)
            uv = UV(pt_view.X, pt_view.Y)
            
            tag = doc.Create.NewRoomTag(LinkElementId(room.Id), uv, view.Id)
            
            tid = options.get("room_tag_type_id")
            if tid and tag: tag.ChangeTypeId(tid)
            try: tag.HasLeader = False
            except: pass
        except Exception as e: print("Erro Tag Room: {}".format(e))

    # 3. TAG ESQUADRIAS (Centralizadas no BBox)
    if options.get("do_door_win_tag", False):
        try:
            col = FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
            cats = List[BuiltInCategory]([BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows])
            elements = col.WherePasses(ElementMulticategoryFilter(cats)).ToElements()
            
            door_style = options.get("door_tag_type_id")
            win_style = options.get("win_tag_type_id")

            for el in elements:
                # Usa BBox da geometria para achar o centro visual real
                bb = el.get_BoundingBox(view)
                if not bb: continue
                
                # Centro do BBox na vista
                mid_x = (bb.Min.X + bb.Max.X) / 2.0
                mid_y = (bb.Min.Y + bb.Max.Y) / 2.0
                mid_pt_view = XYZ(mid_x, mid_y, 0)
                
                target_style = door_style if el.Category.Id.IntegerValue == int(BuiltInCategory.OST_Doors) else win_style
                
                try:
                    tag = None
                    if hasattr(IndependentTag, "Create"):
                        tag = IndependentTag.Create(doc, view.Id, Reference(el), False, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, mid_pt_view)
                    else:
                        tag = doc.Create.NewTag(view, el, True, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, mid_pt_view)
                    
                    if tag and target_style: tag.ChangeTypeId(target_style)
                except: pass
        except: pass

# --- UI CLASS ---
class ElevationWindow(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        self.run_script = False
        
        self.templates = get_view_templates()
        self.cb_view_templates.ItemsSource = [t.Name for t in self.templates]
        if self.templates: self.cb_view_templates.SelectedIndex = 0
        
        self.dim_styles = sorted(FilteredElementCollector(doc).OfClass(DimensionType).ToElements(), key=get_rich_name)
        self.dim_styles = [d for d in self.dim_styles if d.StyleType == DimensionStyleType.Linear]
        self.cb_dim_styles.ItemsSource = [get_rich_name(d) for d in self.dim_styles]
        if self.dim_styles: self.cb_dim_styles.SelectedIndex = 0
        
        self.room_tag_types = get_tags_of_category(BuiltInCategory.OST_RoomTags)
        self.cb_room_tag_types.ItemsSource = [get_rich_name(t) for t in self.room_tag_types]
        if self.room_tag_types: self.cb_room_tag_types.SelectedIndex = 0

        self.door_tag_types = get_tags_of_category(BuiltInCategory.OST_DoorTags)
        self.cb_door_tag.ItemsSource = [get_rich_name(t) for t in self.door_tag_types]
        if self.door_tag_types: self.cb_door_tag.SelectedIndex = 0

        self.win_tag_types = get_tags_of_category(BuiltInCategory.OST_WindowTags)
        self.cb_window_tag.ItemsSource = [get_rich_name(t) for t in self.win_tag_types]
        if self.win_tag_types: self.cb_window_tag.SelectedIndex = 0

        cfg = config_manager.get_config(CMD_ID)
        self.tb_offset_top.Text = getattr(cfg, "off_top", "10")
        self.tb_offset_bottom.Text = getattr(cfg, "off_bot", "10")
        self.tb_offset_side.Text = getattr(cfg, "off_side", "0") 
        self.chk_auto_wall.IsChecked = getattr(cfg, "auto_wall", True)
        self.chk_tag_room.IsChecked = getattr(cfg, "do_room_tag", True)
        self.chk_tag_openings.IsChecked = getattr(cfg, "do_door_win_tag", True)
        self.chk_dims.IsChecked = getattr(cfg, "do_dims", True) 

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "off_top": self.tb_offset_top.Text,
            "off_bot": self.tb_offset_bottom.Text,
            "off_side": self.tb_offset_side.Text,
            "auto_wall": self.chk_auto_wall.IsChecked,
            "do_room_tag": self.chk_tag_room.IsChecked,
            "do_door_win_tag": self.chk_tag_openings.IsChecked,
            "do_dims": self.chk_dims.IsChecked
        })
        self.Close()

# --- RUN ---
win = ElevationWindow()
win.ShowDialog()

if not win.run_script: script.exit()

rooms = get_rooms()
if not rooms: forms.alert("Selecione ambientes!", exitscript=True)

try:
    def sf(v): return float(v.replace(',', '.')) / 30.48
    off_top, off_bot, off_side = sf(win.tb_offset_top.Text), sf(win.tb_offset_bottom.Text), sf(win.tb_offset_side.Text)
except: forms.alert("Erro numérico.", exitscript=True)

opts = {
    "do_room_tag": win.chk_tag_room.IsChecked,
    "do_door_win_tag": win.chk_tag_openings.IsChecked,
    "do_dims": win.chk_dims.IsChecked,
    "dim_style_id": None,
    "room_tag_type_id": None,
    "door_tag_type_id": None,
    "win_tag_type_id": None
}

def get_selected_id(combo, list_objs):
    sel_name = combo.SelectedItem
    obj = next((x for x in list_objs if get_rich_name(x) == sel_name), None)
    return obj.Id if obj else None

opts["dim_style_id"] = get_selected_id(win.cb_dim_styles, win.dim_styles)
opts["room_tag_type_id"] = get_selected_id(win.cb_room_tag_types, win.room_tag_types)
opts["door_tag_type_id"] = get_selected_id(win.cb_door_tag, win.door_tag_types)
opts["win_tag_type_id"] = get_selected_id(win.cb_window_tag, win.win_tag_types)

template_id = None
if win.cb_view_templates.SelectedItem:
    t = next((x for x in win.templates if x.Name == win.cb_view_templates.SelectedItem), None)
    if t: template_id = t.Id

directions = []
if win.tg_north.IsChecked: directions.append((1, XYZ.BasisY, "N"))
if win.tg_south.IsChecked: directions.append((3, -XYZ.BasisY, "S"))
if win.tg_east.IsChecked: directions.append((2, XYZ.BasisX, "L"))
if win.tg_west.IsChecked: directions.append((0, -XYZ.BasisX, "O"))

view3d = get_3d_view(doc)
elev_type = next((v for v in FilteredElementCollector(doc).OfClass(ViewFamilyType) if v.ViewFamily == ViewFamily.Elevation), None)

count = 0
with revit.Transaction("Maná Elevações V5.5"):
    for room in rooms:
        bb = room.get_BoundingBox(None)
        if not bb: continue
        center = (bb.Min + bb.Max) / 2.0
        
        ceiling_z, ceiling_ref = get_ceiling_info_fixed(doc, center, view3d)
        marker = ElevationMarker.CreateElevationMarker(doc, elev_type.Id, center, 100)
        
        for idx, vec, suf in directions:
            try:
                view = marker.CreateElevation(doc, doc.ActiveView.Id, idx)
                if template_id: view.ViewTemplateId = template_id
                
                r_num = room.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString() or "00"
                r_name = room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString() or "Amb"
                try: view.Name = "E.{} - {} ({})".format(r_num, r_name, suf)
                except: pass
                
                right = vec.CrossProduct(XYZ.BasisZ).Normalize()
                thk_r = get_wall_thickness_at_vector(room, center, right) if win.chk_auto_wall.IsChecked else 0
                thk_l = get_wall_thickness_at_vector(room, center, -right) if win.chk_auto_wall.IsChecked else 0
                
                offsets = {'top': off_top, 'bottom': off_bot, 'left': thk_l + off_side, 'right': thk_r + off_side}
                
                apply_precise_crop(view, room, offsets, ceiling_z)
                
                doc.Regenerate()
                annotate_elevation(doc, view, room, view3d, ceiling_z, ceiling_ref, opts)
                count += 1
            except Exception as e:
                print("Erro na vista {}: {}".format(suf, e))

forms.toast("Feito: {} vistas.".format(count))