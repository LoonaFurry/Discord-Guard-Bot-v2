import discord
import requests

# Create a new Discord client with intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Your VirusTotal API key
API_KEY = "your-virustotal-api-key"

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

# Event triggered when the bot is ready and connected to Discord
@client.event
async def on_ready():
    print("Bot is ready.")

# Event triggered when a message is received
@client.event
async def on_message(message):
    # Ignore messages sent by the bot itself to prevent an infinite loop
    if message.author == client.user:
        return

    # Check if the message contains a link
    if message.content.startswith("http://") or message.content.startswith("https://"):
        link = message.content

        # Check the safety of the link using VirusTotal API
        is_safe = check_link_safety(link)

        if is_safe:
            await message.channel.send("This link is safe.")
        else:
            await message.channel.send("This link is potentially dangerous. Please be cautious.")

            # Delete the message containing the dangerous link
            await message.delete()

# Run the bot with your Discord bot token
client.run("your-token-here")