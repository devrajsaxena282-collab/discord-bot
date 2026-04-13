import discord
from discord.ext import commands
from datetime import datetime, timedelta
from io import BytesIO
import os

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

cooldowns = {}

STAFF_ROLE = "Staff"
LOG_CHANNEL = "ticket-logs"

# ---------------- READY ----------------
@bot.event
async def on_ready():
    print(f"🔥 Bot Ready: {bot.user}")

# ---------------- BUTTON VIEW ----------------
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Claim", style=discord.ButtonStyle.primary)
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = discord.utils.get(interaction.guild.roles, name=STAFF_ROLE)

        if role not in interaction.user.roles:
            return await interaction.response.send_message(
                "❌ Staff only!",
                ephemeral=True
            )

        await interaction.channel.send(f"👤 {interaction.user.mention} claimed this ticket")

    @discord.ui.button(label="Verify Payment", style=discord.ButtonStyle.success)
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.send(
            f"💰 Payment marked as verified by {interaction.user.mention}"
        )

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        log_channel = discord.utils.get(
            interaction.guild.text_channels,
            name=LOG_CHANNEL
        )

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

            # cooldown
            if interaction.user.id in cooldowns:
                if now < cooldowns[interaction.user.id]:
                    return await interaction.followup.send(
                        "⏳ Wait before creating another ticket",
                        ephemeral=True
                    )

            cooldowns[interaction.user.id] = now + timedelta(seconds=30)

            guild = interaction.guild
            if not guild:
                return await interaction.followup.send("❌ Guild not found", ephemeral=True)

            category = discord.utils.get(guild.categories, name="ticket")
            if not category:
                return await interaction.followup.send(
                    "❌ 'ticket' category missing!",
                    ephemeral=True
                )

            # duplicate check
            for ch in category.channels:
                if str(interaction.user.id) in ch.name:
                    return await interaction.followup.send(
                        "❌ You already have a ticket!",
                        ephemeral=True
                    )

            # create channel
            channel = await guild.create_text_channel(
                name=f"ticket-{interaction.user.id}",
                category=category
            )

            # permissions
            await channel.set_permissions(guild.default_role, read_messages=False)
            await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)

            staff_role = discord.utils.get(guild.roles, name=STAFF_ROLE)
            if staff_role:
                await channel.set_permissions(staff_role, read_messages=True, send_messages=True)

            # embed
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

            await interaction.followup.send(
                f"✅ Ticket created: {channel.mention}",
                ephemeral=True
            )

        except Exception as e:
            print("ERROR:", e)
            await interaction.followup.send("❌ Bot error occurred", ephemeral=True)

# ---------------- PANEL ----------------
@bot.command()
async def panel(ctx):

    embed = discord.Embed(
        title="INTELLECT-X – Official Tickets System",
        description="""
Admin: iqs.caelis

Welcome to the official ticket system of INTELLECT-X.
Open a ticket for purchases, support, or any product-related inquiries.

━━━━━━━━━━━━━━━━━━━━━━
🧡 Rules:
• Tickets are only for purchases and support.
• Any unrelated requests = instant ban.
• Maintain respect with staff at all times.
━━━━━━━━━━━━━━━━━━━━━━

Interact with the below combo box to proceed!
━━━━━━━━━━━━━━━━━━━━━━
""",
        color=discord.Color.dark_red()
    )

    embed.set_author(
        name="INTELLECT-X Security System",
        icon_url="https://i.postimg.cc/6q1XHnPh/1000204859.png"
    )

    await ctx.send(embed=embed, view=TicketView())

# ---------------- VIEW ----------------
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketDropdown())

# ---------------- RUN ----------------
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("❌ DISCORD_TOKEN missing in environment variables")
else:
    bot.run(TOKEN)
