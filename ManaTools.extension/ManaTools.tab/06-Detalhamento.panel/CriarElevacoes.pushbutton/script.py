# -*- coding: utf-8 -*-
"""
Gerador de Elevações V2.1 (Ceiling Detector).
Feature: Raycast vertical para detectar Forros/Lajes e ajustar o Crop Top.
"""
import os
import clr
import math

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType, ISelectionFilter
from pyrevit import forms, script, revit
from manalib import config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_elevacoes_v2"

# --- HELPER: SELEÇÃO ---
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

def get_view_templates():
    collector = FilteredElementCollector(doc).OfClass(View)
    templates = []
    for v in collector:
        if v.IsTemplate and (v.ViewType == ViewType.Elevation or v.ViewType == ViewType.Section):
            templates.append(v)
    return sorted(templates, key=lambda x: x.Name)

# --- HELPER 3D ---
def get_3d_view(doc):
    """Encontra uma vista 3D válida para o Raytrace."""
    col = FilteredElementCollector(doc).OfClass(View3D)
    for v in col:
        if not v.IsTemplate and not v.IsAssemblyView:
            return v
    return None

# --- ENGINE: DETECÇÃO DE ALTURA (FORRO/LAJE) ---
def get_ceiling_z(doc, center_pt, view3d):
    """
    Dispara um raio para cima para encontrar Forro, Laje ou Telhado.
    Retorna a cota Z do elemento encontrado.
    """
    if not view3d: return None
    
    # Categorias alvo: Forros, Pisos (Laje acima), Telhados
    cats = [
        BuiltInCategory.OST_Ceilings,
        BuiltInCategory.OST_Floors,
        BuiltInCategory.OST_Roofs
    ]
    # Cria filtro multicategoria
    # No IronPython, List[BuiltInCategory] pode ser chato, vamos usar FilterElementCollector logic
    # ReferenceIntersector aceita ElementFilter
    
    # Criando o filtro da maneira correta para API
    filters = List[ElementFilter]()
    for c in cats:
        filters.Add(ElementCategoryFilter(c))
    final_filter = LogicalOrFilter(filters)
    
    # ReferenceIntersector(targetFilter, targetElementCheck, view3d)
    intersector = ReferenceIntersector(final_filter, FindReferenceTarget.Element, view3d)
    intersector.FindReferencesInRevitLinks = True # Importante se o forro for linkado
    
    # Dispara do centro (elevado 10cm para não pegar o próprio chão)
    origin = XYZ(center_pt.X, center_pt.Y, center_pt.Z + 0.5) 
    direction = XYZ.BasisZ
    
    # Busca o mais próximo
    context = intersector.FindNearest(origin, direction)
    
    if context:
        # Pega o ponto de impacto
        hit_pt = context.GetReference().GlobalPoint
        return hit_pt.Z
        
    return None

# --- ENGINE: DETECÇÃO DE PAREDE LATERAL (2D) ---
def get_wall_thickness_at_vector(room, center_pt, direction_vec):
    options = SpatialElementBoundaryOptions()
    boundary_segments = room.GetBoundarySegments(options)
    if not boundary_segments: return 0.5
    
    closest_dist = float('inf')
    target_wall = None
    
    center_2d = XYZ(center_pt.X, center_pt.Y, 0)
    dir_2d = XYZ(direction_vec.X, direction_vec.Y, 0).Normalize()
    ray_line = Line.CreateUnbound(center_2d, dir_2d)
    
    for segment_list in boundary_segments:
        for seg in segment_list:
            curve = seg.GetCurve()
            results = clr.Reference[IntersectionResultArray]()
            res = ray_line.Intersect(curve, results)
            
            if res == SetComparisonResult.Overlap and results.Value:
                int_pt = results.Value[0].XYZPoint
                dist = center_2d.DistanceTo(int_pt)
                vec_to_int = (int_pt - center_2d).Normalize()
                if vec_to_int.DotProduct(dir_2d) > 0.9:
                    if dist < closest_dist:
                        closest_dist = dist
                        w = doc.GetElement(seg.ElementId)
                        if isinstance(w, Wall): target_wall = w

    if target_wall: return target_wall.Width
    return 0.5

