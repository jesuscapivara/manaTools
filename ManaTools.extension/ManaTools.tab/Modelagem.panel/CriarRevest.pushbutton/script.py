# -*- coding: utf-8 -*-
"""
Cria revestimentos (cebola) em Ambientes.
V2.0: Inclui lógica de Auto-Join para recortar vãos de portas e janelas.
"""
import os
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import forms, script, revit
from manalib import finishes, config_manager # Mantemos para utilitários se necessário

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_criarrevest"

# --- HELPER: NOME SEGURO ---
def get_name_safe(element):
    if not element: return ""
    try:
        p = element.get_Parameter(BuiltInParameter.ALL_MODEL_TYPE_NAME)
        if p and p.HasValue: return p.AsString()
    except: pass
    try: return Element.Name.GetValue(element)
    except: return "Elemento <{}>".format(element.Id)

# --- HELPER: SELEÇÃO ---
def get_selected_rooms():
    selection = revit.get_selection()
    rooms = []
    seen = set()
    
    def add(r):
        if r and r.Id not in seen:
            rooms.append(r)
            seen.add(r.Id)

    for elem in selection:
        if not elem.Category: continue
        if elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms):
            add(elem)
        elif elem.Category.Id.IntegerValue == int(BuiltInCategory.OST_RoomTags):
            if isinstance(elem, SpatialElementTag):
                if hasattr(elem, "Room"): add(elem.Room)
                elif hasattr(elem, "GetTaggedLocalElement"): add(elem.GetTaggedLocalElement())
            
    if not rooms:
        try:
            with forms.WarningBar(title="Selecione Ambientes (ESC para sair):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes")
                for r in refs: 
                    e = doc.GetElement(r)
                    if e.Category.Id.IntegerValue == int(BuiltInCategory.OST_Rooms): add(e)
                    elif e.Category.Id.IntegerValue == int(BuiltInCategory.OST_RoomTags): 
                        if e.Room: add(e.Room)
        except: pass
    return rooms

