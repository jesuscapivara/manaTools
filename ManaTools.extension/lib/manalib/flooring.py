# -*- coding: utf-8 -*-
"""
Lógica de criação de Pisos com Geometria Sólida (CSG).
Agora suporta seleção explícita de Ambientes e Portas.
"""
from System.Collections.Generic import List
from Autodesk.Revit.DB import (FilteredElementCollector, BuiltInCategory, BuiltInParameter,
                              Floor, FloorType, Level, CurveLoop, GeometryCreationUtilities,
                              BooleanOperationsUtils, BooleanOperationsType,
                              SpatialElementBoundaryOptions, SpatialElementBoundaryLocation,
                              XYZ, UV, Line, Solid, PlanarFace, SpatialElementGeometryCalculator,
                              Wall, LocationCurve)

def get_floor_types(doc):
    """Retorna lista de Tipos de Piso disponíveis."""
    return FilteredElementCollector(doc)\
           .OfClass(FloorType)\
           .WhereElementIsElementType()\
           .ToElements()

def get_room_solid(doc, room):
    """
    Usa SpatialElementGeometryCalculator para extrair o sólido exato da sala.
    """
    options = SpatialElementBoundaryOptions()
    options.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    try:
        calc = SpatialElementGeometryCalculator(doc, options)
        results = calc.CalculateSpatialElementGeometry(room)
        room_solid = results.GetGeometry() 
        return room_solid
    except Exception as e:
        print("Aviso: Falha no GeometryCalculator para sala {}: {}".format(room.Id, e))
        return None

def create_door_bridge_solid(doc, door, height=1.0, overlap_width=0.16):
    """
    Cria um sólido (caixa) para a porta selecionada.
    Usa o EIXO da parede para centralizar a geometria e evitar deslocamentos.
    
    Args:
        overlap_width (float): Valor em pés para expandir a largura da soleira para dentro das salas.
    """
    wall = door.Host
    if not wall: return None
    
    # 1. Dados Geométricos da Parede
    wall_thickness = wall.Width
    wall_loc = wall.Location
    
    if not isinstance(wall_loc, LocationCurve):
        return None
        
    wall_curve = wall_loc.Curve
    
    # 2. Dados da Porta
    # Largura (Prioriza parâmetro de instância, depois tipo)
    width = 0.80
    p_w = door.get_Parameter(BuiltInParameter.DOOR_WIDTH)
    if p_w and p_w.HasValue:
        width = p_w.AsDouble()
    else:
        type_elem = doc.GetElement(door.GetTypeId())
        if type_elem:
            p_w_type = type_elem.get_Parameter(BuiltInParameter.DOOR_WIDTH)
            if p_w_type and p_w_type.HasValue:
                width = p_w_type.AsDouble()

    # 3. Ponto Central Real (No Eixo da Parede)
    door_pt = door.Location.Point
    # Projeta o ponto da porta na linha da parede para garantir centralização na espessura
    proj_result = wall_curve.Project(door_pt)
    center_pt = proj_result.XYZPoint
    # Força Z=0
    center_pt = XYZ(center_pt.X, center_pt.Y, 0.0)
    
    # 4. Vetores Direcionais (Baseados na Curva da Parede)
    # Tangente da parede no ponto (Direção da Largura/Hand)
    param = proj_result.Parameter
    tangent = wall_curve.ComputeDerivatives(param, False).BasisX.Normalize()
    tangent = XYZ(tangent.X, tangent.Y, 0.0).Normalize()
    
    # Normal da parede (Direção da Espessura/Facing)
    # Rotaciona tangente 90 graus em Z
    normal = XYZ(-tangent.Y, tangent.X, 0.0).Normalize()
    
    # 5. Dimensões com Overlap Dinâmico
    # Sem overlap na espessura (para respeitar face da parede)
    overlap_thick = 0.00 
    
    half_w = (width / 2.0) + overlap_width
    half_thk = (wall_thickness / 2.0) + overlap_thick
    
    # 6. Vértices do Retângulo
    v_width = tangent * half_w
    v_thick = normal * half_thk
    
    p1 = center_pt - v_width - v_thick
    p2 = center_pt + v_width - v_thick
    p3 = center_pt + v_width + v_thick
    p4 = center_pt - v_width + v_thick
    
    try:
        cl = CurveLoop()
        cl.Append(Line.CreateBound(p1, p2))
        cl.Append(Line.CreateBound(p2, p3))
        cl.Append(Line.CreateBound(p3, p4))
        cl.Append(Line.CreateBound(p4, p1))
        
        bridge_solid = GeometryCreationUtilities.CreateExtrusionGeometry(
            List[CurveLoop]([cl]), XYZ.BasisZ, height
        )
        return bridge_solid
    except:
        return None

