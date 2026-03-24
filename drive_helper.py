import os
import io
import json
import logging
from datetime import datetime, timezone, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

WITA   = timezone(timedelta(hours=8))
SCOPES = ['https://www.googleapis.com/auth/drive']

def _drive_service():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def _get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Buat atau ambil folder. Jika parent_id None, buat di root service account."""
    if parent_id:
        q = (f"name='{name}' and '{parent_id}' in parents "
             f"and mimeType='application/vnd.google-apps.folder' and trashed=false")
    else:
        q = (f"name='{name}' and 'root' in parents "
             f"and mimeType='application/vnd.google-apps.folder' and trashed=false")

    results = service.files().list(q=q, fields='files(id)').execute()
    files   = results.get('files', [])
    if files:
        return files[0]['id']

    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]

    folder = service.files().create(body=meta, fields='id').execute()
    return folder['id']

async def upload_photo(bot, file_id: str) -> dict | None:
    try:
        # Download dari Telegram
        tg_file    = await bot.get_file(file_id)
        file_bytes = await tg_file.download_as_bytearray()

        service = _drive_service()
        now     = datetime.now(WITA)

        # Buat folder BMP-Photos di root service account, lalu subfolder bulan
        root_folder = _get_or_create_folder(service, 'BMP-Photos')
        subfolder   = _get_or_create_folder(service, now.strftime('%Y-%m'), root_folder)
        filename    = f"visit_{now.strftime('%Y%m%d_%H%M%S')}.jpg"

        media    = MediaIoBaseUpload(io.BytesIO(bytes(file_bytes)), mimetype='image/jpeg')
        uploaded = service.files().create(
            body={'name': filename, 'parents': [subfolder]},
            media_body=media,
            fields='id,webViewLink'
        ).execute()

        # Buat file bisa diakses publik
        service.permissions().create(
            fileId=uploaded['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        logger.info(f'Photo uploaded: {uploaded["id"]}')
        return {'file_id': uploaded['id'], 'url': uploaded.get('webViewLink', '')}

    except Exception as e:
        logger.error(f'upload_photo error: {e}', exc_info=True)
        return None
