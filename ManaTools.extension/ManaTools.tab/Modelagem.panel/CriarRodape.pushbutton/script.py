# -*- coding: utf-8 -*-
"""
Cria Rodapés (Line Based) em Ambientes.
ABORDAGEM GEOMÉTRICA: Calcula o perímetro e subtrai as portas matematicamente.
"""
import clr
import math
import os
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
logger = script.get_logger()

CMD_ID = "manatools_criarrodape_line"

# --- 1. SELEÇÃO ROBUSTA ---
def get_selected_rooms():
    selection = revit.get_selection()
    rooms = []
    seen_ids = set()

    def process(elem):
        r = None
        if not elem or not elem.Category: return
        cat_id = elem.Category.Id.IntegerValue
        if cat_id == int(BuiltInCategory.OST_Rooms): r = elem
        elif cat_id == int(BuiltInCategory.OST_RoomTags):
            if isinstance(elem, SpatialElementTag):
                if hasattr(elem, "Room") and elem.Room: r = elem.Room
                elif hasattr(elem, "GetTaggedLocalElement"): r = elem.GetTaggedLocalElement()
        if r and r.Id not in seen_ids:
            rooms.append(r)
            seen_ids.add(r.Id)

    for s in selection: process(s)
    if not rooms:
        try:
            with forms.WarningBar(title="Selecione Ambientes (ESC para sair):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes")
                for r in refs: process(doc.GetElement(r))
        except: pass
    return rooms

# --- 2. FILTRO DE FAMÍLIAS (LINE BASED) ---
def get_line_based_families():
    # Busca Generic Models que são baseados em curva
    symbols = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_GenericModel).ToElements()
    valid = []
    for s in symbols:
        try:
            # Verifica se é Line Based
            if s.Family.FamilyPlacementType == FamilyPlacementType.CurveDrivenStructural or \
               s.Family.FamilyPlacementType == FamilyPlacementType.CurveBased:
                valid.append(s)
        except: pass
    return valid

def get_name(e):
    try: return Element.Name.GetValue(e)
    except: return e.Name

