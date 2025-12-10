# -*- coding: utf-8 -*-
"""
Exporta PDFs com opção de arquivo único ou separados (Naming Convention Control).
"""
import os
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId
from pyrevit import forms, script
from manalib import text_utils, revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# --- CONFIGURAÇÃO ---
ENFORCE_REVISION = True 

# --- 1. Seleção de Escopo ---
all_sheets = revit_utils.get_all_sheets(doc)
if not all_sheets:
    forms.alert("Não há pranchas neste projeto.", exitscript=True)

selected_sheets = forms.SelectFromList.show(
    all_sheets,
    multiselect=True,
    name_attr='Name', 
    title='Selecione as Pranchas',
    button_name='Próximo'
)

if not selected_sheets:
    script.exit()

# --- 2. Filtro de QA/QC ---
valid_sheets = []
skipped_sheets = []

for sheet in selected_sheets:
    rev_ids = sheet.GetAllRevisionIds()
    has_revision = rev_ids and rev_ids.Count > 0
    if ENFORCE_REVISION and not has_revision:
        skipped_sheets.append(sheet)
    else:
        valid_sheets.append(sheet)

if skipped_sheets:
    msg = "QA/QC: {} pranchas sem revisão ignoradas.".format(len(skipped_sheets))
    if valid_sheets:
        res = forms.alert(msg, options=["Seguir com as Válidas", "Cancelar"])
        if res == "Cancelar": script.exit()
    else:
        forms.alert(msg, exitscript=True)

if not valid_sheets: script.exit()

# --- 3. Escolha do Modo de Exportação ---
export_mode = forms.CommandSwitchWindow.show(
    ["Arquivos Separados (Por Prancha)", "Arquivo Único (Combinado)"],
    message="Como deseja gerar os arquivos?",
)

if not export_mode: script.exit()

# --- 4. Configuração de Destino ---
dest_folder = forms.pick_folder(title="Salvar PDFs em...")
if not dest_folder: script.exit()

# --- 5. Execução ---
options = revit_utils.create_pdf_options(doc)

# === MODO COMBINADO ===
if export_mode == "Arquivo Único (Combinado)":
    # Pede o nome do arquivo final
    default_name = "JOGO_COMPLETO_{}".format(text_utils.sanitize_filename(doc.Title))
    combined_name = forms.ask_for_string(
        default=default_name,
        prompt="Nome do arquivo PDF (sem .pdf):",
        title="Exportação Combinada"
    )
    if not combined_name: script.exit()
    
    # Sanitiza o nome inserido pelo usuário
    final_name = text_utils.sanitize_filename(combined_name)
    
    try:
        options.Combine = True
        options.FileName = final_name  # Revit coloca .pdf sozinho
        
        # Prepara lista tipada .NET para exportação
        export_ids = List[ElementId]()
        for sheet in valid_sheets:
            export_ids.Add(sheet.Id)
        
        # Exporta a lista inteira de uma vez
        doc.Export(dest_folder, export_ids, options)
        
        forms.toast("Arquivo único gerado com sucesso!", click=dest_folder)
        
    except Exception as e:
        forms.alert("Erro na exportação combinada:\n{}".format(e))

# === MODO SEPARADO ===
else:
    with forms.ProgressBar(title='Exportando Separados...', cancellable=True) as pb:
        success_count = 0
        
        for count, sheet in enumerate(valid_sheets):
            if pb.cancelled: break
            
            try:
                # CRÍTICO: Cria um novo objeto options para cada exportação
                # Isso evita que o Revit mantenha estado interno que bloqueia exportações subsequentes
                sheet_options = revit_utils.create_pdf_options(doc)
                sheet_options.Combine = False  # Garante que não combine
                
                # Sanitização e Nomenclatura
                c_num = text_utils.sanitize_filename(sheet.SheetNumber)
                c_name = text_utils.sanitize_filename(sheet.Name)
                
                rev_ids = sheet.GetAllRevisionIds()
                if rev_ids and rev_ids.Count > 0:
                    last_rev_id = rev_ids[rev_ids.Count - 1]
                    rev_elem = doc.GetElement(last_rev_id)
                    rev_num = rev_elem.RevisionNumber
                    c_rev = "R" + text_utils.sanitize_filename(rev_num)
                else:
                    c_rev = "R00"

                # CORREÇÃO: Removemos o ".pdf" da string
                filename = "{}_{}_{}".format(c_num, c_name, c_rev)
                
                # Configura nome específico para esta iteração
                sheet_options.FileName = filename
                
                # Exporta 1 por 1 para garantir o nome exato
                export_ids = List[ElementId]()
                export_ids.Add(sheet.Id)
                doc.Export(dest_folder, export_ids, sheet_options)
                
                logger.info("Exportado: " + filename)
                success_count += 1
                
            except Exception as e:
                logger.error("Erro em {}: {}".format(sheet.SheetNumber, e))
                
            pb.update_progress(count + 1, len(valid_sheets))

    if success_count > 0:
        forms.toast(
            "{} arquivos gerados.".format(success_count),
            title="Exportação Concluída",
            click=dest_folder
        )
