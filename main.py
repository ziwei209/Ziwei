import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import random
import urllib.parse
import requests
import tempfile
import os
import xml.etree.ElementTree as ET

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# Bộ nhớ tạm NSFW
temp_nsfw_channels = set()

@bot.event
async def on_ready():
    print(f"🤖 Bot online dưới tên: {bot.user}")
    # In ra link công khai Replit
    import os
    url = f"https://{os.getenv('REPL_SLUG')}.{os.getenv('REPL_OWNER')}.repl.co"
    print(f"🌐 Link công khai Replit của bạn: {url}")
    try:
        synced = await tree.sync()
        print(f"🔁 Slash command đã sync: {len(synced)} lệnh")
    except Exception as e:
        print(f"❌ Lỗi khi sync command: {e}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower().startswith("l.zi "):
        tag = message.content[5:].strip()
        if not tag:
            await message.reply("❌ Nhập tag sau `L.zi`, ví dụ: `L.zi yae miko`")
            return

        await message.channel.typing()
        try:
            encoded_tag = urllib.parse.quote_plus(tag)
            search_url = f"https://rule34.xxx/index.php?page=post&s=list&tags={encoded_tag}"
            headers = {"User-Agent": "Mozilla/5.0"}

            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as resp:
                    if resp.status != 200:
                        await message.reply("❌ Không thể truy cập Rule34.")
                        return
                    html = await resp.text()

            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            thumbs = soup.find_all("span", class_="thumb")
            if not thumbs:
                await message.reply("❌ Không tìm thấy kết quả.")
                return

            random.shuffle(thumbs)
            for thumb in thumbs:
                post = thumb.find("a")
                post_url = "https://rule34.xxx/" + post["href"]

                async with aiohttp.ClientSession() as session:
                    async with session.get(post_url, headers=headers) as resp:
                        if resp.status != 200:
                            continue
                        post_html = await resp.text()

                post_soup = BeautifulSoup(post_html, "html.parser")

                video = post_soup.find("video", id="gelcomVideoPlayer")
                if video:
                    source = video.find("source")
                    if source and "src" in source.attrs:
                        await message.reply(source["src"])
                        return

                image = post_soup.find("img", id="image")
                if image and "src" in image.attrs:
                    await message.reply(image["src"])
                    return

            await message.reply("❌ Không tìm thấy ảnh hoặc video hợp lệ.")
        except Exception as e:
            await message.reply(f"❌ Lỗi khi tìm: `{e}`")

    await bot.process_commands(message)

# Lệnh /r34
@tree.command(name="r34", description="🔞 Tìm ảnh/gif/video từ Rule34 theo tag")
@app_commands.describe(tag="Tag chính", tag2="Tag phụ", tag3="...", tag4="...", tag5="...", amount="Số lượng kết quả")
async def r34(inter: discord.Interaction, tag: str, tag2: str = "", tag3: str = "", tag4: str = "", tag5: str = "", amount: int = 1):
    if not inter.channel.is_nsfw() and inter.channel_id not in temp_nsfw_channels:
        return await inter.response.send_message("❌ Chỉ dùng trong kênh NSFW.", ephemeral=True)

    await inter.response.defer()
    tags = " ".join(t for t in [tag, tag2, tag3, tag4, tag5] if t)
    amount = max(1, min(amount, 30))

    try:
        res = requests.get(f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=100&tags={tags}", headers={"User-Agent": "DiscordBot"})
        if res.status_code != 200:
            return await inter.followup.send("❌ Không thể truy cập Rule34.")

        root = ET.fromstring(res.text)
        files = [p.get("file_url") for p in root.findall("post") if p.get("file_url")]

        if not files:
            return await inter.followup.send(f"❌ Không tìm thấy tag `{tags}`.")

        selected = random.sample(files, min(amount, len(files)))
        for url in selected:
            await inter.followup.send(f"🔞 `{tags}`\n{url}")
    except Exception:
        return await inter.followup.send("❌ Lỗi khi truy vấn dữ liệu từ Rule34.")

import discord
from discord import app_commands
import requests
import random

# ==== HÀM LẤY ẢNH TỪ DANBOORU ====
def get_danbooru_image(tag):
    try:
        url = f"https://danbooru.donmai.us/posts.json?tags={tag}&limit=50"
        headers = {"User-Agent": "DiscordBot"}
        res = requests.get(url, headers=headers, timeout=5)
        if res.status_code != 200:
            return None
        data = res.json()
        posts = [post.get("file_url") for post in data if post.get("file_url")]
        return random.choice(posts) if posts else None
    except Exception as e:
        print(f"Lỗi khi lấy ảnh từ Danbooru: {e}")
        return None

# ==== HÀM GỬI EMBED ====
async def send_embed(inter: discord.Interaction, url: str, title: str):
    embed = discord.Embed(title=title, color=0xFF69B4)
    embed.set_image(url=url)
    await inter.followup.send(embed=embed)

# ==== LỆNH /pussy ====
@tree.command(name="pussy", description="🌸 Xem ảnh pussy (NSFW)")
async def pussy(inter: discord.Interaction):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Lệnh này chỉ dùng ở kênh NSFW.", ephemeral=True)

    await inter.response.defer()
    img = get_danbooru_image("pussy")

    if not img:
        return await inter.followup.send("❌ Không tìm thấy ảnh.")

    await send_embed(inter, img, "🌸 Pussy")

# ==== GIF TAG NGƯỜI DÙNG ====
def get_rule34_gif(tag):
    try:
        url = f"https://rule34.xxx/index.php?page=dapi&s=post&q=index&limit=100&tags={tag}+animated"
        headers = {"User-Agent": "DiscordBot"}
        res = requests.get(url, headers=headers)
        if res.status_code != 200:
            return None
        root = ET.fromstring(res.text)
        gifs = [p.attrib.get("file_url") for p in root.findall("post") if p.attrib.get("file_url", "").endswith(".gif")]
        return random.choice(gifs) if gifs else None
    except:
        return None
@tree.command(name="fuck", description="💦 Chịch người khác (NSFW)")
@app_commands.describe(user="Người bị chịch")
async def fuck(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("sex")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang chịch {user.display_name} 💦", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="kiss", description="💋 Hôn người khác (NSFW)")
@app_commands.describe(user="Người được hôn")
async def kiss(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("kiss")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} hôn {user.display_name} 💋", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="lick", description="👅 Liếm người khác (NSFW)")
@app_commands.describe(user="Người bị liếm")
async def lick(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("lick")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang liếm {user.display_name} 👅", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="spank", description="🍑 Vỗ mông người khác (NSFW)")
@app_commands.describe(user="Người bị vỗ mông")
async def spank(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("spank")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} vỗ mông {user.display_name} 🍑", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="cum_on", description="💦 Cum lên người khác (NSFW)")
@app_commands.describe(user="Người bị cum lên")
async def cum_on(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("cum")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} cum lên {user.display_name} 💦", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="finger", description="👆 Móc lồn người khác (NSFW)")
@app_commands.describe(user="Người bị móc")
async def finger(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("fingering")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang móc lồn {user.display_name} 👆💦", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="bj", description="👄 Bú cu người khác (NSFW)")
@app_commands.describe(user="Người bị bú")
async def bj(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("blowjob")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang bú cu {user.display_name} 👄", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="anal", description="🍑 Địt đít người khác (NSFW)")
@app_commands.describe(user="Người bị địt đít")
async def anal(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("anal")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang địt đít {user.display_name} 🍑", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="boobs", description="🍈 Show vú cho người khác (NSFW)")
@app_commands.describe(user="Người được show vú")
async def boobs(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("boobs")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} show vú cho {user.display_name} 🍈", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)

@tree.command(name="cowgirl", description="🐴 Cưỡi người khác kiểu cowgirl (NSFW)")
@app_commands.describe(user="Người bị cưỡi")
async def cowgirl(inter: discord.Interaction, user: discord.User):
    if not inter.channel.is_nsfw():
        return await inter.response.send_message("❌ Cần bật NSFW.", ephemeral=True)
    await inter.response.defer()
    gif = get_rule34_gif("cowgirl")
    if not gif:
        return await inter.followup.send("❌ Không có gif.")
    embed = discord.Embed(title=f"{inter.user.display_name} đang cưỡi {user.display_name} kiểu cowgirl 🐴💦", color=0xFF69B4)
    embed.set_image(url=gif)
    await inter.followup.send(embed=embed)


# ==== BẬT NSFW KÊNH ====
@tree.command(name="setnsfw", description="🛠️ Bật NSFW cho kênh (chỉ người có quyền)")
async def setnsfw(inter: discord.Interaction):
    # Kiểm tra nếu user không có quyền Manage Channels
    if not inter.user.guild_permissions.manage_channels:
        await inter.response.send_message("⛔ Bạn cần quyền **Quản lý kênh** để dùng lệnh này.", ephemeral=True)
        return

    try:
        await inter.channel.edit(nsfw=True)
        await inter.response.send_message("✅ Đã bật NSFW cho kênh này.", ephemeral=True)
    except Exception as e:
        await inter.response.send_message(f"❌ Không thể bật NSFW: {e}", ephemeral=True)
# ==== LỆNH /START CHỈ CHO ADMIN ====
@tree.command(name="start", description="📢 Giới thiệu bot (chỉ Admin dùng được)")
async def start(inter: discord.Interaction):
    if not inter.user.guild_permissions.administrator:
        await inter.response.send_message("⛔ Bạn không có quyền dùng lệnh này.", ephemeral=True)
        return

    await inter.response.send_message(
        "**👋 Chào mọi người đã đến với bot **`Lồn Mini`**!**\n\n"
        "🔞 Đây là bot giải trí NSFW siêu tốc dành cho server người lớn!\n\n"
        "**📌 Các chức năng chính:**\n"
        "• `/r34 [tag]` – Tìm ảnh/video từ Rule34\n"
        "• `L.zi [tag]` – Tìm nhanh ảnh Rule34 từ tin nhắn thường\n"
        "• `/fuck @user` – Làm tình với ai đó 😳\n"
        "• `/kiss @user` – Hôn người khác 💋\n"
        "• `/cum_on @user` – Xuất tinh lên người 🤤\n"
        "• `/anal @user` – Chơi lỗ hậu 😈\n"
        "• `/cowgirl @user` – Cưỡi ngựa với ai đó 🐎\n"
        "• `/bj @user` – Cho ai đó blowjob 🍆💦\n"
        "• `/lick @user` – Liếm người khác 😋\n"
        "• `/spank @user` – Đánh mông người khác 🔥\n"
        "• `/finger @user` – Móc lồn người khác 😳\n"
        "• `/boobs @user` – Show vú người khác 🍈\n"
        "• `/setnsfw [on/off]` – Bật/tắt chế độ NSFW cho kênh\n\n"
        "💡 Dùng lệnh `/setnsfw on` để bật các lệnh NSFW cho kênh!\n"
        "❗ Nếu bot không phản hồi lệnh, hãy kiểm tra xem kênh đã bật NSFW chưa!"
    )
# ===== RUN BOT =====
from keep_alive import keep_alive
keep_alive()
bot.run(TOKEN)
