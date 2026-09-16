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

bot = commands.Bot(command_prefix=[".", "!", "?"], intents=intents, help_command=None)

BLACK = 0x000000
WARN_FILE = "warnings.json"
MUTE_FILE = "mutes.json"

# ==================== AUTO-MOD ====================
AUTO_MUTE_SECONDS = 36
AUTO_REPLIES = [
    "clm mồm như bãi rác v mà cũng dám mở ra nói, ra đường cẩn thận đấy",
    "dm nghĩ m là ai z hả, mồm lồn vcl, im đc k thì im",
    "lại lòi ra nói bậy nữa, biến về nhà chải cái mồm đi đã rồi chat",
    "kệ m, cái mồm thối hơn hầm cầu thế mà cũng dám chat",
    "vcl m này lại pha nữa rồi, tí nữa tả chốt đơn cho m bây giờ",
    "dm cả xóm nghe m nói xong ai cũng muốn ói, tục như đổ vỏ ve chai",
    "mồm để ăn cơm k m mà cứ nhả ra mấy câu lồn thế kia",
    "thôi m out khỏi server đi, cái trình chat này shame vcl",
    "clgt vậy m, nói câu nào tục câu đấy, ai dạy m nói chuyện thế",
    "dm nghe mà não tơ muốn xịt, cái mồm súc bằng nước lau sàn đi",
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

# ==================== JSON ====================
def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

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
        tpl_x = AV + 20 + GAP - tip[0]
        tpl_y = 20
        av_x, av_y = 20, max(10, tpl_y + tip[1] - AV // 2)
        W = tpl_x + tw + 10
        H = max(th + tpl_y, av_y + AV + 10, 300)
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        canvas.alpha_composite(avatar, (av_x, av_y))
        canvas.alpha_composite(tpl, (tpl_x, tpl_y))
    else:
        W, H = 1250, 400
        canvas = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        canvas.paste(avatar, (60, 60), avatar)
        draw = ImageDraw.Draw(canvas)
        tip, tail = (395, 340), (630, 110)
        handdrawn_line(draw, tail, tip)
        ang = math.atan2(tip[1]-tail[1], tip[0]-tail[0])
        for s in (1, -1):
            a = ang + math.pi + s * 0.5
            handdrawn_line(draw, tip, (tip[0]+90*math.cos(a), tip[1]+90*math.sin(a)))
        font = load_font(110)
        layer = Image.new("RGBA", (580, 220), (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((0, 0), ROAST_TEXT, font=font, fill="white")
        layer = layer.rotate(8, expand=True, resample=Image.BICUBIC)
        canvas.alpha_composite(layer, (660, 55))

    buf = io.BytesIO()
    canvas.convert("RGB").save(buf, format="PNG")
    buf.seek(0)
    return buf

async def send_with_roast(ctx, embed, member):
    try:
        avatar_bytes = await member.display_avatar.replace(format="png", size=256).read()
        buf = create_roast_image(avatar_bytes)
        file = discord.File(buf, filename="roast.png")
        embed.set_image(url="attachment://roast.png")
        await ctx.send(embed=embed, file=file)
    except Exception as e:
        print("Lỗi tạo ảnh:", e)
        await ctx.send(embed=embed)

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

    @discord.ui.button(label="Tu ngay", emoji="🔨", style=discord.ButtonStyle.danger)
    async def ban_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("clm k có quyền Ban Members mà cũng đòi ban ngta, mơ đi m", ephemeral=True)
        try:
            await self.member.ban(reason=f"đủ 5 warnings | bấm bởi {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message("dm bot thiếu quyền ban rồi, kệ m đi", ephemeral=True)
        except discord.NotFound:
            return await interaction.response.send_message("thằng này thấy sóng lớn chạy trước rồi, ban j giờ", ephemeral=True)

        warnings = load_json(WARN_FILE)
        gid, uid = str(interaction.guild_id), str(self.member.id)
        if gid in warnings and uid in warnings[gid]:
            del warnings[gid][uid]
            save_json(WARN_FILE, warnings)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            content=f"**{self.member}** chốt đơn bởi **{interaction.user}** — out khỏi server chớ ngoái đầu nhìn gì",
            embed=None, view=self)

        embed = discord.Embed(title="CHỐT ĐƠN — BAY MÀU RA KHỎI SERVER (WARN LIMIT)", color=BLACK, timestamp=discord.utils.utcnow())
        embed.add_field(name="Người bay", value=f"{self.member} ({self.member.id})", inline=False)
        embed.add_field(name="Người bấm", value=interaction.user.mention, inline=True)
        try:
            avatar_bytes = await self.member.display_avatar.replace(format="png", size=256).read()
            buf = create_roast_image(avatar_bytes)
            file = discord.File(buf, filename="roast.png")
            embed.set_image(url="attachment://roast.png")
            await interaction.channel.send(embed=embed, file=file)
        except Exception:
            await interaction.channel.send(embed=embed)

    @discord.ui.button(label="Xoa all w", emoji="🧹", style=discord.ButtonStyle.secondary)
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
            content=f"**{interaction.user}** tha chết cho **{self.member}** — tái phạm nx là chốt đơn luôn nhớ đấy",
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
    print(f"✅ Bot online: {bot.user}")
    await bot.change_presence(activity=discord.Game(name=".help | .m .b .w"))

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

                embed = discord.Embed(title="AUTO-MUTE — VỪA PHẠT VỪA CHỬI", color=BLACK, timestamp=discord.utils.utcnow())
                embed.add_field(name="Đối tượng", value=f"{member.mention} ({member})", inline=False)
                embed.add_field(name="Bị bịt mồm", value=f"**{AUTO_MUTE_SECONDS} giây**", inline=True)
                embed.add_field(name="Lý do", value="mồm thối, vả cho bịt rách luôn", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                await message.channel.send(content=f"{member.mention} {random.choice(AUTO_REPLIES)}", embed=embed)
            except discord.Forbidden:
                await message.channel.send("dm cho t quyền Timeout members đi rồi t xử nó mặt_nóng chứ để t ngắm nó à")

    await bot.process_commands(message)

# ==================== MUTE (.m) ====================
@bot.command(aliases=["m"])
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member = None, time: str = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="Sai cú pháp", description=".m @user 10m ly_do — tag thiếu thì mute cái j bay giờ", color=BLACK))
    seconds = parse_duration(time) if time else None
    if time and check_time_format(time) and seconds is None:
        return await ctx.send(embed=discord.Embed(title="Sai thời gian rồi m ơi",
            description="`1s`-`60s` • `1p`-`60p` • `1h`-`24h` • `1d`-`28d`", color=BLACK))
    if time and seconds is None:
        reason = f"{time} {reason}" if reason else time
        time = None
    if member == ctx.author:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="tự mute mình luôn hả m, não đâu mà xài vậy", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="mute bot làm j, bot có mồm đâu mà chửi bậy", color=BLACK))
    if member.guild_permissions.moderate_members and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta là mod mà đòi đụ ngang hàm, mơ đi", color=BLACK))

    if seconds is None:
        seconds = 28 * 86400

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    try:
        await member.timeout(until, reason=f"bởi {ctx.author} | {reason or 'k có lý do'}")
    except discord.Forbidden:
        return await ctx.send(embed=discord.Embed(title="BOT THIẾU QUYỀN",
            description="dm cho bot quyền Timeout Members với role cao hơn nạn nhân rồi hẵng nói", color=BLACK))

    mutes = load_json(MUTE_FILE)
    mutes.setdefault(str(ctx.guild.id), {})[str(member.id)] = {
        "until": until.isoformat(), "mod": str(ctx.author), "reason": reason or "k có lý do"}
    save_json(MUTE_FILE, mutes)

    try:
        dm = discord.Embed(title="MỒM M BỊ BỊT RỒI ĐÓ", color=BLACK)
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Thời lượng", value=f"{format_duration(seconds)} — đừng hỏi v sao, tự ngẫm đi", inline=True)
        dm.add_field(name="Lý do", value=reason or "k có lý do, chấm", inline=True)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="ĐÃ BỊT MỒM (TIMEOUT)", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="Đối tượng", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="Thời lượng", value=f"**{format_duration(seconds)}**", inline=True)
    embed.add_field(name="Hết mute lúc", value=until.strftime("%H:%M:%S %d/%m/%Y"), inline=True)
    embed.add_field(name="Lý do", value=reason or "k có lý do", inline=False)
    embed.add_field(name="Mod", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"ID: {member.id}")
    await send_with_roast(ctx, embed, member)

