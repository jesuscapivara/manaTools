# -*- coding: utf-8 -*-
"""
Detalhador de Elevações V12.1 (Fix NameError).
Author: Lucas Rossetti | Maná Arquitetura
Fixes:
- Restaura função 'get_room_from_view' que faltava na V12.0.
- Mantém lógica vetorial de posicionamento.
"""
import os
import clr
import math
import traceback

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from pyrevit import forms, script, revit
from manalib import config_manager, dimensions 
from System.Collections.Generic import List 

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_elevacoes_detail"

# --- HELPER CLASSES ---
class TagTask:
    def __init__(self, element, category_id, mid_pt_view):
        self.element = element
        self.category_id = category_id
        self.initial_y = mid_pt_view.Y
        self.final_y = mid_pt_view.Y
        self.mid_pt_view = mid_pt_view 

# --- HELPERS ---
def get_safe_name(e):
    try: return Element.Name.GetValue(e)
    except: return e.Name

def get_rich_name(e):
    name = get_safe_name(e)
    try:
        if hasattr(e, "FamilyName") and e.FamilyName: return "{} : {}".format(e.FamilyName, name)
    except: pass
    return name

def get_tags(cat):
    col = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(cat)
    return sorted(list(col.ToElements()), key=get_rich_name)

def get_dim_styles():
    col = FilteredElementCollector(doc).OfClass(DimensionType)
    valid = [d for d in col if d.StyleType == DimensionStyleType.Linear]
    return sorted(valid, key=get_rich_name)

def get_all_elevations():
    return [v for v in FilteredElementCollector(doc).OfClass(View) 
            if not v.IsTemplate and v.ViewType == ViewType.Elevation]

# --- INTELLIGENCE (RESTAURADA) ---
def get_room_from_view(view):
    """Recupera o Room baseado na geometria da vista ou nome."""
    # 1. Geometria (Centro do Crop)
    if view.CropBoxActive:
        bb = view.CropBox
        center_view = (bb.Min + bb.Max) / 2.0
        t = view.CropBox.Transform
        origin = t.OfPoint(center_view)
        view_level = view.GenLevel
        if view_level:
            # Tenta em várias alturas
            for h in [0.5, 1.5, 2.5]:
                pt = XYZ(origin.X, origin.Y, view_level.Elevation + (h/0.3048))
                room = doc.GetRoomAtPoint(pt)
                if room: return room
                # Tenta projetar pra frente (caso o corte esteja na parede)
                room = doc.GetRoomAtPoint(pt + (view.ViewDirection * 3.0))
                if room: return room

    # 2. Fallback Nome (Ex: "E.05 - Cozinha")
    try:
        parts = view.Name.split(' - ')
        if len(parts) > 1 and '.' in parts[0]:
            num = parts[0].split('.')[-1].strip()
            for r in FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms):
                if r.get_Parameter(BuiltInParameter.ROOM_NUMBER).AsString() == num: return r
    except: pass
    return None

def get_compatible_3d_view(doc, target_phase_id):
    """Busca vista 3D compatível com a fase."""
    col = FilteredElementCollector(doc).OfClass(View3D)
    valid_views = [v for v in col if not v.IsTemplate and not v.IsAssemblyView]
    uncropped = [v for v in valid_views if not v.IsSectionBoxActive]
    candidates = uncropped if uncropped else valid_views
    
    if target_phase_id:
        for v in candidates:
            p = v.get_Parameter(BuiltInParameter.VIEW_PHASE)
            if p and p.AsElementId() == target_phase_id: return v
            
    for v in valid_views:
        if v.Name == "{3D}": return v
    return valid_views[0] if valid_views else None

# --- ENGINE: FIND FLOOR/CEILING ---
def find_room_vertical_refs(doc, room, view3d):
    if not room or not view3d: return None, None, None, None
    center = room.Location.Point
    cats_ceil = [BuiltInCategory.OST_Ceilings, BuiltInCategory.OST_Floors, BuiltInCategory.OST_Roofs, BuiltInCategory.OST_StructuralFraming, BuiltInCategory.OST_GenericModel]
    cats_floor = [BuiltInCategory.OST_Floors]
    origin = XYZ(center.X, center.Y, room.Level.Elevation + 1.6)
    offsets = [XYZ.Zero, XYZ(0.5, 0.5, 0), XYZ(-0.5, 0.5, 0)]
    ref_ceil, z_ceil = None, None
    ref_floor, z_floor = None, None
    for off in offsets:
        if ref_ceil and ref_floor: break
        origin_try = origin + off
        if not ref_ceil:
            pt, ref = dimensions.raytrace_generic(view3d, origin_try, XYZ.BasisZ, cats_ceil)
            if ref: ref_ceil = ref; z_ceil = pt.Z
        if not ref_floor:
            pt, ref = dimensions.raytrace_generic(view3d, origin_try, XYZ.BasisZ.Negate(), cats_floor)
            if ref: ref_floor = ref; z_floor = pt.Z
    return ref_floor, z_floor, ref_ceil, z_ceil

