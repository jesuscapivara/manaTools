# -*- coding: utf-8 -*-
"""
Utilitários para tratamento de strings e sanitização de nomes de arquivos.
"""
import re
import unicodedata


def sanitize_filename(text):
    """
    Transforma strings sujas em padrão de arquivo seguro/web-friendly.
    
    Ex: 'PL-01 - Térreo (Final)' -> 'PL-01_TERREO_FINAL'
    
    Args:
        text (str): Texto a ser sanitizado
        
    Returns:
        str: Nome de arquivo sanitizado
    """
    if not text:
        return "SEM_NOME"
    
    # 1. Normalização Unicode (remove acentos: á -> a, ç -> c)
    # Compatível com Python 2.7 (IronPython) e Python 3+
    try:
        # Verifica se estamos em Python 2.7 (IronPython)
        unicode_type = type(u'')  # Define unicode_type dinamicamente
        if isinstance(text, unicode_type):
            text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore')
        else:
            text = unicodedata.normalize('NFKD', unicode_type(text, 'utf-8')).encode('ASCII', 'ignore')
    except (NameError, UnicodeDecodeError, TypeError, AttributeError):
        # Python 3+ ou string já em ASCII
        try:
            if isinstance(text, str):
                text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
            else:
                text = str(text)
        except:
            # Fallback: converte para string e tenta normalizar
            text = str(text)
            text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore')
            if isinstance(text, bytes):
                text = text.decode('ASCII')
    
    # 2. Upper case
    text = text.upper()
    
    # 3. Substitui espaços e hifens por underscore
    text = re.sub(r'[\s-]+', '_', text)
    
    # 4. Remove qualquer caractere que não seja letra, número ou underscore
    text = re.sub(r'[^A-Z0-9_]', '', text)
    
    # 5. Remove underscores duplicados
    text = re.sub(r'_{2,}', '_', text)
    
    return text.strip('_')