# ==================== UNMUTE (.um) ====================
@bot.command(aliases=["um"])
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="Sai cú pháp", description="tag thiếu thì unmute cái j", color=BLACK))
    if member.timed_out_until is None:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta có bị bịt mồm đâu mà đòi mở", color=BLACK))
    try:
        await member.timeout(None, reason=f"unmute bởi {ctx.author}")
    except discord.Forbidden:
        return await ctx.send(embed=discord.Embed(title="BOT THIẾU QUYỀN", color=BLACK))

    mutes = load_json(MUTE_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in mutes and uid in mutes[gid]:
        del mutes[gid][uid]
        save_json(MUTE_FILE, mutes)

    embed = discord.Embed(title="MỒM MỞ CÁI MỒM LỒN M RA ĐỂ A ĐÚT VÀO", color=BLACK)
    embed.add_field(name="Người dùng", value=member.mention, inline=True)
    embed.add_field(name="Tha chết bởi", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await ctx.send(embed=embed)

# ==================== MUTEINFO (.mi) ====================
@bot.command(aliases=["mi"])
async def muteinfo(ctx, member: discord.Member = None):
    member = member or ctx.author
    info = load_json(MUTE_FILE).get(str(ctx.guild.id), {}).get(str(member.id))

    if member.timed_out_until:
        until = member.timed_out_until
        total_sec = int((until - discord.utils.utcnow()).total_seconds())
        embed = discord.Embed(title="CÒN BAO LÂU MỚI MỞ MỒM", color=BLACK)
        embed.add_field(name="Người dùng", value=member.mention, inline=False)
        if total_sec > 0:
            hours, remainder = divmod(total_sec, 3600)
            minutes, secs = divmod(remainder, 60)
            days, hours = divmod(hours, 24)
            parts = []
            if days: parts.append(f"**{days}** ngày")
            if hours: parts.append(f"**{hours}** giờ")
            if minutes: parts.append(f"**{minutes}** phút")
            if secs: parts.append(f"**{secs}** giây")
            embed.add_field(name="Còn phải im", value=" ".join(parts), inline=True)
        embed.add_field(name="Hết bịt mồm lúc", value=until.strftime("%H:%M:%S %d/%m/%Y"), inline=True)
        if info:
            embed.add_field(name="Lý do", value=info.get("reason", "?"), inline=False)
            embed.add_field(name="Mod", value=info.get("mod", "?"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        return await ctx.send(embed=embed)

    if info:
        return await ctx.send(embed=discord.Embed(title="Hết mute lúc", description=info['until'][:19], color=BLACK))
    await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta có bị mute đâu mà hỏi hoài z", color=BLACK))

# ==================== BAN (.b) ====================
@bot.command(aliases=["b"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="Sai cú pháp", description="tag thiếu thì đụ ai ban bây giờ", color=BLACK))
    if member == ctx.author:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="tự ban mình luôn hả m, đi khám đi rồi hẵng làm mod", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="ban bot làm j, bot ngồi yên kilmington đụng ai", color=BLACK))
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta role cao hơn m mà đòi đụ, mơ đi", color=BLACK))
    await member.ban(reason=f"{reason} | Mod: {ctx.author}")

    try:
        dm = discord.Embed(title="M BỊ CHỐT ĐƠN RỒI ĐÓ", color=BLACK)
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Lý do", value=reason or "k có lý do — bay là bay luôn", inline=False)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="CHỐT ĐƠN — BAY MÀU (ĐÃ BAN)", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="Người dùng", value=f"{member} ({member.id})", inline=False)
    embed.add_field(name="Lý do", value=reason or "k có lý do", inline=True)
    embed.add_field(name="Mod", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_with_roast(ctx, embed, member)

# ==================== UNBAN (.ub) ====================
@bot.command(aliases=["ub"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int = None, *, reason=None):
    if user_id is None:
        embed = discord.Embed(title="UNBAN", color=BLACK)
        embed.description = "nhập ID ng cần unban:\n`.ub 123456789`"
        embed.add_field(name="k biết ID?", value="dùng `.banlist` coi danh sách banned + ID", inline=False)
        return await ctx.send(embed=embed)
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"bởi {ctx.author} | {reason or 'k có lý do'}")
        embed = discord.Embed(title="THA CHẾT — ĐÃ UNBAN", color=BLACK)
        embed.add_field(name="Người dùng", value=f"{user} ({user.id})", inline=False)
        embed.add_field(name="Mod", value=ctx.author.mention, inline=True)
        embed.set_thumbnail(url=user.display_avatar.url)
        await ctx.send(embed=embed)
    except discord.NotFound:
        await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta có bị ban đâu mà đòi tha, coi .banlist đi kkk", color=BLACK))

# ==================== BANLIST (.bl) ====================
@bot.command(aliases=["bl"])
@commands.has_permissions(ban_members=True)
async def banlist(ctx):
    bans = [b async for b in ctx.guild.bans()]
    if not bans:
        return await ctx.send(embed=discord.Embed(title="DANH SÁCH BAN", description="chưa có l ngu bị a chửi cả", color=BLACK))

    embed = discord.Embed(title=f"DANH SÁCH BỊ CHỐT ({len(bans)} thằng)", color=BLACK)
    for i, b in enumerate(bans[:25], 1):
        embed.add_field(name=f"{i}. {b.user}", value=f"ID: `{b.user.id}`", inline=True)
    if len(bans) > 25:
        embed.set_footer(text=f"...và {len(bans) - 25} thằng nx")
    embed.set_footer(text="lấy ID bỏ vào mồm r nhai nhai *.ub <ID> để tha chết")
    await ctx.send(embed=embed)

# ==================== WARN (.w) ====================
@bot.command(aliases=["w"])
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="Sai cú pháp", description="tag thiếu thì warn cái j", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="Sai rồi", description="warn bot làm j, bot chửi bậy đâu mà warn", color=BLACK))

    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, [])
    warnings[gid][uid].append({"reason": reason or "k có lý do", "mod": str(ctx.author)})
    save_json(WARN_FILE, warnings)
    count = len(warnings[gid][uid])

    try:
        dm = discord.Embed(title="M BỊ CẢNH BÁO RỒI ĐÓ NGHE CHƯA", color=BLACK, timestamp=discord.utils.utcnow())
        dm.add_field(name="Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="Lý do", value=reason or "k có lý do — tự ngẫm mà làm", inline=False)
        dm.add_field(name="Lần cảnh báo", value=f"**{count}/5**" + (" — nx là chốt đơn ra khỏi server luôn" if count >= 5 else " — đủ 5 lần là mod chốt đơn"), inline=True)
        dm.add_field(name="Mod", value=str(ctx.author), inline=True)
        if ctx.guild.icon:
            dm.set_thumbnail(url=ctx.guild.icon.url)
        await member.send(embed=dm)
        dm_status = "đã ib chửi riêng"
    except discord.Forbidden:
        dm_status = "đóng DM trốn rồi, trốn trời đc à"

    if count >= 5:
        embed = discord.Embed(
            title="Đủ 5 warn r ra ngoài để ý xe sì chia tí,
            description=f"{member.mention} gom đủ **{count}/5** warnings!\n\nmod quyuết",
            color=BLACK, timestamp=discord.utils.utcnow())
        embed.add_field(name="Người dùng", value=f"{member.mention} ({member})", inline=False)
        embed.add_field(name="Warn mới nhất", value=reason or "k có lý do", inline=False)
        embed.add_field(name="Mod", value=ctx.author.mention, inline=True)
        embed.add_field(name="DM", value=dm_status, inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)

        view = WarnActionView(member)
        view.message = await ctx.send(content=f"{ctx.author.mention} quyết đi, nó mồm thối lắm rồi đấy", embed=embed, view=view)
        return

    embed = discord.Embed(title="ĐÃ WARN — NHẮC NHỞ KỸ RỒI ĐÓ", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="Người dùng", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="Lý do", value=reason or "k có lý do", inline=True)
    embed.add_field(name="Lần", value=f"**{count}/5**", inline=True)
    embed.add_field(name="Mod", value=ctx.author.mention, inline=True)
    embed.add_field(name="DM", value=dm_status, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_with_roast(ctx, embed, member)

# ==================== WARNS (.ws) ====================
@bot.command(aliases=["ws", "warnings"])
async def warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_json(WARN_FILE).get(str(ctx.guild.id), {}).get(str(member.id), [])
    embed = discord.Embed(title=f"TIỀN ÁN TIỀN SỰ — {member.name}", color=BLACK)
    embed.set_thumbnail(url=member.display_avatar.url)
    if not data:
        embed.description = "sạch bong, chưa bị ai đụ gì cả"
    else:
        for i, w in enumerate(data, 1):
            embed.add_field(name=f"Warn #{i}", value=f"lý do: {w['reason']}\nmod: {w['mod']}", inline=False)
    await ctx.send(embed=embed)

# ==================== CLEARWARN (.cw) ====================
@bot.command(aliases=["cw"])
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="Sai cú pháp", description="tag thiếu thì xóa warn của ai giờ", color=BLACK))
    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in warnings and uid in warnings[gid]:
        del warnings[gid][uid]
        save_json(WARN_FILE, warnings)
        await ctx.send(embed=discord.Embed(title="XÓA SẠCH TIỀN ÁN", description=f"{member.mention} — tha lần này, tái phạm nx là chốt đơn luôn", color=BLACK))
    else:
        await ctx.send(embed=discord.Embed(title="Sai rồi", description="ngta sạch chưa từng bị warn, xóa cái j", color=BLACK))

