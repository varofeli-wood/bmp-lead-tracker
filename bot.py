import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
    ContextTypes
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ── Conversation States ───────────────────────────────────────────────────────
COMPANY, PIC, JABATAN, ZONA, STATUS, KETERANGAN, FOTO, CONFIRM, PHOTO_CONFIRM = range(9)

BOT_TOKEN = os.environ.get('BOT_TOKEN', '').strip()
logger.info(f'BOT_TOKEN loaded: length={len(BOT_TOKEN)}, starts_with={BOT_TOKEN[:10] if BOT_TOKEN else "EMPTY"}')

# ── Helpers ───────────────────────────────────────────────────────────────────

def status_emoji(s):
    return {'hot': '🔥', 'warm': '🌡️', 'cold': '❄️'}.get(s, '❓')

def init_data(foto_file_id=''):
    return {
        'company_name': '',
        'pic_name': '',
        'pic_jabatan': '',
        'zona_industri': '',
        'status_lead': '',
        'keterangan': '',
        'foto_file_id': foto_file_id
    }

def status_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('🔥 Hot',   callback_data='status_hot'),
            InlineKeyboardButton('🌡️ Warm', callback_data='status_warm')
        ],
        [
            InlineKeyboardButton('❄️ Cold',  callback_data='status_cold'),
            InlineKeyboardButton('⏭️ Skip',  callback_data='status_skip')
        ]
    ])

async def send_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = context.user_data['data']
    emoji = status_emoji(d['status_lead'])
    status_label = d['status_lead'].capitalize() if d['status_lead'] not in ('', '-') else 'Tidak diset'
    jabatan_str = f' — {d["pic_jabatan"]}' if d.get('pic_jabatan') and d['pic_jabatan'] != '-' else ''
    foto_info = '📸 1 foto' if d.get('foto_file_id') else '📸 Tidak ada foto'
    keterangan_preview = d['keterangan'][:200] if d.get('keterangan') else '-'

    text = (
        '✅ <b>Konfirmasi Data Visit:</b>\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━\n'
        f'🏢 {d["company_name"]}\n'
        f'👤 {d["pic_name"]}{jabatan_str}\n'
        f'📍 {d["zona_industri"]}\n'
        f'🎯 Status: {emoji} {status_label}\n'
        f'📝 {keterangan_preview}\n'
        f'{foto_info}\n\n'
        'Simpan data ini?'
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton('✅ Simpan', callback_data='confirm_save'),
        InlineKeyboardButton('❌ Batal',  callback_data='confirm_cancel')
    ]])

    msg = update.message if update.message else update.callback_query.message
    await msg.reply_text(text, reply_markup=keyboard, parse_mode='HTML')
    return CONFIRM

# ── Command Handlers ──────────────────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '🏭 <b>Selamat datang di BMP Lead Tracker!</b>\n\n'
        'Bot ini untuk mencatat visit ke perusahaan di zona industri.\n\n'
        '📝 /visit — Catat visit baru\n'
        '❌ /batal — Batalkan input\n'
        '❓ /help  — Panduan\n\n'
        'Atau langsung kirim foto dari lokasi visit! 📸',
        parse_mode='HTML'
    )

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '❓ <b>PANDUAN BMP Lead Tracker</b>\n'
        '━━━━━━━━━━━━━━━━━━━━━━━━\n\n'
        '📝 /visit — Mulai catat visit baru\n'
        '  Bot akan tanya 7 pertanyaan:\n'
        '  1. Nama perusahaan\n'
        '  2. Nama PIC\n'
        '  3. Jabatan PIC\n'
        '  4. Zona industri\n'
        '  5. Status lead (Hot/Warm/Cold)\n'
        '  6. Keterangan visit\n'
        '  7. Foto dokumentasi\n\n'
        '  💡 Semua bisa di-skip dengan /skip\n\n'
        '❌ /batal — Batalkan input yang sedang berjalan\n'
        '📸 Kirim foto langsung — Bot akan tanya mau catat visit',
        parse_mode='HTML'
    )

