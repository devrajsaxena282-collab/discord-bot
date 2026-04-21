import discord
from discord.ext import commands
from io import BytesIO
import os
from flask import Flask
from threading import Thread

# --- Flask Server (Keep Alive) ---
app = Flask(__name__)
@app.route("/")
def home(): return "OK"
def run(): app.run(host="0.0.0.0", port=8080)
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ----------------- BUTTONS -----------------
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="btn_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket claimed!", ephemeral=True)

    @discord.ui.button(label="Verify Payment", style=discord.ButtonStyle.success, custom_id="btn_verify")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Payment verified!", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="btn_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# ----------------- DROPDOWN -----------------
class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=p, emoji="🔴") for p in ["BASIC PANEL", "UID BYPASS", "EMULATOR BYPASS", "CUSTOM PANEL", "AIMSILENT EXE", "AIMSILENT APK", "STREAMER PANEL", "INTERNAL MAX", "AIMKILL EXE", "OPTIMIZATION", "WINDOWS 10 PRO", "WINDOWS 11 PRO", "MS OFFICE 2021 PREMIUM", "MS 365 PREMIUM", "DEVICE ROOTING", "DRIP CLIENT", "BR MOD", "HG CHEATS", "KOS ROOT"]]
        super().__init__(placeholder="Select Ticket Type", options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        user = interaction.user
        
        # 1. Category verify karein
        category = discord.utils.get(guild.categories, name="ticket")
        if not category:
            return await interaction.followup.send("❌ 'ticket' category nahi mili!", ephemeral=True)
        
        # 2. Permissions override
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
        }
        
        # 3. Channel create karein
        try:
            channel = await guild.create_text_channel(
                name=f"ticket-{user.name}",
                category=category,
                overwrites=overwrites
            )
            
            # Embed bhejein
            embed = discord.Embed(title="INTELLECT-X Support", description=f"Type: **{self.values[0]}**", color=discord.Color.dark_red())
            await channel.send(content=user.mention, embed=embed, view=TicketButtons())
            await interaction.followup.send(f"✅ Ticket created: {channel.mention}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketButtons())
    print(f"🔥 Bot Online: {bot.user}")

@bot.command()
async def panel(ctx):
    embed = discord.Embed(title="INTELLECT-X – Official Tickets", description="Select your inquiry below.", color=discord.Color.dark_red())
    embed.set_thumbnail(url="https://i.postimg.cc/L6Z52HmG/1000204859.png")
    embed.set_image(url="https://www.image2url.com/r2/default/gifs/1776315441121-f3fbcbaa-81cb-43b6-8b30-119cca261799.gif")
    await ctx.send(embed=embed, view=TicketView())

keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))