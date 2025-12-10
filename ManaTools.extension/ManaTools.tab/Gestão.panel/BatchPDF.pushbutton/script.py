# -*- coding: utf-8 -*-
"""
Exporta PDFs com bypass de regras de nomenclatura do Revit.
Usa 'Combine=True' mesmo para arquivos únicos para forçar o nome correto.
"""
import re
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId, BuiltInParameter
from pyrevit import forms, script
from manalib import revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# --- HELPER: BUSCA DE DADOS ---
def get_true_sheet_number(sheet):
    """Recupera o número real da prancha, ignorando 'Folha'."""
    candidates = []
    
    # 1. BuiltInParameter (Fonte da Verdade)
    try:
        p_bip = sheet.get_Parameter(BuiltInParameter.SHEET_NUMBER)
        if p_bip and p_bip.HasValue:
            val = p_bip.AsString()
            if val and val != "Folha": return val
    except: pass

    # 2. Wrapper Python
    try:
        val = sheet.SheetNumber
        if val and val != "Folha": return val
    except: pass

    # 3. Varredura (Último recurso)
    for p in sheet.Parameters:
        try:
            if not p.HasValue: continue
            val = p.AsString()
            if not val or val == "Folha": continue
            name = p.Definition.Name.lower()
            if ("umero" in name or "umber" in name) and len(val) < 15:
                candidates.append(val)
        except: continue
    
    if candidates:
        for c in candidates:  # Prioriza alphanuméricos (A101) sobre textos
            if any(char.isdigit() for char in c): return c
        return candidates[0]

    return "ERRO_NUM"

# --- HELPER UI ---
class SheetListItem(object):
    def __init__(self, sheet):
        self.sheet = sheet
        self.num = get_true_sheet_number(sheet)
        self.name = sheet.Name or "Sem Nome"
        self.display = "{} - {}".format(self.num, self.name)
    def __repr__(self): return self.display

def safe_filename(text):
    if not text: return ""
    return re.sub(r'[<>:"/\\|?*]', '', text).strip()

# --- 1. Seleção ---
all_sheets = revit_utils.get_all_sheets(doc)
if not all_sheets: forms.alert("Não há pranchas.", exitscript=True)

sheet_options = [SheetListItem(s) for s in all_sheets]
selected_wrappers = forms.SelectFromList.show(sheet_options, multiselect=True, title='Selecione as Pranchas', button_name='Exportar')
if not selected_wrappers: script.exit()
selected_sheets = [w.sheet for w in selected_wrappers]

# --- 2. Filtro Revisão ---
ENFORCE_REVISION = True
valid_sheets = []
for sheet in selected_sheets:
    has_rev = sheet.GetAllRevisionIds() and sheet.GetAllRevisionIds().Count > 0
    if not ENFORCE_REVISION or has_rev: valid_sheets.append(sheet)

if not valid_sheets: forms.alert("Nenhuma prancha válida.", exitscript=True)

# --- 3. Configuração ---
export_mode = forms.CommandSwitchWindow.show(["Arquivos Separados", "Arquivo Único"], message="Formato:")
if not export_mode: script.exit()

dest_folder = forms.pick_folder(title="Salvar em...")
if not dest_folder: script.exit()

# --- 4. Execução ---
with forms.ProgressBar(title='Exportando...', cancellable=True) as pb:
    if export_mode == "Arquivo Único":
        try:
            options = revit_utils.create_pdf_options(doc)
            options.Combine = True  # Modo Jogo Completo
            
            safe_title = safe_filename(doc.Title)
            name = forms.ask_for_string(default=safe_title, prompt="Nome:", title="PDF Combinado")
            if name:
                options.FileName = safe_filename(name)
                ids = List[ElementId]([s.Id for s in valid_sheets])
                doc.Export(dest_folder, ids, options)
                forms.toast("Arquivo único gerado!", click=dest_folder)
        except Exception as e: forms.alert(str(e))

    else:
        # MODO SEPARADO (HACKEADO)
        count_success = 0
        for i, sheet in enumerate(valid_sheets):
            if pb.cancelled: break
            try:
                # Monta o nome perfeito
                c_num = safe_filename(get_true_sheet_number(sheet))
                c_name = safe_filename(sheet.Name)
                if c_num in ["ERRO_NUM", "Folha"]: c_num = "ID_" + str(sheet.Id)

                filename = "{}-{}".format(c_num, c_name)
                
                # O PULO DO GATO:
                options = revit_utils.create_pdf_options(doc)
                # Enganamos o Revit dizendo que é um COMBINADO de 1 página só.
                # Isso força ele a usar o FileName exato e ignorar regras de "Folha-Tipo".
                options.Combine = True 
                options.FileName = filename
                
                ids = List[ElementId]()
                ids.Add(sheet.Id)
                doc.Export(dest_folder, ids, options)
                
                count_success += 1
                print("Gerado: " + filename)  # Debug
                
            except Exception as e: logger.error("Erro {}: {}".format(sheet.Id, e))
            pb.update_progress(i+1, len(valid_sheets))
            
        if count_success > 0:
            forms.toast("{} arquivos gerados.".format(count_success), click=dest_folder)
