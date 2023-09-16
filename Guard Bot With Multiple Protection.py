import discord
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from discord.ext import commands
from itertools import cycle
import asyncio
import datetime
import time
import pytz
import os
import random
import json

intents = discord.Intents.all()
intents.members = True

# Set up the Discord client
bot = commands.Bot(command_prefix='/', intents=intents)

# Check for GPU availability and set up the device accordingly
if torch.cuda.is_available():
    device = torch.device("cuda")
else:
    device = torch.device("cpu")

# Set up the Roberta model and tokenizer for Swear And Hate Speech Detection
hate_speech_tokenizer = BertTokenizer.from_pretrained("IMSyPP/hate_speech_en")
hate_speech_model = BertForSequenceClassification.from_pretrained("IMSyPP/hate_speech_en").to(device)

# Swear/hate speech detection function
def detect_hate_speech(input_text):
    # Tokenize the input text
    input_ids = hate_speech_tokenizer.encode(input_text, return_tensors="pt").to(device)

    # Set the attention mask to 1 for all input tokens
    attention_mask = torch.ones_like(input_ids)

    # Classify the input text using the hate speech model
    outputs = hate_speech_model(input_ids=input_ids, attention_mask=attention_mask)

    # Get the predicted label
    predicted_label = outputs.logits.argmax().item()

    return predicted_label

presences = [
    "Modernization!",
    "I Care About Server Safety!",
    "Please Be Respectful To Everyone!",
    "If Someone Is Breaking Our Rules, Please Mention This To Moderators Or Admins!",
    "Don't Break Our Rules!",
    "I'm Ensuring Server Safety!"
]

# Define the path to the file where captcha completion data will be stored
storage_file = 'captcha_storage.json'

# Load existing captcha completion data from file (if it exists)
try:
    with open(storage_file, 'r') as file:
        try:
            captcha_completed = json.load(file)
        except json.JSONDecodeError:
            captcha_completed = {}
except FileNotFoundError:
    captcha_completed = {}

duplicate_messages = {}  # Dictionary to store duplicate messages

# Event handler for bot startup
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name}')

    @bot.event
    async def on_member_join(member):
        while True:
            # Generate a random captcha number
            captcha_number = random.randint(1000, 9999)

            # Send the captcha message to the member
            captcha_message = await member.send(f"Please solve the captcha in 60 seconds otherwise you will be kicked: {captcha_number}")

            # Wait for the member to provide the response
            def check(message):
                return message.content.isdigit() and message.channel == captcha_message.channel

            try:
                user_response = await bot.wait_for('message', timeout=60.0, check=check)
            except asyncio.TimeoutError:
                # If the member doesn't solve the captcha within the timeout period, kick them
                await member.kick(reason='Failed to solve the captcha.')
                return

            # Check if the response matches the captcha number
            if user_response.content == str(captcha_number):
                # If the member solves the captcha, assign them a random role from a list
                roles = ["your-role-here", "your-role-here", "your-role-here"]
                assigned_role = random.choice(roles)
                role = discord.utils.get(member.guild.roles, name=assigned_role)

                if role is None:
                    # If the role doesn't exist, log an error and return
                    print(f"Error: Role '{assigned_role}' doesn't exist in the guild.")
                    return

                try:
                    await member.add_roles(role)
                    await member.send(f"Congratulations! You have been assigned the '{assigned_role}' role.")
                    captcha_completed[str(member.id)] = True  # Mark user as completed captcha
                    save_captcha_data()  # Save the updated captcha completion data
                    break  # Break out of the loop if the captcha is solved correctly
                except discord.Forbidden:
                    # If the bot doesn't have the necessary permissions to assign roles, log an error and return
                    print("Error: Bot doesn't have the necessary permissions to assign roles.")
                    return
            else:
                # If the response doesn't match the captcha number, send an error message and allow the user to try again
                await member.send("Invalid captcha. Please try again.")

    # Set the bot's activity and status
    activity = discord.Activity(
        type=discord.ActivityType.playing,
        name="Swear Word Detection Bot"
    )
    await bot.change_presence(activity=activity, status=discord.Status.online)

    presences_cycle = cycle(presences)
    while True:
        presence = next(presences_cycle)
        presence_with_count = presence.replace("{guild_count}", str(len(bot.guilds)))
        delay = 30  # Delay in seconds, adjust as needed
        await bot.change_presence(activity=discord.Game(name=presence_with_count))
        await asyncio.sleep(delay)

