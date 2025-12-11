# -*- coding: utf-8 -*-
"""
Ferramenta de União Geométrica em Lote (Bulk Join).
Permite unir Paredes x Pisos, Paredes x Pilares, etc., em massa.
"""
import os
import clr
from System.Collections.Generic import List

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from Autodesk.Revit.UI.Selection import ObjectType
from pyrevit import forms, script, revit
from manalib import config_manager, auth

# --- SECURITY CHECK ---
if not auth.check_access()[0]:
    forms.alert("ACESSO NEGADO: " + auth.check_access()[1] + "\n\nPor favor, faça Login na aba 'Gestão'.", exitscript=True)

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument
CMD_ID = "manatools_unirelementos"

# --- HELPERS ---
def get_elements_by_scope(scope_view, category_builtins):
    """
    Retorna elementos baseados no escopo (Seleção ou Vista) e Categorias.
    """
    elements = []
    
    # Filtro de Categoria
    cats = [int(c) for c in category_builtins]
    
    if scope_view:
        # Escopo: Vista Atual
        collector = FilteredElementCollector(doc, doc.ActiveView.Id).WhereElementIsNotElementType()
        # Filtragem manual de categoria para suportar lista de categorias
        for e in collector:
            if e.Category and e.Category.Id.IntegerValue in cats:
                elements.append(e)
    else:
        # Escopo: Seleção
        selection = revit.get_selection()
        for e in selection:
            if e.Category and e.Category.Id.IntegerValue in cats:
                elements.append(e)
                
    return elements

def join_elements_matrix(list_a, list_b, switch_order=False):
    """
    Tenta unir cada elemento da lista A com elementos da lista B que interceptam o BoundingBox.
    """
    count = 0
    
    # Barra de Progresso porque isso pode demorar (O(N*M))
    total_ops = len(list_a)
    
    with forms.ProgressBar(title="Processando Uniões... ({value}/{max_value})", cancellable=True) as pb:
        for i, elem_a in enumerate(list_a):
            if pb.cancelled: break
            pb.update_progress(i, total_ops)
            
            bb_a = elem_a.get_BoundingBox(None)
            if not bb_a: continue
            
            # Outline para filtro rápido
            outline = Outline(bb_a.Min, bb_a.Max)
            
            # Filtra BBox na lista B (Otimização)
            # Para scripts pesados, usar FilteredElementCollector com BoundingBoxIntersectsFilter seria melhor,
            # mas aqui já temos a lista B em memória. Vamos iterar e checar BBox.
            
            for elem_b in list_b:
                # Não unir consigo mesmo
                if elem_a.Id == elem_b.Id: continue
                
                # Check rápido de BBox
                bb_b = elem_b.get_BoundingBox(None)
                if not bb_b: continue
                
                # Intersecção simples de caixas
                if (bb_a.Min.X <= bb_b.Max.X and bb_a.Max.X >= bb_b.Min.X and
                    bb_a.Min.Y <= bb_b.Max.Y and bb_a.Max.Y >= bb_b.Min.Y and
                    bb_a.Min.Z <= bb_b.Max.Z and bb_a.Max.Z >= bb_b.Min.Z):
                    
                    try:
                        # Verifica se já estão unidos
                        if not JoinGeometryUtils.AreElementsJoined(doc, elem_a, elem_b):
                            JoinGeometryUtils.JoinGeometry(doc, elem_a, elem_b)
                            count += 1
                            
                            if switch_order:
                                JoinGeometryUtils.SwitchJoinOrder(doc, elem_a, elem_b)
                        else:
                            # Se já unidos e pediu pra inverter
                            if switch_order:
                                # Verifica quem corta quem
                                if JoinGeometryUtils.IsCuttingElementInJoin(doc, elem_b, elem_a):
                                    # Se B corta A, mas queremos inverter (depende da definição de switch)
                                    # SwitchJoinOrder apenas troca.
                                    JoinGeometryUtils.SwitchJoinOrder(doc, elem_a, elem_b)
                                    count += 1
                    except:
                        pass
                        
    return count

