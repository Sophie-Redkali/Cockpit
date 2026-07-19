"""
Utilitaires pour uploader des fichiers vers SharePoint via Microsoft Graph,
en utilisant le flow On-Behalf-Of (OBO) : les droits d'accès réels sur
SharePoint sont ceux de l'utilisateur connecté en SSO, pas ceux d'un
compte de service applicatif. 
"""

import re
import msal
import requests
from django.conf import settings

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"

# Pour les gros fichiers il faut utiliser une autre méthode PUT > "upload session"
# Limite imposé par graph : 4Mo
LARGE_FILE_THRESHOLD = 4*1024*1024

# récupération des autorisations
class SharePointUplaodError(Exception):
    # Erreur levée en cas d'échec d'authentification ou de chargement vers le Sharepoint
    pass

def _get_confidential_client():
    # récupération des autorisation pour l'application
    return msal.ConfidentialClientApplication(
        client_id=settings.SP_CLIENT_ID,
        client_credential=settings.SP_CLIENT_SECRET,
        authority=f'https//login.microsoftonline.com/{settings.SP_TENANT_ID}',
    )

def get_graph_token_obo(user_access_token):
    # user_access_token : token obtenu lors du sso de l'utilisateur
    # échange du token utilisateur contre un token graph, via le flux OBO
    app = _get_confidential_client()

    result = app.acquire_token_on_behalf_of(
        user_assertion = user_access_token,
        scopes=["https://graph.microsoft.com/.default"],
    )
    if "access_token" not in result:
        raise SharePointUplaodError(f"Erreur OBO : {result.get('error')} - {result.get('errot_description')}")
    return result["access_token"]

def get_site_id(token: str) -> str:
    url = f'{GRAPH_BASE_URL}/sites/{settings.SP_SITE_HOSTNAME}:{settings.SP_SITE_PATH}'
    resp = requests.get(url, headers={"Authorization": f'Bearer {token}'})
    if resp.status_code != 200:
        raise SharePointUplaodError(
            f'Impossible de récupérer le site SharePoint ({resp.status_code}):{resp.text}'
        )
    return resp.json()["id"]

# gestions des emplacements d'enregistrements des documents: création dynamiques des dossiers
def sanitize_folder_name(name: str) -> str:
    #suppression des caractères interdit dans les noms de dossiers sharepoint
    name = name.strip()
    name = re.sub(r'[":\*<>?/\\|]', "", name)
    name = re.sub(r"\s+", " ", name) # en cas d'espaces multiples
    
    return name[:100] # réduit les noms à 100 caractère si le nom du projet est trop long

def build_unique_folder_name(base_name: str, object_id: int) -> str:
    # construit un nom de dossier unique avec l'id en base
    return f"{sanitize_folder_name(base_name)} ({object_id})"

def folder_exists(token: str, site_id: str, folder_path: str) -> str:
    # vérification si un dossier existe déjà pour le projet/contact/these/...
    url = f'{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{folder_path}'
    resp = requests.get(url, headers={"Authorization": f'Bearer {token}'})
    return resp.status_code == 200

def create_folder(token: str, site_id:str, parent_path: str, folder_name: str) -> dict:
    # créé un sous-dossier sous parent_path
    # si parent_path est vide, crée le dossier à la racine
    if parent_path:
        url = f'{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{parent_path}:/children'
    else:
        url = f'{GRAPH_BASE_URL}/sites/{site_id}/drive/root/children'

    resp =requests.post(
        url,
        headers={
            "Authorization": f'Bearer {token}',
            "Content-Type": "application/json",
        },
        json={
            "name": folder_name,
            "folder": {},
            "@microsoft.graph.conflictBehavior": "fail", # échoue si le dossier existe déjà
        },
    )
    if resp.status_code not in (200, 201):
        raise SharePointUplaodError(
            f"Impossible de créer le dossier '{folder_name}' ({resp.status_code}) : {resp.text}"
        )
    return resp.json()

def get_or_create_subfolder(token: str, site_id:str, parent_folder: str, folder_name: str) -> str:
    full_path = f'{parent_folder}/{folder_name}' if parent_folder else folder_name

    if not folder_exists(token, site_id, full_path):
        create_folder(token, site_id, parent_folder, folder_name)

    return full_path

# chargement de fichiers avec distinction de traitement entre les petits et gros fichiers
def _upload_small_file(token: str, site_id: str, folder_path: str, filename: str, file_obj) -> dict:
    url = f'{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{folder_path}/{filename}:/content'
    resp = requests.put(
        url,
        headers={
            "Authorization": f'Bearer {token}',
            "Content-Type": "application/octet-stream",
        },
        data=file_obj.read(),
    )
    if resp.status_code not in (200, 201):
        raise SharePointUplaodError(
            f"Echec de l'upload SharePoint ({resp.status_code}) : {resp.text}"
        )
    return resp.json()

def _upload_large_file(token: str, site_id: str, folder_path: str, filename: str, file_obj, file_size: int) -> dict:
    session_url = f"{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{folder_path}/{filename}:/createUploadSession"
    resp = requests.post(
        session_url,
        headers={
            "Authorization": f'Bearer {token}',
            "Content-Type": "application/json",
        },
        json={"item": {"@microsoft.graph.conflictBehavior": "replace"}},
    )
    if resp.status_code != 200:
        raise SharePointUplaodError(
            f"Impossible de créer la session d'upload ({resp.status_code}) : {resp.text}"
        )
    upload_url = resp.json()["uploadUrl"]
    chunk_size = 5*1024*1024
    start = 0
    last_response = None
    file_obj.seek(0)
    while start < file_size:
        chunk = file_obj.read(chunk_size)
        end = start + len(chunk) - 1
        last_response = requests.put(
            upload_url,
            headers={
                "Content-Length": str(len(chunk)),
                "Content-Range": f"bytes {start}-{end}/{file_size}",
            },
            data=chunk,
        )
        if last_response.status_code not in (200, 201, 202):
            raise SharePointUplaodError(
                f"Echec de l'uplaod par bloc ({last_response.status_code}) : {last_response.text}"
            )
        start += len(chunk)
    return last_response.json()
    
def upload_file_to_sharepoint(user_access_token:str, file_obj, filename: str, folder_path: str) -> str:
    token = get_graph_token_obo(user_access_token)
    site_id = get_site_id(token)
    file_obj.seek(0, 2)
    file_size = file_obj.tell()
    file_obj.seek(0)

    if file_size < LARGE_FILE_THRESHOLD:
        result = _upload_small_file(token, site_id, folder_path, filename, file_obj)
    else:
        result = _upload_large_file(token, site_id, folder_path, filename, file_obj, file_size)
    return result.get("webUrl")