# --- ENGINE: COTA CADEIA (VETORIAL) ---
def create_opening_chain(doc, view, element, room, view3d, dim_style_id):
    try:
        print("   [DEBUG] Vão: {}".format(get_safe_name(element)))
        
        # 1. SCANNER HÍBRIDO (V11.0 logic)
        ref_bot, ref_top, z_min, z_max, method = dimensions.get_hybrid_vertical_refs(doc, element, view)
        print("      > Método: {}".format(method))
        
        if not ref_top: return

        # 2. SCANNER AMBIENTE
        ref_floor, z_floor, ref_ceil, z_ceil = find_room_vertical_refs(doc, room, view3d)

        # 3. LISTA DE PONTOS
        refs_to_dim = []
        if ref_floor: refs_to_dim.append((z_floor, ref_floor))
        if ref_ceil: refs_to_dim.append((z_ceil, ref_ceil))
        
        is_window = element.Category.Id.IntegerValue == int(BuiltInCategory.OST_Windows)
        if ref_top: refs_to_dim.append((z_max, ref_top))
        if ref_bot:
            if is_window: refs_to_dim.append((z_min, ref_bot))
            elif ref_floor and abs(z_min - z_floor) > 0.05:
                refs_to_dim.append((z_min, ref_bot))

        # Ordena e remove duplicatas
        refs_to_dim.sort(key=lambda x: x[0])
        unique_refs = []
        if refs_to_dim:
            unique_refs.append(refs_to_dim[0])
            for i in range(1, len(refs_to_dim)):
                if abs(refs_to_dim[i][0] - refs_to_dim[i-1][0]) > 0.01:
                    unique_refs.append(refs_to_dim[i])
        final_refs = [r[1] for r in unique_refs]
        if len(final_refs) < 2: return

        # 4. POSICIONAMENTO VETORIAL
        bb = element.get_BoundingBox(view)
        center = (bb.Min + bb.Max) / 2.0
        width = bb.Max.X - bb.Min.X 
        
        # Distancia do centro até a borda esquerda = width / 2
        # Offset total = (width / 2) + 25cm
        dist_to_left = (width / 2.0) + (0.25 / 0.3048)
        
        # Ponto Base Z
        z_start = z_floor if z_floor else z_min - 1.0
        z_end = z_ceil if z_ceil else z_max + 1.0
        
        # Ponto no espaço 3D correspondente à linha vertical esquerda
        # Usamos o View.RightDirection NEGATIVO para ir para a esquerda
        pos_x_world = center + (view.RightDirection * -dist_to_left)
        
        # Ajusta Z
        p1 = XYZ(pos_x_world.X, pos_x_world.Y, z_start)
        p2 = XYZ(pos_x_world.X, pos_x_world.Y, z_end)
        
        line = Line.CreateBound(p1, p2)
        dim = dimensions.create_linear_dimension(doc, view, line, final_refs, dim_style_id)
        if dim: print("      > Cota Criada.")
        
    except Exception as e:
        print("      > Erro Cota: {}".format(e))

# --- ENGINE: TAGS ESQUADRIAS (VETORIAL) ---
def create_tags_vector(doc, view, elements, tag_opts):
    try:
        tasks = []
        for el in elements:
            bb = el.get_BoundingBox(view)
            if not bb: continue
            center = (bb.Min + bb.Max) / 2.0
            width = bb.Max.X - bb.Min.X
            tasks.append({'el': el, 'center': center, 'width': width, 'z': center.Z})
            
        tasks.sort(key=lambda x: x['z'])
        
        for t in tasks:
            # Posição: Centro + (Metade Largura) + 40cm para a DIREITA
            dist_right = (t['width'] / 2.0) + (0.40 / 0.3048)
            
            # Ponto de inserção da Tag (Head)
            head_pos = t['center'] + (view.RightDirection * dist_right)
            
            cat_id = t['el'].Category.Id.IntegerValue
            sym_id = tag_opts['door_style'] if cat_id == int(BuiltInCategory.OST_Doors) else tag_opts['win_style']
            
            tag = None
            if hasattr(IndependentTag, "Create"):
                tag = IndependentTag.Create(doc, view.Id, Reference(t['el']), True, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, head_pos)
            else:
                tag = doc.Create.NewTag(view, t['el'], True, TagMode.TM_ADDBY_CATEGORY, TagOrientation.Horizontal, head_pos)
            
            if tag:
                if sym_id: tag.ChangeTypeId(sym_id)
                tag.LeaderEndCondition = LeaderEndCondition.Free
                tag.TagHeadPosition = head_pos
                
                elbow = t['center'] + (view.RightDirection * (dist_right * 0.6))
                tag.SetLeaderElbow(Reference(t['el']), elbow)
        
        print("   [OK] Tags posicionadas via Vetor.")
    except Exception as e:
        print("   [ERRO] Tags: {}".format(e))

