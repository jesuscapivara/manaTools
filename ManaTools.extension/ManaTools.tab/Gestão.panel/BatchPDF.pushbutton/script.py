# -*- coding: utf-8 -*-
"""
Exporta PDFs de pranchas selecionadas com verificação de segurança (QA/QC).
"""
import os
from System.Collections.Generic import List
from Autodesk.Revit.DB import ElementId
from pyrevit import forms, script
from manalib import text_utils, revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# --- CONFIGURAÇÃO DE SEGURANÇA ---
# Trava a exportação se a prancha não tiver revisão.
# Para "furar" o bloqueio, mude para False temporariamente.
ENFORCE_REVISION = True 

# --- 1. Seleção de Escopo ---
all_sheets = revit_utils.get_all_sheets(doc)

if not all_sheets:
    forms.alert("Não há pranchas neste projeto.", exitscript=True)

# UI de Seleção
selected_sheets = forms.SelectFromList.show(
    all_sheets,
    multiselect=True,
    name_attr='Name', 
    title='Selecione as Pranchas (QA: {})'.format("ON" if ENFORCE_REVISION else "OFF"),
    button_name='Analisar e Exportar'
)

if not selected_sheets:
    script.exit()

# --- 2. Filtro de QA/QC (Architecture Check) ---
valid_sheets = []
skipped_sheets = []

for sheet in selected_sheets:
    # A API retorna uma lista de IDs de revisão. Se vazia, não tem revisão.
    has_revision = len(sheet.GetAllRevisionIds()) > 0
    
    if ENFORCE_REVISION and not has_revision:
        skipped_sheets.append(sheet)
    else:
        valid_sheets.append(sheet)

# Feedback de Bloqueio (UX)
if skipped_sheets:
    msg = "BLOQUEIO DE QA: {} pranchas sem revisão ignoradas:\n\n".format(len(skipped_sheets))
    msg += "\n".join(["- {} : {}".format(s.SheetNumber, s.Name) for s in skipped_sheets])
    
    # Dá opção de continuar apenas com as válidas
    if valid_sheets:
        res = forms.alert(msg, title="Controle de Qualidade Maná", warn_icon=True, 
                          options=["Seguir com as Válidas", "Cancelar Tudo"])
        if res == "Cancelar Tudo":
            script.exit()
    else:
        forms.alert(msg, title="Todas as pranchas foram rejeitadas", exitscript=True)

if not valid_sheets:
    script.exit()

# --- 3. Output ---
dest_folder = forms.pick_folder(title="Salvar PDFs aprovados em...")
if not dest_folder:
    script.exit()

# --- 4. Execução ---
options = revit_utils.create_pdf_options(doc)

with forms.ProgressBar(title='Processando...', cancellable=True) as pb:
    success_count = 0
    
    for count, sheet in enumerate(valid_sheets):
        if pb.cancelled: break
            
        try:
            # Lógica de Nomenclatura
            clean_num = text_utils.sanitize_filename(sheet.SheetNumber)
            clean_name = text_utils.sanitize_filename(sheet.Name)
            
            # Pega a última revisão real
            rev_ids = sheet.GetAllRevisionIds()
            # Verificação explícita de Count para listas .NET
            if rev_ids and rev_ids.Count > 0:
                # Usa índice positivo explícito (Count - 1) para evitar erro de IndexOutOfRange do .NET
                last_rev_id = rev_ids[rev_ids.Count - 1]
                last_rev_elem = doc.GetElement(last_rev_id)
                rev_number = last_rev_elem.RevisionNumber
                clean_rev = "R" + text_utils.sanitize_filename(rev_number)
            else:
                clean_rev = "R00" # Fallback apenas se ENFORCE_REVISION = False

            filename = "{}_{}_{}.pdf".format(clean_num, clean_name, clean_rev)
            
            # Exportação
            options.FileName = filename
            
            # Tipagem estrita para .NET (Revit 2025 Friendly)
            export_ids = List[ElementId]()
            export_ids.Add(sheet.Id)

            # O truque do Revit 2022+: Exportar uma lista de 1 item
            doc.Export(dest_folder, export_ids, options)
            
            logger.info("Exportado: " + filename)
            success_count += 1
            
        except Exception as e:
            logger.error("Falha em {}: {}".format(sheet.SheetNumber, e))
            
        pb.update_progress(count + 1, len(valid_sheets))

# --- 5. Relatório ---
if success_count > 0:
    forms.toast(
        "{} arquivos gerados.".format(success_count),
        title="ManaTools Export",
        click=dest_folder
    )