async def cmd_unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '⚠️ Perintah tidak dikenal.\n\n'
        '📝 /visit — Catat visit baru\n'
        '❌ /batal — Batalkan input\n'
        '❓ /help  — Panduan'
    )

async def msg_no_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        '👋 Ketik /visit untuk mulai catat visit baru.\n'
        'Atau kirim /help untuk panduan.'
    )

# ── Visit Flow ────────────────────────────────────────────────────────────────

async def visit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data'] = init_data()
    await update.message.reply_text(
        '🏢 <b>Nama perusahaan?</b>\n(Ketik nama, atau /skip)',
        parse_mode='HTML'
    )
    return COMPANY

# — COMPANY —
async def step_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['company_name'] = update.message.text
    await update.message.reply_text(
        '👤 <b>Nama PIC / Contact Person?</b>\n(Ketik nama, atau /skip)',
        parse_mode='HTML'
    )
    return PIC

async def skip_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['company_name'] = '-'
    await update.message.reply_text(
        '👤 <b>Nama PIC?</b>\n(Ketik nama, atau /skip)', parse_mode='HTML')
    return PIC

# — PIC —
async def step_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['pic_name'] = update.message.text
    await update.message.reply_text(
        '💼 <b>Jabatan PIC?</b>\n'
        '(Contoh: Purchasing Manager, Owner, Kepala Teknik)\n'
        '(Ketik jabatan, atau /skip)',
        parse_mode='HTML'
    )
    return JABATAN

async def skip_pic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['pic_name'] = '-'
    await update.message.reply_text(
        '💼 <b>Jabatan PIC?</b>\n(Ketik jabatan, atau /skip)', parse_mode='HTML')
    return JABATAN

# — JABATAN —
async def step_jabatan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['pic_jabatan'] = update.message.text
    await update.message.reply_text(
        '📍 <b>Zona Industri mana?</b>\n'
        'Ketik nama zona, contoh: KIMA Makassar, KIGM Mamminasata\n'
        '(Atau /skip)',
        parse_mode='HTML'
    )
    return ZONA

async def skip_jabatan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['pic_jabatan'] = '-'
    await update.message.reply_text(
        '📍 <b>Zona Industri mana?</b>\nKetik nama zona.\n(Atau /skip)', parse_mode='HTML')
    return ZONA

# — ZONA —
async def step_zona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['zona_industri'] = update.message.text
    await update.message.reply_text(
        '🎯 <b>Status lead saat ini?</b>',
        reply_markup=status_keyboard(),
        parse_mode='HTML'
    )
    return STATUS

