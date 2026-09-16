import discord
from discord.ext import commands
import json
import os
import re
import io
import math
import random
import threading
import time
import unicodedata
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==================== PORT CHO RENDER ====================
class PingHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write("Bot dang chay! OK".encode())

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()

    def log_message(self, *args):
        pass

def open_port():
    port = int(os.getenv("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), PingHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f"🌐 Port {port} đã mở — Render yên tâm rồi")
    except Exception as e:
        print("⚠️ Không mở được port:", e)

# ==================== TOKEN ====================
TOKEN = os.getenv("DISCORD_TOKEN") or "DÁN_TOKEN_VÀO_ĐÂY_NẾU_CHẠY_LOCAL"

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(
    command_prefix=[".", "!", "?"],
    intents=intents,
    help_command=None,
    case_insensitive=True,
    allowed_mentions=discord.AllowedMentions(everyone=False, roles=False),
)

BLACK = 0x000000
DARKER = 0x0A0A0A
WARN_FILE = "warnings.json"
MUTE_FILE = "mutes.json"

# ==================== AUTO-MOD ====================
AUTO_MUTE_SECONDS = 36
AUTO_REPLIES = [
    "dm mồm như bãi phốt v mà cũng dám mở ra nói, ra đường cẩn thận đấy",
    "ngu như con bò mà mồm thì tục như con đĩ, im mồm lại cho cha nhờ",
    "clm đẻ ra mà k ai dạy nói chuyện hả con, mồm dơ vcl ra",
    "óc chó vừa thôi, mặt phò mà mồm còn thối hơn bãi rác",
    "nói câu nào tục câu đấy, cút ra chỗ khác chat cho cha nhờ",
    "thế hệ sau mà ngu thế này thì cộng đồng tiêu thật rồi",
    "mồm như hố xí k nắp đậy, ai nghe mà k đỏ mặt hông",
    "sì ke thật, mồm rộng vậy mà óc bé như hạt bụi",
    "ôn lại cái mồm cái lưỡi đi con, nói chuyện như gà mắc tóc",
    "ngu + tục = combo m đấy, chúc mừng ha",
    "xấu và dốt đi chung với nhau như m là hiếm lắm đấy",
    "dm nguy hiểm cái mồm chứ não trống rỗng, về làm lại cái đầu đi",
    "con đĩ lồn m tu luyện mấy chục năm cũng đéo bằng bố m đâu, nói lắm v??",
]

BAD_WORDS = [
    "nhutgay", "nhutga", "nhatgay", "nutgay",
    "nhutbede", "nhutbd", "nhutpede", "nhutpd",
    "nhutlgbt", "nhutbong", "gaynhut",
]

ROAST_TEXT = "is stupid"
TEMPLATE_FILE = "arrow.png"
TEMPLATE_URL = "https://i.pinimg.com/1200x/d0/ef/e9/d0efe9560ad8d16e47643939024025c6.jpg"
_tpl_cache = None
_avatar_cache = {}
_last_msg = {}

# ==================== JSON ====================
def load_json(path):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except (json.JSONDecodeError, OSError):
        pass
    return {}

def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        os.replace(tmp, path)
    except OSError:
        pass

# ==================== CHUẨN HÓA CHỮ ====================
def normalize_text(text):
    text = unicodedata.normalize("NFD", text.lower())
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[\s\._\-*/\\]+", "", text)

# ==================== BANNER MŨI TÊN ====================
def download_template():
    if os.path.exists(TEMPLATE_FILE):
        return
    try:
        req = urllib.request.Request(TEMPLATE_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r, open(TEMPLATE_FILE, "wb") as f:
            f.write(r.read())
        print("✅ Đã tải banner mũi tên")
    except Exception as e:
        print("⚠️ Không tải được banner → tự vẽ:", e)

def load_font(size):
    for path in ["Caveat-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                 "C:/Windows/Fonts/Inkfree.ttf", "C:/Windows/Fonts/comici.ttf",
                 "/System/Library/Fonts/Supplemental/MarkerFelt.ttc"]:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

def handdrawn_line(draw, start, end, width=8):
    for _ in range(2):
        pts = []
        for i in range(21):
            t = i / 20
            pts.append((start[0] + (end[0]-start[0])*t + random.uniform(-3,3),
                        start[1] + (end[1]-start[1])*t + random.uniform(-3,3)))
        draw.line(pts, fill="white", width=width, joint="curve")

def get_template():
    global _tpl_cache
    if _tpl_cache is not None:
        return _tpl_cache
    if not os.path.exists(TEMPLATE_FILE):
        return None
    tpl = Image.open(TEMPLATE_FILE).convert("RGBA")
    if tpl.width > 1200:
        tpl = tpl.resize((1200, int(tpl.height * 1200 / tpl.width)))
    mask = tpl.convert("L").point(lambda v: 255 if v > 40 else 0)
    tpl.putalpha(mask)
    _tpl_cache = tpl
    return tpl

def create_roast_image(avatar_bytes):
    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
    avatar = ImageOps.fit(avatar, (280, 280))

    tpl = get_template()
    if tpl:
        tw, th = tpl.size
        tip = (int(tw * 0.11), int(th * 0.81))
        GAP, AV = 25, 280
        AV_X = 60
        tpl_x = AV_X + AV + GAP - tip[0]
        tpl_y = 20
        av_x, av_y = AV_X, max(10, tpl_y + tip[1] - AV // 2)
        W = tpl_x + tw + 10
        H = max(th + tpl_y, av_y + AV + 10, 300)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        canvas.alpha_composite(avatar, (av_x, av_y))
        canvas.alpha_composite(tpl, (tpl_x, tpl_y))
    else:
        W, H = 1250, 400
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        canvas.paste(avatar, (100, 60), avatar)
        draw = ImageDraw.Draw(canvas)
        tip, tail = (435, 340), (670, 110)
        handdrawn_line(draw, tail, tip)
        ang = math.atan2(tip[1]-tail[1], tip[0]-tail[0])
        for s in (1, -1):
            a = ang + math.pi + s * 0.5
            handdrawn_line(draw, tip, (tip[0]+90*math.cos(a), tip[1]+90*math.sin(a)))
        font = load_font(110)
        layer = Image.new("RGBA", (580, 220), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((0, 0), ROAST_TEXT, font=font, fill="white")
        layer = layer.rotate(8, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(layer, (700, 55))

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

async def get_avatar(member):
    key = (member.id, str(member.display_avatar))
    now = time.time()
    if key in _avatar_cache and now - _avatar_cache[key][1] < 600:
        return _avatar_cache[key][0]
    data = await member.display_avatar.replace(format="png", size=256).read()
    _avatar_cache[key] = (data, now)
    if len(_avatar_cache) > 200:
        oldest = min(_avatar_cache, key=lambda k: _avatar_cache[k][1])
        _avatar_cache.pop(oldest, None)
    return data

async def send_with_roast(ctx, embed, member):
    try:
        avatar_bytes = await get_avatar(member)
        buf = create_roast_image(avatar_bytes)
        file = discord.File(buf, filename="roast.png")
        embed.set_image(url="attachment://roast.png")
        await ctx.send(embed=embed, file=file)
    except Exception as e:
        print("Lỗi tạo ảnh:", e)
        await ctx.send(embed=embed)

# ==================== EMBED ====================
def base_embed(title: str, description: str = None, member: discord.Member = None):
    """Embed nền đen, không emoji, header tối giản kiểu hồ sơ"""
    e = discord.Embed(title=title, description=description, color=BLACK, timestamp=discord.utils.utcnow())
    if member:
        e.set_author(name=str(member), icon_url=member.display_avatar.url)
    return e

def progress_bar(current: int, total: int, length: int = 10):
    filled = int(length * current / total)
    return "▓" * filled + "░" * (length - filled)

def time_left_embed_style(total_sec: int):
    days, rem = divmod(total_sec, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days: parts.append(f"**{days}** ngày")
    if hours: parts.append(f"**{hours}** giờ")
    if minutes: parts.append(f"**{minutes}** phút")
    if secs: parts.append(f"**{secs}** giây")
    return " ".join(parts) if parts else "**0** giây"

def footer_cmd(ctx):
    return f"{ctx.prefix}{ctx.command} • {ctx.guild.name}" if ctx.guild else f"{ctx.prefix}{ctx.command}"

# ==================== THỜI GIAN ====================
def check_time_format(text):
    return bool(re.fullmatch(r"(\d+)([spmhd])", text.lower().strip()))

def parse_duration(text):
    m = re.fullmatch(r"(\d+)([spmhd])", text.lower().strip())
    if not m:
        return None
    a, u = int(m.group(1)), m.group(2)
    if u == "s":  return a if 1 <= a <= 60 else None
    if u in ("p", "m"): return a * 60 if 1 <= a <= 60 else None
    if u == "h":  return a * 3600 if 1 <= a <= 24 else None
    if u == "d":  return a * 86400 if 1 <= a <= 28 else None
    return None

def format_duration(s):
    if s < 60: return f"{s} giây"
    if s < 3600: return f"{s//60} phút"
    if s < 86400: return f"{s//3600} giờ"
    return f"{s//86400} ngày"

# ==================== NÚT BAN / XÓA WARN ====================
class WarnActionView(discord.ui.View):
    def __init__(self, member: discord.Member):
        super().__init__(timeout=600)
        self.member = member
        self.message = None

    @discord.ui.button(label="Tu ngay", style=discord.ButtonStyle.danger)
    async def ban_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("clm k có quyền Ban Members mà cũng đòi ban ngta, mơ đi m", ephemeral=True)
        try:
            await self.member.ban(reason=f"đủ 5 warnings | bấm bởi {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message("dm bot thiếu quyền ban rồi, kệ m đi", ephemeral=True)
        except discord.NotFound:
            return await interaction.response.send_message("thằng này thấy sóng to chạy trước rồi, ban j giờ", ephemeral=True)

        warnings = load_json(WARN_FILE)
        gid, uid = str(interaction.guild_id), str(self.member.id)
        if gid in warnings and uid in warnings[gid]:
            del warnings[gid][uid]
            save_json(WARN_FILE, warnings)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"**{self.member}** chốt đơn bởi **{interaction.user}** — out khỏi server chớ ngoái đầu",
            embed=None, view=self)

        embed = base_embed("CÚT — BAY MÀU (WARN LIMIT)", member=self.member)
        embed.color = DARKER
        embed.description = f"**{self.member.mention}** vừa bị đuổi khỏi server. ID: `{self.member.id}`"
        embed.add_field(name="Người bấm", value=interaction.user.mention, inline=True)
        try:
            avatar_bytes = await get_avatar(self.member)
            buf = create_roast_image(avatar_bytes)
            file = discord.File(buf, filename="roast.png")
            embed.set_image(url="attachment://roast.png")
            await interaction.channel.send(embed=embed, file=file)
        except Exception:
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Xoa all w", style=discord.ButtonStyle.secondary)
    async def clear_warns(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_messages:
            return await interaction.response.send_message("cần quyền Manage Messages mới tha đc, m là ai mà đòi tha", ephemeral=True)
        warnings = load_json(WARN_FILE)
        gid, uid = str(interaction.guild_id), str(self.member.id)
        if gid in warnings and uid in warnings[gid]:
            del warnings[gid][uid]
            save_json(WARN_FILE, warnings)
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"**{interaction.user}** tha chết cho **{self.member}** — tái phạm nx là cút đéo nói nhiều",
            embed=None, view=self)

    async def on_timeout(self):
        try:
            for item in self.children:
                item.disabled = True
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    download_template()
    print(f"✅ Bot online: {bot.user} — {len(bot.guilds)} server")
    try:
        await bot.change_presence(activity=discord.Game(name=".help | .m .b .w"))
    except Exception:
        pass

# ==================== AUTO-MOD ====================
@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        await bot.process_commands(message)
        return

    n = normalize_text(message.content)
    if any(word in n for word in BAD_WORDS):
        member = message.author
        if member.guild_permissions.moderate_members or member.guild_permissions.administrator:
            await bot.process_commands(message)
            return

        already_muted = member.timed_out_until and member.timed_out_until > discord.utils.utcnow()

        try:
            await message.delete()
        except (discord.Forbidden, discord.NotFound):
            pass

        if not already_muted:
            until = discord.utils.utcnow() + timedelta(seconds=AUTO_MUTE_SECONDS)
            try:
                await member.timeout(until, reason=f"auto-mod: mồm thối chat tại #{message.channel}")

                mutes = load_json(MUTE_FILE)
                mutes.setdefault(str(message.guild.id), {})[f"automod_{member.id}"] = {
                    "until": until.isoformat(),
                    "mod": "AUTO-MOD",
                    "reason": f"mồm thối chat tại #{message.channel}"}
                save_json(MUTE_FILE, mutes)

                e = base_embed("AUTO-MUTE — BỊT MỒM", member=member)
                e.description = f"{member.mention} vừa ăn timeout vì mồm thối"
                e.add_field(name="Thời gian", value=f"**{AUTO_MUTE_SECONDS} giây**", inline=True)
                e.add_field(name="Lý do", value="nói bậy ở kênh chat, bịt lại cho đỡ thúi server", inline=True)
                e.add_field(name="ID", value=f"`{member.id}`", inline=True)
                e.set_thumbnail(url=member.display_avatar.url)
                await message.channel.send(content=f"{member.mention} {random.choice(AUTO_REPLIES)}", embed=e)
                print(f"Auto-mute {member} ({AUTO_MUTE_SECONDS}s)")
            except discord.Forbidden:
                await message.channel.send("dm cho bot quyền Timeout members đi rồi bot xử nó, để bot ngắm nó à")

    await bot.process_commands(message)

# ==================== ANTI-SPAM ====================
async def cooldown_check(ctx):
    key = (ctx.author.id, ctx.command.qualified_name)
    now = time.time()
    last = _last_msg.get(key, 0)
    if now - last < 3:
        raise commands.CommandOnCooldown(None, 3 - (now - last))
    _last_msg[key] = now
    return True

bot.add_check(cooldown_check)

# ==================== MUTE (.m) ====================
@bot.command(aliases=["m"])
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member = None, time: str = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=base_embed("SAI CÚ PHÁP", ".m @user 10m lý_do — tag thiếu thì mute cái gì con", member=ctx.author))
    seconds = parse_duration(time) if time else None
    if time and check_time_format(time) and seconds is None:
        return await ctx.send(embed=base_embed("SAI THỜI GIAN", "`1s`-`60s` • `1p`-`60p` • `1h`-`24h` • `1d`-`28d`", member=ctx.author))
    if time and seconds is None:
        reason = f"{time} {reason}" if reason else time
        time = None
    if member == ctx.author:
        return await ctx.send(embed=base_embed("NGU VCL", "tự mute mình luôn hả m, não đâu mà xài vậy", member=ctx.author))
    if member.bot:
        return await ctx.send(embed=base_embed("K ĐỔI RỒI", "mute bot làm gì, bot có mồm đâu mà chửi bậy như m", member=ctx.author))
    if member.guild_permissions.moderate_members and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=base_embed("MƠ ĐI", "ngta là mod mà đòi đụ ngang hàm, sì ke thật", member=ctx.author))

    if seconds is None:
        seconds = 28 * 86400

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    try:
        await member.timeout(until, reason=f"bởi {ctx.author} | {reason or 'k có lý do'}")
    except discord.Forbidden:
        return await ctx.send(embed=base_embed("BOT THIẾU QUYỀN", "đụ má cho bot quyền Timeout Members với role cao hơn nạn nhân rồi hẵng nói", member=ctx.author))

    mutes = load_json(MUTE_FILE)
    mutes.setdefault(str(ctx.guild.id), {})[str(member.id)] = {
        "until": until.isoformat(), "mod": str(ctx.author), "reason": reason or "k có lý do"}
    save_json(MUTE_FILE, mutes)

    try:
        dm = base_embed("MỒM M BỊ BỊT RỒI ĐÓ", member=ctx.author)
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Thời lượng", value=f"**{format_duration(seconds)}**", inline=True)
        dm.add_field(name="Lý do", value=reason or "k có lý do, chấm", inline=True)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        dm.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    e = base_embed("ĐÃ BỊT MỒM (TIMEOUT)", member=member)
    e.color = DARKER
    e.description = (
        f"{member.mention} mồm đã bị bịt\n"
        f"Hết mute lúc **{until.strftime('%H:%M:%S %d/%m/%Y')}**"
    )
    e.add_field(name="Thời lượng", value=f"**{format_duration(seconds)}**", inline=True)
    e.add_field(name="Lý do", value=reason or "k có lý do", inline=True)
    e.add_field(name="Mod", value=ctx.author.mention, inline=True)
    e.add_field(name="ID", value=f"`{member.id}`", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
    await send_with_roast(ctx, e, member)

# ==================== UNMUTE (.um) ====================
@bot.command(aliases=["um"])
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=base_embed("SAI CÚ PHÁP", "tag thiếu thì unmute cái gì con", member=ctx.author))
    if member.timed_out_until is None:
        return await ctx.send(embed=base_embed("NGU VẬY", "ngta có bị bịt mồm đâu mà đòi mở", member=ctx.author))
    try:
        await member.timeout(None, reason=f"unmute bởi {ctx.author}")
    except discord.Forbidden:
        return await ctx.send(embed=base_embed("BOT THIẾU QUYỀN", "thiếu quyền Timeout Members", member=ctx.author))

    mutes = load_json(MUTE_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in mutes and uid in mutes[gid]:
        del mutes[gid][uid]
        save_json(MUTE_FILE, mutes)

    e = base_embed("MỒM MỞ LẠI RỒI", "nói chuyện chừa chỉ nhé, tái phạm là lại ăn", member=member)
    e.add_field(name="Người dùng", value=member.mention, inline=True)
    e.add_field(name="Tha chết bởi", value=ctx.author.mention, inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=e)

# ==================== MUTEINFO (.mi) ====================
@bot.command(aliases=["mi"])
async def muteinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    info = load_json(MUTE_FILE).get(str(ctx.guild.id), {}).get(str(member.id))

    if member.timed_out_until:
        until = member.timed_out_until
        total_sec = int((until - discord.utils.utcnow()).total_seconds())
        e = base_embed("CÒN BAO LÂU MỚI MỞ MỒM", member=member)
        if total_sec > 0:
            e.add_field(name="Còn phải im", value=time_left_embed_style(total_sec), inline=True)
        e.add_field(name="Hết mute lúc", value=until.strftime("%H:%M:%S %d/%m/%Y"), inline=True)
        if info:
            e.add_field(name="Lý do", value=info.get("reason", "?"), inline=False)
            e.add_field(name="Mod", value=info.get("mod", "?"), inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
        return await ctx.send(embed=e)

    if info:
        return await ctx.send(embed=base_embed("Hết mute lúc", info['until'][:19], member=member))
    return await ctx.send(embed=base_embed("SAI RỒI", "ngta có bị mute đâu mà hỏi hoài z", member=member))

# ==================== BAN (.b) ====================
@bot.command(aliases=["b"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=base_embed("SAI CÚ PHÁP", "tag thiếu thì đụ ai ban bây giờ con", member=ctx.author))
    if member == ctx.author:
        return await ctx.send(embed=base_embed("NGU RA MẶT", "tự ban mình luôn hả con, đi khám đi rồi hẵng làm mod", member=ctx.author))
    if member.bot:
        return await ctx.send(embed=base_embed("NGU VCL", "ban bot làm cái lồn gì, bot ngồi im k đụng ai cả", member=ctx.author))
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=base_embed("MƠ ĐI CON PHÒ", "ngta role cao hơn m mà định đụ, ngu k biết đường đâu", member=ctx.author))
    await member.ban(reason=f"{reason} | Mod: {ctx.author}")

    try:
        dm = base_embed("M BỊ CHỐT ĐƠN RỒI", member=ctx.author)
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Lý do", value=reason or "k có lý do — bay là bay luôn", inline=False)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    e = base_embed("CHỐT ĐƠN — BAY MÀU (ĐÃ BAN)", member=member)
    e.color = DARKER
    e.description = f"{member.mention} đã bị đuổi khỏi server vĩnh viễn"
    e.add_field(name="Lý do", value=reason or "k có lý do", inline=True)
    e.add_field(name="Mod", value=ctx.author.mention, inline=True)
    e.add_field(name="ID", value=f"`{member.id}`", inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
    await send_with_roast(ctx, e, member)

# ==================== UNBAN (.ub) ====================
@bot.command(aliases=["ub"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int = None, *, reason=None):
    if user_id is None:
        e = base_embed("UNBAN", "nhập ID ng cần unban:\n`.ub 123456789`", member=ctx.author)
        e.add_field(name="k biết ID?", value="dùng `.banlist` coi danh sách banned + ID", inline=False)
        return await ctx.send(embed=e)
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"bởi {ctx.author} | {reason or 'k có lý do'}")
        e = base_embed("THA CHẾT — ĐÃ UNBAN", member=user)
        e.add_field(name="Người dùng", value=f"{user.mention}\n`{user.id}`", inline=False)
        e.add_field(name="Mod", value=ctx.author.mention, inline=True)
        e.set_thumbnail(url=user.display_avatar.url)
        e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)
    except discord.NotFound:
        return await ctx.send(embed=base_embed("SAI RỒI CON", "ngta có bị ban đâu mà đòi tha, coi .banlist đi", member=ctx.author))

# ==================== BANLIST (.bl) ====================
@bot.command(aliases=["bl"])
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    bans = [b async for b in ctx.guild.bans()]
    if not bans:
        return await ctx.send(embed=base_embed("DANH SÁCH BAN", "chưa đụ thằng nào cả, server yên bình vãi", member=ctx.author))

    e = base_embed(f"DANH SÁCH BỊ CHỐT ({len(bans)} thằng)", member=ctx.author)
    for i, b in enumerate(bans[:25], 1):
        e.add_field(name=f"{i}. {b.user}", value=f"`{b.user.id}`", inline=True)
    if len(bans) > 25:
        e.set_footer(text=f"...và {len(bans) - 25} thằng nx")
    e.set_footer(text="lấy ID bỏ vào .ub <ID> để tha chết")
    await ctx.send(embed=e)

# ==================== WARN (.w) ====================
@bot.command(aliases=["w"])
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=base_embed("SAI CÚ PHÁP", "tag thiếu thì warn cái lồn gì con", member=ctx.author))
    if member.bot:
        return await ctx.send(embed=base_embed("NGU VẬY", "warn bot làm j, bot mồm sạch hơn m nghìn lần", member=ctx.author))

    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, [])
    warnings[gid][uid].append({"reason": reason or "k có lý do", "mod": str(ctx.author)})
    save_json(WARN_FILE, warnings)
    count = len(warnings[gid][uid])

    try:
        dm = base_embed("BỊ CẢNH BÁO RỒI ĐÓ NGHE CHƯA", member=ctx.author)
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Lý do", value=reason or "k có lý do — tự ngẫm mà làm", inline=False)
        dm.add_field(name="Lần cảnh báo", value=f"{progress_bar(count, 5)} `{count}/5`", inline=False)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        if ctx.guild.icon:
            dm.set_thumbnail(url=ctx.guild.icon.url)
        await member.send(embed=dm)
        dm_status = "đã ib chửi riêng"
    except discord.Forbidden:
        dm_status = "đóng DM trốn rồi, trốn trời đc à"

    if count >= 5:
        e = base_embed("ĐỦ 5 WARN — RA NGOÀI ĐỂ Ý XE ĐẤY", member=member)
        e.description = (
            f"{member.mention} gom đủ **{count}/5** warnings\n"
            f"{progress_bar(count, 5)}\n\n"
            "mod quyết đi k thì nó lại ló mặt nx đó"
        )
        e.add_field(name="Warn mới nhất", value=reason or "k có lý do", inline=False)
        e.add_field(name="Mod", value=ctx.author.mention, inline=True)
        e.add_field(name="DM", value=dm_status, inline=True)
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)

        view = WarnActionView(member)
        view.message = await ctx.send(content=f"{ctx.author.mention} quyết đi, mồm như cái l ngta", embed=e, view=view)
        return

    e = base_embed("ĐÃ WARN", member=member)
    e.description = f"{member.mention} vừa ăn 1 cảnh báo"
    e.add_field(name="Tiến độ", value=f"{progress_bar(count, 5)} `{count}/5`", inline=False)
    e.add_field(name="Lý do", value=reason or "k có lý do", inline=True)
    e.add_field(name="Mod", value=ctx.author.mention, inline=True)
    e.add_field(name="DM", value=dm_status, inline=True)
    e.set_thumbnail(url=member.display_avatar.url)
    e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
    await send_with_roast(ctx, e, member)

# ==================== WARNS (.ws) ====================
@bot.command(aliases=["ws", "warnings"])
async def warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_json(WARN_FILE).get(str(ctx.guild.id), {}).get(str(member.id), [])
    e = base_embed("TIỀN ÁN TIỀN SỰ", member=member)
    e.set_thumbnail(url=member.display_avatar.url)
    if not data:
        e.description = "sạch bong, chưa bị ai đụ gì cả"
    else:
        e.description = f"{member.mention} đang mang `{len(data)}/5` cảnh báo\n{progress_bar(len(data), 5)}"
        for i, w in enumerate(data, 1):
            e.add_field(name=f"Warn #{i}", value=f"lý do: {w['reason']}\nmod: {w['mod']}", inline=False)
    e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
    await ctx.send(embed=e)

# ==================== CLEARWARN (.cw) ====================
@bot.command(aliases=["cw"])
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=base_embed("SAI CÚ PHÁP", "tag thiếu thì xóa warn của ai giờ", member=ctx.author))
    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in warnings and uid in warnings[gid]:
        del warnings[gid][uid]
        save_json(WARN_FILE, warnings)
        e = base_embed("XÓA SẠCH TIỀN ÁN", f"{member.mention} — tha lần này, tái phạm nx là cút con mẹ m ln", member=member)
        e.set_thumbnail(url=member.display_avatar.url)
        e.set_footer(text=footer_cmd(ctx), icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=e)
    else:
        return await ctx.send(embed=base_embed("SAI RỒI", "ngta sạch chưa từng bị warn, xóa cái gì", member=ctx.author))

# ==================== HELP ====================
@bot.command()
async def help(ctx):
    e = base_embed("LỆNH BOT", None, member=ctx.author)
    e.description = (
        "**Moderation** — mute, ban, warn đầy đủ\n"
        "**Auto-mod** — chặn từ cấm tự động\n"
        "*Gõ lệnh với prefix `.`, `!` hoặc `?`*"
    )
    e.add_field(name=".m @user <30s|10p|2h|1d> [lý do]", value="bịt mồm — k nhập thời gian = 28 ngày, ib riêng", inline=False)
    e.add_field(name=".um @user", value="mở mồm lại, phạm tiếp bố đụ chết con mm", inline=False)
    e.add_field(name=".mi @user", value="còn nhiêu lâu cái mồm mới mở dc", inline=False)
    e.add_field(name=".b @user [lý do]", value="chốt đơn (ban)", inline=False)
    e.add_field(name=".ub <ID>", value="tha chết (unban)", inline=False)
    e.add_field(name=".banlist", value="danh sách mấy con ngu bị chốt + ID", inline=False)
    e.add_field(name=".w @user [lý do]", value="warn + ib riêng, đủ 5 lần hiện NÚT", inline=False)
    e.add_field(name=".ws [@user]", value="tiền án tiền sự", inline=False)
    e.add_field(name=".cw @user", value="xóa sạch tiền án", inline=False)
    e.add_field(name="Thời gian", value="`s` 1-60 • `p`/`m` 1-60 • `h` 1-24 • `d` 1-28", inline=False)
    e.add_field(name="Auto-mod", value=f"chat từ cấm → bịt mồm {AUTO_MUTE_SECONDS}s + chửi sấp mặt", inline=False)
    e.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)
    e.set_footer(text=f"{ctx.guild.name} • prefix: . ! ?", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
    await ctx.send(embed=e)

# ==================== LỖI ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        return await ctx.send(embed=base_embed("TỪ TỪ THÔI CON", f"spam lệnh vậy buồn cười thật, đợi **{error.retry_after:.1f}s** nx", member=ctx.author), delete_after=5)
    if isinstance(error, commands.MissingPermissions):
        return await ctx.send(embed=base_embed("K ĐỦ QUYỀN ĐÂY CON", "k có quyền mà đòi dùng lệnh, mơ đi", member=ctx.author))
    if isinstance(error, commands.BotMissingPermissions):
        return await ctx.send(embed=base_embed("BOT THIẾU QUYỀN", "đụ má cho bot quyền (Moderate Members / Ban Members) rồi hẵng sai nó làm", member=ctx.author))
    if isinstance(error, commands.MemberNotFound):
        return await ctx.send(embed=base_embed("SAI RỒI CON", "kiếm đâu ra thằng mặt lồn này v???, server k có ai như z", member=ctx.author))
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        return await ctx.send(embed=base_embed("THIẾU THÔNG TIN RỒI CON LỒN", "gõ .help coi lại cách dùng rồi làm", member=ctx.author))
    print(f"Lỗi lệnh {ctx.command}: {error}")

# ==================== CHẠY ====================
open_port()

while True:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Bot lỗi: {e} — tự khởi động lại sau 5 giây...")
        time.sleep(5)