def join_all_in_list(elements):
    """
    Une tudo contra tudo numa única lista (Modo Seleção Livre).
    """
    count = 0
    with forms.ProgressBar(title="Unindo Seleção... ({value}/{max_value})") as pb:
        for i in range(len(elements)):
            pb.update_progress(i, len(elements))
            for j in range(i + 1, len(elements)):
                e1 = elements[i]
                e2 = elements[j]
                
                try:
                    if not JoinGeometryUtils.AreElementsJoined(doc, e1, e2):
                        # BBox Check rápido
                        bb1 = e1.get_BoundingBox(None)
                        bb2 = e2.get_BoundingBox(None)
                        if bb1 and bb2:
                             if (bb1.Min.X <= bb2.Max.X and bb1.Max.X >= bb2.Min.X and
                                 bb1.Min.Y <= bb2.Max.Y and bb1.Max.Y >= bb2.Min.Y and
                                 bb1.Min.Z <= bb2.Max.Z and bb1.Max.Z >= bb2.Min.Z):
                                    JoinGeometryUtils.JoinGeometry(doc, e1, e2)
                                    count += 1
                except: pass
    return count

# --- GUI ---
class JoinWindow(forms.WPFWindow):
    def __init__(self):
        xaml_file = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_file)
        
        # Config Recovery
        cfg = config_manager.get_config(CMD_ID)
        self.chk_switch_order.IsChecked = getattr(cfg, "switch_order", False)
        
        # Defaults
        # (Não salvamos o modo de operação pois varia muito)

    def button_run_clicked(self, sender, args):
        config_manager.save_config(CMD_ID, {
            "switch_order": self.chk_switch_order.IsChecked
        })
        self.Close()

win = JoinWindow()
win.ShowDialog()

# --- PARÂMETROS ---
scope_view = win.rb_scope_view.IsChecked
switch_order = win.chk_switch_order.IsChecked

mode = None
if win.rb_walls_floors.IsChecked: mode = "WF"
elif win.rb_walls_columns.IsChecked: mode = "WC"
elif win.rb_walls_framing.IsChecked: mode = "WV"
elif win.rb_walls_walls.IsChecked: mode = "WW"
elif win.rb_selection_all.IsChecked: mode = "ALL"

if not mode: script.exit()

# --- EXECUÇÃO ---
t = Transaction(doc, "Unir Elementos")
t.Start()

try:
    joined_count = 0
    
    if mode == "WF": # Parede x Piso
        walls = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Walls])
        floors = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Floors])
        if not walls or not floors:
            forms.alert("Elementos insuficientes encontrados.")
            script.exit()
        joined_count = join_elements_matrix(walls, floors, switch_order)
        
    elif mode == "WC": # Parede x Pilar
        walls = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Walls])
        cols = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Columns, BuiltInCategory.OST_StructuralColumns])
        if not walls or not cols:
            forms.alert("Elementos insuficientes encontrados.")
            script.exit()
        joined_count = join_elements_matrix(walls, cols, switch_order)
        
    elif mode == "WV": # Parede x Viga
        walls = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Walls])
        framing = get_elements_by_scope(scope_view, [BuiltInCategory.OST_StructuralFraming])
        if not walls or not framing:
            forms.alert("Elementos insuficientes encontrados.")
            script.exit()
        joined_count = join_elements_matrix(walls, framing, switch_order)
        
    elif mode == "WW": # Parede x Parede
        walls = get_elements_by_scope(scope_view, [BuiltInCategory.OST_Walls])
        if len(walls) < 2:
            forms.alert("Menos de 2 paredes encontradas.")
            script.exit()
        # Usa a lógica de lista única
        joined_count = join_all_in_list(walls)
        
    elif mode == "ALL": # Tudo x Tudo (Seleção)
        # Pega toda a seleção
        selection = revit.get_selection()
        elements = [e for e in selection] # Converte para lista Python
        if len(elements) < 2:
            forms.alert("Selecione pelo menos 2 elementos.")
            script.exit()
        joined_count = join_all_in_list(elements)

    t.Commit()
    forms.toast("Concluído: {} uniões processadas.".format(joined_count))

except Exception as e:
    t.RollBack()
    forms.alert("Erro: {}".format(e))
