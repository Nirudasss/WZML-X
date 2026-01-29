from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall
from time import time

from psutil import cpu_percent, disk_usage, virtual_memory

from ... import (
    DOWNLOAD_DIR,
    bot_cache,
    bot_start_time,
    status_dict,
    task_dict,
    task_dict_lock,
)
from ...core.config_manager import Config
from ..telegram_helper.button_build import ButtonMaker

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]


class MirrorStatus:
    STATUS_UPLOAD = "Upload"
    STATUS_DOWNLOAD = "Download"
    STATUS_CLONE = "Clone"
    STATUS_QUEUEDL = "QueueDl"
    STATUS_QUEUEUP = "QueueUp"
    STATUS_PAUSED = "Pause"
    STATUS_ARCHIVE = "Archive"
    STATUS_EXTRACT = "Extract"
    STATUS_SPLIT = "Split"
    STATUS_CHECK = "CheckUp"
    STATUS_SEED = "Seed"
    STATUS_SAMVID = "SamVid"
    STATUS_CONVERT = "Convert"
    STATUS_FFMPEG = "FFmpeg"
    STATUS_YT = "YouTube"
    STATUS_METADATA = "Metadata"


class EngineStatus:
    def __init__(self):
        ver = bot_cache.get("eng_versions", {})
        self.STATUS_ARIA2 = f"Aria2 v{ver.get('aria2', 'N/A')}"
        self.STATUS_AIOHTTP = f"AioHttp v{ver.get('aiohttp', 'N/A')}"
        self.STATUS_GDAPI = f"Google-API v{ver.get('gapi', 'N/A')}"
        self.STATUS_QBIT = f"qBit v{ver.get('qBittorrent', 'N/A')}"
        self.STATUS_TGRAM = f"Pyro v{ver.get('pyrotgfork', 'N/A')}"
        self.STATUS_MEGA = f"MegaCMD v{ver.get('mega', 'N/A')}"
        self.STATUS_YTDLP = f"yt-dlp v{ver.get('yt-dlp', 'N/A')}"
        self.STATUS_FFMPEG = f"ffmpeg v{ver.get('ffmpeg', 'N/A')}"
        self.STATUS_7Z = f"7z v{ver.get('7z', 'N/A')}"
        self.STATUS_RCLONE = f"RClone v{ver.get('rclone', 'N/A')}"
        self.STATUS_SABNZBD = f"SABnzbd+ v{ver.get('SABnzbd+', 'N/A')}"
        self.STATUS_QUEUE = "QSystem v2"
        self.STATUS_JD = "JDownloader v2"
        self.STATUS_YT = "Youtube-Api"
        self.STATUS_METADATA = "Metadata"
        self.STATUS_UPHOSTER = "Uphoster"


STATUSES = {
    "ALL": "All",
    "DL": MirrorStatus.STATUS_DOWNLOAD,
    "UP": MirrorStatus.STATUS_UPLOAD,
    "QD": MirrorStatus.STATUS_QUEUEDL,
    "QU": MirrorStatus.STATUS_QUEUEUP,
    "AR": MirrorStatus.STATUS_ARCHIVE,
    "EX": MirrorStatus.STATUS_EXTRACT,
    "SD": MirrorStatus.STATUS_SEED,
    "CL": MirrorStatus.STATUS_CLONE,
    "CM": MirrorStatus.STATUS_CONVERT,
    "SP": MirrorStatus.STATUS_SPLIT,
    "SV": MirrorStatus.STATUS_SAMVID,
    "FF": MirrorStatus.STATUS_FFMPEG,
    "PA": MirrorStatus.STATUS_PAUSED,
    "CK": MirrorStatus.STATUS_CHECK,
}


# ---------------------- Async Task Utilities ---------------------- #

async def get_task_by_gid(gid: str):
    async with task_dict_lock:
        for tk in task_dict.values():
            if hasattr(tk, "seeding"):
                await tk.update()
            if tk.gid() == gid:
                return tk
        return None


