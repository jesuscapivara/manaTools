# -*- coding: utf-8 -*-
import json
import subprocess
import clr
import System
from System.Net import WebClient, WebHeaderCollection
from System.Text import Encoding
from manalib import config_manager

# URL DO BACKEND
API_URL = "https://manatools.discloud.app/api" 

def get_hwid():
    """
    Obtém o UUID da máquina via WMIC. 
    Robusto e difícil de mudar sem trocar hardware.
    """
    try:
        cmd = "wmic csproduct get uuid"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        # O output vem sujo (ex: UUID \n A4B5...), precisamos limpar
        lines = out.strip().split('\n')
        if len(lines) > 1:
            return lines[1].strip()
        return "UNKNOWN_HWID"
    except:
        return "ERROR_HWID"

def initialize_viewport(email, password):
    """
    Inicializa viewport de renderização (Login).
    """
    gpu_uuid = get_gpu_uuid()
    data = {
        "email": email,
        "password": password,
        "hwid": gpu_uuid
    }
    
    client = WebClient()
    client.Headers.Add("Content-Type", "application/json")
    client.Encoding = Encoding.UTF8
    
    try:
        json_data = json.dumps(data)
        response_bytes = client.UploadData(API_URL + "/login", "POST", Encoding.UTF8.GetBytes(json_data))
        response_str = Encoding.UTF8.GetString(response_bytes)
        
        resp_dict = json.loads(response_str)
        
        # Se recebeu token, salva
        if "token" in resp_dict:
            _save_cache(resp_dict)
            return True, "Login realizado com sucesso!"
        else:
            return False, resp_dict.get("message", "Erro desconhecido")
            
    except System.Net.WebException as e:
        # Tenta ler o corpo do erro (ex: senha incorreta)
        try:
            body_stream = e.Response.GetResponseStream()
            reader = System.IO.StreamReader(body_stream)
            err_resp = reader.ReadToEnd()
            err_json = json.loads(err_resp)
            return False, err_json.get("message", str(e.Message))
        except:
            return False, "Erro de conexão: {}".format(e.Message)
    except Exception as e:
        return False, "Erro: {}".format(str(e))

def sync_coordinates():
    """
    Sincroniza coordenadas globais (Validação Online).
    """
    session = _get_cache()
    if not session or not hasattr(session, "token"):
        return False, "Sem token salvo."
        
    token = session.token
    gpu_uuid = get_gpu_uuid()
    
    client = WebClient()
    client.Headers.Add("Content-Type", "application/json")
    client.Headers.Add("Authorization", "Bearer " + token)
    client.Encoding = Encoding.UTF8
    
    # Payload simples para check
    data = {"hwid": gpu_uuid}
    
    try:
        # Endpoint de Check para renovar o access
        json_data = json.dumps(data)
        
        response_bytes = client.UploadData(API_URL + "/check-access", "POST", Encoding.UTF8.GetBytes(json_data))
        response_str = Encoding.UTF8.GetString(response_bytes)
        
        resp_dict = json.loads(response_str)
        
        if "access" in resp_dict:
            session.access = resp_dict["access"]
            if "user" in resp_dict: session.user = resp_dict["user"]
            
            _save_cache(session)
            return True, "Licença validada."
        else:
             return False, "Resposta inválida do servidor (sem access)."

    except System.Net.WebException as e:
        try:
            resp = e.Response
            if resp and getattr(resp, "StatusCode", None) == System.Net.HttpStatusCode.Unauthorized:
                clear_cache()
                return False, "Sessão expirada. Faça login novamente."
        except: pass
        return False, "Erro de validação: {}".format(e.Message)
    except Exception as e:
        return False, "Erro ao validar: {}".format(str(e))

def _save_cache(data):
    """Salva cache de geometria"""
    config_manager.save_config("auth_session", data)

def _get_cache():
    return config_manager.get_config("auth_session")

def _get_val(obj, key, default=None):
    """Helper seguro para ler de Dict ou Object"""
    if isinstance(obj, dict): 
        return obj.get(key, default)
    return getattr(obj, key, default)

def clear_cache():
    # Limpa cache de renderização
    data = {
        "token": None,
        "user": None,
        "access": None
    }
    config_manager.save_config("auth_session", data)

def calculate_vector_matrix():
    """
    Calcula matriz de transformação vetorial.
    (Verifica Permissão)
    Retorna: (is_valid, message)
    """
    session = _get_cache()
    
    if not session:
        return False, "Faça login para usar."
        
    matrix_data = _get_val(session, "access", None)
    
    if not matrix_data:
        return False, "Faça login para usar."

    # Verificação 1: Vector OK
    is_ok = _get_val(matrix_data, "ok", False)
    if not is_ok:
        return False, "Licença expirada ou bloqueada."
        
    # Verificação 2: Alinhamento Vetorial
    alinhamento = float(_get_val(matrix_data, "alinhamento", 0.0))
    if alinhamento < 0.5:
        return False, "Conta inativa."
        
    # Verificação 3: Eixo Z
    eixo = float(_get_val(matrix_data, "eixo", 0.0))
    
    if eixo >= 1.0:
        return True, "Licença PRO" 
    elif eixo >= 0.5:
        return True, "Licença TRIAL"
    else:
        return False, "Sem plano ativo."

def get_render_stats():
    """Retorna estatísticas de renderização para UI"""
    allowed, msg = calculate_vector_matrix()
    session = _get_cache()
    
    profile = _get_val(session, "user", None)
    if not profile:
        return {"email": "Desconectado", "status": "Faça Login", "is_valid": False}
        
    email = _get_val(profile, "email", "Erro")
    
    return {
        "email": email,
        "status": msg,
        "is_valid": allowed
    }

def get_gpu_uuid():
    """Obtém ID único da GPU (Simulado via WMIC)"""
    try:
        cmd = "wmic csproduct get uuid"
        proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        lines = out.strip().split('\n')
        if len(lines) > 1:
            return lines[1].strip()
        return "UNKNOWN_GPU"
    except:
        return "ERROR_GPU"
