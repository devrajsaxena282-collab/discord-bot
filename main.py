import discord
from discord.ext import commands
from datetime import datetime
from io import BytesIO
import os
from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def run():
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

active_tickets = {}

STAFF_ROLE = "Staff"
LOG_CHANNEL = "ticket-logs"

@bot.event
async def on_ready():
    print(f"🔥 Bot Ready: {bot.user}")

# ---------------- PURGE COMMAND (ADDED) ----------------

@bot.command()
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int = 100):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"🧹 {amount} messages deleted!", delete_after=3)

# ---------------- BUTTONS ----------------

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)

        if not role or role not in interaction.user.roles:
            return await interaction.response.send_message("❌ Staff only!", ephemeral=True)

        await interaction.response.send_message(f"👤 {interaction.user.mention} claimed this ticket")

    @discord.ui.button(label="Verify Payment", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(f"💰 Payment verified by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        guild = interaction.guild
        log_channel = discord.utils.get(guild.text_channels, name=LOG_CHANNEL)

        try:
            user_id = int(interaction.channel.name.split("-")[1])
            active_tickets.pop(user_id, None)
        except:
            pass

        transcript = []
        async for msg in interaction.channel.history(limit=200):
            transcript.append(f"{msg.author}: {msg.content}")

        text = "\n".join(transcript[::-1])

        if log_channel:
            file = discord.File(BytesIO(text.encode()), filename="transcript.txt")
            await log_channel.send(f"📜 Transcript: {interaction.channel.name}", file=file)

        await interaction.channel.delete()

# ---------------- DROPDOWN ----------------

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="BASIC PANEL", emoji="🔴"),
            discord.SelectOption(label="UID BYPASS", emoji="🔴"),
            discord.SelectOption(label="EMULATOR BYPASS", emoji="🔴"),
            discord.SelectOption(label="CUSTOM PANEL", emoji="🔴"),

discord.SelectOption(label="AIMSILENT EXE", emoji="🔴"),

discord.SelectOption(label="STREAMER PANEL", emoji="🔴"),
        ]
        super().__init__(placeholder="Select Ticket Type", options=options)

    async def callback(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        user_id = interaction.user.id

        if user_id in active_tickets:
            return await interaction.followup.send("❌ You already have a ticket!", ephemeral=True)

        category = discord.utils.get(guild.categories, name="ticket")
        if not category:
            return await interaction.followup.send("❌ Create 'ticket' category first", ephemeral=True)

        channel = await guild.create_text_channel(
            name=f"ticket-{user_id}",
            category=category
        )

        # 🔒 PERMISSIONS
        await channel.set_permissions(guild.default_role, view_channel=False)

        await channel.set_permissions(
            interaction.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True
        )

        staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE)
        if staff_role:
            await channel.set_permissions(
                staff_role,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )

        active_tickets[user_id] = channel.id

        embed = discord.Embed(
            title="INTELLECT-X Support",
            description="Welcome! Staff will assist you soon.",
            color=discord.Color.dark_red()
        )

        await channel.send(content=interaction.user.mention, embed=embed, view=TicketButtons())

        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

# ---------------- VIEW ----------------

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ---------------- PANEL ----------------

@bot.command()
async def panel(ctx):

    embed = discord.Embed(
        title="INTELLECT-X – Official Tickets System",
        description="""
Welcome to the official ticket system of INTELLECT-X.
Open a ticket for support or purchases.

━━━━━━━━━━━━━━━━━━━━━━
🧡 Rules:
• Only support & purchase tickets
• No spam
• Respect staff
━━━━━━━━━━━━━━━━━━━━━━
""",
        color=discord.Color.dark_red()
    )

    embed.set_thumbnail(url="https://i.postimg.cc/L6Z52HmG/1000204859.png")

    await ctx.send(embed=embed, view=TicketView())

# ---------------- RUN ----------------

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN missing")
