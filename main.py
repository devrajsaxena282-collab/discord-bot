import discord
from discord.ext import commands
from io import BytesIO
import sqlite3
import asyncio
import os
from flask import Flask
from threading import Thread

# ---------------- FLASK ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    Thread(target=run).start()

# ---------------- INTENTS ----------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------- SAFE RESPONSE CORE (PERMANENT FIX) ----------------
async def safe(interaction, content=None, embed=None, view=None, ephemeral=False):
    try:
        if interaction.response.is_done():
            return await interaction.followup.send(
                content=content,
                embed=embed,
                view=view,
                ephemeral=ephemeral
            )
        else:
            return await interaction.response.send_message(
                content=content,
                embed=embed,
                view=view,
                ephemeral=ephemeral
            )
    except:
        try:
            return await interaction.channel.send(content or "Error occurred")
        except:
            pass

# ---------------- DATABASE ----------------
conn = sqlite3.connect("tickets.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tickets (
    user_id INTEGER,
    channel_id INTEGER,
    ticket_number INTEGER,
    ticket_type TEXT
)
""")
conn.commit()

def add_ticket(user_id, channel_id, num, ttype):
    cursor.execute("INSERT INTO tickets VALUES (?, ?, ?, ?)",
                   (user_id, channel_id, num, ttype))
    conn.commit()

def remove_ticket(channel_id):
    cursor.execute("DELETE FROM tickets WHERE channel_id=?", (channel_id,))
    conn.commit()

def get_user_ticket(user_id):
    cursor.execute("SELECT * FROM tickets WHERE user_id=?", (user_id,))
    return cursor.fetchone()

# ---------------- CONFIG ----------------
STAFF_ROLE = "Staff"
LOG_CHANNEL = "ticket-logs"
CATEGORY = "ticket"

ticket_count = 0

# ---------------- PURGE ----------------
@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 100):
    if amount <= 0:
        return await ctx.send("❌ Invalid amount")

    if amount > 100:
        return await ctx.send("❌ Max limit is 100 messages")

    deleted = await ctx.channel.purge(limit=amount + 1)
    msg = await ctx.send(f"🧹 Deleted {len(deleted)-1} messages")

    await asyncio.sleep(2)
    await msg.delete()

# ---------------- AUTO CLOSE ----------------
async def auto_close(channel):
    await asyncio.sleep(3600)
    try:
        await channel.send("⏱️ Auto closed due to inactivity")
        await channel.delete()
    except:
        pass

# ---------------- CREATE TICKET ----------------
async def create_ticket(interaction, selected_type):
    global ticket_count

    try:
        if not interaction.response.is_done():
            await interaction.response.defer()
    except:
        pass

    existing = get_user_ticket(interaction.user.id)
    if existing:
        ch = interaction.guild.get_channel(existing[1])
        if ch:
            return await safe(interaction, "❌ You already have a ticket!", True)
        else:
            remove_ticket(existing[1])

    category = discord.utils.get(interaction.guild.categories, name=CATEGORY)
    if not category:
        return await safe(interaction, "❌ Category missing", True)

    ticket_count += 1
    num = str(ticket_count).zfill(3)

    channel = await interaction.guild.create_text_channel(
        f"ticket-{num}",
        category=category,
        topic=str(interaction.user.id)
    )

    await channel.set_permissions(interaction.guild.default_role, view_channel=False)
    await channel.set_permissions(interaction.user, view_channel=True)

    role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)
    if role:
        await channel.set_permissions(role, view_channel=True)

    add_ticket(interaction.user.id, channel.id, ticket_count, selected_type)

    embed = discord.Embed(
        title="🎫 INTELLECT-X TICKET OPENED",
        description=f"""
🎟️ Ticket #{num}

👋 {interaction.user.mention}

📌 Type: {selected_type}