def unify_solids(solids_list):
    """
    Tenta unir uma lista de sólidos.
    Retorna lista de sólidos resultantes (ilhas).
    """
    if not solids_list: return []
    
    pool = list(solids_list)
    results = []
    
    while pool:
        base = pool.pop(0)
        merged_any = True
        while merged_any:
            merged_any = False
            i = 0
            while i < len(pool):
                candidate = pool[i]
                try:
                    union = BooleanOperationsUtils.ExecuteBooleanOperation(
                        base, candidate, BooleanOperationsType.Union
                    )
                    if union and union.Volume > 0:
                        base = union
                        pool.pop(i)
                        merged_any = True
                    else:
                        i += 1
                except:
                    i += 1
        results.append(base)
            
    return results

def generate_floor_from_solid(doc, solid, floor_type, level, offset):
    """Extrai face inferior e cria piso."""
    bottom_face = None
    min_z = float('inf')
    
    for face in solid.Faces:
        try:
            if isinstance(face, PlanarFace):
                normal = face.FaceNormal
                if normal.IsAlmostEqualTo(XYZ(0,0,-1)) or normal.Z < -0.9:
                    z_origin = face.Origin.Z
                    if z_origin < min_z:
                        min_z = z_origin
                        bottom_face = face
        except: pass
            
    if not bottom_face: return None
    
    loops = bottom_face.GetEdgesAsCurveLoops()
    
    try:
        f = Floor.Create(doc, loops, floor_type.Id, level.Id)
        p = f.get_Parameter(BuiltInParameter.FLOOR_HEIGHTABOVELEVEL_PARAM)
        if p: p.Set(offset)
        return f
    except Exception as e:
        print("Erro Floor.Create: {}".format(e))
        return None

def create_floors(doc, selection_list, floor_type, level, offset_z, door_overlap=0.16, merge_all=False):
    """
    Cria pisos baseados na seleção explícita de Ambientes e Portas.
    Args:
        door_overlap (float): Avanço do piso da porta para dentro das salas (em pés).
    """
    created_floors = []
    
    # 1. Separação por Categoria
    rooms = []
    doors = []
    
    for elem in selection_list:
        if not elem: continue
        cat_id = elem.Category.Id.IntegerValue
        if cat_id == int(BuiltInCategory.OST_Rooms):
            rooms.append(elem)
        elif cat_id == int(BuiltInCategory.OST_Doors):
            doors.append(elem)
            
    if not rooms: return []

    # 2. Gera Sólidos
    solids = []
    
    # Sólidos de Sala
    for r in rooms:
        s = get_room_solid(doc, r)
        if s and s.Volume > 0: solids.append(s)
        
    # Sólidos de Porta (Só das selecionadas!)
    for d in doors:
        # Altura arbitrária 5.0 para garantir interseção
        # Passamos o overlap configurado
        s = create_door_bridge_solid(doc, d, height=5.0, overlap_width=door_overlap) 
        if s and s.Volume > 0: solids.append(s)
        
    if not solids: return []

    # 3. Processamento
    if merge_all:
        # Une tudo que foi selecionado num bolo só
        final_solids = unify_solids(solids)
        for sol in final_solids:
            f = generate_floor_from_solid(doc, sol, floor_type, level, offset_z)
            if f: created_floors.append(f)
            
    else:
        # Modo Individual: Cria pisos isolados para cada sólido gerado
        for s in solids:
            f = generate_floor_from_solid(doc, s, floor_type, level, offset_z)
            if f: created_floors.append(f)

    return created_floors
