# -*- coding: utf-8 -*-
"""
Maná SmartJoin V4.0
Interface intuitiva: Selecione Dominante -> Selecione Submisso.
"""
import os
import clr

clr.AddReference("RevitAPI")
from Autodesk.Revit.DB import *
from pyrevit import forms, script, revit

doc = __revit__.ActiveUIDocument.Document
uidoc = __revit__.ActiveUIDocument

# --- CONFIGURAÇÃO DE CATEGORIAS ---
# Mapeia Nome Amigável -> BuiltInCategory
CAT_MAP = {
    "Paredes": BuiltInCategory.OST_Walls,
    "Pisos (Lajes/Acab.)": BuiltInCategory.OST_Floors,
    "Pilares (Arq)": BuiltInCategory.OST_Columns,
    "Pilares (Est)": BuiltInCategory.OST_StructuralColumns,
    "Vigas (Framing)": BuiltInCategory.OST_StructuralFraming,
    "Forros": BuiltInCategory.OST_Ceilings,
    "Telhados": BuiltInCategory.OST_Roofs,
    "Fundações": BuiltInCategory.OST_StructuralFoundation,
    "Topografia": BuiltInCategory.OST_Topography
}

# --- ENGINE ---
def get_elements_of_categories(selected_names):
    """Coleta elementos de todas as categorias selecionadas na lista."""
    if not selected_names: return []
    
    cats_to_find = [CAT_MAP[name] for name in selected_names]
    
    # Cria filtro multicategoria
    filters = sorted([ElementCategoryFilter(c) for c in cats_to_find], key=lambda x: str(x))
    # Nota: No IronPython antigo, LogicalOrFilter precisa de IList, as vezes é chato.
    # Vamos fazer collector simples iterativo que é mais seguro
    
    final_list = []
    for c in cats_to_find:
        # Pega elementos da vista atual (mais rápido e seguro) ou do documento todo?
        # Para Join, geralmente queremos Vista Atual ou Seleção. Vamos usar Vista Atual por segurança.
        col = FilteredElementCollector(doc, doc.ActiveView.Id).OfCategory(c).WhereElementIsNotElementType().ToElements()
        final_list.extend(list(col))
        
    return final_list

def run_smart_join(primaries, secondaries, mode):
    count = 0
    
    # Otimização: Se a lista for a mesma (ex: Parede x Parede), remove duplicatas de processamento
    is_self_join = (primaries == secondaries)
    
    processed_pairs = set()

    with forms.ProgressBar(title='Processando Uniões ({0})...'.format(mode)) as pb:
        total = len(primaries)
        current = 0
        
        for p in primaries:
            current += 1
            if current % 2 == 0: pb.update_progress(current, total)
            
            p_bb = p.get_BoundingBox(None)
            if not p_bb: continue
            p_outline = Outline(p_bb.Min, p_bb.Max)
            
            # Filtra Secundários que colidem com o Primário
            # (Poderíamos usar ElementIntersectsElementFilter aqui, mas em loop python as vezes BBox check manual é rapido o suficiente para ~1000 objs)
            
            for s in secondaries:
                if p.Id == s.Id: continue # Não une consigo mesmo
                
                # Cache Check
                pair_key = frozenset([p.Id.IntegerValue, s.Id.IntegerValue])
                if pair_key in processed_pairs: continue
                
                # BBox Check Rápido
                s_bb = s.get_BoundingBox(None)
                if not s_bb: continue
                s_outline = Outline(s_bb.Min, s_bb.Max)
                
                if p_outline.Intersects(s_outline, 0):
                    # Candidato válido
                    processed_pairs.add(pair_key)
                    
                    try:
                        are_joined = JoinGeometryUtils.AreElementsJoined(doc, p, s)
                        
                        if mode == 'join':
                            if not are_joined:
                                JoinGeometryUtils.JoinGeometry(doc, p, s)
                                count += 1
                                # Tenta forçar a ordem? (Primeiro corta Segundo)
                                # O Revit nem sempre obedece na criação.
                                
                        elif mode == 'switch':
                            if are_joined:
                                # Aqui garantimos que o Primário CORTE o Secundário
                                # IsCuttingElementInJoin(doc, cutter, cut_element)
                                if not JoinGeometryUtils.IsCuttingElementInJoin(doc, p, s):
                                    JoinGeometryUtils.SwitchJoinOrder(doc, p, s)
                                    count += 1
                                    
                        elif mode == 'unjoin':
                            if are_joined:
                                JoinGeometryUtils.UnjoinGeometry(doc, p, s)
                                count += 1
                    except:
                        pass
    return count

# --- UI CLASS ---
class SmartJoinWindow(forms.WPFWindow):
    def __init__(self):
        xaml_path = os.path.join(os.path.dirname(__file__), 'script.xaml')
        forms.WPFWindow.__init__(self, xaml_path)
        
        # Popula Listas
        sorted_cats = sorted(CAT_MAP.keys())
        self.lb_primary.ItemsSource = sorted_cats
        self.lb_secondary.ItemsSource = sorted_cats
        
        # Seleção Padrão (Ex: Pisos na esq, Paredes na dir)
        self.lb_primary.SelectedItems.Add("Pisos (Lajes/Acab.)")
        self.lb_secondary.SelectedItems.Add("Paredes")

    def button_run_clicked(self, sender, args):
        self.Close()
        
        # Coleta Inputs
        sel_prim = list(self.lb_primary.SelectedItems)
        sel_sec = list(self.lb_secondary.SelectedItems)
        
        if not sel_prim or not sel_sec:
            forms.alert("Selecione pelo menos uma categoria em cada coluna!")
            return

        mode = "join"
        if self.rb_switch.IsChecked: mode = "switch"
        elif self.rb_unjoin.IsChecked: mode = "unjoin"
        
        # Coleta Elementos
        prim_elements = get_elements_of_categories(sel_prim)
        sec_elements = get_elements_of_categories(sel_sec)
        
        if not prim_elements or not sec_elements:
            forms.alert("Nenhum elemento encontrado na vista atual para as categorias selecionadas.")
            return

        # Executa
        with revit.Transaction("Maná SmartJoin"):
            cnt = run_smart_join(prim_elements, sec_elements, mode)
            
        action_name = {"join": "uniões", "switch": "inversões", "unjoin": "desuniões"}
        forms.toast("Concluído: {} {} realizadas.".format(cnt, action_name[mode]))

# --- RUN ---
SmartJoinWindow().ShowDialog()