#!/usr/bin/env python3
import platform
from time import time
from datetime import datetime
from sys import executable
from os import execl as osexecl
from asyncio import create_subprocess_exec, gather
from uuid import uuid4
from base64 import b64decode
from quoters import Quote

from requests import get as rget
from pytz import timezone
from bs4 import BeautifulSoup
from signal import signal, SIGINT
from aiofiles.os import path as aiopath, remove as aioremove
from aiofiles import open as aiopen
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, cpu_freq, virtual_memory, net_io_counters, boot_time
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.filters import command, private, regex
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from bot import bot, config_dict, user_data, botStartTime, LOGGER, Interval, DATABASE_URL, QbInterval, INCOMPLETE_TASK_NOTIFIER, scheduler
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.bot_utils import get_progress_bar_string, get_readable_file_size, get_readable_time, cmd_exec, sync_to_async, set_commands, update_user_ldata, new_thread, format_validity_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, editMessage, sendFile, deleteMessage, one_minute_del
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker
from .helper.listeners.aria2_listener import start_aria2_listener
from .helper.themes import BotTheme
from .modules import authorize, clone, gd_count, gd_delete, gd_list, cancel_mirror, mirror_leech, status, torrent_search, torrent_select, ytdlp, \
                     rss, shell, eval, users_settings, bot_settings, speedtest, save_msg, images, anilist, mediainfo, mydramalist, broadcast

@new_thread
async def stats(_, message):
    total, used, free, disk = disk_usage('/')
    memory = virtual_memory()
    currentTime = get_readable_time(time() - botStartTime)
    mem_p = memory.percent
    osUptime = get_readable_time(time() - boot_time())
    cpuUsage = cpu_percent(interval=0.5)
    DIRECT_LIMIT = config_dict['DIRECT_LIMIT']
    YTDLP_LIMIT = config_dict['YTDLP_LIMIT']
    GDRIVE_LIMIT = config_dict['GDRIVE_LIMIT']
    TORRENT_LIMIT = config_dict['TORRENT_LIMIT']
    CLONE_LIMIT = config_dict['CLONE_LIMIT']
    MEGA_LIMIT = config_dict['MEGA_LIMIT']
    LEECH_LIMIT = config_dict['LEECH_LIMIT']
    USER_MAX_TASKS = config_dict['USER_MAX_TASKS']
    torrent_limit = '∞' if TORRENT_LIMIT == '' else f'{TORRENT_LIMIT}GB/Link'
    clone_limit = '∞' if CLONE_LIMIT == '' else f'{CLONE_LIMIT}GB/Link'
    gdrive_limit = '∞' if GDRIVE_LIMIT == '' else f'{GDRIVE_LIMIT}GB/Link'
    mega_limit = '∞' if MEGA_LIMIT == '' else f'{MEGA_LIMIT}GB/Link'
    leech_limit = '∞' if LEECH_LIMIT == '' else f'{LEECH_LIMIT}GB/Link'
    user_task = '∞' if USER_MAX_TASKS == '' else f'{USER_MAX_TASKS} Tasks/user'
    ytdlp_limit = '∞' if YTDLP_LIMIT == '' else f'{YTDLP_LIMIT}GB/Link'
    direct_limit = '∞' if DIRECT_LIMIT == '' else f'{DIRECT_LIMIT}GB/Link'
    stats = f'<b>SYSTEM INFO</b>\n\n'\
            f'<code>• Bot uptime :</code> {currentTime}\n'\
            f'<code>• Sys uptime :</code> {osUptime}\n'\
            f'<code>• CPU usage  :</code> {cpuUsage}%\n'\
            f'<code>• RAM usage  :</code> {mem_p}%\n'\
            f'<code>• Disk usage :</code> {disk}%\n'\
            f'<code>• Disk space :</code> {get_readable_file_size(free)}/{get_readable_file_size(total)}\n\n'\
            f'<b>LIMITATIONS</b>\n\n'\
            f'<code>• Torrent    :</code> {torrent_limit}\n'\
            f'<code>• Gdrive     :</code> {gdrive_limit}\n'\
            f'<code>• Ytdlp      :</code> {ytdlp_limit}\n'\
            f'<code>• Direct     :</code> {direct_limit}\n'\
            f'<code>• Leech      :</code> {leech_limit}\n'\
            f'<code>• Clone      :</code> {clone_limit}\n'\
            f'<code>• Mega       :</code> {mega_limit}\n'\
            f'<code>• User tasks :</code> {user_task}\n\n'
    reply_message = await sendMessage(message, stats, photo='IMAGES')
    await deleteMessage(message)
    await one_minute_del(reply_message)