# Set the duration (in seconds) for which duplicate messages should be remembered
DUPLICATE_DURATION = 5

# Dictionary to store duplicate messages and their timestamps
duplicate_messages = {}

# Event handler for incoming messages
@bot.event
async def on_message(message):
    if isinstance(message.channel, discord.DMChannel) and str(message.author.id) not in captcha_completed:
        # Block the user from sending messages if they haven't completed the captcha
        await message.author.send("Please complete the captcha to send messages.")
        await message.delete()
    else:
        await bot.process_commands(message)


def save_captcha_data():
    with open(storage_file, 'w') as file:
        json.dump(captcha_completed, file)


@bot.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == bot.user:
        return

    # Log the message in a text file
    log_chat_message(message)

    # Check if the message is in full caps
    if message.content.isupper():
        # Delete the message in full caps
        await message.delete()

        # Send a warning message
        warning_message = await message.channel.send(f"{message.author.mention}, please avoid sending messages in full capitalization.")

        # Delete the warning message after 5 seconds
        await asyncio.sleep(5)
        await warning_message.delete()

        return

    # Initialize the message_limits dictionary if not already initialized
    if not hasattr(bot, 'message_limits'):
        bot.message_limits = {}

    # Check if the message is a duplicate
    if message.content in duplicate_messages:
        # Get the timestamp of the duplicate message
        timestamp = duplicate_messages[message.content]
        current_time = time.time()

        # Check if the duplicate message is still within the duration
        if current_time - timestamp <= DUPLICATE_DURATION:
            # Delete the duplicate message
            await message.delete()

            # Send a warning message
            warning_message = await message.channel.send(
                f"{message.author.mention}, please refrain from sending duplicate messages.")

            # Delete the warning message after 5 seconds
            await asyncio.sleep(5)
            await warning_message.delete()

            return
        else:
            # Remove the expired duplicate message from the dictionary
            del duplicate_messages[message.content]

    # Store the message and its timestamp as a potential duplicate
    duplicate_messages[message.content] = time.time()

    # Check if the message contains swear words
    swear_label = detect_hate_speech(message.content)
    if swear_label == 1:
        # Delete the message containing swear words
        await message.delete()

        # Send a warning message
        warning_message = await message.channel.send(f"{message.author.mention}, please refrain from using inappropriate language.")

        # Delete the warning message after 5 seconds
        await asyncio.sleep(5)
        await warning_message.delete()

        return

    # Check if the message is in full caps
    if message.content.isupper():
        # Delete the message in full caps
        await message.delete()

        # Send a warning message
        warning_message = await message.channel.send(f"{message.author.mention}, please avoid sending messages in full capitalization.")

        # Delete the warning message after 5 seconds
        await asyncio.sleep(5)
        await warning_message.delete()

        return

    # Limit message rate to 1 message per second
    current_time = time.time()
    author_id = message.author.id
    if author_id in bot.message_limits:
        message_times = bot.message_limits[author_id]
        message_times.append(current_time)
        # Remove messages sent more than 1 second ago
        message_times = [t for t in message_times if current_time - t <= 1]
        bot.message_limits[author_id] = message_times
        if len(message_times) > 1:
            # Delete the message exceeding the rate limit
            await message.delete()
            return
    else:
        bot.message_limits[author_id] = [current_time]

    await bot.process_commands(message)  # Process other commands

def log_chat_message(message):
    with open("chat_history.txt", "a", encoding="utf-8") as file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        author_name = f"{message.author.name} ({message.author.id})"
        content = message.content

        file.write(f"{timestamp} | {author_name}: {content}\n")

log_directory = "logs"
log_file = "anti_raid_log.txt"  # File name for the log file
log_path = os.path.join(log_directory, log_file)

log_directory = "logs"
log_file = "member_leave_log.txt"  # File name for the log file
log_path = os.path.join(log_directory, log_file)


# Ensure the log directory exists
os.makedirs(log_directory, exist_ok=True)

# Event handler for guild member leave
@bot.event
async def on_member_remove(member):
    log_member_leave(member)

def log_member_leave(member):
    with open("member_leave_log.txt", "a", encoding="utf-8") as file:
        current_time = datetime.datetime.now().strftime("%H:%M:%S")
        leave_date = datetime.datetime.now().strftime("%Y-%m-%d")
        member_name = member.name
        old_member_name = member.nick or None
        member_id = member.id
        file.write(f"{leave_date} | {current_time} | User: {member_name} | Old User: {old_member_name} | ID: {member_id}\n")