# ==================== HELP ====================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="LỆNH BOT", color=BLACK)
    embed.add_field(name=".m @user <30s|10p|2h|1d> [lý do]", value="bịt mồm — k nhập thời gian = 28 ngày, ib riêng", inline=False)
    embed.add_field(name=".um @user", value="mở mồm lại phạm tiếp bố đánh chết con mm", inline=False)
    embed.add_field(name=".mi @user", value="còn nhiêu p cho l câm này v.", inline=False)
    embed.add_field(name=".b @user [lý do]", value="cút (ban)", inline=False)
    embed.add_field(name=".ub <ID>", value="tha chết (unban)", inline=False)
    embed.add_field(name=".banlist", value="danh sách của mấy l ngu + ID", inline=False)
    embed.add_field(name=".w @user [lý do]", value="warn", inline=False)
    embed.add_field(name=".ws [@user]", value="tiền án tiền sự", inline=False)
    embed.add_field(name=".cw @user", value="xóa sạch tiền án", inline=False)
    embed.add_field(name="Thời gian", value="`s` 1-60 • `p`/`m` 1-60 • `h` 1-24 • `d` 1-28", inline=False)
    embed.add_field(name="Auto-mod", value=f"mồm thối chat từ cấm → bịt mồm {AUTO_MUTE_SECONDS}s + chửi sấp mặt luôn", inline=False)
    embed.set_footer(text="prefix: . ! ? — ae xài subtree nhá")
    await ctx.send(embed=embed)

# ==================== LỖI ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(title="K ĐỦ QUYỀN", description="k có quyền mà đòi dùng lệnh này, mơ đi l óc ngu", color=BLACK))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=discord.Embed(title="BOT THIẾU QUYỀN",
            description="dm cho bot quyền (Moderate Members / Ban Members) rồi hẵng nói", color=BLACK))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=discord.Embed(title="Sai rồi", description="kiếm đâu ra thằng mặt lồn này v???", color=BLACK))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="THIẾU THÔNG TIN RỒI", description="gõ .help coi lại cách dùng rồi làm", color=BLACK))

# ==================== CHẠY ====================
open_port()

while True:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"⚠️ Bot lỗi: {e} — tự khởi động lại sau 5 giây...")
        time.sleep(5)
