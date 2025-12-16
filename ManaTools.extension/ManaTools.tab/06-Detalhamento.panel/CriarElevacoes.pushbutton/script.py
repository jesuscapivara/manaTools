# -*- coding: utf-8 -*-
"""
Gerador de Elevações V6.0 (Pure Creation).
Foco: Criação de vistas, Nomenclatura e Crop Box preciso.
"""
import clr
import os
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from pyrevit import forms, script, revit
from manalib import config_manager, dimensions # Mantemos dimensions para o Raytrace do Forro

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_elevacoes_create"

# --- HELPERS ---
def get_safe_name(e):
    try: return e.Name
    except: return "Unnamed"

def get_view_templates():
    col = FilteredElementCollector(doc).OfClass(View)
    return sorted([v for v in col if v.IsTemplate and v.ViewType == ViewType.Elevation], key=get_safe_name)

def get_3d_view(doc):
    col = FilteredElementCollector(doc).OfClass(View3D)
    for v in col:
        if not v.IsTemplate and not v.IsAssemblyView: return v
    return None

# --- ENGINE ---
def get_ceiling_height(doc, center, view3d):
    """Retorna Z do forro ou None."""
    cats = [BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs]
    origin = XYZ(center.X, center.Y, center.Z + 1.5) # +1.5m pra ignorar móveis
    pt, _ = dimensions.raytrace_generic(view3d, origin, XYZ.BasisZ, cats)
    if pt: return pt.Z
    return None

def apply_crop(view, room, offsets, ceiling_z):
    bb = room.get_BoundingBox(None)
    if not bb: return
    
    # Altura: Se achou forro usa, senão usa 2.80m padrão
    min_z = bb.Min.Z
    max_z = ceiling_z if ceiling_z else (min_z + (2.80/0.3048))
    
    # 8 Cantos do Room (Base e Topo)
    corners = [
        XYZ(bb.Min.X, bb.Min.Y, min_z), XYZ(bb.Max.X, bb.Max.Y, min_z),
        XYZ(bb.Max.X, bb.Min.Y, min_z), XYZ(bb.Min.X, bb.Max.Y, min_z),
        XYZ(bb.Min.X, bb.Min.Y, max_z), XYZ(bb.Max.X, bb.Max.Y, max_z),
        XYZ(bb.Max.X, bb.Min.Y, max_z), XYZ(bb.Min.X, bb.Max.Y, max_z)
    ]
    
    # Transforma para coordenadas da Vista
    t_inv = view.CropBox.Transform.Inverse
    pts_view = [t_inv.OfPoint(p) for p in corners]
    
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

def get_wall_thickness(room, center, vec):
    # Lógica simplificada de raytrace 2D
    opt = SpatialElementBoundaryOptions()
    segs = room.GetBoundarySegments(opt)
    if not segs: return 0.5
    
    ray = Line.CreateUnbound(XYZ(center.X, center.Y, 0), XYZ(vec.X, vec.Y, 0))
    for sl in segs:
        for s in sl:
            if ray.Intersect(s.GetCurve()) == SetComparisonResult.Overlap:
                e = doc.GetElement(s.ElementId)
                if isinstance(e, Wall): return e.Width
    return 0.5

# --- UI ---
class CreateElevUI(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        self.run_script = False
        
        self.templates = get_view_templates()
        self.cb_view_templates.ItemsSource = [t.Name for t in self.templates]
        if self.templates: self.cb_view_templates.SelectedIndex = 0
        
        cfg = config_manager.get_config(CMD_ID)
        self.tb_top.Text = getattr(cfg, "top", "10")
        self.tb_bot.Text = getattr(cfg, "bot", "10")
        self.tb_side.Text = getattr(cfg, "side", "0") 
        self.chk_wall.IsChecked = getattr(cfg, "auto_wall", True)

    def btn_ok_click(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "top": self.tb_top.Text, "bot": self.tb_bot.Text, 
            "side": self.tb_side.Text, "auto_wall": self.chk_wall.IsChecked
        })
        self.Close()

# --- RUN ---
win = CreateElevUI()
win.ShowDialog()
if not win.run_script: script.exit()

# Seleção de Salas
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
class RoomFilter(ISelectionFilter):
    def AllowElement(self, e): return e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)
    def AllowReference(self, r, p): return False

sel_ids = uidoc.Selection.GetElementIds()
rooms = [doc.GetElement(id) for id in sel_ids if doc.GetElement(id).Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)]
if not rooms:
    try:
        refs = uidoc.Selection.PickObjects(ObjectType.Element, RoomFilter(), "Selecione os Ambientes")
        rooms = [doc.GetElement(r) for r in refs]
    except: script.exit()

if not rooms: script.exit()

# Inputs
try:
    def sf(v): return float(v.replace(',', '.')) / 30.48
    off_top, off_bot, off_side = sf(win.tb_top.Text), sf(win.tb_bot.Text), sf(win.tb_side.Text)
except: forms.alert("Erro nos valores.", exitscript=True)

tmpl_id = None
if win.cb_view_templates.SelectedItem:
    t = next((x for x in win.templates if x.Name == win.cb_view_templates.SelectedItem), None)
    if t: tmpl_id = t.Id

dirs = []
if win.tg_n.IsChecked: dirs.append((1, XYZ.BasisY, "N"))
if win.tg_s.IsChecked: dirs.append((3, -XYZ.BasisY, "S"))
if win.tg_l.IsChecked: dirs.append((2, XYZ.BasisX, "L"))
if win.tg_o.IsChecked: dirs.append((0, -XYZ.BasisX, "O"))

view3d = get_3d_view(doc)
elev_type = next((v for v in FilteredElementCollector(doc).OfClass(ViewFamilyType) if v.ViewFamily == ViewFamily.Elevation), None)

count = 0
with revit.Transaction("Gerar Elevações"):
    for room in rooms:
        bb = room.get_BoundingBox(None)
        if not bb: continue
        center = (bb.Min + bb.Max) / 2.0
        
        ceil_z = get_ceiling_height(doc, center, view3d)
        marker = ElevationMarker.CreateElevationMarker(doc, elev_type.Id, center, 100)
        
        for idx, vec, suf in dirs:
            try:
                view = marker.CreateElevation(doc, doc.ActiveView.Id, idx)
                if tmpl_id: view.ViewTemplateId = tmpl_id
                
                # Naming
                r_num = room.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString() or "00"
                r_name = room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString() or "Amb"
                try: view.Name = "E.{} - {} ({})".format(r_num, r_name, suf)
                except: pass # Se der erro de nome duplicado, segue com o padrão
                
                # Crop
                right = vec.CrossProduct(XYZ.BasisZ).Normalize()
                thk_r = get_wall_thickness(room, center, right) if win.chk_wall.IsChecked else 0
                thk_l = get_wall_thickness(room, center, -right) if win.chk_wall.IsChecked else 0
                
                offsets = {'top': off_top, 'bottom': off_bot, 'left': thk_l + off_side, 'right': thk_r + off_side}
                apply_crop(view, room, offsets, ceil_z)
                count += 1
            except: pass

forms.toast("Criadas {} vistas.".format(count))