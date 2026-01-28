from asyncio import gather, iscoroutinefunction
from html import escape
from re import findall
from time import time
from psutil import cpu_percent, disk_usage, virtual_memory

from ... import DOWNLOAD_DIR, bot_start_time, task_dict, task_dict_lock
from ...core.config_manager import Config

# =========================
# POWERED HEADER
# =========================
POWERED_BY_HEADER = (
    "<b>🚀 <a href='https://t.me/Radha_Rani_Backup'>POWERED BY ELITEBOTZ</a></b>\n"
    "<b>━━━━━━━━━━━━━━━━━━━━</b>\n\n"
)

def apply_locked_header(text: str) -> str:
    if text.startswith(POWERED_BY_HEADER):
        return text
    return POWERED_BY_HEADER + text

# =========================
# FILE SIZE UNITS
# =========================
SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]

# =========================
# TASK HELPERS
# =========================
def get_task_by_gid(gid):
    for task in task_dict.values():
        if task.gid() == gid:
            return task
    return None

def get_all_tasks():
    return list(task_dict.values())

async def get_specific_tasks(status, user_id):
    """
    Filter tasks by status and user_id
    """
    tasks = list(task_dict.values())
    if user_id:
        tasks = [t for t in tasks if t.listener.user_id == user_id]

    if status == "All":
        return tasks

    # Handle coroutine status functions
    coro_tasks = [t for t in tasks if iscoroutinefunction(t.status)]
    coro_status = await gather(*[t.status() for t in coro_tasks])

    result = []
    idx = 0
    for task in tasks:
        if task in coro_tasks:
            st = coro_status[idx]
            idx += 1
        else:
            st = task.status()
        if st == status:
            result.append(task)
    return result

# =========================
# STATUS DEFINITIONS
# =========================
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

# =========================
# ENGINE STATUS
# =========================
class EngineStatus:
    ARIA2 = "aria2"
    FFMPEG = "ffmpeg"
    PYROGRAM = "pyrogram"
    TORRENT = "torrent"
    YTDL = "youtube_dl"
    METADATA = "metadata"

    ALL_ENGINES = [ARIA2, FFMPEG, PYROGRAM, TORRENT, YTDL, METADATA]

# =========================
# HELPER FUNCTIONS
# =========================
def get_readable_file_size(size):
    if not size:
        return "0B"
    size = float(size)
    i = 0
    while size >= 1024 and i < len(SIZE_UNITS) - 1:
        size /= 1024
        i += 1
    return f"{size:.2f}{SIZE_UNITS[i]}"

def get_readable_time(seconds):
    seconds = int(seconds)
    d, seconds = divmod(seconds, 86400)
    h, seconds = divmod(seconds, 3600)
    m, s = divmod(seconds, 60)
    out = ""
    if d:
        out += f"{d}d"
    if h:
        out += f"{h}h"
    if m:
        out += f"{m}m"
    if s or not out:
        out += f"{s}s"
    return out

def get_raw_time(time_str):
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    return sum(int(v) * units[u] for v, u in findall(r"(\d+)([dhms])", time_str))

def time_to_seconds(time_str):
    """
    Convert time string like 1d2h3m4s -> total seconds
    """
    if not time_str:
        return 0
    units = {"d": 86400, "h": 3600, "m": 60, "s": 1}
    total = 0
    for value, unit in findall(r"(\d+)([dhms])", time_str):
        total += int(value) * units.get(unit, 0)
    return total

def get_progress_bar_string(pct):
    pct = float(str(pct).replace("%", ""))
    pct = min(max(pct, 0), 100)
    filled = int(pct // 8)
    empty = 12 - filled
    return f"[{'⬢' * filled}{'⬡' * empty}]"

# =========================
# TASK MESSAGE BUILDER (OPTIONAL)
# =========================
async def get_readable_message(sid, is_user, page_no=1, status="All"):
    """
    Generate readable Telegram message with all task info and stats
    """
    from ..telegram_helper.button_build import ButtonMaker
    from ..telegram_helper.bot_commands import BotCommands

    msg = ""
    buttons = ButtonMaker()

def speed_string_to_bytes(speed_str):
    if not speed_str:
        return 0
    try:
        speed_str = speed_str.lower().strip()
        value = float(speed_str.split()[0])
        if "kb" in speed_str:
            return value * 1024
        elif "mb" in speed_str:
            return value * 1024 ** 2
        elif "gb" in speed_str:
            return value * 1024 ** 3
    except:
        return 0
    return 0    

    async with task_dict_lock:
        tasks = await get_specific_tasks(status, sid if is_user else None)

    STATUS_LIMIT = Config.STATUS_LIMIT
    total = len(tasks)
    pages = (max(total, 1) + STATUS_LIMIT - 1) // STATUS_LIMIT
    page_no = max(1, min(page_no, pages))
    start = (page_no - 1) * STATUS_LIMIT

    for task in tasks[start:start + STATUS_LIMIT]:
        tstatus = await task.status() if iscoroutinefunction(task.status) else task.status()
        elapsed = int(time() - task.listener.message.date.timestamp())

        msg += (
            f"📊 <b>{escape(task.name())}</b>\n"
            f"│ {get_progress_bar_string(task.progress())}\n"
            f"│\n"
            f"├ 📈 <b>Process</b> : {task.progress()}%\n"
            f"├ 📦 <b>Processed</b> : {task.processed_bytes()} of {task.size()}\n"
            f"├ 📥 <b>Status</b> : {tstatus}...\n"
            f"├ ⚡ <b>Speed</b> : {task.speed()}\n"
            f"├ ⏱ <b>Time</b> : {task.eta()} of "
            f"{get_readable_time(elapsed + get_raw_time(task.eta()))}\n"
            f"│   ( {get_readable_time(elapsed)} )\n"
            f"│\n"
            f"├ 🛠 <b>Engine</b> : {task.engine}\n"
            f"├ 👤 <b>User</b> : {task.listener.message.from_user.id}\n"
            f"┖ ⛔ <b>Stop</b> : /{BotCommands.CancelTaskCommand[1]}_{task.gid()}\n\n"
        )

    if not msg:
        msg = "❌ <b>No Active Tasks</b>\n\n"

    # Bot stats
    msg += (
        "🤖 <b><u>Bot Stats</u></b>\n"
        f"│ 🖥 <b>CPU</b>: {cpu_percent()}%\n"
        f"│ 🧠 <b>RAM</b>: {virtual_memory().percent}%\n"
        f"│ 💾 <b>FREE</b>: {get_readable_file_size(disk_usage(DOWNLOAD_DIR).free)}\n"
        f"┖ ⏰ <b>UP Time</b>: {get_readable_time(time() - bot_start_time)}\n"
    )

    buttons.data_button("♻️ Refresh", f"status {sid} ref", position="header")
    if total > STATUS_LIMIT:
        buttons.data_button("<<", f"status {sid} pre", position="header")
        buttons.data_button(">>", f"status {sid} nex", position="header")

    for label, st in STATUSES.items():
        if st != status:
            buttons.data_button(label, f"status {sid} st {st}")

    msg = apply_locked_header(msg)
    return msg, buttons.build_menu(8)
