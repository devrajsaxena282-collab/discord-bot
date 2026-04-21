import discord
from discord.ext import commands
from io import BytesIO
import os
from flask import Flask
from threading import Thread

# --- FLASK KEEP ALIVE ---
app = Flask(__name__)
@app.route("/")
def home(): return "OK"
def run(): app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- BOT CONFIG ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- VIEWS & DROPDOWNS ---

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="c_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(f"👤 {interaction.user.mention} has claimed this ticket.", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="c_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class TicketDropdown(discord.ui.Select):
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
        super().__init__(placeholder="Select Ticket Type", options=options, custom_id="c_dropdown")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="ticket")
        
        if not category:
            return await interaction.followup.send("❌ 'ticket' category not found!", ephemeral=True)
        
        # Permissions setup to make sure channel is visible
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"ticket-{interaction.user.name}", 
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(
            title="Ticket Support", 
            description=f"Welcome {interaction.user.mention}!\nSelected Type: **{self.values[0]}**\nStaff will be with you shortly.",
            color=discord.Color.dark_red()
        )
        await channel.send(embed=embed, view=TicketButtons())
        await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# --- BOT EVENTS ---
@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketButtons())
    print(f"🔥 Bot is online as {bot.user}")

@bot.command()
async def panel(ctx):
    embed = discord.Embed(
        title="INTELLECT-X – Official Tickets System",
        description="Welcome to the official support system. Please select your inquiry below.",
        color=discord.Color.dark_red()
    )
    embed.set_thumbnail(url="https://i.postimg.cc/L6Z52HmG/1000204859.png")
    embed.set_image(url="https://www.image2url.com/r2/default/gifs/1776315441121-f3fbcbaa-81cb-43b6-8b30-119cca261799.gif")
    await ctx.send(embed=embed, view=TicketView())

# --- RUN ---
keep_alive()
bot.run(os.getenv("DISCORD_TOKEN"))