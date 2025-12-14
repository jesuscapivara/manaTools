# -*- coding: utf-8 -*-
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
    return sorted(styles, key=lambda x: getattr(x, "Name", "Unnamed"))

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
    except Exception as e:
        print("Erro dimension: {}".format(e))
        return None

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

def get_room_boundary_references(doc, room, view_direction):
    """Retorna refs laterais (Esq/Dir) para cota horizontal."""
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    segments = room.GetBoundarySegments(opt)
    if not segments: return None, None
    
    vec_right = view_direction.CrossProduct(XYZ.BasisZ).Normalize()
    ref_left = None
    ref_right = None
    min_proj = float('inf')
    max_proj = float('-inf')
    center = room.Location.Point
    
    for seg_list in segments:
        for seg in seg_list:
            curve = seg.GetCurve()
            p0 = curve.GetEndPoint(0)
            p1 = curve.GetEndPoint(1)
            vec_wall = (p1 - p0).Normalize()
            if abs(vec_wall.DotProduct(view_direction)) > 0.8:
                mid = (p0 + p1) / 2.0
                proj = (mid - center).DotProduct(vec_right)
                if proj < min_proj:
                    min_proj = proj
                    elem = doc.GetElement(seg.ElementId)
                    if isinstance(elem, Wall): ref_left = Reference(elem)
                if proj > max_proj:
                    max_proj = proj
                    elem = doc.GetElement(seg.ElementId)
                    if isinstance(elem, Wall): ref_right = Reference(elem)
    return ref_left, ref_right