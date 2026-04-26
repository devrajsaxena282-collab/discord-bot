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

# ---------------- DATABASE ----------------
conn = sqlite3.connect("tickets.db")
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

def get_ticket_by_channel(channel_id):
    cursor.execute("SELECT * FROM tickets WHERE channel_id=?", (channel_id,))
    return cursor.fetchone()

# ---------------- BOT ----------------
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

STAFF_ROLE = "Staff"
LOG_CHANNEL = "ticket-logs"
CATEGORY = "ticket"

ticket_count = 0

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

    # 🔥 FIXED CHECK (DB + REAL CHANNEL)
    existing = get_user_ticket(interaction.user.id)
    if existing:
        channel = interaction.guild.get_channel(existing[1])
        if channel:
            return await interaction.response.send_message(
                "❌ You already have a ticket!", ephemeral=True
            )
        else:
            remove_ticket(existing[1])  # ghost remove

    category = discord.utils.get(interaction.guild.categories, name=CATEGORY)
    if not category:
        return await interaction.response.send_message(
            "❌ Create 'ticket' category first", ephemeral=True
        )

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
        title="Support" if selected_type == "Support" else "Purchase",
        description=f"Ticket #{num}\nType: {selected_type}",
        color=discord.Color.red()
    )

    await channel.send(content=interaction.user.mention, embed=embed, view=TicketButtons())

    await interaction.response.send_message(
        f"✅ Ticket created for {interaction.user.mention}",
        ephemeral=True
    )

    bot.loop.create_task(auto_close(channel))

# ---------------- BUTTONS ----------------
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()

        log_channel = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL)
        data = get_ticket_by_channel(interaction.channel.id)

        ticket_number = interaction.channel.name.split("-")[-1]
        user_name = "Unknown"
        ticket_type = "Unknown"

        if data:
            user = interaction.guild.get_member(data[0])
            if user:
                user_name = user.name
            ticket_type = data[3]

        msgs = []
        async for m in interaction.channel.history(limit=200):
            msgs.append(f"{m.author}: {m.content}")

        file = discord.File(BytesIO("\n".join(msgs[::-1]).encode()), filename="transcript.txt")

        if log_channel:
            await log_channel.send(
                f"📜 Ticket #{ticket_number} | User: {user_name} (Type: {ticket_type})",
                file=file
            )

        remove_ticket(interaction.channel.id)
        await interaction.channel.delete()

# ---------------- PANEL DROPDOWN ----------------
class PanelDropdown(discord.ui.Select):
    def __init__(self):
        options = [
           discord.SelectOption(label="BASIC PANEL", emoji="🔴"),
            discord.SelectOption(label="UID BYPASS", emoji="🔴"),
            discord.SelectOption(label="EMULATOR BYPASS", emoji="🔴"),
            discord.SelectOption(label="CUSTOM PANEL", emoji="🔴"),
            discord.SelectOption(label="AIMSILENT EXE", emoji="🔴"),
            discord.SelectOption(label="AIMSILENT APK", emoji="🔴"),
            discord.SelectOption(label="STREAMER PANEL", emoji="🔴"),
            discord.SelectOption(label="INTERNAL MAX", emoji="🔴"),
            discord.SelectOption(label="AIMKILL EXE", emoji="🔴"),
            discord.SelectOption(label="OPTIMIZATION", emoji="🔴"),
            discord.SelectOption(label="WINDOWS 10 PRO", emoji="🔴"),
            discord.SelectOption(label="WINDOWS 11 PRO", emoji="🔴"),
            discord.SelectOption(label="MS OFFICE 2021 PREMIUM", emoji="🔴"),
            discord.SelectOption(label="MS 365 PREMIUM", emoji="🔴"),
            discord.SelectOption(label="DEVICE ROOTING", emoji="🔴"),
            discord.SelectOption(label="DRIP CLIENT", emoji="🔴"),
            discord.SelectOption(label="BR MOD", emoji="🔴"),
            discord.SelectOption(label="HG CHEATS", emoji="🔴"),
            discord.SelectOption(label="KOS ROOT", emoji="🔴"),
        ]
        super().__init__(placeholder="Select Panel", options=options)

    async def callback(self, interaction: discord.Interaction):
        await create_ticket(interaction, self.values[0])

class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PanelDropdown())

# ---------------- MAIN DROPDOWN ----------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support"),
            discord.SelectOption(label="Purchase"),
        ]
        super().__init__(placeholder="Select Option", options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "Support":
            await create_ticket(interaction, "Support")

        elif self.values[0] == "Purchase":
            await interaction.response.send_message(
                "🛒 Select Panel below:",
                view=PanelView(),
                ephemeral=True
            )

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ---------------- PANEL COMMAND ----------------
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="INTELLECT-X – Official Tickets System",
        description="""
Welcome to the official ticket system of INTELLECT-X.

━━━━━━━━━━━━━━━━━━━━━━
🧡 Rules:
* Only support & purchase tickets
* No spam
* Respect staff
━━━━━━━━━━━━━━━━━━━━━━
""",
        color=discord.Color.dark_red()
    )

    embed.set_thumbnail(url="https://i.postimg.cc/L6Z52HmG/1000204859.png")
    embed.set_image(url="https://www.image2url.com/r2/default/gifs/1776315441121-f3fbcbaa-81cb-43b6-8b30-119cca261799.gif")

    await ctx.send(embed=embed, view=TicketView())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"🔥 {bot.user} Online")

# ---------------- RUN ----------------
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
