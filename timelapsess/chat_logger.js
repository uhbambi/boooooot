const puppeteer = require('puppeteer');
const { Client, GatewayIntentBits } = require('discord.js');

// Configura el bot de Discord
const client = new Client({ intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages] });
const DISCORD_TOKEN = 'MTI1MDE2MzA2OTc1ODIxNDMxNg.GZfIcy.tsuRsXG3GDPThBuH_63VtonWB5Jd0soxIm3Ryg'; // Pon tu token aquí
const CHANNEL_ID = '1305991556242735134'; // Pon el ID de tu canal aquí

// Función para monitorear la página
async function monitorPage() {
    const browser = await puppeteer.launch({ headless: false }); // Ejecuta Puppeteer
    const page = await browser.newPage();
    await page.goto('https://pixelplanet.fun/chat/907'); // Pon la URL de la página

    // Espera hasta que el contenedor de mensajes esté disponible
    await page.waitForSelector('.chatmsg'); // Esperamos al contenedor de mensajes

    // Expón una función para enviar mensajes a Discord
    await page.exposeFunction('sendMessageToDiscord', async (message) => {
        const filteredMessage = message.replace(/(@everyone|@here)/g, '[MENCIÓN FILTRADA]');
        const formattedMessage = `**[${new Date().toLocaleString()}]** ***${message.split(":")[0]}:*** \`${filteredMessage}\``;

        const channel = await client.channels.fetch(CHANNEL_ID);
        await channel.send(formattedMessage);
    });

    // Inicia un MutationObserver para observar los nuevos mensajes
    await page.evaluate(() => {
        const observer = new MutationObserver((mutationsList) => {
            for (const mutation of mutationsList) {
                if (mutation.type === 'childList') {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === Node.ELEMENT_NODE && node.matches('.chatmsg')) {
                            const time = node.querySelector('.chatts') ? node.querySelector('.chatts').innerText : 'Hora no disponible';
                            const user = node.querySelector('.chatname') ? node.querySelector('.chatname').innerText : 'Usuario no disponible';
                            const text = node.querySelector('.msg') ? node.querySelector('.msg').innerText : 'Mensaje no disponible';

                            const message = `[${time}] ${user}: ${text}`;
                            window.sendMessageToDiscord(message);
                        }
                    });
                }
            }
        });

        const container = document.querySelector('.chatmsg');
        if (container) {
            observer.observe(container.parentElement, { childList: true, subtree: true });
        }
    });
}

// Inicia el bot de Discord
client.once('ready', () => {
    console.log('Bot conectado a Discord');
    monitorPage();
});

client.login(DISCORD_TOKEN);