async def get_specific_tasks(status, user_id):
    if status == "All":
        if user_id:
            return [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        else:
            return list(task_dict.values())

    tasks_to_check = (
        [tk for tk in task_dict.values() if tk.listener.user_id == user_id]
        if user_id
        else list(task_dict.values())
    )

    coro_tasks = [tk for tk in tasks_to_check if iscoroutinefunction(tk.status)]
    coro_statuses = await gather(*[tk.status() for tk in coro_tasks])

    result = []
    coro_index = 0
    for tk in tasks_to_check:
        if tk in coro_tasks:
            st = coro_statuses[coro_index]
            coro_index += 1
        else:
            st = tk.status()

        if (st == status) or (status == MirrorStatus.STATUS_DOWNLOAD and st not in STATUSES.values()):
            result.append(tk)

    return result


async def get_all_tasks(req_status: str, user_id):
    async with task_dict_lock:
        return await get_specific_tasks(req_status, user_id)


# ---------------------- File & Time Utilities ---------------------- #

def get_raw_file_size(size):
    num, unit = size.split()
    return int(float(num) * (1024 ** SIZE_UNITS.index(unit)))


def get_readable_file_size(size_in_bytes):
    if not size_in_bytes:
        return "0B"

    index = 0
    while size_in_bytes >= 1024 and index < len(SIZE_UNITS) - 1:
        size_in_bytes /= 1024
        index += 1

    return f"{size_in_bytes:.2f}{SIZE_UNITS[index]}"


def get_readable_time(seconds: int):
    periods = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]
    result = ""
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            result += f"{int(period_value)}{period_name}"
    return result


def get_raw_time(time_str: str) -> int:
    time_units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(int(value) * time_units[unit] for value, unit in findall(r"(\d+)([dhms])", time_str))


def time_to_seconds(time_duration):
    try:
        parts = time_duration.split(":")
        if len(parts) == 3:
            hours, minutes, seconds = map(float, parts)
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = map(float, parts)
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = float(parts[0])
        else:
            return 0
        return hours * 3600 + minutes * 60 + seconds
    except Exception:
        return 0


def speed_string_to_bytes(size_text: str):
    size_text = size_text.lower()
    if "k" in size_text:
        return float(size_text.split("k")[0]) * 1024
    if "m" in size_text:
        return float(size_text.split("m")[0]) * 1048576
    if "g" in size_text:
        return float(size_text.split("g")[0]) * 1073741824
    if "t" in size_text:
        return float(size_text.split("t")[0]) * 1099511627776
    if "b" in size_text:
        return float(size_text.split("b")[0])
    return 0


def get_progress_bar_string(pct: float) -> str:
    """
    Return a colorful progress bar using emojis based on percentage.
    """
    pct = max(0.0, min(100.0, float(pct)))  # Clamp to 0-100%
    total_blocks = 12

    filled_blocks = int((pct / 100) * total_blocks)

    colors = ["🟥", "🟧", "🟨", "🟩"]
    if pct <= 25:
        block = colors[0]
    elif pct <= 50:
        block = colors[1]
    elif pct <= 75:
        block = colors[2]
    else:
        block = colors[3]

    bar = block * filled_blocks + "⬜" * (total_blocks - filled_blocks)
    return f"[{bar}] {pct:.1f}%"
    
def premium_header():
    return (
        "<b>__Powered By</b>\n"
        "<a href='https://t.me/Radha_Rani_Backup'><b>POWERED BY ELITEBOTZ</b></a>\n\n"
    )

def status_icon(status):
    return {
        "Download": "⬇️",
        "Upload": "⬆️",
        "Seed": "🌱",
        "Extract": "🗜",
        "Archive": "📦",
        "QueueDl": "⏳",
        "QueueUp": "⏳",
        "Pause": "⏸",
        "Clone": "🧬",
        "Convert": "🎞",
        "FFmpeg": "🎬",
    }.get(status, "⚙️")


# ---------------------- Readable Message ---------------------- #

