import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from dotenv import load_dotenv
import os
import time
import re

# Carga el archivo .env
load_dotenv()
DISCORD_TOKEN = ("MTI1MDE2MzA2OTc1ODIxNDMxNg.GZfIcy.tsuRsXG3GDPThBuH_63VtonWB5Jd0soxIm3Ryg")  # Cargar el token desde la variable de entorno

# Resto de tu código...

# Configura los intents para permitir leer el contenido de los mensajes
intents = discord.Intents.default()
intents.message_content = True  # Habilitar la intención de contenido del mensaje

bot = commands.Bot(command_prefix="!", intents=intents)

# Función para hacer la captura de pantalla
def capture_screenshot(url):
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(url)
    time.sleep(3)  # Ajusta el tiempo de espera
    
    screenshot_path = "screenshot.png"
    driver.save_screenshot(screenshot_path)
    driver.quit()
    
    return screenshot_path

# Función para ajustar el link y reemplazar la parte final con "0"
def adjust_url(url):
    adjusted_url = re.sub(r'(-?\d+)$', '0', url)
    return adjusted_url

# Comando chilecap para capturar la pantalla de la zona de PixelPlanet
@bot.command(name="chilecap")
async def chilecap(ctx, url: str):
    await ctx.send("Tomando captura de pantalla de la zona...")
    adjusted_url = adjust_url(url)
    screenshot_path = capture_screenshot(adjusted_url)
    await ctx.send(file=discord.File(screenshot_path))

# Inicia el bot
bot.run(DISCORD_TOKEN)
