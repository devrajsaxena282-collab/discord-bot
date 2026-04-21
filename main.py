import discord
from discord.ext import commands
import os
from flask import Flask
from threading import Thread

# --- Flask Server ---
app = Flask(__name__)
@app.route("/")
def home(): return "Bot is Alive"

def run(): app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- Bot Setup ---
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- Views ---
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary, custom_id="btn_claim")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket claimed!", ephemeral=True)

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="btn_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

class TicketDropdown(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=p, emoji="🔴") for p in ["BASIC PANEL", "UID BYPASS", "EMULATOR BYPASS"]]
        super().__init__(placeholder="Select Type", options=options, custom_id="ticket_dropdown")

    async def callback(self, interaction: discord.Interaction):
        # Yahan defer ka sahi istemal
        await interaction.response.defer(ephemeral=True)
        
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="ticket")
        
        if not category:
            return await interaction.followup.send("Error: 'ticket' category missing!", ephemeral=True)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True)
        }

        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await channel.send(f"Welcome {interaction.user.mention}", view=TicketButtons())
        await interaction.followup.send(f"Ticket created: {channel.mention}", ephemeral=True)

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

@bot.event
async def on_ready():
    bot.add_view(TicketView())
    bot.add_view(TicketButtons())
    print("Bot is ready")

@bot.command()
async def panel(ctx):
    await ctx.send("Select below:", view=TicketView())

keep_alive()
bot.run(os.environ.get("DISCORD_TOKEN"))