# --- ENGINE: CROP BOX MATEMÁTICO ---
def apply_precise_crop(view, room, offsets, detected_ceiling_z=None):
    """
    Aplica o crop box transformando coordenadas do Mundo -> Vista.
    """
    bb = room.get_BoundingBox(None)
    if not bb: return
    
    # Se detectamos forro, substituímos o Max.Z do BBox
    max_z = bb.Max.Z
    if detected_ceiling_z:
        max_z = detected_ceiling_z
    else:
        # Se não achou forro, usa altura do room ou um default (ex: 2.80m do nivel)
        # Fallback para bbox do room
        pass

    # Limites "Ideais" no Mundo
    # Z Min = Nível do Room (Base)
    # Z Max = Forro
    # X/Y = BBox do Room
    
    # 1. Obter a Transform da Vista (Mundo -> Vista)
    # View.CropBox.Transform é a transformação da caixa. 
    # A coordenada da vista é local.
    # Precisamos projetar os pontos do Room no plano da vista.
    
    view_transform = view.CropBox.Transform
    inverse_transform = view_transform.Inverse
    
    # Pontos de interesse do Room (8 cantos do BBox ajustado)
    # Ajustamos o Z Max aqui antes de transformar
    
    corners = [
        XYZ(bb.Min.X, bb.Min.Y, bb.Min.Z),      # Base
        XYZ(bb.Max.X, bb.Max.Y, bb.Min.Z),
        XYZ(bb.Max.X, bb.Min.Y, bb.Min.Z),
        XYZ(bb.Min.X, bb.Max.Y, bb.Min.Z),
        
        XYZ(bb.Min.X, bb.Min.Y, max_z),         # Topo (Forro)
        XYZ(bb.Max.X, bb.Max.Y, max_z),
        XYZ(bb.Max.X, bb.Min.Y, max_z),
        XYZ(bb.Min.X, bb.Max.Y, max_z)
    ]
    
    # Transforma para coordenadas da Vista
    pts_view = [inverse_transform.OfPoint(p) for p in corners]
    
    # Encontra os limites na Vista (X e Y da vista = Largura e Altura do Crop)
    # Nota: No sistema da vista de elevação:
    # X = Horizontal (Largura)
    # Y = Vertical (Altura)
    # Z = Profundidade (Far Clip)
    
    v_min_x = min(p.X for p in pts_view)
    v_max_x = max(p.X for p in pts_view)
    v_min_y = min(p.Y for p in pts_view)
    v_max_y = max(p.Y for p in pts_view)
    
    # Aplica os Offsets do Usuário + Espessuras de Parede
    # offsets = {top, bottom, left, right}
    
    final_min_x = v_min_x - offsets['left']
    final_max_x = v_max_x + offsets['right']
    final_min_y = v_min_y - offsets['bottom']
    final_max_y = v_max_y + offsets['top']
    
    # Atualiza o CropBox
    cb = view.CropBox
    cb.Min = XYZ(final_min_x, final_min_y, cb.Min.Z)
    cb.Max = XYZ(final_max_x, final_max_y, cb.Max.Z)
    
    view.CropBox = cb
    view.CropBoxActive = True
    view.CropBoxVisible = True

# --- UI CLASS ---
from System.Collections.Generic import List # Necessário para o List do filtro

