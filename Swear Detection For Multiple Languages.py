import random
import discord
from discord.ext import commands, tasks
import asyncio
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch

# Initialize tokenizer and model
def initialize_sentiment_analysis():
    tokenizer = AutoTokenizer.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")
    model = AutoModelForSequenceClassification.from_pretrained("cardiffnlp/twitter-xlm-roberta-base-sentiment")
    return tokenizer, model

# Perform sentiment analysis on text
def perform_sentiment_analysis(tokenizer, model, text: str) -> int:
    inputs = tokenizer.encode_plus(
        text,
        add_special_tokens=True,
        return_tensors="pt"
    )
    outputs = model(**inputs)
    predictions = torch.argmax(outputs.logits, dim=1)
    return predictions.item()

# Discord bot setup
def setup_discord_bot():
    intents = discord.Intents.default()
    intents.message_content = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'Bot is ready. Logged in as {bot.user}')
        update_status.start()

    @tasks.loop(minutes=1)
    async def update_status():
        await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=get_random_status()))

    @bot.event
    async def on_message(message):
        if message.author == bot.user:
            return

        tokenizer, model = initialize_sentiment_analysis()
        sentiment = perform_sentiment_analysis(tokenizer, model, message.content)

        if sentiment == 0:
            await message.delete()
            warning_message = await message.channel.send(f'{message.author.mention}, please refrain from using inappropriate language.')
            await asyncio.sleep(10)
            await warning_message.delete()

        await bot.process_commands(message)

    return bot

def get_random_status():
    statuses = [
        "Hello, world!",
        "I'm here to help!",
        "Ready to analyze messages.",
        "Let's keep the chat clean!",
    ]
    return random.choice(statuses)

# Replace 'YOUR_BOT_TOKEN' with your actual bot token
bot.run('your-discord-token-here')
