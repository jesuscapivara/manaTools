# -*- coding: utf-8 -*-
"""
Cria Forros (Ceilings) e Tabicas (Line Based Families) em Ambientes selecionados.
Features: Auto-Flip de tabica, Offset negativo do forro, Tratamento de erros de geometria.
"""
import os
import math
import clr
clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from Autodesk.Revit.Exceptions import OperationCanceledException
from pyrevit import forms, script, revit
from manalib import config_manager

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
logger = script.get_logger()

CMD_ID = "manatools_criarforro"

# --- HELPER: SELEÇÃO ROBUSTA (Reutilizável) ---
def get_selected_rooms():
    selection = revit.get_selection()
    rooms = []
    seen_ids = set()

    def process(elem):
        r = None
        if not elem or not elem.Category: return
        cat_id = elem.Category.Id.IntegerValue
        
        if cat_id == int(BuiltInCategory.OST_Rooms):
            r = elem
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
            with forms.WarningBar(title="Selecione Ambientes ou Tags (ESC para cancelar):"):
                refs = uidoc.Selection.PickObjects(ObjectType.Element, "Selecione Ambientes")
                for r in refs: process(doc.GetElement(r))
        except OperationCanceledException:
            script.exit()
            
    return rooms

# --- HELPER: GEOMETRIA Z=0 ---
def flatten_loop_to_z(curve_loop, z_val=0.0):
    """Reconstrói um CurveLoop forçando todas as coordenadas Z para um valor fixo."""
    curves = []
    iterator = curve_loop
    
    if isinstance(curve_loop, CurveLoop):
        iterator = curve_loop
        
    for curve in iterator:
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        new_p0 = XYZ(p0.X, p0.Y, z_val)
        new_p1 = XYZ(p1.X, p1.Y, z_val)
        
        try:
            if isinstance(curve, Line):
                curves.append(Line.CreateBound(new_p0, new_p1))
            else:
                trans = XYZ(0, 0, z_val - p0.Z)
                curves.append(curve.CreateTransformed(Transform.CreateTranslation(trans)))
        except:
            pass 
            
    try:
        return CurveLoop.Create(curves)
    except:
        return None

# --- HELPER: DADOS DO PROJETO ---
def get_ceiling_types():
    return FilteredElementCollector(doc).OfClass(CeilingType).ToElements()

def get_line_based_families():
    symbols = FilteredElementCollector(doc).OfClass(FamilySymbol).OfCategory(BuiltInCategory.OST_GenericModel).ToElements()
    valid = []
    for s in symbols:
        try:
            if s.Family.FamilyPlacementType == FamilyPlacementType.CurveDrivenStructural or \
               s.Family.FamilyPlacementType == FamilyPlacementType.CurveBased:
                valid.append(s)
        except: pass
    return valid

def get_name(e):
    return Element.Name.GetValue(e)

