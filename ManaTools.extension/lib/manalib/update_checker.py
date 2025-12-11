# -*- coding: utf-8 -*-
"""
Verificação de versão remota para ManaTools.
Consulta uma rota pública e compara com a versão local.
"""
import json
import clr

clr.AddReference("System.Net.Http")
clr.AddReference("System")
import System
from System.Net.Http import HttpClient
from System import TimeSpan

# Endpoint da API (prod)
API_URL = "https://manatools.discloud.app/api"


def get_remote_version_info():
    """Consulta a API para saber a versão mais recente."""
    # Garante TLS 1.2 (evita falha em ambientes .NET legados)
    try:
        System.Net.ServicePointManager.SecurityProtocol = System.Net.SecurityProtocolType.Tls12
    except:
        pass

    def _call(url):
        client = HttpClient()
        try:
            # Timeout curto para não travar o Revit se a internet estiver lenta
            client.Timeout = TimeSpan.FromSeconds(3)
            response = client.GetAsync(url).Result
            if response.IsSuccessStatusCode:
                content = response.Content.ReadAsStringAsync().Result
                return json.loads(content)
            else:
                print("ManaTools Update | HTTP {} em {}".format(response.StatusCode, url))
        except Exception as exc:
            print("ManaTools Update | falha em {} | {}".format(url, exc))
            return None
        return None

    # Tenta HTTPS, se falhar tenta HTTP (fallback)
    data = _call(API_URL + "/version")
    if data:
        return data

    try:
        http_url = API_URL.replace("https://", "http://")
        if http_url != API_URL:
            return _call(http_url + "/version")
    except:
        pass

    return None


def is_update_available(local_version_str):
    """Compara versões simples (semver básico)."""
    remote_data = get_remote_version_info()
    if not remote_data:
        return False, None

    remote_ver = remote_data.get("latest_version", "0.0.0")

    if _version_gt(remote_ver, local_version_str):
        return True, remote_data

    return False, None


def _version_gt(remote, local):
    """Compara strings de versão 'x.y.z' de forma segura."""
    def to_tuple(v):
        try:
            return tuple(int(x) for x in v.split("."))
        except:
            return (0,)

    return to_tuple(remote) > to_tuple(local)