# --- 3. MATH ENGINE: SUBTRAÇÃO DE PORTAS (COM BUSCA EM PAREDES UNIDAS) ---
def get_wall_segments_minus_doors(room):
    """
    Retorna uma lista de Curvas (Lines) onde o rodapé deve passar.
    Lógica: Pega o contorno -> Identifica Portas na parede (e unidas) -> Subtrai o vão.
    """
    final_curves = []
    
    # Opções de geometria
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish 
    
    segments_list = room.GetBoundarySegments(opt)
    if not segments_list: return []

    print("Processando Sala: {}".format(room.Number))

    for segments in segments_list:
        for seg in segments:
            curve = seg.GetCurve()
            p_start = curve.GetEndPoint(0)
            p_end = curve.GetEndPoint(1)
            
            p_start_2d = XYZ(p_start.X, p_start.Y, 0)
            p_end_2d = XYZ(p_end.X, p_end.Y, 0)
            line_vec = (p_end_2d - p_start_2d).Normalize()
            seg_length = p_start_2d.DistanceTo(p_end_2d)
            
            wall = doc.GetElement(seg.ElementId)
            cuts = []
            
            if isinstance(wall, Wall):
                # 1. Busca portas na parede hospedeira direta
                inserts_ids = list(wall.FindInserts(True, False, False, False))
                
                # 2. Busca portas em paredes unidas (Caso Parede Cebola)
                try:
                    joined_ids = JoinGeometryUtils.GetJoinedElements(doc, wall)
                    for j_id in joined_ids:
                        j_wall = doc.GetElement(j_id)
                        if isinstance(j_wall, Wall):
                            # Pega inserts da parede unida
                            j_inserts = j_wall.FindInserts(True, False, False, False)
                            for ji in j_inserts:
                                if ji not in inserts_ids:
                                    inserts_ids.append(ji)
                except: pass

                # Processa todas as portas encontradas
                for ins_id in inserts_ids:
                    door = doc.GetElement(ins_id)
                    # Filtra apenas Portas (ou janelas que tocam o chão se quiser expandir)
                    if door.Category.Id.IntegerValue != int(BuiltInCategory.OST_Doors): continue
                    
                    # Ponto da porta
                    pt_door = door.Location.Point
                    pt_door_2d = XYZ(pt_door.X, pt_door.Y, 0)
                    
                    # Projeção na linha do segmento
                    vec_to_door = pt_door_2d - p_start_2d
                    dot = vec_to_door.DotProduct(line_vec)
                    
                    # Verifica distância ortogonal (se a porta está longe da linha, ignora)
                    # Isso evita pegar portas da parede de trás que não pertencem a este lado
                    # Calculando a distância do ponto à linha
                    perp_dist = abs((p_end_2d.X - p_start_2d.X) * (p_start_2d.Y - pt_door_2d.Y) - (p_start_2d.X - pt_door_2d.X) * (p_end_2d.Y - p_start_2d.Y)) / seg_length
                    
                    # Se a porta está a mais de 50cm da linha do rodapé, provavelmente é do outro lado ou outra parede
                    if perp_dist > 1.64: # ~50cm (1.64ft)
                        continue

                    # Largura
                    width_param = door.get_Parameter(BuiltInParameter.DOOR_WIDTH)
                    if not width_param: width_param = door.Symbol.get_Parameter(BuiltInParameter.DOOR_WIDTH)
                    door_w = width_param.AsDouble() if width_param else 3.0 # Default ~90cm
                    
                    # Intervalo de corte
                    # Adiciona 2cm de folga de cada lado para acabamento
                    gap = 0.065 # ~2cm
                    door_start_dist = dot - (door_w / 2.0) + gap
                    door_end_dist = dot + (door_w / 2.0) - gap
                    
                    # Verifica intersecção
                    start_cut = max(0, door_start_dist)
                    end_cut = min(seg_length, door_end_dist)
                    
                    if start_cut < end_cut: 
                        cuts.append((start_cut, end_cut))
                        print(" > Porta detectada (corte: {:.2f}-{:.2f})".format(start_cut, end_cut))

            # Processa os cortes
            cuts.sort(key=lambda x: x[0])
            merged_cuts = []
            if cuts:
                curr_start, curr_end = cuts[0]
                for i in range(1, len(cuts)):
                    next_start, next_end = cuts[i]
                    if next_start < curr_end:
                        curr_end = max(curr_end, next_end)
                    else:
                        merged_cuts.append((curr_start, curr_end))
                        curr_start, curr_end = next_start, next_end
                merged_cuts.append((curr_start, curr_end))
            
            # Gera linhas
            current_dist = 0.0
            for cut_start, cut_end in merged_cuts:
                if cut_start - current_dist > 0.05:
                    p1 = p_start + (line_vec * current_dist)
                    p2 = p_start + (line_vec * cut_start)
                    final_curves.append(Line.CreateBound(p1, p2))
                current_dist = max(current_dist, cut_end)
                
            if seg_length - current_dist > 0.05:
                p1 = p_start + (line_vec * current_dist)
                p2 = p_start + (line_vec * seg_length)
                final_curves.append(Line.CreateBound(p1, p2))
                
    return final_curves