━━━━━━━━━━━━━━
Staff will join soon
━━━━━━━━━━━━━━
""",
        color=discord.Color.red()
    )

    await channel.send(content=interaction.user.mention, embed=embed, view=TicketButtons())

    log = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL)
    if log:
        await log.send(f"📥 Ticket #{num} created")

    await safe(interaction, f"✅ Ticket created: {channel.mention}", True)

    bot.loop.create_task(auto_close(channel))

# ---------------- BUTTONS ----------------
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction, button):
        await safe(interaction, f"👤 Claimed by {interaction.user.mention}")

    @discord.ui.button(label="Verify Payment", style=discord.ButtonStyle.success)
    async def verify(self, interaction, button):
        await safe(interaction, f"💰 Verified by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction, button):

        try:
            await interaction.response.defer()
        except:
            pass

        log = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL)

        transcript = []
        async for msg in interaction.channel.history(limit=200):
            transcript.append(f"{msg.author}: {msg.content}")

        file = discord.File(BytesIO("\n".join(transcript[::-1]).encode()), filename="transcript.txt")

        if log:
            await log.send("📜 Ticket Closed", file=file)

        remove_ticket(interaction.channel.id)

        await interaction.channel.delete()

# ---------------- SUPPORT PANEL ----------------
class SupportPanelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="GENERAL SUPPORT", emoji="❤️"),
            discord.SelectOption(label="TECH ISSUE", emoji="🛠️"),
            discord.SelectOption(label="BILLING HELP", emoji="💳"),
            discord.SelectOption(label="ACCOUNT ISSUE", emoji="🔐"),
            discord.SelectOption(label="PRODUCT HELP", emoji="📦"),
            discord.SelectOption(label="PANEL SUPPORT", emoji="🔴"),
            discord.SelectOption(label="SOFTWARE HELP", emoji="💻"),
        ]
        super().__init__(placeholder="Select Support Type", options=options)

    async def callback(self, interaction):
        await create_ticket(interaction, self.values[0])

class SupportPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SupportPanelSelect())

# ---------------- PURCHASE PANEL ----------------
class PurchasePanelSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="BASIC PANEL", emoji="⭕"),
            discord.SelectOption(label="UID BYPASS", emoji="⭕"),
            discord.SelectOption(label="EMULATOR BYPASS", emoji="⭕"),
            discord.SelectOption(label="CUSTOM PANEL", emoji="⭕"),
            discord.SelectOption(label="AIMSILENT EXE", emoji="⭕"),
            discord.SelectOption(label="AIMSILENT APK", emoji="⭕"),
            discord.SelectOption(label="STREAMER PANEL", emoji="⭕"),
            discord.SelectOption(label="INTERNAL MAX", emoji="⭕"),
            discord.SelectOption(label="AIMKILL EXE", emoji="⭕"),
            discord.SelectOption(label="OPTIMIZATION", emoji="⭕"),
            discord.SelectOption(label="WINDOWS 10 PRO", emoji="⭕"),
            discord.SelectOption(label="WINDOWS 11 PRO", emoji="⭕"),
        ]
        super().__init__(placeholder="Select Purchase Panel", options=options)

    async def callback(self, interaction):
        await create_ticket(interaction, self.values[0])

class PurchasePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PurchasePanelSelect())

# ---------------- SALE PANEL ----------------
class SalePanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔥 Discount", style=discord.ButtonStyle.success)
    async def discount(self, interaction, button):
        await create_ticket(interaction, "SALE DISCOUNT")

    @discord.ui.button(label="💸 Buy Now", style=discord.ButtonStyle.primary)
    async def buy(self, interaction, button):
        await create_ticket(interaction, "SALE PURCHASE")

# ---------------- DROPDOWN ----------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support", emoji="❤️"),
            discord.SelectOption(label="Purchase", emoji="🛒"),
            discord.SelectOption(label="SALE PANEL", emoji="🔥"),
        ]
        super().__init__(placeholder="Select Ticket Type", options=options)

    async def callback(self, interaction):
        if self.values[0] == "Support":
            await interaction.response.send_message("Support", view=SupportPanelView(), ephemeral=True)
        elif self.values[0] == "Purchase":
            await interaction.response.send_message("Purchase", view=PurchasePanelView(), ephemeral=True)
        else:
            await interaction.response.send_message("Sale", view=SalePanelView(), ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ---------------- PANEL ----------------
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="INTELLECT-X",
        description="Ticket System",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=TicketView())

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ---------------- RUN ----------------
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
