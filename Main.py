import discord
import random
import asyncio
from discord import Client, Game, File
from discord.ext.commands import Bot
import pickle
import requests

import configparser
from os.path import exists
import re

config = configparser.ConfigParser()
if exists('variables.ini'):
    config.read('variables.ini')
else:
    config.read('defaultVariables.ini')

HIGHLIGHT_CHANNEL_ID = config['DEFAULT']['HIGHLIGHT_CHANNEL_ID']
ANIMAL_CHANNEL_ID = config['DEFAULT']['ANIMAL_CHANNEL_ID']
GENERAL_CHANNEL_ID = config['DEFAULT']['GENERAL_CHANNEL_ID']
LOG_CHANNEL_ID = config['DEFAULT']['LOG_CHANNEL_ID']
TOKEN = config['DEFAULT']['TOKEN']
TOKEN_MASTER = config['DEFAULT']['TOKEN_MASTER']
FORBIDDEN_WORD = config['DEFAULT']['FORBIDDEN_WORD']
FORBIDDEN_NUMBERS = config['DEFAULT']['FORBIDDEN_NUMBERS']
prefix = config['DEFAULT']['prefix']
bank = {}

client = Bot(command_prefix=prefix)


async def load_bank():
    """
    Loads the "bank" file from the log channel specified by the log channel variable
    :return: None
    """
    global bank
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    messages = []
    async for message in log_channel.history(limit=3):
        if not len(message.attachments) == 0:
            messages.append(message)
    if len(messages) != 0:
        url = messages[0].attachments[0].url
        bank_request = requests.get(url)
        with open("bank.bin", 'wb') as f:
            f.write(bank_request.content)
        with open("bank.bin", "rb") as f:
            bank = pickle.load(f)


async def save_bank():
    """
    Saves the bank by creating a file using the "bank: map variable and uploading it to the log channel
    specified by LOG_CHANNEL_ID
    :return: None
    """
    global bank
    log_channel = client.get_channel(LOG_CHANNEL_ID)
    with open("bank.bin", "wb") as f:
        pickle.dump(bank, f)
    bank_file = File('bank.bin')
    await log_channel.send("file", file=bank_file)
    bank_file.close()


@client.event
async def on_ready():
    """
    Attempts to change discord status and load the bank from the log channel specified by LOG_CHANNEL_ID
    :return: None
    """
    print("logged in")
    await client.change_presence(activity=Game(name='Sifting through your filth'))
    try:
        await load_bank()
        print(bank)
    except FileNotFoundError:
        print("no file found")
    except EOFError:
        print("Empty File")


@client.event
async def on_disconnect():
    """
    Attempts to save the bank
    :return: None
    """
    print("logged out")
    try:
        await save_bank()
    except FileNotFoundError:
        print("no file found")


async def periodic_updates():
    """
    Defines a function that calls necessary update functions periodically
    :return: None
    """
    await client.wait_until_ready()
    while not client.is_closed():
        await asyncio.sleep(14400)
        await save_bank()


async def send_highlight(channel, from_channel):
    """
    Sends a "highlight" to the specified channel by selecting a random image attachment
    from the discord channel specified by HIGHLIGHT_CHANNEL_ID
    :param from_channel: the channel to get the highlight from
    :param channel: the channel to send the highlight to
    :return:
    """
    highlight_channel = client.get_channel(from_channel)
    messages = []
    async for message in highlight_channel.history(limit=10000):
        if not len(message.attachments) == 0:
            messages.append(message)
    highlight_message = random.choice(messages)
    print(highlight_message.author)
    for attachment in highlight_message.attachments:
        print(attachment.url)
        await channel.send(attachment.url)


@client.command()
async def coin_flip(ctx):
    """
    Simulates a coin_flip
    :param ctx: the Discord.py Context in which the command was invoked
    :return: a string representing the result of the flip
    """
    result_string = "The coin landed on heads" if random.random() > .5 else "The coin landed on tails"
    await ctx.channel.send(result_string)


@client.command()
async def highlight(context):
    """
    Sends a highlight to the channel the context belongs to
    :param context: the Discord.py Context in which the command was invoked
    :return: None
    """
    await send_highlight(context.channel, HIGHLIGHT_CHANNEL_ID)


@client.command()
async def animal(context):
    """
    sends a animal picture to the channel specified by context
    :param context:
    :return: None
    """
    await send_highlight(context.channel, ANIMAL_CHANNEL_ID)


@client.command(pass_context=True)
async def save(ctx):
    """
    saves the bank
    :param ctx: the Discord.py Context in which the command was invoked
    :return: None
    """
    await save_bank()
    await ctx.message.channel.send("saved successfully")