async def start(client, message):
    id_ = message.from_user.id
    if message.chat.type == "private":
        if 'users' not in db.list_collection_names():
            db.create_collection('users')  
    if id_ and id_ not in user_data or user_data[id_].get('is_bot_user'):
        update_user_ldata(id_, 'is_bot_user', True)
    if DATABASE_URL:
        await DbManger().update_user_data(id_)
    buttons = ButtonMaker()
    reply_markup = buttons.build_menu(2)
    if len(message.command) > 1 and config_dict['TOKEN_TIMEOUT']:
        userid = message.from_user.id
        encrypted_url = message.command[1]
        input_token, pre_uid = (b64decode(encrypted_url.encode()).decode()).split('&&')
        if int(pre_uid) != userid:
            return await sendMessage(message, '<b>Temporary Token is not yours!</b>\n\n<i>Kindly generate your own.</i>')
        data = user_data.get(userid, {})
        if 'token' not in data or data['token'] != input_token:
            return await sendMessage(message, '<b>This token already used!</b>\n\n<i>Kindly collect a new one.</i>')
        buttons.ibutton('Activate token', f'pass {input_token}', 'header')
        reply_markup = buttons.build_menu(2)
        msg = 'Your token has successfully generated!\n\n'
        msg += f'It will valid for {format_validity_time(int(config_dict["TOKEN_TIMEOUT"]))}'
        return await sendMessage(message, msg, reply_markup)
    elif await CustomFilters.authorized(client, message):
        start_string = BotTheme('ST_MSG', help_command=f"/{BotCommands.HelpCommand}")
        await sendMessage(message, start_string, photo='IMAGES')
    elif config_dict['BOT_PM']:
        await sendMessage(message, BotTheme('ST_BOTPM'), photo='IMAGES')
    else:
        await sendMessage(message, BotTheme('ST_UNAUTH'), photo='IMAGES')

async def token_callback(_, query):
    user_id = query.from_user.id
    input_token = query.data.split()[1]
    data = user_data.get(user_id, {})
    if 'token' not in data or data['token'] != input_token:
        return await query.answer('Already used, collect new one', show_alert=True)
    update_user_ldata(user_id, 'token', str(uuid4()))
    update_user_ldata(user_id, 'time', time())
    await query.answer('Token activated!', show_alert=True)
    kb = query.message.reply_markup.inline_keyboard[1:]
    kb.insert(0, [InlineKeyboardButton('Activated', callback_data='pass activated')])
    await query.edit_message_reply_markup(InlineKeyboardMarkup(kb))
    
async def restart(client, message):
    restart_message = await sendMessage(message, BotTheme('RESTARTING'))
    if scheduler.running:
        scheduler.shutdown(wait=False)
    for interval in [QbInterval, Interval]:
        if interval:
            interval[0].cancel()
    await sync_to_async(clean_all)
    proc1 = await create_subprocess_exec('pkill', '-9', '-f', '-e', 'gunicorn|buffet|openstack|render|zcl')
    proc2 = await create_subprocess_exec('python3', 'update.py')
    await gather(proc1.wait(), proc2.wait())
    async with aiopen(".restartmsg", "w") as f:
        await f.write(f"{restart_message.chat.id}\n{restart_message.id}\n")
    osexecl(executable, executable, "-m", "bot")


async def ping(client, message):
    start_time = int(round(time() * 1000))
    reply = await sendMessage(message, BotTheme('PING'))
    end_time = int(round(time() * 1000))
    await editMessage(reply, BotTheme('PING_VALUE', value=(end_time - start_time)))


async def log(client, message):
    await sendFile(message, 'log.txt')


async def search_images():
    if not config_dict['IMG_SEARCH']:
        return
    try:
        query_list = config_dict['IMG_SEARCH']
        total_pages = config_dict['IMG_PAGE']
        base_url = "https://www.wallpaperflare.com/search"

        for query in query_list:
            query = query.strip().replace(" ", "+")
            for page in range(1, total_pages + 1):
                url = f"{base_url}?wallpaper={query}&width=1280&height=720&page={page}"
                r = rget(url)
                soup = BeautifulSoup(r.text, "html.parser")
                images = soup.select('img[data-src^="https://c4.wallpaperflare.com/wallpaper"]')
                for img in images:
                    img_url = img['data-src']
                    if img_url not in config_dict['IMAGES']:
                        config_dict['IMAGES'].append(img_url)
            if DATABASE_URL:
                await DbManger().update_config({'IMAGES': config_dict['IMAGES']})
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")


