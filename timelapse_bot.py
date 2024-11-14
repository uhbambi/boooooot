import discord
import PIL.Image
import io
import os
import datetime
import asyncio
import aiohttp
import shutil
import subprocess

from discord.ext import commands, tasks

USER_AGENT = "ppfun historyDownload 1.0"
PPFUN_URL = "https://pixelplanet.fun"
PPFUN_STORAGE_URL = "https://storage.pixelplanet.fun"
frameskip = 1  # Número de fotogramas a omitir

# Configuración del bot de Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Función para obtener los datos del usuario desde la API de PixelPlanet
async def fetchMe():
    url = f"{PPFUN_URL}/api/me"
    headers = {'User-Agent': USER_AGENT}
    async with aiohttp.ClientSession() as session:
        attempts = 0
        while True:
            try:
                async with session.get(url, headers=headers) as resp:
                    data = await resp.json()
                    return data
            except:
                if attempts > 3:
                    print(f"Could not get {url} in three tries, cancelling")
                    raise
                attempts += 1
                await asyncio.sleep(5)

# Función para descargar los tiles del lienzo
async def fetch(session, url, offx, offy, image, bkg, needed=False):
    attempts = 0
    headers = {'User-Agent': USER_AGENT}
    while True:
        try:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 404:
                    if needed:
                        img = PIL.Image.new('RGB', (256, 256), color=bkg)
                        image.paste(img, (offx, offy))
                        img.close()
                    return
                if resp.status != 200:
                    if needed:
                        continue
                    return
                data = await resp.read()
                img = PIL.Image.open(io.BytesIO(data)).convert('RGBA')
                image.paste(img, (offx, offy), img)
                img.close()
                return
        except:
            if attempts > 3:
                raise
            attempts += 1

# Función para descargar el área seleccionada del lienzo durante un rango de fechas
async def get_area(canvas_id, canvas, x, y, w, h, start_date, end_date):
    canvas_size = canvas["size"]
    bkg = tuple(canvas['colors'][0])

    delta = datetime.timedelta(days=1)
    end_date = end_date.strftime("%Y%m%d")
    iter_date = None
    cnt = 0
    previous_day = PIL.Image.new('RGB', (w, h), color=bkg)
    while iter_date != end_date:
        iter_date = start_date.strftime("%Y%m%d")
        start_date = start_date + delta

        fetch_canvas_size = canvas_size
        if 'historicalSizes' in canvas:
            for ts in canvas['historicalSizes']:
                date = ts[0]
                size = ts[1]
                if iter_date <= date:
                    fetch_canvas_size = size

        offset = int(-fetch_canvas_size / 2)
        xc = (x - offset) // 256
        wc = (x + w - offset) // 256
        yc = (y - offset) // 256
        hc = (y + h - offset) // 256

        tasks = []
        async with aiohttp.ClientSession() as session:
            image = PIL.Image.new('RGBA', (w, h))
            for iy in range(yc, hc + 1):
                for ix in range(xc, wc + 1):
                    url = '%s/%s/%s/%s/%s/tiles/%s/%s.png' % (PPFUN_STORAGE_URL, iter_date[0:4], iter_date[4:6], iter_date[6:], canvas_id, ix, iy)
                    offx = ix * 256 + offset - x
                    offy = iy * 256 + offset - y
                    tasks.append(fetch(session, url, offx, offy, image, bkg, True))
            await asyncio.gather(*tasks)
            cnt += 1
            image.save(f'./timelapse/t{cnt}.png')
            headers = {'User-Agent': USER_AGENT}
            while True:
                async with session.get(f'{PPFUN_URL}/history?day={iter_date}&id={canvas_id}', headers=headers) as resp:
                    try:
                        time_list = await resp.json()
                        break
                    except:
                        print(f'Couldn\'t decode json for day {iter_date}, trying again')

            for i, time in enumerate(time_list):
                if i % frameskip != 0:
                    continue
                if time == '0000':
                    continue
                tasks = []
                image_rel = image.copy()
                for iy in range(yc, hc + 1):
                    for ix in range(xc, wc + 1):
                        url = f'{PPFUN_STORAGE_URL}/{iter_date[0:4]}/{iter_date[4:6]}/{iter_date[6:]}/{canvas_id}/{time}/{ix}/{iy}.png'
                        offx = ix * 256 + offset - x
                        offy = iy * 256 + offset - y
                        tasks.append(fetch(session, url, offx, offy, image_rel, bkg))
                await asyncio.gather(*tasks)
                cnt += 1
                image_rel.save(f'./timelapse/t{cnt}.png')
                if time == time_list[-1]:
                    previous_day = image_rel.copy()
                image_rel.close()
            image.close()
    previous_day.close()

