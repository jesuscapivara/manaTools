# -*- coding: utf-8 -*-
"""
Módulo de Cotagem V11.0 (Sill Hunter).
Compatibilidade: IronPython 2.7
"""
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from System.Collections.Generic import List

def get_dimension_styles(doc, linear_only=True):
    col = FilteredElementCollector(doc).OfClass(DimensionType)
    styles = []
    for d in col:
        if linear_only and d.StyleType != DimensionStyleType.Linear: continue
        styles.append(d)
    return sorted(styles, key=lambda x: x.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME).AsString() if x.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME) else x.Name)

def create_linear_dimension(doc, view, line, references, dim_style_id=None):
    if len(references) < 2: return None
    ref_array = ReferenceArray()
    for r in references: ref_array.Append(r)
    try:
        dim = doc.Create.NewDimension(view, line, ref_array)
        if dim_style_id:
            style = doc.GetElement(dim_style_id)
            if style: dim.DimensionType = style
        return dim
    except: return None

def raytrace_generic(view3d, origin, direction, categories_list):
    if not view3d: return None, None
    filters = List[ElementFilter]()
    for cat in categories_list: filters.Add(ElementCategoryFilter(cat))
    final_filter = LogicalOrFilter(filters)
    intersector = ReferenceIntersector(final_filter, FindReferenceTarget.Element, view3d)
    intersector.FindReferencesInRevitLinks = True 
    context = intersector.FindNearest(origin, direction)
    if context:
        return context.GetReference().GlobalPoint, context.GetReference()
    return None, None

def is_face_part_of_opening(face, element_bb):
    try:
        mesh = face.Triangulate()
        if not mesh: return False
        vertices = mesh.Vertices
        if vertices.Count == 0: return False
        sum_x = 0; sum_y = 0
        for v in vertices: sum_x += v.X; sum_y += v.Y
        cx = sum_x / vertices.Count
        cy = sum_y / vertices.Count
        margin = 0.30 
        if (cx > (element_bb.Min.X - margin)) and (cx < (element_bb.Max.X + margin)):
            if (cy > (element_bb.Min.Y - margin)) and (cy < (element_bb.Max.Y + margin)):
                return True
    except: pass
    return False