# --- CORE LOGIC: TABICA (SIMPLIFICADO + VERTICAL FLIP) ---
def create_tabica_instance(doc, curve, symbol, level, force_invert_h=False, force_invert_z=False):
    """
    Cria a tabica e aplica inversões.
    force_invert_h: Inverte a linha (Horizontal Flip)
    force_invert_z: Espelha a geometria (Vertical Flip)
    """
    try:
        p0 = curve.GetEndPoint(0)
        p1 = curve.GetEndPoint(1)
        
        final_curve = curve
        
        # Inversão Horizontal (Linha)
        if force_invert_h:
            final_curve = Line.CreateBound(p1, p0)
            
        instance = doc.Create.NewFamilyInstance(final_curve, symbol, level, Structure.StructuralType.NonStructural)
        
        # Inversão Vertical (Mirror Z)
        # O Revit não tem Flip Vertical nativo para genéricos.
        # Usamos ElementTransformUtils.Mirror em torno de um plano horizontal.
        if force_invert_z and instance:
            doc.Regenerate()
            
            # Plano Horizontal passando pela linha (Z da linha)
            # Normal do plano = Z
            # Origem = qualquer ponto da linha (p0)
            # Mas p0 pode ser relativo ao nível 0 se viermos de flatten_loop.
            # O Mirror precisa ser no espaço 3D real.
            
            # Se a linha está em Z=0, e a instância no Nível, o plano deve ser no nível.
            # Porém, queremos flipar "em torno de si mesma". 
            # O eixo de espelhamento deve ser o plano XY local da instância.
            
            # Cria plano de espelho
            # Plane.CreateByNormalAndOrigin(XYZ.BasisZ, p0) requer XYZ, XYZ
            # Nota: p0 da curva flattened é Z=0. A instância está no nível.
            
            # Se espelharmos pelo plano Z=0, a tabica vai parar lá embaixo se o nível for alto.
            # Precisamos espelhar e manter a altura? 
            # O Mirror inverte a geometria mas também a posição Z se não for pelo centro.
            
            # ESTRATÉGIA SEGURA: Mirror e depois move de volta?
            # Ou Mirror pelo plano que passa pelo Location Point Z da instância?
            
            # Vamos tentar pegar o Z real da instância (após colocação)
            # Para LineBased, Location é LocationCurve.
            
            # Se espelharmos pelo plano horizontal que passa pelo nível da instância, ela fica de cabeça para baixo no mesmo nível.
            # Plane Z = Level Elevation?
            
            plane_z = level.Elevation
            mirror_plane = Plane.CreateByNormalAndOrigin(XYZ.BasisZ, XYZ(0,0, plane_z))
            
            # Mirror cria cópia e retorna IDs
            new_ids = ElementTransformUtils.MirrorElement(doc, instance.Id, mirror_plane)
            
            # Deleta original
            doc.Delete(instance.Id)
            
            # Retorna nova instância
            if new_ids:
                return doc.GetElement(new_ids[0])
            else:
                return None

        return instance
    except Exception as e:
        return None

# --- CORE LOGIC: FORRO ---
def create_ceiling_geometry(room, offset_dist):
    """Gera o CurveLoop do forro com offset negativo."""
    loops = []
    
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    
    segments_list = room.GetBoundarySegments(opt)
    
    if not segments_list: return None
    
    for segments in segments_list:
        curves = []
        for seg in segments:
            curves.append(seg.GetCurve())
            
        try:
            original_loop = flatten_loop_to_z(curves, 0.0)
            if not original_loop: continue
            
            if abs(offset_dist) > 0.001:
                try:
                    offset_loops = CurveLoop.CreateViaOffset(original_loop, -offset_dist, XYZ.BasisZ)
                    
                    if isinstance(offset_loops, CurveLoop):
                        loops.append(offset_loops)
                    else:
                        for ol in offset_loops:
                            loops.append(ol)
                except Exception as offset_err:
                    loops.append(original_loop)
            else:
                loops.append(original_loop)
                
        except Exception as e:
            pass
            
    return loops

def get_tabica_curves(room, offset_dist):
    """Retorna curvas para a tabica (com offset se necessário)."""
    tabica_curves = []
    
    opt = SpatialElementBoundaryOptions()
    opt.SpatialElementBoundaryLocation = SpatialElementBoundaryLocation.Finish
    segments_list = room.GetBoundarySegments(opt)
    
    if not segments_list: return []
    
    if abs(offset_dist) < 0.001:
        for segments in segments_list:
            for seg in segments:
                elem = doc.GetElement(seg.ElementId)
                if isinstance(elem, Wall):
                    c = seg.GetCurve()
                    p0 = c.GetEndPoint(0)
                    p1 = c.GetEndPoint(1)
                    line = Line.CreateBound(XYZ(p0.X, p0.Y, 0), XYZ(p1.X, p1.Y, 0))
                    tabica_curves.append(line)
        return tabica_curves

    for segments in segments_list:
        curves = []
        for seg in segments:
            curves.append(seg.GetCurve())
            
        original_loop = flatten_loop_to_z(curves, 0.0)
        if not original_loop: continue
        
        try:
            offset_loops = CurveLoop.CreateViaOffset(original_loop, -offset_dist, XYZ.BasisZ)
            
            loops_to_process = []
            if isinstance(offset_loops, CurveLoop):
                loops_to_process.append(offset_loops)
            else:
                for ol in offset_loops: loops_to_process.append(ol)
                
            for ol in loops_to_process:
                for c in ol:
                    tabica_curves.append(c)
        except:
            pass
            
    return tabica_curves

