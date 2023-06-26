from pyrogram.handlers import MessageHandler
from pyrogram.filters import command

from bot import bot, LOGGER, user_data
from bot.helper.telegram_helper.filters import CustomFilters

async def broadcast_message(client, message):
    chat_id = message.chat.id
    if message.reply_to_message is None:
        await message.reply_text("Please reply to a message to broadcast.")
        return
        
    success = 0
    failed = 0
    for id_ in user_data.keys():
        try:
            await client.copy_message(chat_id=id_, from_chat_id=chat_id, message_id=message.reply_to_message_id)
            success += 1
        except Exception as err:
            LOGGER.error(err)
            failed += 1
    total_users = success + failed
    msg = f"<b>Broadcasting Complete</b>\n\n"
    msg += f"<b>• Total Users: </b>{total_users}\n"
    msg += f"<b>• Successful: </b>{success}\n"
    msg += f"<b>• Failed: </b>{failed}"
    await client.send_message(message.chat.id, msg)

bot.add_handler(MessageHandler(broadcast_message, filters=command("broadcast") & CustomFilters.sudo))