def annotate_view_logic(view, opts, view3d):
    print("\n>>> Vista: {}".format(view.Name))
    room = get_room_from_view(view)
    if not room: 
        print("   [ERRO] Room não encontrado.")
        return

    # 1. COTAS VÃO
    if opts['do_dim_v']:
        try:
            col = FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
            cats = List[BuiltInCategory]([BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows])
            elems = col.WherePasses(ElementMulticategoryFilter(cats)).ToElements()
            for el in elems:
                create_opening_chain(doc, view, el, room, view3d, opts['dim_style'])
        except: traceback.print_exc()

    # 2. COTA HORIZONTAL (Mantida lógica simples, se falhar migramos para vetorial)
    if opts['do_dim_h']:
        try:
            ref_l, ref_r = dimensions.get_room_boundary_references(doc, room, view.ViewDirection)
            if ref_l and ref_r:
                dim_y_view = view.CropBox.Min.Y + (1.20 / 0.3048)
                t_inv = view.CropBox.Transform.Inverse
                depth_z = t_inv.OfPoint(room.Location.Point).Z
                line = Line.CreateBound(
                    view.CropBox.Transform.OfPoint(XYZ(view.CropBox.Min.X+0.5, dim_y_view, depth_z)), 
                    view.CropBox.Transform.OfPoint(XYZ(view.CropBox.Max.X-0.5, dim_y_view, depth_z))
                )
                dimensions.create_linear_dimension(doc, view, line, [ref_l, ref_r], opts['dim_style'])
                print("   [OK] Cota Horizontal.")
        except: pass

    # 3. TAG ROOM
    if opts['do_room']:
        try:
            center_room = room.Location.Point
            t_inv = view.CropBox.Transform.Inverse
            pt_view = t_inv.OfPoint(center_room)
            uv = UV(pt_view.X, pt_view.Y + (0.5/0.3048))
            
            tag = doc.Create.NewRoomTag(LinkElementId(room.Id), uv, view.Id)
            if tag and opts['room_style']: tag.ChangeTypeId(opts['room_style'])
            print("   [OK] Tag Room.")
        except: pass

    # 4. TAGS ESQUADRIAS
    if opts['do_tags']:
        col = FilteredElementCollector(doc, view.Id).WhereElementIsNotElementType()
        cats = List[BuiltInCategory]([BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows])
        elems = col.WherePasses(ElementMulticategoryFilter(cats)).ToElements()
        
        tag_opts = {
            'door_style': opts['door_style'], 
            'win_style': opts['win_style']
        }
        create_tags_vector(doc, view, elems, tag_opts)

# --- UI CLASS ---
class DetailUI(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        self.dim_styles = get_dim_styles()
        self.cb_dim.ItemsSource = [get_rich_name(x) for x in self.dim_styles]
        if self.dim_styles: self.cb_dim.SelectedIndex = 0
        self.tag_rooms = get_tags(BuiltInCategory.OST_RoomTags)
        self.cb_room.ItemsSource = [get_rich_name(x) for x in self.tag_rooms]
        if self.tag_rooms: self.cb_room.SelectedIndex = 0
        self.tag_doors = get_tags(BuiltInCategory.OST_DoorTags)
        self.cb_door.ItemsSource = [get_rich_name(x) for x in self.tag_doors]
        if self.tag_doors: self.cb_door.SelectedIndex = 0
        self.tag_wins = get_tags(BuiltInCategory.OST_WindowTags)
        self.cb_win.ItemsSource = [get_rich_name(x) for x in self.tag_wins]
        if self.tag_wins: self.cb_win.SelectedIndex = 0

    def btn_run_click(self, sender, args):
        self.Close()
        target_views = []
        active_view = doc.ActiveView
        if active_view.ViewType == ViewType.Elevation: target_views = [active_view]
        else:
            all_elevs = get_all_elevations()
            if not all_elevs: return
            class ViewOption(object):
                def __init__(self, v): self.view = v; self.name = "{} (ID: {})".format(v.Name, v.Id)
                def __repr__(self): return self.name
            sel = forms.SelectFromList.show([ViewOption(v) for v in all_elevs], multiselect=True, button_name="Detalhar")
            if not sel: return
            target_views = [x.view for x in sel]
        def get_id(cb, lst): return lst[cb.SelectedIndex].Id if lst and cb.SelectedIndex >= 0 else None
        opts = {
            'do_room': self.chk_room.IsChecked,
            'room_style': get_id(self.cb_room, self.tag_rooms),
            'do_tags': self.chk_tags.IsChecked,
            'door_style': get_id(self.cb_door, self.tag_doors),
            'win_style': get_id(self.cb_win, self.tag_wins),
            'do_dim_h': self.chk_dim_h.IsChecked,
            'do_dim_v': self.chk_dim_v.IsChecked,
            'dim_style': get_id(self.cb_dim, self.dim_styles)
        }
        phase_id = None
        if target_views:
            p_param = target_views[0].get_Parameter(BuiltInParameter.VIEW_PHASE)
            if p_param: phase_id = p_param.AsElementId()
        v3d = get_compatible_3d_view(doc, phase_id)
        if v3d: print("Usando Vista 3D: {}".format(v3d.Name))
        with revit.Transaction("Detalhar Elevações"):
            for v in target_views: annotate_view_logic(v, opts, v3d)
        forms.toast("Concluído.")

DetailUI().ShowDialog()