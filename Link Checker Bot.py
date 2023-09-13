import discord
import requests
import random
from discord.ext import commands, tasks

# Create a new Discord client with intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Your VirusTotal API key
API_KEY = "8c8369b766b811703c1d73d541dd4de6242984df66a7b961628d3fe771b8c7e5"

# List of status messages
status_messages = [
    "Checking Links",
    "Watching The Chat",
    "Looking To Link",
    "Checking Links Safety",
    "Checking All Links"
]

# Function to check if a link is safe using VirusTotal API
def check_link_safety(link):
    url = f"https://www.virustotal.com/vtapi/v2/url/report?apikey={API_KEY}&resource={link}"
    response = requests.get(url)
    data = response.json()

    if data["response_code"] == 1:
        if data["positives"] > 0:
            return False
        else:
            return True
    else:
        return False

@bot.event
async def on_ready():
    print("Bot is ready.")
    change_status.start()

@tasks.loop(minutes=5)  # Change status every 5 minutes
async def change_status():
    new_status = random.choice(status_messages)
    await bot.change_presence(activity=discord.Game(name=new_status))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if message.content.startswith("http://") or message.content.startswith("https://"):
        link = message.content
        is_safe = check_link_safety(link)

        if is_safe:
            await message.channel.send("This link is safe.")
        else:
            await message.channel.send("This link is potentially dangerous. Please be cautious.")
            await message.delete()

    await bot.process_commands(message)

# Run the bot with your Discord bot token
bot.run("MTA2NzYyNTc1ODUwNTMxMjMyNg.GRwyuI.COvpLyI-mqj36wjZRONLLTZU8SJS2WNMYY1Ql4")