# Event handler for guild member join
@bot.event
async def on_member_join(member):
    guild = member.guild
    join_timestamp = join_timestamps.get(guild.id)
    current_time = time.time()

    # Check if join_timestamp exists and the time difference is within the allowed window
    if join_timestamp and current_time - join_timestamp <= 30:
        # Get the list of members joined within the window
        joined_members = [m for m in guild.members if m.joined_at and current_time - m.joined_at.timestamp() <= 30]

        # Check if the number of joined members exceeds the allowed limit (2 in this case)
        if len(joined_members) > 2:
            # Kick the member
            await member.kick(reason="Possible raid attempt")

            # Send a log message to a specific channel
            log_channel_id = 123456789  # Replace with your desired log channel ID
            log_channel = guild.get_channel(log_channel_id)
            if log_channel is not None:
                kick_message = f"Possible raid attempt detected. Kicked user: {member.display_name}"
                joined_members_names = [m.display_name for m in joined_members]
                info_message = f"Currently joined members within the 30-second window: {', '.join(joined_members_names)}"
                invite_link = await guild.text_channels[0].create_invite(max_uses=1)
                invite_message = f"Invite Link: {invite_link.url}"
                await log_channel.send(f"{kick_message}\n{info_message}\n{invite_message}")

    join_timestamps[guild.id] = current_time

    # Log the anti-raid event
    log_anti_raid_event(member)

def log_anti_raid_event(member):
    with open(log_path, "a", encoding="utf-8") as file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        member_info = f"{member.name} ({member.id})"
        old_name = member.name
        if member.nick:
            old_name = f"{member.nick} (nickname)"

        log_message = f"{timestamp} | Member joined: {member_info} | Old name: {old_name}"
        file.write(log_message + "\n")
        print(log_message)

@bot.event
async def on_member_join(member):
    # Replace 'Your Role Name' with the name of the role you want to assign
    role = discord.utils.get(member.guild.roles, name='Your Role Name')

    if role is not None:
        await member.add_roles(role)
        print(f"Assigned role {role.name} to {member.display_name}")

# Event handler for voice state update
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        # User joined or left a voice channel
        if before.channel is not None:
            # User left a voice channel
            if before.channel is not None:
                log_voice_chat(member, before.channel, after.channel)

def log_voice_chat(member, old_voice_channel, new_voice_channel):
    if old_voice_channel is None and new_voice_channel is None:
        return  # Ignore if both old and new voice channels are None

    with open("voice_history.txt", "a", encoding="utf-8") as file:
        timestamp = datetime.datetime.now(pytz.utc).strftime("%Y-%m-%d %H:%M:%S")
        member_name = f"{member.name} ({member.id})"
        old_nick = member.nick or member.name
        new_nick = member.nick or member.name
        old_voice_channel_name = old_voice_channel.name if old_voice_channel else None
        new_voice_channel_name = new_voice_channel.name if new_voice_channel else None

        if old_voice_channel and new_voice_channel:
            time_passed = datetime.datetime.now() - old_voice_channel.voice_states[member].channel.created_at
            time_passed_str = str(time_passed)
            file.write(
                f"{timestamp} | {member_name} | Old Nickname: {old_nick} | New Nickname: {new_nick} | Old Voice Channel: {old_voice_channel_name} | New Voice Channel: {new_voice_channel_name} | Time Passed: {time_passed_str}\n"
            )
        else:
            file.write(
                f"{timestamp} | {member_name} | Old Nickname: {old_nick} | New Nickname: {new_nick} | Old Voice Channel: {old_voice_channel_name} | New Voice Channel: {new_voice_channel_name}\n"
            )

nickname_history = {}  # Dictionary to store nickname history

@bot.event
async def on_member_update(before, after):
    member_id = after.id
    old_nickname = before.nick or before.name
    new_nickname = after.nick or after.name

    if old_nickname != new_nickname:
        # Update the nickname history
        if member_id in nickname_history:
            nickname_history[member_id].append((old_nickname, new_nickname))
        else:
            nickname_history[member_id] = [(old_nickname, new_nickname)]

        # Log the nickname change
        log_nickname_change(member_id, nickname_history[member_id])

def log_nickname_change(member_id, nickname_history):
    with open("nickname_history.txt", "a", encoding="utf-8") as file:
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file.write(f"{timestamp} | Member ID: {member_id} | Nickname History: {nickname_history}\n")

# Run the bot
bot.run('your-token-here')
