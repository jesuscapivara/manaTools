# -*- coding: utf-8 -*-
"""Lógica de criação de Revestimentos (Paredes Cebola)."""
from System.Collections.Generic import List
from Autodesk.Revit.DB import (FilteredElementCollector, BuiltInCategory, BuiltInParameter,
                              Wall, WallType, Level, JoinGeometryUtils,
                              SpatialElementBoundaryOptions, SpatialElementBoundaryLocation,
                              CurveLoop, XYZ)


def get_wall_types(doc):
    """Retorna lista de Tipos de Parede disponíveis."""
    return FilteredElementCollector(doc)\
           .OfClass(WallType)\
           .WhereElementIsElementType()\
           .ToElements()


def get_levels(doc):
    """Retorna lista de Níveis ordenados por elevação."""
    levels = FilteredElementCollector(doc)\
             .OfClass(Level)\
             .WhereElementIsNotElementType()\
             .ToElements()
    return sorted(levels, key=lambda l: l.Elevation)


def create_finishes_in_room(doc, room, wall_type, base_level, top_level, height, offset_base_z=0.0):
    """
    Cria paredes offsetadas para dentro do perímetro de acabamento do ambiente.
    """
    created_walls = []
    
    # 1. Configurações de Fronteira
    opt = SpatialElementBoundaryOptions()
    # Usa a face de acabamento como referência
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    boundary_loops = room.GetBoundarySegments(opt)
    
    if not boundary_loops: 
        return []

    # --- CORREÇÃO DE SINAL ---
    # Se antes (width/2) foi para dentro da parede, agora invertemos para (-width/2).
    # Isso deve trazer a parede para dentro do ambiente.
    width = wall_type.Width
    offset_dist = -width / 2.0 
    
    normal = XYZ.BasisZ

    for loop_segments in boundary_loops:
        original_curve_loop = CurveLoop()
        host_map = [] 
        
        for seg in loop_segments:
            original_curve_loop.Append(seg.GetCurve())
            host_map.append(seg.ElementId)

        try:
            # 2. Gera o Loop Deslocado (Agora com sinal invertido)
            offset_loop = CurveLoop.CreateViaOffset(original_curve_loop, offset_dist, normal)
            
            for i, curve in enumerate(offset_loop):
                
                # 3. Criação da Parede
                new_wall = Wall.Create(
                    doc,
                    curve,
                    wall_type.Id,
                    base_level.Id,
                    height,
                    0.0, 
                    False, 
                    False
                )

                # 4. Ajustes de Parâmetros
                if offset_base_z != 0:
                    p_base = new_wall.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET)
                    if p_base: 
                        p_base.Set(offset_base_z)

                if top_level:
                    p_top = new_wall.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)
                    if p_top: 
                        p_top.Set(top_level.Id)
                    p_top_off = new_wall.get_Parameter(BuiltInParameter.WALL_TOP_OFFSET)
                    if p_top_off: 
                        p_top_off.Set(0.0)
                else:
                    p_h = new_wall.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM)
                    if p_h: 
                        p_h.Set(height)

                # Ajusta Location Line para "Face de Acabamento: Interna" (Visual)
                p_loc = new_wall.get_Parameter(BuiltInParameter.WALL_KEY_REF_PARAM)
                if p_loc: 
                    p_loc.Set(3)

                # 5. Flip (Inverter Sentido)
                # Geralmente necessário quando trazemos a parede para dentro, 
                # para que o acabamento fique virado para o ambiente.
                try:
                    new_wall.Flip()
                except: 
                    pass

                # 6. União Inteligente
                if i < len(host_map):
                    host_id = host_map[i]
                    if host_id.IntegerValue > 0:
                        host_wall = doc.GetElement(host_id)
                        if isinstance(host_wall, Wall):
                            try:
                                JoinGeometryUtils.JoinGeometry(doc, new_wall, host_wall)
                            except: 
                                pass
                
                created_walls.append(new_wall)

        except Exception as e:
            # Se der erro no CreateViaOffset (geometria inválida com negativo), avisamos
            print("Erro loop offset: {}".format(e))

    return created_walls