async def get_readable_message(sid, is_user, page_no=1, status="All", page_step=1):
    from ..telegram_helper.bot_commands import BotCommands  # Local import to fix circular import

    msg = premium_header()
    button = None

    tasks = await get_specific_tasks(status, sid if is_user else None)

    STATUS_LIMIT = Config.STATUS_LIMIT
    tasks_no = len(tasks)
    pages = (max(tasks_no, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT

    if page_no > pages:
        page_no = (page_no - 1) % pages + 1
        status_dict[sid]["page_no"] = page_no
    elif page_no < 1:
        page_no = pages - (abs(page_no) % pages)
        status_dict[sid]["page_no"] = page_no

    start = (page_no - 1) * STATUS_LIMIT

    for i, task in enumerate(tasks[start:start + STATUS_LIMIT], start=1):
        tstatus = (
            status if status != "All"
            else await task.status() if iscoroutinefunction(task.status)
            else task.status()
        )

        elapsed = time() - task.listener.message.date.timestamp()
        eta_seconds = get_raw_time(task.eta())
        total_time = elapsed + eta_seconds
        remaining_time = max(total_time - elapsed, 0)

        user = task.listener.message.from_user
        source = "Magnet" if task.listener.is_torrent else "Link"

        msg += (
            f"📊 <b>{escape(task.name())}</b>\n"
            f"{get_progress_bar_string(task.progress())}\n"
            f"┣ 🔄 <b>Process</b> : {task.progress()}%\n"
            f"┣ 📦 <b>Processed</b> : {task.processed_bytes()} of {task.size()}\n"
            f"┣ 📌 <b>Status</b> : {status_icon(tstatus)} {tstatus}\n"
            f"┣ ⚡ <b>Speed</b> : {task.speed()}\n"
            f"┣ ⏱️ <b>Time</b> : {task.eta()} of {get_readable_time(total_time)} "
            f"({get_readable_time(remaining_time)})\n"
        )

        if tstatus == MirrorStatus.STATUS_DOWNLOAD and (task.listener.is_torrent or task.listener.is_qbit):
            try:
                msg += f"┣ 🌱 <b>Seeders</b> : {task.seeders_num()} | <b>Leechers</b> : {task.leechers_num()}\n"
            except Exception:
                pass

        msg += (
            f"┣ 🛠️ <b>Engine</b> : {task.engine}\n"
            f"┣ 📥 <b>In Mode</b> : {task.listener.mode[0]}\n"
            f"┣ 📤 <b>Out Mode</b> : {task.listener.mode[1]}\n"
            f"┣ 👤 <b>User</b> : {escape(user.first_name)}\n"
            f"┣ 🆔 <b>ID</b> : {user.id}\n"
            f"┣ 🔗 <b>Source</b> : {source}\n"
        )

        msg += f"┗ 🛑 <b>Stop</b> : <i>/{BotCommands.CancelTaskCommand[1]}_{task.gid()}</i>\n\n"

    if not tasks:
        return None, None

    # ---------- BOT STATS ----------
    msg += (
        "⌬ <b><u>Bot Stats</u></b>\n"
        f"┣ 🖥️ CPU : {cpu_percent()}%\n"
        f"┣ 💾 RAM : {virtual_memory().percent}%\n"
        f"┣ 📂 Free : {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)} "
        f"[{round(100 - disk_usage(DOWNLOAD_DIR).percent, 1)}%]\n"
        f"┗ ⏳ Uptime : {get_readable_time(time() - bot_start_time)}\n"
    )

    # ---------- BUTTONS ----------
    buttons = ButtonMaker()
    if not is_user:
        buttons.data_button("📜 TStats", f"status {sid} ov", position="header")

    if tasks_no > STATUS_LIMIT:
        buttons.data_button("⬅️", f"status {sid} pre", position="header")
        buttons.data_button("➡️", f"status {sid} nex", position="header")

    if status != "All" or tasks_no > 20:
        for label, status_value in STATUSES.items():
            if status_value != status:
                buttons.data_button(label, f"status {sid} st {status_value}")

    buttons.data_button("♻️ Refresh", f"status {sid} ref", position="header")
    button = buttons.build_menu(8)

    return msg, button
