# -*- coding: utf-8 -*-
"""
Cria revestimentos (cebola) em Ambientes.
V2.3: Seleção Robusta + Detecção Automática do Nível da Vista + Clean Logs.
"""
import os
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

# --- 1. FILTRO DE SELEÇÃO ---
class RoomOnlyFilter(ISelectionFilter):
    def AllowElement(self, elem):
        if not elem.Category: return False
        cid = elem.Category.Id.IntegerValue
        if cid == int(BuiltInCategory.OST_Rooms): return True
        if cid == int(BuiltInCategory.OST_RoomTags): return True
        return False
    def AllowReference(self, reference, position): return False

# --- 2. SELEÇÃO INTERATIVA ---
def get_user_selection():
    rooms = []
    seen_ids = set()
    
    # Verifica pré-seleção
    pre_selection = uidoc.Selection.GetElementIds()
    if pre_selection:
        filter_instance = RoomOnlyFilter()
        for eid in pre_selection:
            elem = doc.GetElement(eid)
            if filter_instance.AllowElement(elem):
                r = resolve_room(elem)
                if r and r.Id not in seen_ids:
                    rooms.append(r)
                    seen_ids.add(r.Id)
        if rooms: return rooms

    # Pede nova seleção
    try:
        with forms.WarningBar(title="Clique nos Ambientes para Revestir (ESC para concluir):"):
            refs = uidoc.Selection.PickObjects(ObjectType.Element, RoomOnlyFilter(), "Selecione Ambientes")
            for r in refs:
                elem = doc.GetElement(r)
                room = resolve_room(elem)
                if room and room.Id not in seen_ids:
                    rooms.append(room)
                    seen_ids.add(room.Id)
    except OperationCanceledException: pass
    return rooms

def resolve_room(elem):
    cid = elem.Category.Id.IntegerValue
    if cid == int(BuiltInCategory.OST_Rooms): return elem
    elif cid == int(BuiltInCategory.OST_RoomTags):
        if isinstance(elem, SpatialElementTag):
            if elem.Room: return elem.Room
            elif hasattr(elem, "GetTaggedLocalElement"): return elem.GetTaggedLocalElement()
    return None

# --- ENGINE V2.3: CRIAÇÃO SEGURA (SILENT) ---
def create_finish_walls_v2(room, wall_type, base_level, top_level, height_val, offset_val, do_join):
    created_walls = []
    
    # Opções de Limite
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    try: segments_list = room.GetBoundarySegments(opt)
    except: return []
        
    if not segments_list: return []
    
    base_level_id = base_level.Id
    
    for segments in segments_list:
        for seg in segments:
            host_wall = doc.GetElement(seg.ElementId)
            
            # Só processa se o hospedeiro for Parede e não for Cortina
            if not isinstance(host_wall, Wall): continue
            if host_wall.WallType.Kind == WallKind.Curtain: continue

            curve = seg.GetCurve()
            
            try:
                # ESTRATÉGIA SEGURA: Sempre criar Desconectado primeiro
                safe_h = height_val if height_val > 0.1 else 10.0
                
                new_wall = Wall.Create(doc, curve, wall_type.Id, base_level_id, safe_h, offset_val, False, False)
                
                # Pós-Processamento de Parâmetros
                # 1. Location Line -> Face Externa (2)
                p_loc = new_wall.get_Parameter(BuiltInParameter.WALL_KEY_REF_PARAM)
                if p_loc: p_loc.Set(2) 
                
                # 2. Base Offset
                p_base_off = new_wall.get_Parameter(BuiltInParameter.WALL_BASE_OFFSET)
                if p_base_off: p_base_off.Set(offset_val)
                
                # 3. Top Constraint (Se houver nível de topo)
                if top_level:
                    p_top_constr = new_wall.get_Parameter(BuiltInParameter.WALL_HEIGHT_TYPE)
                    if p_top_constr: p_top_constr.Set(top_level.Id)
                    
                    p_top_off = new_wall.get_Parameter(BuiltInParameter.WALL_TOP_OFFSET)
                    if p_top_off: p_top_off.Set(0.0)
                
                # 4. Room Bounding False
                p_room_bound = new_wall.get_Parameter(BuiltInParameter.WALL_ATTR_ROOM_BOUNDING)
                if p_room_bound: p_room_bound.Set(0)
                
                created_walls.append(new_wall)
                
                # 5. Join Geometry
                if do_join:
                    try: JoinGeometryUtils.JoinGeometry(doc, new_wall, host_wall)
                    except: pass
                        
            except:
                # Silenciosamente ignora falhas de geometria
                pass

    return created_walls