def get_hybrid_vertical_refs(doc, element, view):
    """
    Busca Híbrida: Tenta preencher Verga e Peitoril independentemente.
    Prioridade: Parede -> Elemento -> Nome.
    """
    res = {'head': None, 'h_z': float('-inf'), 'sill': None, 's_z': float('inf'), 'log': []}
    bb = element.get_BoundingBox(view)
    if not bb: return None, None, None, None, "Sem BBox"

    # 1. SCAN NA PAREDE (Melhor para Osso)
    host_wall = element.Host
    if host_wall:
        opt = Options()
        opt.ComputeReferences = True
        opt.DetailLevel = ViewDetailLevel.Fine
        opt.IncludeNonVisibleObjects = True
        wall_geom = host_wall.get_Geometry(opt)
        
        def scan_wall(geom, r):
            if not geom: return
            for g in geom:
                if isinstance(g, Solid) and g.Volume > 0:
                    for f in g.Faces:
                        if isinstance(f, PlanarFace):
                            # Só aceita faces planas horizontais
                            if abs(f.FaceNormal.X) < 0.01 and abs(f.FaceNormal.Y) < 0.01:
                                if is_face_part_of_opening(f, bb):
                                    z = f.Origin.Z
                                    # Verga (Z aponta pra baixo)
                                    if f.FaceNormal.Z < -0.9 and abs(z - bb.Max.Z) < 1.2:
                                        r['head'] = f.Reference; r['h_z'] = z
                                    # Peitoril (Z aponta pra cima)
                                    elif f.FaceNormal.Z > 0.9 and abs(z - bb.Min.Z) < 1.2:
                                        r['sill'] = f.Reference; r['s_z'] = z
                elif isinstance(g, GeometryInstance): scan_wall(g.GetInstanceGeometry(), r)
        
        scan_wall(wall_geom, res)
        if res['head']: res['log'].append("Wall-Head")
        if res['sill']: res['log'].append("Wall-Sill")

    # 2. SCAN NO ELEMENTO (Fallback se faltou algo)
    if not res['head'] or not res['sill']:
        opt = Options()
        opt.ComputeReferences = True
        opt.DetailLevel = ViewDetailLevel.Fine
        elem_geom = element.get_Geometry(opt)
        
        # Scans temporários para o elemento
        el_res = {'h': None, 'hz': float('-inf'), 's': None, 'sz': float('inf')}
        
        def scan_el(geom, r):
            if not geom: return
            for g in geom:
                if isinstance(g, Solid) and g.Volume > 0:
                    for f in g.Faces:
                        if isinstance(f, PlanarFace):
                            # Aceita inclinação (Pingadeira) -> Normal Z > 0.5 (45 graus)
                            nz = f.FaceNormal.Z
                            z = f.Origin.Z # Ponto na face
                            
                            # Para elemento, não checamos is_face_part_of_opening rigorosamente
                            # Apenas checamos se o Z faz sentido
                            
                            # Busca Topo (Face pra cima ou pra baixo no topo da janela?)
                            # Batente superior geralmente tem face pra baixo (Z < 0) ou pra cima (Z > 0)
                            # Vamos pegar o Z MÁXIMO da geometria
                            if z > r['hz']: 
                                r['hz'] = z; r['h'] = f.Reference
                            
                            # Busca Base (Z MÍNIMO da geometria)
                            # Face deve apontar pra CIMA (Peitoril)
                            if nz > 0.5 and z < r['sz']:
                                r['sz'] = z; r['s'] = f.Reference
                                
                elif isinstance(g, GeometryInstance): scan_el(g.GetInstanceGeometry(), r)
        
        scan_el(elem_geom, el_res)
        
        # Preenche o que falta
        if not res['head'] and el_res['h']:
            # Valida se está perto do topo do BBox (evita pegar maçaneta)
            if abs(el_res['hz'] - bb.Max.Z) < 1.0:
                res['head'] = el_res['h']; res['h_z'] = el_res['hz']
                res['log'].append("Elem-Head")
                
        if not res['sill'] and el_res['s']:
            # Valida se está perto da base
            if abs(el_res['sz'] - bb.Min.Z) < 1.0:
                res['sill'] = el_res['s']; res['s_z'] = el_res['sz']
                res['log'].append("Elem-Sill")

    # 3. NOMES (Último recurso)
    if not res['head']:
        for n in ["Top", "Head", "Topo", "Verga", "Superior"]:
            try:
                r = element.GetReferenceByName(n)
                if r: res['head'] = r; res['h_z'] = bb.Max.Z; res['log'].append("Name-Head"); break
            except: pass
            
    if not res['sill']:
        for n in ["Bottom", "Sill", "Base", "Peitoril", "Inferior"]:
            try:
                r = element.GetReferenceByName(n)
                if r: res['sill'] = r; res['s_z'] = bb.Min.Z; res['log'].append("Name-Sill"); break
            except: pass

    debug_str = "+".join(res['log']) if res['log'] else "Nenhum"
    return res['sill'], res['head'], res['s_z'], res['h_z'], debug_str

def get_room_boundary_references(doc, room, view_direction):
    # (Mantido igual)
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    segments = room.GetBoundarySegments(opt)
    if not segments: return None, None
    vec_right = view_direction.CrossProduct(XYZ.BasisZ).Normalize()
    ref_left, ref_right = None, None
    min_proj, max_proj = float('inf'), float('-inf')
    center = room.Location.Point
    for seg_list in segments:
        for seg in seg_list:
            curve = seg.GetCurve()
            p0 = curve.GetEndPoint(0)
            vec_wall = (curve.GetEndPoint(1) - p0).Normalize()
            if abs(vec_wall.DotProduct(view_direction)) > 0.8:
                mid = (p0 + curve.GetEndPoint(1)) / 2.0
                proj = (mid - center).DotProduct(vec_right)
                if proj < min_proj: min_proj = proj; ref_left = Reference(doc.GetElement(seg.ElementId))
                if proj > max_proj: max_proj = proj; ref_right = Reference(doc.GetElement(seg.ElementId))
    return ref_left, ref_right