# Función para eliminar las imágenes guardadas en el computador
def delete_images():
    folder = './timelapse'
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
    shutil.rmtree(folder)

# Comando del bot de Discord para iniciar la descarga paso a paso
@bot.command()
async def timelapse(ctx):
    # Paso 1: Solicitar el nombre del archivo de salida
    await ctx.send("Por favor, proporciona un nombre para el archivo de salida del timelapse (por ejemplo, 'timelapse_video').")
    try:
        name_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
        name = name_msg.content
    except asyncio.TimeoutError:
        await ctx.send("Tiempo agotado. Por favor, intenta de nuevo.")
        return

    # Paso 2: Solicitar el canvas ID
    apime = await fetchMe()
    await ctx.send("Por favor, proporciona el ID del lienzo que deseas usar.")
    for canvas_id, canvas in apime['canvases'].items():
        if 'v' not in canvas or not canvas['v']:
            await ctx.send(f"{canvas_id} = {canvas['title']}")
    
    try:
        canvas_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
        canvas_id = canvas_msg.content
    except asyncio.TimeoutError:
        await ctx.send("Tiempo agotado. Por favor, intenta de nuevo.")
        return

    if canvas_id not in apime['canvases']:
        await ctx.send("Lienzo inválido.")
        return

    canvas = apime['canvases'][canvas_id]

    # Paso 3: Solicitar las coordenadas de inicio y fin
    await ctx.send("Por favor, proporciona las coordenadas de inicio y fin en el formato 'x_y' (por ejemplo, 0_0 para inicio).")
    try:
        coords_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
        start_coords, end_coords = coords_msg.content.split()
    except asyncio.TimeoutError:
        await ctx.send("Tiempo agotado. Por favor, intenta de nuevo.")
        return

    start = start_coords.split('_')
    end = end_coords.split('_')

    # Paso 4: Solicitar las fechas de inicio y fin
    await ctx.send("Por favor, proporciona la fecha de inicio en formato YYYY-MM-DD.")
    try:
        start_date_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
        start_date = datetime.date.fromisoformat(start_date_msg.content)
    except asyncio.TimeoutError:
        await ctx.send("Tiempo agotado. Por favor, intenta de nuevo.")
        return

    await ctx.send("Por favor, proporciona la fecha de fin en formato YYYY-MM-DD. Si no deseas una fecha de fin, responde con 'hoy'.")
    try:
        end_date_msg = await bot.wait_for('message', check=lambda m: m.author == ctx.author, timeout=60)
        end_date = end_date_msg.content
        if end_date.lower() == 'hoy':
            end_date = datetime.date.today()
        else:
            end_date = datetime.date.fromisoformat(end_date)
    except asyncio.TimeoutError:
        await ctx.send("Tiempo agotado. Por favor, intenta de nuevo.")
        return

    x, y = int(start[0]), int(start[1])
    w, h = int(end[0]) - x + 1, int(end[1]) - y + 1

    if not os.path.exists('./timelapse'):
        os.mkdir('./timelapse')

    # Paso 5: Descargar y procesar los frames
    await get_area(canvas_id, canvas, x, y, w, h, start_date, end_date)

    # Paso 6: Crear el video del timelapse con ffmpeg
    await ctx.send("Creando el video del timelapse... Esto puede tomar un momento.")
    try:
        subprocess.run(['ffmpeg', '-framerate', '15', '-f', 'image2', '-i', './timelapse/t%d.png', '-c:v', 'libvpx-vp9', '-pix_fmt', 'yuva420p', f'./{name}.webm'], check=True)
        await ctx.send(file=discord.File(f'./{name}.webm'))
    except subprocess.CalledProcessError:
        await ctx.send("Hubo un error al crear el video.")

    # Paso 7: Eliminar las imágenes después de enviar el video
    delete_images()
    await ctx.send("Las imágenes temporales han sido eliminadas.")

bot.run('MTI1MDE2MzA2OTc1ODIxNDMxNg.GZfIcy.tsuRsXG3GDPThBuH_63VtonWB5Jd0soxIm3Ryg')
