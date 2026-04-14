import discord
from discord.ext import commands
from datetime import datetime, timedelta
from io import BytesIO
import os

from flask import Flask
from threading import Thread

app = Flask(__name__)

@app.route("/")
def home():
    return "OK"

def run():
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        debug=False,
        use_reloader=False
    )

def keep_alive():
    Thread(target=run, daemon=True).start()


# ---------------- BOT ----------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}

STAFF_ROLE = "Staff"
LOG_CHANNEL = "ticket-logs"


@bot.event
async def on_ready():
    print(f"🔥 Bot Ready: {bot.user}")


# ---------------- BUTTONS ----------------

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)

        if role not in interaction.user.roles:
            return await interaction.followup.send("❌ Staff only!", ephemeral=True)

        await interaction.followup.send(f"👤 {interaction.user.mention} claimed this ticket")

    @discord.ui.button(label="Verify Payment", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        await interaction.followup.send(f"💰 Payment verified by {interaction.user.mention}")

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.defer()

        try:
            log_channel = discord.utils.get(interaction.guild.text_channels, name=LOG_CHANNEL)

            transcript = []
            async for msg in interaction.channel.history(limit=200):
                transcript.append(f"{msg.author}: {msg.content}")

            text = "\n".join(transcript[::-1])

            if log_channel:
                file = discord.File(BytesIO(text.encode()), filename="transcript.txt")
                await log_channel.send(
                    f"📜 Transcript: {interaction.channel.name}",
                    file=file
                )

            await interaction.channel.delete()

        except Exception as e:
            print("Close error:", e)
            try:
                await interaction.followup.send("❌ Close failed", ephemeral=True)
            except:
                pass


# ---------------- DROPDOWN ----------------

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="BASIC PANEL", emoji="🔴"),
            discord.SelectOption(label="UID BYPASS", emoji="🔴"),
            discord.SelectOption(label="EMULATOR BYPASS", emoji="🔴"),
            discord.SelectOption(label="CUSTOM PANEL", emoji="🔴"),
        ]
        super().__init__(placeholder="Select Ticket Type", options=options)

    async def callback(self, interaction: discord.Interaction):

        try:
            await interaction.response.defer(ephemeral=True)

            now = datetime.now()

            if interaction.user.id in cooldowns:
                if now < cooldowns[interaction.user.id]:
                    return await interaction.followup.send("⏳ Wait before creating another ticket", ephemeral=True)

            cooldowns[interaction.user.id] = now + timedelta(seconds=30)

            guild = interaction.guild
            if not guild:
                return await interaction.followup.send("❌ Guild not found", ephemeral=True)

            category = discord.utils.get(guild.categories, name="ticket")
            if not category:
                return await interaction.followup.send("❌ Create 'ticket' category first", ephemeral=True)

            for ch in category.channels:
                if str(interaction.user.id) in ch.name:
                    return await interaction.followup.send("❌ You already have a ticket!", ephemeral=True)

            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.id}",
                category=category
            )

            try:
                await channel.set_permissions(guild.default_role, read_messages=False)
            except:
                pass

            try:
                await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            except:
                pass

            staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE)
            if staff_role:
                try:
                    await channel.set_permissions(staff_role, read_messages=True, send_messages=True)
                except:
                    pass

            embed = discord.Embed(
                title="INTELLECT-X Support",
                description=f"Category: **{self.values[0]}**\nStaff will assist you shortly.",
                color=discord.Color.dark_red(),
                timestamp=datetime.now()
            )

            await channel.send(
                content=interaction.user.mention,
                embed=embed,
                view=TicketButtons()
            )

            await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

        except Exception as e:
            print("ERROR:", e)
            try:
                await interaction.followup.send("❌ Bot error occurred", ephemeral=True)
            except:
                pass


# ---------------- PANEL ----------------

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())


@bot.command()
async def panel(ctx):

    embed = discord.Embed(
        title="INTELLECT-X – Official Tickets System",
        description="Open ticket for support or purchases.",
        color=discord.Color.dark_red()
    )

    # LEFT SIDE CIRCLE LOGO
    embed.set_thumbnail(url="https://i.postimg.cc/L6Z52HmG/1000204859.png")

    await ctx.send(embed=embed, view=TicketView())


# ---------------- RUN ----------------

keep_alive()

TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("❌ DISCORD_TOKEN missing")