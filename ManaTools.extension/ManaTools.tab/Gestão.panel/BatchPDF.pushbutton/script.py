# -*- coding: utf-8 -*-
"""
Exporta PDFs de pranchas selecionadas com nomenclatura sanitizada.
Nomenclatura: NUMERO_NOME_REVISAO.pdf
"""
import os
from pyrevit import forms, script, revit
from manalib import text_utils, revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# --- 1. Seleção de Escopo ---
all_sheets = revit_utils.get_all_sheets(doc)

# Prompt de seleção (Multi-select nativo do pyRevit)
selected_sheets = forms.SelectFromList.show(
    all_sheets,
    multiselect=True,
    name_attr='Name',  # O que aparece na lista (pode concatenar Numero + Nome)
    title='Selecione as Pranchas para Exportar',
    button_name='Exportar PDFs'
)

if not selected_sheets:
    script.exit()

# --- 2. Definição de Output ---
# Pede pasta de destino
dest_folder = forms.pick_folder(title="Onde salvar os PDFs?")

if not dest_folder:
    script.exit()

# --- 3. Execução (Batch) ---
# Usamos TransactionGroup para agrupar operações se houver modificação no modelo
# (Embora exportar seja 'read-only', o Revit às vezes pede transação para configurações temporárias)
options = revit_utils.create_pdf_options(doc)

# Barra de progresso visual
with forms.ProgressBar(title='Gerando PDFs... ({value}/{max_value})', cancellable=True) as pb:
    
    success_count = 0
    
    # Inicia transação de exportação (Revit 2022+ method)
    # Nota: Exportação nativa muitas vezes não exige transação aberta, 
    # mas é boa prática ter controle de erro.
    
    for count, sheet in enumerate(selected_sheets):
        if pb.cancelled:
            break
            
        try:
            # A. Construção do Nome
            clean_num = text_utils.sanitize_filename(sheet.SheetNumber)
            clean_name = text_utils.sanitize_filename(sheet.Name)
            revision = sheet.GetCurrentRevision()  # Pega ID da revisão atual
            clean_rev = "R" + str(len(sheet.GetAllRevisionIds())) if revision else "R0"
            
            filename = "{}_{}_{}.pdf".format(clean_num, clean_name, clean_rev)
            full_path = os.path.join(dest_folder, filename)
            
            # B. Configuração Específica
            options.FileName = filename
            # O truque do Revit 2022: Exportar uma lista de 1 item
            # Isso evita que o Revit combine tudo num PDF único (se não configurado)
            
            # C. Exportação
            doc.Export(dest_folder, [sheet.Id], options)
            
            logger.info("Sucesso: " + filename)
            success_count += 1
            
        except Exception as e:
            logger.error("Erro na prancha {}: {}".format(sheet.SheetNumber, e))
            
        pb.update_progress(count + 1, len(selected_sheets))

# --- 4. Relatório Final ---
if success_count > 0:
    forms.toast(
        "Exportação concluída!",
        title="ManaTools",
        message="{} arquivos gerados em {}".format(success_count, dest_folder)
    )

