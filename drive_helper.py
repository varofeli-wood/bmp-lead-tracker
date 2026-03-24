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

def _get_or_create_folder(service, name: str, parent_id: str) -> str:
    q = (f"name='{name}' and '{parent_id}' in parents "
         f"and mimeType='application/vnd.google-apps.folder' and trashed=false")
    results = service.files().list(q=q, fields='files(id)').execute()
    files   = results.get('files', [])
    if files:
        return files[0]['id']
    meta   = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = service.files().create(body=meta, fields='id').execute()
    return folder['id']

async def upload_photo(bot, file_id: str) -> dict | None:
    try:
        drive_folder_id = os.environ.get('DRIVE_FOLDER_ID', '')
        if not drive_folder_id:
            logger.warning('DRIVE_FOLDER_ID not set, skipping photo upload')
            return None

        # Download from Telegram
        tg_file    = await bot.get_file(file_id)
        file_bytes = await tg_file.download_as_bytearray()

        # Upload to Drive
        service     = _drive_service()
        now         = datetime.now(WITA)
        folder_name = now.strftime('%Y-%m')
        subfolder   = _get_or_create_folder(service, folder_name, drive_folder_id)
        filename    = f"visit_{now.strftime('%Y%m%d_%H%M%S')}.jpg"

        media    = MediaIoBaseUpload(io.BytesIO(bytes(file_bytes)), mimetype='image/jpeg')
        uploaded = service.files().create(
            body={'name': filename, 'parents': [subfolder]},
            media_body=media,
            fields='id,webViewLink'
        ).execute()

        # Make publicly viewable
        service.permissions().create(
            fileId=uploaded['id'],
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()

        logger.info(f'Photo uploaded: {uploaded["id"]}')
        return {'file_id': uploaded['id'], 'url': uploaded.get('webViewLink', '')}

    except Exception as e:
        logger.error(f'upload_photo error: {e}', exc_info=True)
        return None