@client.command(pass_context=True)
async def add_tokens(ctx):
    """
    adds tokens to the user (without affecting the caller's "balance") specified by the second token of the message in
    ctx (only accessible to the user specified by the TOKEN_MASTER_ID variable)
    :param ctx: the Discord.py Context in which the command was invoked
    :return: None
    """
    number = ctx.message.content.split()[1]
    if ctx.message.author.id == TOKEN_MASTER:
        for receiver in ctx.message.mentions:
            if receiver.id not in bank.keys():
                bank[receiver.id] = int(number)
            else:
                bank[receiver.id] += int(number)
        await ctx.message.channel.send("successfully added {} 𝘄𝘁".format(int(number)))
        return
    await ctx.message.channel.send("you are not authorized to use this command, bitch")


@client.command(pass_context=True)
async def give_tokens(ctx):
    """
    gives tokens to the user specified by the second token of the message in ctx by subtracting them from the current
    user's balance and adding them to the specified user
    :param ctx:
    :return: None
    """
    number = ctx.message.content.split()[1]
    print(ctx.message.author.id)
    receiver = ctx.message.mentions[0]
    if int(number) >= 0:
        if ctx.message.author.id not in bank.keys() or bank[ctx.message.author.id] < int(number):
            await ctx.message.channel.send("not enough 𝘄𝘁 to give")
            return
        if receiver.id not in bank.keys():
            bank[receiver.id] = int(number)
            bank[ctx.message.author.id] -= int(number)
            await ctx.message.channel.send("successfully gave {} {} 𝘄𝘁".format(receiver, int(number)))
            return
        bank[receiver.id] += int(number)
        bank[ctx.message.author.id] -= int(number)
        await ctx.message.channel.send("successfully gave {} {} 𝘄𝘁".format(receiver, int(number)))
        return


@client.command(pass_context=True)
async def see_all_tokens(ctx):
    """
    Prints a list of all the users and their balances in the Discord.py Channel specified by ctx
    :param ctx: The Discord.py Context in which the command was invoked
    :return: None
    """
    for id in bank.keys():
        await ctx.message.channel.send("{}: {} 𝘄𝘁".format(await ctx.message.guild.fetch_member(id), bank[id]))
    return


@client.command(pass_context=True)
async def see_tokens(ctx):
    """
    Shows the balance of the user specified by the second token of the message in ctx
    (i.e, sends a message representing the user's balance to the channel in which the command was called)
    :param ctx: The Discord.py Context in which the command was invoked
    :return: None
    """
    if ctx.message.author.id == TOKEN_MASTER:
        receiver = ctx.message.mentions[0]
        if receiver.id not in bank.keys():
            await ctx.message.channel.send("{} has 0 𝘄𝘁".format(receiver))
            return
        await ctx.message.channel.send("{} has {} 𝘄𝘁".format(receiver, bank[receiver.id]))
        return
    await ctx.message.channel.send("you are not authorized to use this command, bitch")


@client.command(pass_context=True)
async def clear_tokens_for_all_users(ctx):
    """
    clears the balance for every user (only accessible to the user specified by TOKEN_MASTER_ID)
    :param ctx: The Discord.py Context in which the command was invoked
    :return: None
    """
    if ctx.message.author.id == TOKEN_MASTER:
        global bank
        bank = {}
        await ctx.message.channel.send("cleared all tokens")
        return
    await ctx.message.channel.send("you are not authorized to use this command, bitch")


@client.command(pass_context=True)
async def tokens(ctx):
    """
    Shows the calling user's balance (i.e, sends a message representing the user's balance to the channel in which the
    command was called)
    :param ctx: The Discord.py Context in which the command was invoked
    :return: None
    """
    if ctx.message.author.id not in bank.keys():
        await ctx.message.channel.send("You have 0 𝘄𝘁")
        return
    await ctx.message.channel.send("You have {} 𝘄𝘁".format(bank[ctx.message.author.id]))


async def check_for_word(word, message):
    lowercase_text = message.content.lower()
    if word in lowercase_text:
        await message.channel.send(":oncoming_police_car: :oncoming_police_car: :oncoming_police_car: "
                                   "YOU SAID THE NO NO WORD :oncoming_police_car: :oncoming_police_car: "
                                   ":oncoming_police_car: \n :regional_indicator_j: :regional_indicator_a: "
                                   ":regional_indicator_i: :regional_indicator_l: ")


async def check_for_number(word, message):
    lowercase_text = message.content.lower()
    if word in lowercase_text:
        await message.channel.send("AHAHAHA, YOU JUST SAID THE FUNNY NUMBER :sob::sob::sob:\n COMEDY PERSON!")

client.loop.create_task(periodic_updates())
client.run(TOKEN)