async def skip_zona(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['zona_industri'] = '-'
    await update.message.reply_text(
        '🎯 <b>Status lead saat ini?</b>',
        reply_markup=status_keyboard(),
        parse_mode='HTML'
    )
    return STATUS

# — STATUS —
async def step_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    status_map = {
        'status_hot': 'hot', 'status_warm': 'warm',
        'status_cold': 'cold', 'status_skip': '-'
    }
    context.user_data['data']['status_lead'] = status_map.get(query.data, '-')
    await query.message.reply_text(
        '📝 <b>Keterangan hasil visit?</b>\n'
        'Tulis bebas: info yang didapat, alasan status lead,\n'
        'rencana follow-up, dll.\n'
        '(Atau /skip)',
        parse_mode='HTML'
    )
    return KETERANGAN

# — KETERANGAN —
async def step_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['keterangan'] = update.message.text
    if context.user_data['data'].get('foto_file_id'):
        return await send_confirmation(update, context)
    await update.message.reply_text(
        '📸 <b>Kirim foto dokumentasi visit</b>\n(Kirim foto, atau /skip)',
        parse_mode='HTML'
    )
    return FOTO

async def skip_keterangan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['keterangan'] = '-'
    if context.user_data['data'].get('foto_file_id'):
        return await send_confirmation(update, context)
    await update.message.reply_text(
        '📸 <b>Kirim foto dokumentasi visit</b>\n(Kirim foto, atau /skip)',
        parse_mode='HTML'
    )
    return FOTO

# — FOTO —
async def step_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    context.user_data['data']['foto_file_id'] = photo.file_id
    return await send_confirmation(update, context)

async def skip_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['data']['foto_file_id'] = ''
    return await send_confirmation(update, context)

# — CONFIRM —
async def step_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'confirm_cancel':
        context.user_data.clear()
        await query.message.reply_text('❌ Input dibatalkan.')
        return ConversationHandler.END

    await query.message.reply_text('⏳ Menyimpan data...')

    try:
        d = context.user_data['data']
        foto_url, foto_id = '', ''

        if d.get('foto_file_id'):
            from drive_helper import upload_photo
            result = await upload_photo(query.message.get_bot(), d['foto_file_id'])
            if result:
                foto_url = result['url']
                foto_id  = result['file_id']

        from sheets_helper import append_visit, upsert_lead
        visit_id = append_visit({**d, 'foto_url': foto_url, 'foto_id': foto_id})
        upsert_lead(d)

        context.user_data.clear()
        await query.message.reply_text(
            f'✅ <b>Visit disimpan!</b> ({visit_id})\n\n'
            'Ketik /visit untuk catat visit berikutnya.',
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f'confirm error: {e}', exc_info=True)
        await query.message.reply_text(f'⚠️ Error menyimpan: {str(e)}')

    return ConversationHandler.END

# — CANCEL —
async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text('❌ Input dibatalkan.')
    return ConversationHandler.END

# ── Quick Photo (kirim foto di luar conversation) ─────────────────────────────

async def photo_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    context.user_data['pending_photo'] = photo.file_id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('📝 Ya, mulai input visit', callback_data='quick_yes')],
        [InlineKeyboardButton('❌ Tidak',                 callback_data='quick_no')]
    ])
    await update.message.reply_text(
        '📸 Foto diterima!\nMau catat sebagai visit baru?',
        reply_markup=keyboard
    )
    return PHOTO_CONFIRM

async def photo_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'quick_no':
        await query.message.reply_text('OK, foto tidak dicatat sebagai visit.')
        return ConversationHandler.END

    photo_file_id = context.user_data.pop('pending_photo', '')
    context.user_data['data'] = init_data(foto_file_id=photo_file_id)
    await query.message.reply_text(
        '📸 Foto sudah tersimpan!\n\n'
        '🏢 <b>Nama perusahaan?</b>\n(Ketik nama, atau /skip)',
        parse_mode='HTML'
    )
    return COMPANY

# ── App Setup ─────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            CommandHandler('visit', visit_start),
            MessageHandler(filters.PHOTO & ~filters.COMMAND, photo_entry),
        ],
        states={
            COMPANY:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_company),
                            CommandHandler('skip', skip_company)],
            PIC:           [MessageHandler(filters.TEXT & ~filters.COMMAND, step_pic),
                            CommandHandler('skip', skip_pic)],
            JABATAN:       [MessageHandler(filters.TEXT & ~filters.COMMAND, step_jabatan),
                            CommandHandler('skip', skip_jabatan)],
            ZONA:          [MessageHandler(filters.TEXT & ~filters.COMMAND, step_zona),
                            CommandHandler('skip', skip_zona)],
            STATUS:        [CallbackQueryHandler(step_status, pattern='^status_')],
            KETERANGAN:    [MessageHandler(filters.TEXT & ~filters.COMMAND, step_keterangan),
                            CommandHandler('skip', skip_keterangan)],
            FOTO:          [MessageHandler(filters.PHOTO, step_foto),
                            CommandHandler('skip', skip_foto)],
            CONFIRM:       [CallbackQueryHandler(step_confirm, pattern='^confirm_')],
            PHOTO_CONFIRM: [CallbackQueryHandler(photo_confirm, pattern='^quick_')],
        },
        fallbacks=[CommandHandler('batal', cmd_cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler('start', cmd_start))
    app.add_handler(CommandHandler('help', cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_no_state))
    app.add_handler(MessageHandler(filters.COMMAND, cmd_unknown))

    logger.info('BMP Lead Tracker bot started (polling)...')
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