class ElevationWindow(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        self.run_script = False
        
        self.templates = get_view_templates()
        self.cb_view_templates.ItemsSource = [t.Name for t in self.templates]
        if self.templates: self.cb_view_templates.SelectedIndex = 0
        
        cfg = config_manager.get_config(CMD_ID)
        self.tb_offset_top.Text = getattr(cfg, "off_top", "10")
        self.tb_offset_bottom.Text = getattr(cfg, "off_bot", "10")
        self.chk_auto_wall.IsChecked = getattr(cfg, "auto_wall", True)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "off_top": self.tb_offset_top.Text,
            "off_bot": self.tb_offset_bottom.Text,
            "auto_wall": self.chk_auto_wall.IsChecked
        })
        self.Close()

# --- RUN ---
win = ElevationWindow()
win.ShowDialog()

if not win.run_script: script.exit()

rooms = get_rooms()
if not rooms: forms.alert("Selecione ambientes!", exitscript=True)

try:
    off_top = float(win.tb_offset_top.Text) / 30.48
    off_bot = float(win.tb_offset_bottom.Text) / 30.48
    off_side_extra = float(win.tb_offset_side.Text) / 30.48
except: forms.alert("Valores inválidos.", exitscript=True)

auto_wall = win.chk_auto_wall.IsChecked
sel_tmpl_name = win.cb_view_templates.SelectedItem
template_id = None
if sel_tmpl_name:
    t = next((x for x in win.templates if x.Name == sel_tmpl_name), None)
    if t: template_id = t.Id

directions = []
if win.tg_north.IsChecked: directions.append((1, XYZ.BasisY, "Norte"))
if win.tg_south.IsChecked: directions.append((3, -XYZ.BasisY, "Sul"))
if win.tg_east.IsChecked: directions.append((2, XYZ.BasisX, "Leste"))
if win.tg_west.IsChecked: directions.append((0, -XYZ.BasisX, "Oeste"))

vft = FilteredElementCollector(doc).OfClass(ViewFamilyType).ToElements()
elev_type = next((v for v in vft if v.ViewFamily == ViewFamily.Elevation), None)

if not elev_type: forms.alert("Sem tipo de Elevação.", exitscript=True)

# Busca Vista 3D para Raytrace
view3d = get_3d_view(doc)
if not view3d: 
    print("AVISO: Nenhuma vista 3D encontrada. A detecção de forro pode falhar.")

count = 0
with revit.Transaction("Maná Elevações V2.1"):
    for room in rooms:
        bb = room.get_BoundingBox(None)
        center = (bb.Min + bb.Max) / 2.0
        
        # 1. Detecta Forro (Uma vez por sala)
        # Se não achar, ceiling_z fica None e usa o BBox do Room
        ceiling_z = get_ceiling_z(doc, center, view3d)
        
        marker = ElevationMarker.CreateElevationMarker(doc, elev_type.Id, center, 100)
        
        for idx, vec_dir, suffix in directions:
            try:
                view = marker.CreateElevation(doc, doc.ActiveView.Id, idx)
                if template_id: view.ViewTemplateId = template_id
                
                r_name = room.get_Parameter(BuiltInParameter.ROOM_NAME).AsString()
                r_num = room.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString()
                try: view.Name = "ELEV - {} - {} - {}".format(r_num, r_name, suffix)
                except: pass
                
                # 2. Detecta Paredes Laterais (Uma vez por vista)
                right_vec = vec_dir.CrossProduct(XYZ.BasisZ).Normalize()
                left_vec = right_vec.Negate()
                
                thk_right = get_wall_thickness_at_vector(room, center, right_vec) if auto_wall else 0
                thk_left = get_wall_thickness_at_vector(room, center, left_vec) if auto_wall else 0
                
                offsets = {
                    'top': off_top,
                    'bottom': off_bot,
                    'left': thk_left + off_side_extra,
                    'right': thk_right + off_side_extra
                }
                
                # 3. Aplica Crop Matemático
                apply_precise_crop(view, room, offsets, ceiling_z)
                count += 1
                
            except Exception as e:
                print("Erro vista {}: {}".format(suffix, e))

forms.toast("Geradas {} elevações.".format(count))