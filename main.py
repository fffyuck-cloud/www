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

# ==================== AUTO-MOD CẤU HÌNH ====================
AUTO_MUTE_SECONDS = 36                      # thời gian auto mute khi chat cấm
AUTO_REPLY = "ngu ngu cc 🤡"                # câu mỉa khi bị auto mute
BAD_WORDS = ["nhutgay", "nhutga"]           # biến thể từ cấm (không dấu, không khoảng trắng)

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

# ==================== CHUẨN HÓA CHỮ (BẮT TRÈO) ====================
def normalize_text(text):
    """Bỏ dấu tiếng Việt, bỏ khoảng trắng/ký tự chèn → bắt 'Nhựt ga y', 'nhut-gay'..."""
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
    """s:1-60 | p/m:1-60 | h:1-24 | d:1-28 (Discord timeout giới hạn 28 ngày)"""
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

# ==================== SỰ KIỆN ====================
@bot.event
async def on_ready():
    download_template()
    print(f"✅ Bot online: {bot.user}")
    await bot.change_presence(activity=discord.Game(name=".help | .m .b .w"))

# ==================== AUTO-MOD: CHAT TỪ CẤM = MUTE 36s + MỈA ====================
@bot.event
async def on_message(message):
    if message.author.bot or message.guild is None:
        await bot.process_commands(message)
        return

    n = normalize_text(message.content)
    if any(word in n for word in BAD_WORDS):
        member = message.author

        # Mod/admin khỏi bị auto mute
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
                await member.timeout(until, reason=f"Auto-mod: chat từ cấm tại #{message.channel}")

                mutes = load_json(MUTE_FILE)
                mutes.setdefault(str(message.guild.id), {})[f"automod_{member.id}"] = {
                    "until": until.isoformat(),
                    "mod": "AUTO-MOD",
                    "reason": f"Chat từ cấm tại #{message.channel}"}
                save_json(MUTE_FILE, mutes)

                embed = discord.Embed(title="🤖 AUTO-MUTE", color=BLACK,
                                      timestamp=discord.utils.utcnow())
                embed.add_field(name="👤 Người dùng", value=f"{member.mention} ({member})", inline=False)
                embed.add_field(name="⏱️ Thời lượng", value=f"**{AUTO_MUTE_SECONDS} giây**", inline=True)
                embed.add_field(name="📄 Lý do", value="Chat từ cấm 🤡", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                await message.channel.send(content=f"{member.mention} **{AUTO_REPLY}**", embed=embed)
                print(f"🤖 Auto-mute {member} trong {AUTO_MUTE_SECONDS}s")
            except discord.Forbidden:
                await message.channel.send("⚠️ Bot thiếu quyền **Timeout members** để auto-mute!")

    await bot.process_commands(message)   # QUAN TRỌNG: giữ lệnh chạy bình thường

# ==================== MUTE (.m) — TIMEOUT GỐC DISCORD ====================
@bot.command(aliases=["m"])
@commands.has_permissions(moderate_members=True)
async def mute(ctx, member: discord.Member = None, time: str = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="`.m @user 10m spam`", color=BLACK))
    seconds = parse_duration(time) if time else None
    if time and check_time_format(time) and seconds is None:
        return await ctx.send(embed=discord.Embed(title="❌ SAI THỜI GIAN",
            description="`1s`-`60s` • `1p`-`60p` • `1h`-`24h` • `1d`-`28d`\n⚠️ Timeout Discord giới hạn tối đa **28 ngày**", color=BLACK))
    if time and seconds is None:
        reason = f"{time} {reason}" if reason else time
        time = None
    if member == ctx.author:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không thể mute chính mình!", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không thể mute bot!", color=BLACK))
    if member.guild_permissions.moderate_members and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Người này có quyền moderation, không mute được!", color=BLACK))

    if seconds is None:
        seconds = 28 * 86400   # không nhập thời gian = 28 ngày

    until = discord.utils.utcnow() + timedelta(seconds=seconds)
    try:
        await member.timeout(until, reason=f"Bởi {ctx.author} | {reason or 'Không lý do'}")
    except discord.Forbidden:
        return await ctx.send(embed=discord.Embed(title="🚫 BOT THIẾU QUYỀN",
            description="Bot cần quyền **Timeout members** (và role cao hơn nạn nhân)!", color=BLACK))

    mutes = load_json(MUTE_FILE)
    mutes.setdefault(str(ctx.guild.id), {})[str(member.id)] = {
        "until": until.isoformat(),
        "mod": str(ctx.author),
        "reason": reason or "Không lý do"}
    save_json(MUTE_FILE, mutes)

    # DM riêng cho nạn nhân
    try:
        dm = discord.Embed(title="🔇 BẠN BỊ MUTE", color=BLACK, timestamp=discord.utils.utcnow())
        dm.add_field(name="🏠 Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="⏱️ Thời lượng", value=format_duration(seconds), inline=True)
        dm.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=True)
        dm.add_field(name="🛡️ Mod", value=str(ctx.author), inline=True)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="🔇 ĐÃ TIMEOUT (MUTE GỐC DISCORD)", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="👤 Người dùng", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="⏱️ Thời lượng", value=f"**{format_duration(seconds)}**", inline=True)
    embed.add_field(name="⏰ Hết mute lúc", value=until.strftime("%H:%M:%S %d/%m/%Y"), inline=True)
    embed.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=False)
    embed.add_field(name="🛡️ Mod", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.set_footer(text=f"ID: {member.id}")
    await send_with_roast(ctx, embed, member)

# ==================== UNMUTE (.um) ====================
@bot.command(aliases=["um"])
@commands.has_permissions(moderate_members=True)
async def unmute(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Tag người cần unmute!", color=BLACK))
    if member.timed_out_until is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Người này không bị timeout!", color=BLACK))
    try:
        await member.timeout(None, reason=f"Unmute bởi {ctx.author}")
    except discord.Forbidden:
        return await ctx.send(embed=discord.Embed(title="🚫 BOT THIẾU QUYỀN", color=BLACK))

    mutes = load_json(MUTE_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in mutes and uid in mutes[gid]:
        del mutes[gid][uid]
        save_json(MUTE_FILE, mutes)

    embed = discord.Embed(title="🔊 ĐÃ UNMUTE", color=BLACK)
    embed.add_field(name="👤", value=member.mention, inline=True)
    embed.add_field(name="🛡️", value=ctx.author.mention, inline=True)
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
        embed = discord.Embed(title="⏳ THÔNG TIN TIMEOUT", color=BLACK)
        embed.add_field(name="👤", value=member.mention, inline=False)
        if total_sec > 0:
            hours, remainder = divmod(total_sec, 3600)
            minutes, secs = divmod(remainder, 60)
            days, hours = divmod(hours, 24)
            parts = []
            if days: parts.append(f"**{days}** ngày")
            if hours: parts.append(f"**{hours}** giờ")
            if minutes: parts.append(f"**{minutes}** phút")
            if secs: parts.append(f"**{secs}** giây")
            embed.add_field(name="⏱️ Còn lại", value=" ".join(parts), inline=True)
        embed.add_field(name="⏰ Hết lúc", value=until.strftime("%H:%M:%S %d/%m/%Y"), inline=True)
        if info:
            embed.add_field(name="📄 Lý do", value=info.get("reason", "?"), inline=False)
            embed.add_field(name="🛡️ Mod", value=info.get("mod", "?"), inline=True)
        embed.set_thumbnail(url=member.display_avatar.url)
        return await ctx.send(embed=embed)

    if info:
        return await ctx.send(embed=discord.Embed(title="⏳", description=f"Hết mute lúc {info['until'][:19]}", color=BLACK))
    await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Người này không bị mute!", color=BLACK))

# ==================== BAN (.b) ====================
@bot.command(aliases=["b"])
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Tag người cần ban!", color=BLACK))
    if member == ctx.author:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không thể ban chính mình!", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không thể ban bot!", color=BLACK))
    if member.top_role >= ctx.author.top_role and ctx.author != ctx.guild.owner:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không ban được người cấp cao hơn bạn!", color=BLACK))
    await member.ban(reason=f"{reason} | Mod: {ctx.author}")

    # DM riêng trước khi mất kết nối
    try:
        dm = discord.Embed(title="🔨 BẠN BỊ BAN", color=BLACK)
        dm.add_field(name="🏠 Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=False)
        dm.add_field(name="🛡️ Mod", value=str(ctx.author), inline=True)
        await member.send(embed=dm)
    except discord.Forbidden:
        pass

    embed = discord.Embed(title="🔨 ĐÃ BAN", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="👤", value=f"{member} ({member.id})", inline=False)
    embed.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=True)
    embed.add_field(name="🛡️ Mod", value=ctx.author.mention, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_with_roast(ctx, embed, member)

# ==================== UNBAN (.ub) ====================
@bot.command(aliases=["ub"])
@commands.has_permissions(ban_members=True)
async def unban(ctx, user_id: int = None):
    if user_id is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Nhập ID cần unban!", color=BLACK))
    try:
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        await ctx.send(embed=discord.Embed(title="✅ ĐÃ UNBAN", description=f"{user} ({user.id})", color=BLACK))
    except discord.NotFound:
        await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Người này không bị ban!", color=BLACK))

# ==================== WARN (.w) — CÓ DM RIÊNG ====================
@bot.command(aliases=["w"])
@commands.has_permissions(manage_messages=True)
async def warn(ctx, member: discord.Member = None, *, reason=None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Tag người cần warn!", color=BLACK))
    if member.bot:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không thể warn bot!", color=BLACK))

    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    warnings.setdefault(gid, {}).setdefault(uid, [])
    warnings[gid][uid].append({"reason": reason or "Không lý do", "mod": str(ctx.author)})
    save_json(WARN_FILE, warnings)
    count = len(warnings[gid][uid])

    if count >= 5:
        await member.ban(reason=f"Đạt {count} warnings")
        return await ctx.send(embed=discord.Embed(title="🔨 AUTO BAN",
            description=f"{member.mention} đạt **{count} warnings**!", color=BLACK))

    # ===== DM RIÊNG KÈM LÝ DO =====
    try:
        dm = discord.Embed(title="⚠️ BẠN BỊ CẢNH BÁO", color=BLACK, timestamp=discord.utils.utcnow())
        dm.add_field(name="🏠 Server", value=ctx.guild.name, inline=False)
        dm.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=False)
        dm.add_field(name="🔢 Lần cảnh báo", value=f"**{count}/5** — đủ 5 lần = BAN", inline=True)
        dm.add_field(name="🛡️ Mod", value=str(ctx.author), inline=True)
        if ctx.guild.icon:
            dm.set_thumbnail(url=ctx.guild.icon.url)
        await member.send(embed=dm)
        dm_status = "✅ Đã DM riêng"
    except discord.Forbidden:
        dm_status = "❌ Không DM được (user đóng DM)"

    embed = discord.Embed(title="⚠️ ĐÃ WARN", color=BLACK, timestamp=discord.utils.utcnow())
    embed.add_field(name="👤", value=f"{member.mention} ({member})", inline=False)
    embed.add_field(name="📄 Lý do", value=reason or "Không có lý do", inline=True)
    embed.add_field(name="🔢 Lần", value=f"**{count}/5**", inline=True)
    embed.add_field(name="🛡️ Mod", value=ctx.author.mention, inline=True)
    embed.add_field(name="📩 DM", value=dm_status, inline=True)
    embed.set_thumbnail(url=member.display_avatar.url)
    await send_with_roast(ctx, embed, member)

# ==================== WARNS (.ws) ====================
@bot.command(aliases=["ws", "warnings"])
async def warns(ctx, member: discord.Member = None):
    member = member or ctx.author
    data = load_json(WARN_FILE).get(str(ctx.guild.id), {}).get(str(member.id), [])
    embed = discord.Embed(title=f"⚠️ WARN — {member.name}", color=BLACK)
    embed.set_thumbnail(url=member.display_avatar.url)
    if not data:
        embed.description = "✅ Không có cảnh báo nào!"
    else:
        for i, w in enumerate(data, 1):
            embed.add_field(name=f"Warn #{i}", value=f"📄 {w['reason']}\n🛡️ {w['mod']}", inline=False)
    await ctx.send(embed=embed)

# ==================== CLEARWARN (.cw) ====================
@bot.command(aliases=["cw"])
@commands.has_permissions(manage_messages=True)
async def clearwarn(ctx, member: discord.Member = None):
    if member is None:
        return await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Tag người cần xóa warn!", color=BLACK))
    warnings = load_json(WARN_FILE)
    gid, uid = str(ctx.guild.id), str(member.id)
    if gid in warnings and uid in warnings[gid]:
        del warnings[gid][uid]
        save_json(WARN_FILE, warnings)
        await ctx.send(embed=discord.Embed(title="🧹 ĐÃ XÓA WARN", description=member.mention, color=BLACK))
    else:
        await ctx.send(embed=discord.Embed(title="❌ Lỗi", description="Không có warn nào!", color=BLACK))

# ==================== HELP ====================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="📖 LỆNH BOT", color=BLACK)
    embed.add_field(name="🔇 .m @user <30s|10p|2h|1d> [lý do]", value="Timeout gốc Discord — không nhập thời gian = 28 ngày, kèm DM", inline=False)
    embed.add_field(name="🔊 .um @user", value="Gỡ timeout", inline=False)
    embed.add_field(name="⏳ .mi @user", value="Xem còn bao lâu hết mute", inline=False)
    embed.add_field(name="🔨 .b @user [lý do]", value="Ban — kèm DM riêng", inline=False)
    embed.add_field(name="✅ .ub <ID>", value="Unban", inline=False)
    embed.add_field(name="⚠️ .w @user [lý do]", value="Warn (5 lần = ban) — DM riêng kèm lý do", inline=False)
    embed.add_field(name="📋 .ws [@user]", value="Xem warn", inline=False)
    embed.add_field(name="🧹 .cw @user", value="Xóa warn", inline=False)
    embed.add_field(name="⏱️ Thời gian", value="`s` 1-60 • `p`/`m` 1-60 • `h` 1-24 • `d` 1-28", inline=False)
    embed.add_field(name="🤖 Auto-mod", value=f"Chat từ cấm → tự xóa tin + mute {AUTO_MUTE_SECONDS}s + mỉa 😜", inline=False)
    embed.set_footer(text="Prefix: . ! ?")
    await ctx.send(embed=embed)

# ==================== LỖI ====================
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(embed=discord.Embed(title="🚫 KHÔNG ĐỦ QUYỀN", color=BLACK))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send(embed=discord.Embed(title="🚫 BOT THIẾU QUYỀN",
            description="Bot thiếu quyền (Moderate Members / Ban Members...)", color=BLACK))
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=discord.Embed(title="❌ Không tìm thấy thành viên!", color=BLACK))
    elif isinstance(error, commands.CommandNotFound):
        pass
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(title="❌ Thiếu tham số", description="Dùng `.help`!", color=BLACK))

# ==================== CHẠY ====================
open_port()

while True:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"⚠️ Bot lỗi: {e} — tự khởi động lại sau 5 giây...")
        time.sleep(5)