help_string = f'''
NOTE: Try each command without any argument to see more detalis.
/{BotCommands.MirrorCommand[0]} or /{BotCommands.MirrorCommand[1]}: Start mirroring to Google Drive.
/{BotCommands.QbMirrorCommand[0]} or /{BotCommands.QbMirrorCommand[1]}: Start Mirroring to Google Drive using qBittorrent.
/{BotCommands.YtdlCommand[0]} or /{BotCommands.YtdlCommand[1]}: Mirror yt-dlp supported link.
/{BotCommands.LeechCommand[0]} or /{BotCommands.LeechCommand[1]}: Start leeching to Telegram.
/{BotCommands.QbLeechCommand[0]} or /{BotCommands.QbLeechCommand[1]}: Start leeching using qBittorrent.
/{BotCommands.YtdlLeechCommand[0]} or /{BotCommands.YtdlLeechCommand[1]}: Leech yt-dlp supported link.
/{BotCommands.CloneCommand} [drive_url]: Copy file/folder to Google Drive.
/{BotCommands.CountCommand} [drive_url]: Count file/folder of Google Drive.
/{BotCommands.DeleteCommand} [drive_url]: Delete file/folder from Google Drive (Only Owner & Sudo).
/{BotCommands.UserSetCommand} [query]: Users settings.
/{BotCommands.BotSetCommand} [query]: Bot settings.
/{BotCommands.BtSelectCommand}: Select files from torrents by gid or reply.
/{BotCommands.CancelMirror}: Cancel task by gid or reply.
/{BotCommands.CancelAllCommand} [query]: Cancel all [status] tasks.
/{BotCommands.ListCommand} [query]: Search in Google Drive(s).
/{BotCommands.SearchCommand} [query]: Search for torrents with API.
/{BotCommands.StatusCommand}: Shows a status of all the downloads.
/{BotCommands.StatsCommand}: Show stats of the machine where the bot is hosted in.
/{BotCommands.PingCommand}: Check how long it takes to Ping the Bot (Only Owner & Sudo).
/{BotCommands.AuthorizeCommand}: Authorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UnAuthorizeCommand}: Unauthorize a chat or a user to use the bot (Only Owner & Sudo).
/{BotCommands.UsersCommand}: show users settings (Only Owner & Sudo).
/{BotCommands.AddSudoCommand}: Add sudo user (Only Owner).
/{BotCommands.RmSudoCommand}: Remove sudo users (Only Owner).
/{BotCommands.RestartCommand}: Restart and update the bot (Only Owner & Sudo).
/{BotCommands.LogCommand}: Get a log file of the bot. Handy for getting crash reports (Only Owner & Sudo).
/{BotCommands.ShellCommand}: Run shell commands (Only Owner).
/{BotCommands.EvalCommand}: Run Python Code Line | Lines (Only Owner).
/{BotCommands.ExecCommand}: Run Commands In Exec (Only Owner).
/{BotCommands.ClearLocalsCommand}: Clear {BotCommands.EvalCommand} or {BotCommands.ExecCommand} locals (Only Owner).
/{BotCommands.RssCommand}: RSS Menu.
'''


async def bot_help(client, message):
    await sendMessage(message, help_string)


async def restart_notification():
    now=datetime.now(timezone('Asia/Dhaka'))
    if await aiopath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
    else:
        chat_id, msg_id = 0, 0

    async def send_incompelete_task_message(cid, msg):
        try:
            if msg.startswith(BotTheme('RESTART_SUCCESS')):
                await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=msg)
                await aioremove(".restartmsg")
            else:
                await bot.send_message(chat_id=cid, text=msg, disable_web_page_preview=True,
                                       disable_notification=True)
        except Exception as e:
            LOGGER.error(e)

    if INCOMPLETE_TASK_NOTIFIER and DATABASE_URL:
        if notifier_dict := await DbManger().get_incomplete_tasks():
            for cid, data in notifier_dict.items():
                msg = BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y'))if cid == chat_id else BotTheme('RESTARTED')
                for tag, links in data.items():
                    msg += f"\n\n{tag}: "
                    for index, link in enumerate(links, start=1):
                        msg += f" <a href='{link}'>{index}</a> |"
                        if len(msg.encode()) > 4000:
                            await send_incompelete_task_message(cid, msg)
                            msg = ''
                if msg:
                    await send_incompelete_task_message(cid, msg)

    if await aiopath.isfile(".restartmsg"):
        try:
            await bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=BotTheme('RESTART_SUCCESS', time=now.strftime('%I:%M:%S %p'), date=now.strftime('%d/%m/%y')))
        except:
            pass
        await aioremove(".restartmsg")


async def main():
    await gather(start_cleanup(), torrent_search.initiate_search_tools(), restart_notification(), search_images(), set_commands(bot))
    await sync_to_async(start_aria2_listener, wait=False)
    
    bot.add_handler(MessageHandler(
        start, filters=command(BotCommands.StartCommand) & private))
    bot.add_handler(CallbackQueryHandler(
        token_callback, filters=regex(r'^pass')))
    bot.add_handler(MessageHandler(log, filters=command(
        BotCommands.LogCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(restart, filters=command(
        BotCommands.RestartCommand) & CustomFilters.sudo))
    bot.add_handler(MessageHandler(ping, filters=command(
        BotCommands.PingCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(bot_help, filters=command(
        BotCommands.HelpCommand) & CustomFilters.authorized))
    bot.add_handler(MessageHandler(stats, filters=command(
        BotCommands.StatsCommand) & CustomFilters.authorized))
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

bot.loop.run_until_complete(main())
bot.loop.run_forever()
