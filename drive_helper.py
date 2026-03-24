# Photo storage: simpan Telegram file_id saja (foto tetap di server Telegram)
# Tidak ada upload ke storage eksternal

async def upload_photo(bot, file_id: str) -> dict | None:
    """Kembalikan Telegram file_id sebagai referensi foto."""
    if not file_id:
        return None
    return {
        'file_id': file_id,
        'url':     ''   # tidak ada URL eksternal
    }