# --- GUI ---
rooms = get_selected_rooms()
if not rooms: script.exit()

all_ceilings = sorted(get_ceiling_types(), key=get_name)
all_tabicas = sorted(get_line_based_families(), key=get_name)

class ForroWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        self.cb_ceiling_type.ItemsSource = [get_name(c) for c in all_ceilings]
        
        tabica_names = ["(Nenhum)"] + [get_name(t) for t in all_tabicas]
        self.cb_tabica_type.ItemsSource = tabica_names
        
        # --- CARREGA CONFIGURAÇÕES ---
        cfg = config_manager.get_config(CMD_ID)
        
        self.cb_ceiling_type.SelectedIndex = 0
        self.cb_tabica_type.SelectedIndex = 0 
        
        if getattr(cfg, "last_ceiling_type", None):
            for i, name in enumerate(self.cb_ceiling_type.ItemsSource):
                if name == cfg.last_ceiling_type:
                    self.cb_ceiling_type.SelectedIndex = i
                    break
                    
        if getattr(cfg, "last_tabica_type", None):
            for i, name in enumerate(tabica_names):
                if name == cfg.last_tabica_type:
                    self.cb_tabica_type.SelectedIndex = i
                    break
        else:
            for i, name in enumerate(tabica_names):
                if "ARQPWR" in name and "Tabica" in name:
                    self.cb_tabica_type.SelectedIndex = i
                    break
        
        self.tb_height.Text = getattr(cfg, "last_height", "260")
        self.tb_gesso_gap.Text = getattr(cfg, "last_gesso_gap", "2.5")
        self.tb_tabica_gap.Text = getattr(cfg, "last_tabica_gap", "0")
        self.tb_tabica_z_offset.Text = getattr(cfg, "last_tabica_z_offset", "0")
        
        self.chk_create_tabica.IsChecked = getattr(cfg, "last_create_tabica", True)
        self.chk_invert_tabica.IsChecked = getattr(cfg, "last_invert_tabica", False)
        self.chk_invert_z_tabica.IsChecked = getattr(cfg, "last_invert_z_tabica", False)
        
        self.run_script = False

    def button_create_clicked(self, sender, args):
        config_manager.save_config(CMD_ID, {
            "last_ceiling_type": self.cb_ceiling_type.SelectedItem,
            "last_tabica_type": self.cb_tabica_type.SelectedItem,
            "last_height": self.tb_height.Text,
            "last_gesso_gap": self.tb_gesso_gap.Text,
            "last_tabica_gap": self.tb_tabica_gap.Text,
            "last_tabica_z_offset": self.tb_tabica_z_offset.Text,
            "last_create_tabica": self.chk_create_tabica.IsChecked,
            "last_invert_tabica": self.chk_invert_tabica.IsChecked,
            "last_invert_z_tabica": self.chk_invert_z_tabica.IsChecked
        })
        
        self.run_script = True
        self.Close()

win = ForroWindow()
win.ShowDialog()

if not win.run_script: script.exit()
if not win.cb_ceiling_type.SelectedItem: script.exit()

sel_ceil_name = win.cb_ceiling_type.SelectedItem
ceil_type = next((x for x in all_ceilings if get_name(x) == sel_ceil_name), None)

sel_tab_name = win.cb_tabica_type.SelectedItem
tab_symbol = None

if sel_tab_name == "(Nenhum)":
    do_tabica = False
    gesso_gap_ft = 0.0 
    tabica_gap_ft = 0.0
    tabica_z_offset_ft = 0.0
    do_invert_h = False
    do_invert_z = False