# --- ENGINE V2: CRIAÇÃO COM AUTO-JOIN ---
def create_finish_walls_v2(room, wall_type, base_level, top_level, height_val, offset_val, do_join):
    """
    Cria paredes de revestimento e une com a parede hospedeira.
    """
    created_walls = []
    
    # Opções de Limite
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    try:
        segments_list = room.GetBoundarySegments(opt)
    except:
        print("Erro ao ler limites da sala {}".format(room.Number))
        return []
    
    if not segments_list: return []
    
    # Determina Nível Base ID
    base_level_id = base_level.Id
    
    # Itera segmentos
    for segments in segments_list:
        
        # --- ETAPA 1: CALCULAR CURVAS OFFSETADAS ---
        raw_offset_curves = []
        host_map = [] # Salva o host para usar depois

        valid_loop = True
        
        for seg in segments:
            # Obtém Host
            host_wall = doc.GetElement(seg.ElementId)
            
            # Só cria revestimento se tiver uma parede atrás
            if not isinstance(host_wall, Wall): continue
            
            # Se a parede hospedeira for Parede Cortina ou Stacked muito complexa, cuidado
            if host_wall.WallType.Kind == WallKind.Curtain: continue

            # Geometria da curva
            curve = seg.GetCurve()
            
            try:
                # --- CÁLCULO DE POSICIONAMENTO ---
                wall_w = wall_type.Width
                
                # 1. Determina vetor "Para Dentro da Sala"
                t = curve.GetEndPoint(1) - curve.GetEndPoint(0)
                t_norm = t.Normalize()
                normal_right = XYZ(t_norm.Y, -t_norm.X, 0)
                mid_pt = (curve.GetEndPoint(0) + curve.GetEndPoint(1)) / 2.0
                test_pt = mid_pt + (normal_right * 0.1) # 10cm para direita
                
                is_room_right = room.IsPointInRoom(test_pt)
                
                # Lógica de Offset e Flip
                if is_room_right:
                    offset_dist = wall_w / 2.0
                    do_flip_wall = False
                else:
                    offset_dist = -(wall_w / 2.0)
                    do_flip_wall = True

                # 2. Cria Curva Offsetada
                try:
                    new_curve = curve.CreateOffset(offset_dist, XYZ.BasisZ)
                except:
                    vec = normal_right * offset_dist 
                    transform = Transform.CreateTranslation(vec)
                    new_curve = curve.CreateTransformed(transform)
                
                # Armazena dados para etapa de trim
                raw_offset_curves.append({
                    "curve": new_curve,
                    "host": host_wall,
                    "flip": do_flip_wall
                })

            except Exception as e:
                # Se falhar offset, ignora segmento
                pass
        
        # Se o loop resultou em curvas vazias (ex: sala sem paredes válidas), pula
        if not raw_offset_curves: continue

        # --- ETAPA 2: TRIM DOS CANTOS (INTERSECÇÃO) ---
        # Tenta calcular intersecção entre i e i+1 para fechar o loop
        # Se falhar (linhas paralelas ou colineares), mantem original.
        
        final_curves_data = []
        n = len(raw_offset_curves)
        
        # Se for só 1 parede (sala aberta?), não tem trim.
        if n < 2:
            final_curves_data = raw_offset_curves
        else:
            # Calcula vértices de interseção
            vertices = []
            
            for i in range(n):
                c1_data = raw_offset_curves[i]
                c2_data = raw_offset_curves[(i + 1) % n] # Próximo (cíclico)
                
                c1 = c1_data["curve"]
                c2 = c2_data["curve"]
                
                # Intersecção matemática 2D (assumindo linhas retas na maioria)
                # Fallback para GetEndPoint se não for linha ou falhar
                
                intersection_pt = None
                
                if isinstance(c1, Line) and isinstance(c2, Line):
                    # Algoritmo Line-Line Intersection Infinite
                    p1 = c1.GetEndPoint(0)
                    v1 = c1.Direction
                    p2 = c2.GetEndPoint(0)
                    v2 = c2.Direction
                    
                    # p1 + v1*t1 = p2 + v2*t2
                    # (v1.x  -v2.x) * (t1) = (p2.x - p1.x)
                    # (v1.y  -v2.y) * (t2)   (p2.y - p1.y)
                    
                    det = v1.X * v2.Y - v1.Y * v2.X
                    
                    if abs(det) > 0.0001: # Não paralelas
                        dx = p2.X - p1.X
                        dy = p2.Y - p1.Y
                        # t1 = (dx * v2.y - dy * v2.x) / (v1.x * v2.y - v1.y * v2.x) (Cramer) -> Nao, wait.
                        # Cramer's Rule for:
                        # t1 * v1.x - t2 * v2.x = p2.x - p1.x
                        # t1 * v1.y - t2 * v2.y = p2.y - p1.y
                        
                        det_sys = v1.X * (-v2.Y) - v1.Y * (-v2.X) # v1x*-v2y - v1y*-v2x = -v1x*v2y + v1y*v2x = -(det)
                        
                        # Vamos usar IntersectionResultArray do Revit que é mais seguro para Z
                        # Mas precisamos de curvas unbound.
                        # Hack: Criar linhas gigantes
                        try:
                            l1_big = Line.CreateBound(p1 - v1*1000, p1 + v1*1000)
                            l2_big = Line.CreateBound(p2 - v2*1000, p2 + v2*1000)
                            
                            results = clr.Reference[IntersectionResultArray]()
                            result = l1_big.Intersect(l2_big, results)
                            
                            if result == SetComparisonResult.Overlap:
                                intersection_pt = results.Value[0].XYZPoint
                        except: pass
                
                if not intersection_pt:
                    # Fallback: média dos pontos (vai ficar fresta ou sobreposição, mas não crasha)
                    intersection_pt = (c1.GetEndPoint(1) + c2.GetEndPoint(0)) / 2.0
                
                vertices.append(intersection_pt)
            
            # Reconstrói as curvas com os novos vértices
            for i in range(n):
                start_pt = vertices[(i - 1) % n] # Vértice anterior é o início desta
                end_pt = vertices[i]             # Vértice atual é o fim desta
                
                # Se os pontos forem muito próximos, ignora (parede nula)
                if start_pt.DistanceTo(end_pt) < 0.01: continue
                
                orig_data = raw_offset_curves[i]
                orig_curve = orig_data["curve"]
                
                # Recria geometria
                if isinstance(orig_curve, Line):
                    new_c = Line.CreateBound(start_pt, end_pt)
                else:
                    # Arcos: Mantemos original pois trim de arco é complexo sem mudar raio
                    # Idealmente deveria ajustar, mas por segurança mantemos o offset simples para arcos
                    new_c = orig_curve
                
                final_curves_data.append({
                    "curve": new_c,
                    "host": orig_data["host"],
                    "flip": orig_data["flip"]
                })

        # --- ETAPA 3: CRIAÇÃO FÍSICA ---
        for data in final_curves_data:
            try:
                new_curve = data["curve"]
                host_wall = data["host"]
                do_flip_wall = data["flip"]

                # ESTRATÉGIA SEGURA: Sempre criar por Altura desconectada primeiro.
                safe_height = height_val if height_val > 0.1 else 10.0
                
                new_wall = Wall.Create(doc, new_curve, wall_type.Id, base_level_id, safe_height, offset_val, do_flip_wall, False)
                
                # 4. Ajuste de Location Line -> Face Externa (2)
                p_loc = new_wall.get_Parameter(BuiltInParameter.WALL_KEY_REF_PARAM)
                if p_loc: p_loc.Set(2) # 2 = Finish Face: Exterior
                
                # 5. Ajuste de Restrições (Top Level)
                if top_level:
                    p_top_constr = new_wall.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)
                    if p_top_constr: p_top_constr.Set(top_level.Id)
                    p_top_off = new_wall.get_Parameter(BuiltInParameter.WALL_TOP_OFFSET)
                    if p_top_off: p_top_off.Set(0.0)
                
                # 3. Ajuste de Base Offset
                p_base_off = new_wall.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET)
                if p_base_off: p_base_off.Set(offset_val)
                
                # 4. Desativa Room Bounding
                p_room_bound = new_wall.get_Parameter(BuiltInParameter.WALL_ATTR_ROOM_BOUNDING)
                if p_room_bound: p_room_bound.Set(0)
                
                created_walls.append(new_wall)
                
                # --- O PULO DO GATO: JOIN GEOMETRY ---
                if do_join:
                    try:
                        JoinGeometryUtils.JoinGeometry(doc, new_wall, host_wall)
                    except: pass
                        
            except Exception as e:
                # print("Erro na criacao: {}".format(e))
                pass
                
    return created_walls