# --- 4. ENGINE: CRIAÇÃO ---
def create_skirting(doc, curve, symbol, level, offset, do_flip=False):
    try:
        # Generic Model Line Based requer NewFamilyInstance(Curve, Symbol, Level, StructuralType)
        
        # Projeta curva no plano do nível (Z=0 relativo ao nível)
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        
        # Cria a linha (Inverte se solicitado)
        if do_flip:
            new_curve = Line.CreateBound(XYZ(p1.X, p1.Y, 0), XYZ(p0.X, p0.Y, 0))
        else:
            new_curve = Line.CreateBound(XYZ(p0.X, p0.Y, 0), XYZ(p1.X, p1.Y, 0))
        
        inst = doc.Create.NewFamilyInstance(new_curve, symbol, level, Structure.StructuralType.NonStructural)
        
        # Tenta setar altura/elevação
        # Parametros comuns: "Elevação", "Offset", "Deslocamento", BuiltIn Elevation
        params_to_try = [
            BuiltInParameter.INSTANCE_ELEVATION_PARAM,
            BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM
        ]
        set_done = False
        for bp in params_to_try:
            p = inst.get_Parameter(bp)
            if p and not p.IsReadOnly:
                p.Set(offset)
                set_done = True
                break
        
        if not set_done:
            # Tenta por nome
            for pname in ["Elevação", "Offset", "Altura", "Deslocamento"]:
                p = inst.LookupParameter(pname)
                if p and not p.IsReadOnly:
                    p.Set(offset)
                    break
                    
        return inst
    except Exception as e:
        print("Erro ao criar instância: {}".format(e))
        return None

# --- GUI ---
rooms = get_selected_rooms()
if not rooms: script.exit()

# Busca famílias Line Based (como a Tabica)
all_families = sorted(get_line_based_families(), key=get_name)

if not all_families:
    forms.alert("Nenhuma Família Genérica Baseada em Linha encontrada.\n\nCarregue uma família de rodapé (Line Based) para usar este método.", exitscript=True)

class RodapeLineWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_sweep_type.ItemsSource = [get_name(t) for t in all_families]
        self.cb_sweep_type.SelectedIndex = 0
        
        # Config
        cfg = config_manager.get_config(CMD_ID)
        if getattr(cfg, "last_family", None):
            for i, name in enumerate(self.cb_sweep_type.ItemsSource):
                if name == cfg.last_family:
                    self.cb_sweep_type.SelectedIndex = i
                    break
        
        self.tb_offset.Text = getattr(cfg, "last_offset", "0")
        self.chk_invert_flip.IsChecked = getattr(cfg, "last_invert_flip", False)
        
        # Desabilita checkbox de corte pois agora é automático via geometria
        self.chk_force_cut.IsChecked = True
        self.chk_force_cut.IsEnabled = False
        self.chk_force_cut.Content = "Corte Automático (Geometria)"

    def button_create_clicked(self, sender, args):
        config_manager.save_config(CMD_ID, {
            "last_family": self.cb_sweep_type.SelectedItem,
            "last_offset": self.tb_offset.Text,
            "last_invert_flip": self.chk_invert_flip.IsChecked
        })
        self.Close()

win = RodapeLineWindow()
win.ShowDialog()

if not win.cb_sweep_type.SelectedItem: script.exit()

sel_name = win.cb_sweep_type.SelectedItem
family_symbol = next((f for f in all_families if get_name(f) == sel_name), None)
do_flip = win.chk_invert_flip.IsChecked

try:
    offset_ft = float(win.tb_offset.Text) / 30.48
except:
    forms.alert("Valor inválido.", exitscript=True)

# --- EXECUÇÃO ---
t = Transaction(doc, "Criar Rodapés (Geometria)")
t.Start()

try:
    if not family_symbol.IsActive: family_symbol.Activate()
    
    total_created = 0
    
    for room in rooms:
        # 1. Calcula linhas limpas (sem portas)
        curves = get_wall_segments_minus_doors(room)
        
        # 2. Cria instâncias
        for c in curves:
            if create_skirting(doc, c, family_symbol, room.Level, offset_ft, do_flip):
                total_created += 1
                
    t.Commit()
    forms.toast("Sucesso: {} segmentos de rodapé criados!".format(total_created))

except Exception as e:
    t.RollBack()
    forms.alert("Erro: {}".format(e))
