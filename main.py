import discord
from discord.ext import commands
from io import BytesIO
import sqlite3
import asyncio
import os
from flask import Flask, request
from threading import Thread

# ---------------- FLASK ----------------
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Running"

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    print("Webhook:", data)
    return "ok"

def run():
    app.run(host="0.0.0.0", port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

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

cursor.execute("""
CREATE TABLE IF NOT EXISTS config (
    key TEXT,
    value TEXT
)
""")
conn.commit()

def get_ticket_count():
    cursor.execute("SELECT value FROM config WHERE key='count'")
    row = cursor.fetchone()
    return int(row[0]) if row else 0

def save_ticket_count(count):
    cursor.execute("DELETE FROM config WHERE key='count'")
    cursor.execute("INSERT INTO config VALUES ('count', ?)", (str(count),))
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

ticket_count = get_ticket_count()

# ---------------- AUTO CLOSE ----------------
async def auto_close(channel):
    await asyncio.sleep(3600)
    try:
        await channel.send("⏱️ Auto closed due to inactivity")
        await channel.delete()
    except:
        pass

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

        # transcript
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

# ---------------- DROPDOWN ----------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Support"),
            discord.SelectOption(label="Purchase")
        ]
        super().__init__(placeholder="Select Ticket Type", options=options)

    async def callback(self, interaction: discord.Interaction):
        global ticket_count

        if get_user_ticket(interaction.user.id):
            return await interaction.response.send_message(
                "❌ You already have a ticket!", ephemeral=True
            )

        category = discord.utils.get(interaction.guild.categories, name=CATEGORY)
        if not category:
            return await interaction.response.send_message(
                "❌ Create 'ticket' category", ephemeral=True
            )

        ticket_count += 1
        save_ticket_count(ticket_count)

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

        add_ticket(interaction.user.id, channel.id, ticket_count, self.values[0])

        embed = discord.Embed(
            title="Support",
            description=f"Ticket #{num}\nType: {self.values[0]}",
            color=discord.Color.red()
        )

        await channel.send(content=interaction.user.mention, embed=embed, view=TicketButtons())

        await interaction.response.send_message(
            f"✅ Ticket created for {interaction.user.mention}",
            ephemeral=True
        )

        bot.loop.create_task(auto_close(channel))

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ---------------- PANEL ----------------
@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="Ticket System",
        description="Select option below",
        color=discord.Color.red()
    )
    await ctx.send(embed=embed, view=TicketView())

# ---------------- READY ----------------
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    print(f"🔥 {bot.user} Online")

# ---------------- RUN ----------------
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))
