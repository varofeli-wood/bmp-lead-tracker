import os
import json
import logging
from datetime import datetime, timezone, timedelta
import gspread
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

WITA   = timezone(timedelta(hours=8))
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def _client():
    creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
    creds_dict = json.loads(creds_json)
    creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(creds)

def _spreadsheet():
    return _client().open_by_key(os.environ.get('SPREADSHEET_ID'))

def _now_wita():
    return datetime.now(WITA)

def _now_str():
    return _now_wita().strftime('%Y-%m-%d %H:%M:%S')

def _visit_id():
    return 'VIS-' + _now_wita().strftime('%Y%m%d-%H%M%S')

def _lead_id():
    return 'LEAD-' + _now_wita().strftime('%Y%m%d-%H%M%S')

# ── Public functions ──────────────────────────────────────────────────────────

def append_visit(data: dict) -> str:
    ss       = _spreadsheet()
    sheet    = ss.worksheet('Visits')
    visit_id = _visit_id()
    row = [
        visit_id,
        _now_str(),
        data.get('company_name', ''),
        data.get('pic_name', ''),
        data.get('pic_jabatan', ''),
        data.get('zona_industri', ''),
        data.get('status_lead', ''),
        data.get('keterangan', ''),
        data.get('foto_url', ''),
        data.get('foto_id', '')
    ]
    sheet.append_row(row, value_input_option='RAW')
    logger.info(f'Visit saved: {visit_id}')
    return visit_id

def get_recent_visits_with_photo(limit: int = 10) -> list:
    """Ambil visit terbaru yang punya foto_id, max `limit` baris."""
    ss     = _spreadsheet()
    sheet  = ss.worksheet('Visits')
    rows   = sheet.get_all_values()  # header + data
    result = []
    for row in reversed(rows[1:]):   # dari terbaru
        if len(row) >= 10 and row[9]:  # kolom foto_id (index 9) tidak kosong
            result.append({
                'visit_id':    row[0],
                'timestamp':   row[1],
                'company':     row[2],
                'foto_id':     row[9]
            })
        if len(result) >= limit:
            break
    return result

def upsert_lead(data: dict):
    ss      = _spreadsheet()
    sheet   = ss.worksheet('Leads')
    records = sheet.get_all_values()   # list of lists including header
    company = data.get('company_name', '')
    now     = _now_str()

    for i, row in enumerate(records[1:], start=2):   # skip header, 1-based index
        if len(row) > 1 and row[1] == company:
            total = int(row[6]) + 1 if len(row) > 6 and str(row[6]).isdigit() else 1
            first = row[7] if len(row) > 7 and row[7] else now
            updated = [
                row[0],
                company,
                data.get('pic_name', row[2] if len(row) > 2 else ''),
                data.get('pic_jabatan', row[3] if len(row) > 3 else ''),
                data.get('zona_industri', row[4] if len(row) > 4 else ''),
                data.get('status_lead', row[5] if len(row) > 5 else ''),
                total,
                first,
                now,
                data.get('keterangan', '')
            ]
            sheet.update(f'A{i}:J{i}', [updated])
            logger.info(f'Lead updated: {company}')
            return

    # New lead
    sheet.append_row([
        _lead_id(), company,
        data.get('pic_name', ''),
        data.get('pic_jabatan', ''),
        data.get('zona_industri', ''),
        data.get('status_lead', ''),
        1, now, now,
        data.get('keterangan', '')
    ], value_input_option='RAW')
    logger.info(f'Lead created: {company}')
