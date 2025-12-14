# -*- coding: utf-8 -*-
"""
Automação de Cotas em Ambientes.
V1.2 FIX: Tratamento de erro no parâmetro de Snap (AttributeError).
"""
import os
import math
import clr
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
CMD_ID = "manatools_cotar"

# --- HELPER SEGURO ---
def get_name_safe(elem):
    if not elem: return ""
    try: return Element.Name.GetValue(elem)
    except: 
        try: return elem.Name
        except: return str(elem.Id)

# --- FILTRO ---
class RoomFilter(ISelectionFilter):
    def AllowElement(self, e): 
        if not e.Category: return False
        return e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms)
    def AllowReference(self, r, p): return False

def get_rooms():
    rooms = []
    try:
        with forms.WarningBar(title="Selecione Ambientes (ESC p/ sair):"):
            refs = uidoc.Selection.PickObjects(ObjectType.Element, RoomFilter(), "Selecione Ambientes")
            for r in refs: 
                elem = doc.GetElement(r)
                if elem: rooms.append(elem)
    except OperationCanceledException:
        script.exit()
    return rooms

# --- MATH ---
def get_view_scale():
    return doc.ActiveView.Scale

def mm_to_feet(mm):
    return mm / 304.8

def get_snap_from_style(dim_type):
    """
    Lê o parâmetro de Snap do estilo de cota de forma segura.
    Se falhar, retorna 5.0mm.
    """
    try:
        # Tenta acessar o BuiltInParameter
        # O 'getattr' evita o crash se o atributo não existir na versão do Revit
        bip = getattr(BuiltInParameter, "DIM_STYLE_LINE_SNAP_IND", None)
        
        if bip:
            p = dim_type.get_Parameter(bip)
            if p and p.HasValue:
                val = p.AsDouble()
                if val > 0.001: return val * 304.8 # Retorna em mm
    except:
        pass
        
    return 5.0 # Default seguro se falhar

# --- CORE GEOMETRY ---
def analyze_room_boundary(room):
    data = []
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    calc = SpatialElementGeometryCalculator(doc, opt)
    try:
        results = calc.CalculateSpatialElementGeometry(room)
    except: 
        return [] 
        
    room_solid = results.GetGeometry()
    
    for face in room_solid.Faces:
        boundary_info_list = results.GetBoundaryFaceInfo(face)
        
        for info in boundary_info_list:
            link_id = info.SpatialBoundaryElement.HostElementId
            if link_id == ElementId.InvalidElementId: continue
            
            elem = doc.GetElement(link_id)
            if not isinstance(elem, Wall): continue
            
            wall_ref = None
            w_opt = Options()
            w_opt.ComputeReferences = True
            w_geom = elem.get_Geometry(w_opt)
            
            room_face_normal = face.FaceNormal
            
            if w_geom:
                found_ref = False
                for obj in w_geom:
                    if isinstance(obj, Solid):
                        for w_face in obj.Faces:
                            if w_face.FaceNormal.IsAlmostEqualTo(-room_face_normal):
                                try:
                                    res = w_face.Project(face.Origin) 
                                    if res and res.Distance < 0.01:
                                        wall_ref = w_face.Reference
                                        found_ref = True
                                        break
                                except: pass
                    if found_ref: break
            
            if wall_ref:
                tangent = XYZ(-room_face_normal.Y, room_face_normal.X, 0).Normalize()
                
                data.append({
                    'wall': elem,
                    'face_ref': wall_ref,
                    'normal': room_face_normal, 
                    'tangent': tangent,
                    'origin': face.Origin 
                })
                
    return data

def create_dimensions(view, dim_type, segments, dist_wall_mm, snap_mm, layers):
    scale = view.Scale
    d_wall = mm_to_feet(dist_wall_mm) * scale
    d_snap = mm_to_feet(snap_mm) * scale
    
    processed_walls = []
    
    with revit.Transaction("Criar Cotas"):
        for i, seg_A in enumerate(segments):
            if seg_A in processed_walls: continue
            
            normal_A = seg_A['normal']
            candidates = []
            for j, seg_B in enumerate(segments):
                if i == j: continue
                if normal_A.DotProduct(seg_B['normal']) < -0.9:
                    vec_connect = seg_B['origin'] - seg_A['origin']
                    if vec_connect.DotProduct(normal_A) > 0:
                        candidates.append(seg_B)
            
            if not candidates: continue
            
            target_seg = min(candidates, key=lambda s: s['origin'].DistanceTo(seg_A['origin']))
            
            # --- LINHA 3 (TOTAL) ---
            if layers['total']:
                try:
                    pt_mid = (seg_A['origin'] + target_seg['origin']) / 2.0
                    line_dir = normal_A
                    
                    p_start = pt_mid
                    p_end = pt_mid + (line_dir * 5)
                    
                    dim_line = Line.CreateBound(p_start, p_end)
                    
                    refs = ReferenceArray()
                    refs.Append(seg_A['face_ref'])
                    refs.Append(target_seg['face_ref'])
                    
                    doc.Create.NewDimension(view, dim_line, refs, dim_type)
                    
                    processed_walls.append(seg_A)
                    processed_walls.append(target_seg)
                    
                except: pass

# --- GUI ---
dim_types = FilteredElementCollector(doc).OfClass(DimensionType).ToElements()
dim_names = [get_name_safe(d) for d in dim_types] 
dim_names = [n for n in dim_names if n]

class CotasWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        self.run_script = False
        self.cb_dim_style.ItemsSource = dim_names
        self.cb_dim_style.SelectedIndex = 0
        
        for i, n in enumerate(dim_names):
            if "2.5" in n or "Arial" in n:
                self.cb_dim_style.SelectedIndex = i
                break
        
        self.update_snap_display()

    def update_snap_display(self):
        if self.cb_dim_style.SelectedItem:
            dt = next((d for d in dim_types if get_name_safe(d) == self.cb_dim_style.SelectedItem), None)
            if dt:
                snap = get_snap_from_style(dt)
                self.tb_snap_dist.Text = "{:.2f}".format(snap)

    def cb_dim_style_changed(self, sender, args):
        self.update_snap_display()

    def button_run_clicked(self, sender, args):
        self.run_script = True
        self.Close()

win = CotasWindow()
try: 
    win.cb_dim_style.SelectionChanged += win.cb_dim_style_changed
except: 
    pass 
win.ShowDialog()

if not win.run_script: script.exit()

rooms = get_rooms()
if not rooms: script.exit()

sel_dim_name = win.cb_dim_style.SelectedItem
dim_type = next((d for d in dim_types if get_name_safe(d) == sel_dim_name), None)

if not dim_type:
    forms.alert("Estilo de cota não encontrado.", exitscript=True)

try:
    snap_mm = float(win.tb_snap_dist.Text)
    wall_dist_mm = float(win.tb_wall_dist.Text)
except:
    forms.alert("Valores numéricos inválidos.", exitscript=True)

layers = {
    'total': win.chk_line_3.IsChecked,
}

try:
    for room in rooms:
        segments = analyze_room_boundary(room)
        if segments:
            create_dimensions(doc.ActiveView, dim_type, segments, wall_dist_mm, snap_mm, layers)
    
    forms.toast("Cotas criadas!")
    
except Exception as e:
    forms.alert("Erro: {}".format(e))