# --- PREP DADOS ---
rooms = get_selected_rooms()
if not rooms: script.exit()

all_wall_types = FilteredElementCollector(doc).OfClass(WallType).ToElements()
# Filtra apenas paredes básicas para limpar a lista
basic_walls = [w for w in all_wall_types if w.Kind == WallKind.Basic]
sorted_walls = sorted(basic_walls, key=get_name_safe)

all_levels = sorted(FilteredElementCollector(doc).OfClass(Level).ToElements(), key=lambda l: l.Elevation)

dict_walls = {get_name_safe(w): w for w in sorted_walls}
dict_levels = {l.Name: l for l in all_levels}

# --- GUI ---
class RevestWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_wall_type.ItemsSource = dict_walls.keys()
        self.cb_base_level.ItemsSource = dict_levels.keys()
        
        top_opts = list(dict_levels.keys())
        top_opts.insert(0, "(Desconectado)")
        self.cb_top_level.ItemsSource = top_opts
        
        # Config Recovery
        cfg = config_manager.get_config(CMD_ID)
        
        self.cb_wall_type.SelectedIndex = 0
        if getattr(cfg, "last_wall", None) in dict_walls:
            self.cb_wall_type.SelectedItem = cfg.last_wall
            
        self.cb_base_level.SelectedIndex = 0
        
        # Tenta achar o nível das salas selecionadas para ser o default
        if rooms:
            first_lvl_id = rooms[0].LevelId
            first_lvl = doc.GetElement(first_lvl_id)
            if first_lvl.Name in dict_levels:
                self.cb_base_level.SelectedItem = first_lvl.Name
        
        self.cb_top_level.SelectedIndex = 0 
        if getattr(cfg, "last_top", None) in top_opts:
            self.cb_top_level.SelectedItem = cfg.last_top
            
        self.tb_base_offset.Text = getattr(cfg, "last_offset", "0")
        self.tb_height.Text = getattr(cfg, "last_height", "280")
        self.chk_join.IsChecked = getattr(cfg, "do_join", True)

    def button_create_clicked(self, sender, args):
        config_manager.save_config(CMD_ID, {
            "last_wall": self.cb_wall_type.SelectedItem,
            "last_top": self.cb_top_level.SelectedItem,
            "last_offset": self.tb_base_offset.Text,
            "last_height": self.tb_height.Text,
            "do_join": self.chk_join.IsChecked
        })
        self.Close()

win = RevestWindow()
win.ShowDialog()

if not win.cb_wall_type.SelectedItem: script.exit()

sel_wall = dict_walls[win.cb_wall_type.SelectedItem]
sel_base = dict_levels[win.cb_base_level.SelectedItem]
sel_top_name = win.cb_top_level.SelectedItem
sel_top = dict_levels[sel_top_name] if sel_top_name != "(Desconectado)" else None
do_join = win.chk_join.IsChecked

try:
    h_cm = float(win.tb_height.Text)
    off_cm = float(win.tb_base_offset.Text)
    val_height = h_cm / 30.48
    val_offset = off_cm / 30.48
except:
    forms.alert("Valores inválidos.", exitscript=True)

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Revestimentos V2")
t.Start()

try:
    total_walls = 0
    for room in rooms:
        walls = create_finish_walls_v2(room, sel_wall, sel_base, sel_top, val_height, val_offset, do_join)
        total_walls += len(walls)
        
    t.Commit()
    
    msg = "Sucesso: {} paredes criadas.".format(total_walls)
    if do_join: msg += "\n(Com recorte automático de vãos)"
    forms.toast(msg)
    
except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))