else:
    tab_symbol = next((x for x in all_tabicas if get_name(x) == sel_tab_name), None)
    do_tabica = win.chk_create_tabica.IsChecked
    do_invert_h = win.chk_invert_tabica.IsChecked
    do_invert_z = win.chk_invert_z_tabica.IsChecked
    
    try:
        gesso_cm = float(win.tb_gesso_gap.Text)
        gesso_gap_ft = gesso_cm / 30.48
        
        tabica_gap_cm = float(win.tb_tabica_gap.Text)
        tabica_gap_ft = tabica_gap_cm / 30.48
        
        z_offset_cm = float(win.tb_tabica_z_offset.Text)
        tabica_z_offset_ft = z_offset_cm / 30.48
    except:
        forms.alert("Valores da tabica inválidos.", exitscript=True)

try:
    h_cm = float(win.tb_height.Text)
    height_ft = h_cm / 30.48
except:
    forms.alert("Altura inválida.", exitscript=True)

t = Transaction(doc, "Criar Forro e Tabica")
t.Start()

count_forros = 0
count_tabicas = 0

try:
    if do_tabica and tab_symbol and not tab_symbol.IsActive:
        tab_symbol.Activate()
        doc.Regenerate()

    for room in rooms:
        level_id = room.LevelId
        
        loops = create_ceiling_geometry(room, gesso_gap_ft)
        
        if loops:
            try:
                valid_loops = []
                for l in loops:
                    if isinstance(l, CurveLoop):
                        if not l.IsOpen():
                            valid_loops.append(l)
                
                if valid_loops:
                    c = Ceiling.Create(doc, valid_loops, ceil_type.Id, level_id)
                    p_off = c.get_Parameter(BuiltInParameter.CEILING_HEIGHTABOVELEVEL_PARAM)
                    if p_off: p_off.Set(height_ft)
                    count_forros += 1

            except Exception as ce:
                pass

        if do_tabica and tab_symbol:
            # Não precisamos mais do centro da sala para a lógica simplificada
            curves_to_draw = get_tabica_curves(room, tabica_gap_ft)
            
            for curve in curves_to_draw:
                # Passa os inverters
                inst = create_tabica_instance(
                    doc, curve, tab_symbol, room.Level, 
                    force_invert_h=do_invert_h,
                    force_invert_z=do_invert_z
                )
                
                if inst:
                    # Ajuste de Altura (Z)
                    # Nota: Se foi espelhado em Z pelo nível, a altura pode ter ficado correta (mesmo Z)
                    # ou invertida (se o plano de espelho não for o centro).
                    # Como usamos o nível como plano, o Z é mantido (z -> -z relativo ao plano 0? não, z=0 é fixo)
                    # Mirror pelo plano Z=h espelha z -> z. 
                    # Mirror pelo plano Z=0 espelha h -> -h.
                    
                    # No código usamos plane_z = level.Elevation.
                    # Se a tabica é criada no nível (offset 0), o mirror pelo plano do nível mantém ela no nível,
                    # apenas invertendo a geometria em Z.
                    
                    # Então aplicamos o offset DEPOIS do mirror.
                    
                    p_elev = inst.get_Parameter(BuiltInParameter.INSTANCE_ELEVATION_PARAM)
                    if not p_elev or p_elev.IsReadOnly:
                        p_elev = inst.get_Parameter(BuiltInParameter.INSTANCE_FREE_HOST_OFFSET_PARAM)
                    
                    final_z = height_ft + tabica_z_offset_ft
                    
                    if p_elev: 
                        p_elev.Set(final_z)
                    else:
                        p_custom = inst.LookupParameter("Elevação") or inst.LookupParameter("Offset") or inst.LookupParameter("Altura")
                        if p_custom: p_custom.Set(final_z)
                    
                    count_tabicas += 1

    t.Commit()
    msg = "Sucesso: {} Forros".format(count_forros)
    if do_tabica: msg += " | {} Tabicas".format(count_tabicas)
    forms.toast(msg)

except Exception as e:
    t.RollBack()
    forms.alert("Erro Crítico: {}".format(e))