# --- PREP DADOS ---
all_wall_types = FilteredElementCollector(doc).OfClass(WallType).ToElements()
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
        
        self.run_script = False
        
        self.cb_wall_type.ItemsSource = dict_walls.keys()
        self.cb_base_level.ItemsSource = dict_levels.keys()
        
        top_opts = list(dict_levels.keys())
        top_opts.insert(0, "(Desconectado)")
        self.cb_top_level.ItemsSource = top_opts
        
        cfg = config_manager.get_config(CMD_ID)
        
        # --- LÓGICA DE SELEÇÃO DE PAREDE (Config ou Default) ---
        self.cb_wall_type.SelectedIndex = 0
        if getattr(cfg, "last_wall", None) in dict_walls:
            self.cb_wall_type.SelectedItem = cfg.last_wall
            
        # --- LÓGICA INTELIGENTE DE NÍVEL (FIX) ---
        # 1. Tenta pegar o nível da Vista Atual
        active_view = doc.ActiveView
        active_level = getattr(active_view, "GenLevel", None)
        
        target_base_level_name = None
        
        if active_level and active_level.Name in dict_levels:
            # Prioridade 1: Nível da Vista
            target_base_level_name = active_level.Name
        elif getattr(cfg, "last_base_level", None) in dict_levels:
            # Prioridade 2: Última configuração salva
            target_base_level_name = cfg.last_base_level
        else:
            # Prioridade 3: Primeiro da lista
            if dict_levels:
                target_base_level_name = list(dict_levels.keys())[0]
                
        if target_base_level_name:
            self.cb_base_level.SelectedItem = target_base_level_name
        
        # --- Nível Topo ---
        self.cb_top_level.SelectedIndex = 0 
        if getattr(cfg, "last_top", None) in top_opts:
            self.cb_top_level.SelectedItem = cfg.last_top
            
        self.tb_base_offset.Text = getattr(cfg, "last_offset", "0")
        self.tb_height.Text = getattr(cfg, "last_height", "280")
        self.chk_join.IsChecked = getattr(cfg, "do_join", True)

    def button_create_clicked(self, sender, args):
        self.run_script = True
        config_manager.save_config(CMD_ID, {
            "last_wall": self.cb_wall_type.SelectedItem,
            "last_base_level": self.cb_base_level.SelectedItem, # Salva para fallback futuro
            "last_top": self.cb_top_level.SelectedItem,
            "last_offset": self.tb_base_offset.Text,
            "last_height": self.tb_height.Text,
            "do_join": self.chk_join.IsChecked
        })
        self.Close()

win = RevestWindow()
win.ShowDialog()

if not win.run_script: script.exit()

rooms = get_user_selection()
if not rooms: script.exit()

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
t = Transaction(doc, "Criar Revestimentos")
t.Start()

try:
    total_walls = 0
    for room in rooms:
        walls = create_finish_walls_v2(room, sel_wall, sel_base, sel_top, val_height, val_offset, do_join)
        total_walls += len(walls)
        
    t.Commit()
    
    if total_walls > 0:
        msg = "Sucesso: {} paredes criadas.".format(total_walls)
        if do_join: msg += "\n(Com recorte automático de vãos)"
        forms.toast(msg)
    else:
        # Mensagem amigável sem logs técnicos
        forms.alert("Nenhuma parede foi criada.\nPossíveis causas:\n1. O ambiente não possui paredes válidas (apenas linhas separadoras).\n2. As paredes do ambiente são Cortinas ou muito complexas.\n3. Segmentos muito curtos.")
    
except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))