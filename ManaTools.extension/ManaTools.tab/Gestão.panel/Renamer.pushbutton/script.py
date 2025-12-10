# -*- coding: utf-8 -*-
"""Módulo de renomeação em massa baseado em regras da ABNT."""
# Imports padrão do pyRevit
from pyrevit import forms, script

# Import da SUA lib (o path é automático pelo pyRevit)
from manalib import utils, revit_utils

doc = __revit__.ActiveUIDocument.Document
logger = script.get_logger()

# 1. UI - Seleção
selection = revit_utils.get_selected_elements(doc)
if not selection:
    forms.alert("Selecione algo, chefe.", exitscript=True)

# 2. Lógica de Negócio (chamando a lib)
with revit_utils.setup_transaction(doc, "Renomear Elementos"):
    count = 0
    for element in selection:
        # Lógica complexa fica na lib, aqui só aplica
        success = utils.apply_naming_convention(element, standard="MANA_2025")
        if success: 
            count += 1

# 3. Feedback
logger.info("Processo finalizado. {} elementos renomeados.".format(count))
forms.alert("{} elementos renomeados com sucesso!".format(count), title="Sucesso")
