#!/usr/bin/env python3
import json, os, logging, threading, asyncio
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from urllib.parse import quote

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN    = "8616508368:AAH6P6rlQXU0ZzQl6SSjC9OW8ZEbPkZABHQ"
ADMIN_ID = 8464360679
DATA_FILE = "boutique_data.json"
WEBAPP_URL = "https://mon-bot-telegram-production-d0ae.up.railway.app/webapp.html"
PORT = int(os.environ.get("PORT", 8080))
STATUTS = ["📦 Commande reçue", "✅ Confirmée", "🔄 En préparation", "🚚 En livraison", "✅ Livrée"]
DEFAULT_DATA = {
    "bienvenue": "👋 Bonjour *{prenom}* ! Bienvenue chez *Allo J'arrive 69* 🚀\n\nClique ci-dessous 👇",
    "produits": [], "commandes": [], "avis": [],
    "codes_promo": {"BIENVENUE": 10, "VIP20": 20}, "compteur_commande": 1,
}

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f: return json.load(f)
    return DEFAULT_DATA.copy()

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(uid): return uid == ADMIN_ID

def get_webapp_url():
    data = load()
    return f"{WEBAPP_URL}?products={quote(json.dumps(data.get('produits',[]),ensure_ascii=False))}&promos={quote(json.dumps(data.get('codes_promo',{}),ensure_ascii=False))}"

# Loop global pour envoyer des messages depuis le serveur web
MAIN_LOOP = None
BOT_TOKEN = TOKEN

async def notify_admin(order):
    """Envoie notification admin via API Telegram directement"""
    import urllib.request
    data = load()
    cmd_id = f"CMD{data.get('compteur_commande',1):03d}"
    data["compteur_commande"] = data.get("compteur_commande",1) + 1
    user_info = order.get("user") or {}
    prenom = user_info.get("first_name","Client") if isinstance(user_info,dict) else "Client"
    username = user_info.get("username","—") if isinstance(user_info,dict) else "—"
    user_id = user_info.get("id",0) if isinstance(user_info,dict) else 0
    commande = {
        "id": cmd_id, "user": f"{prenom} (@{username})", "user_id": user_id,
        "items": order.get("items",[]), "produit": ", ".join([i["nom"] for i in order.get("items",[])]),
        "total": order.get("total",0), "remise": order.get("remise",0),
        "adresse": order.get("adresse","—"), "telephone": order.get("telephone","—"),
        "statut": "📦 Commande reçue", "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
    }
    data["commandes"].append(commande)
    save(data)
    items_text = "\n".join([f"  • {i['nom']} x{i['qty']} — {i['prix']}" for i in order.get("items",[])])
    msg = (f"🛒 *Nouvelle commande {cmd_id}!*\n\n"
           f"👤 {prenom} (@{username})\n\n{items_text}\n\n"
           f"💰 Total: {order.get('total',0)}€\n📍 {order.get('adresse','—')}\n"
           f"📱 {order.get('telephone','—')}\n📅 {commande['date']}")
    # Appel direct API Telegram
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": ADMIN_ID, "text": msg, "parse_mode": "Markdown"}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type":"application/json"})
    urllib.request.urlopen(req, timeout=10)
    return cmd_id

class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def send_cors(self, code=200):
        self.send_response(code)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
    def do_OPTIONS(self):
        self.send_cors(); self.send_header("Content-Length","0"); self.end_headers()
    def do_GET(self):
        path = self.path.split("?")[0]
        fname = "webapp.html" if path in ("/","/webapp.html") else path.lstrip("/")
        if os.path.exists(fname):
            with open(fname,"rb") as f: content = f.read()
            self.send_cors()
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.send_header("Content-Length",str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_cors(404); self.end_headers()
    def do_POST(self):
        if self.path == "/commande":
            try:
                length = int(self.headers.get("Content-Length",0))
                order = json.loads(self.rfile.read(length))
                # Envoyer notification de façon synchrone
                loop = asyncio.new_event_loop()
                cmd_id = loop.run_until_complete(notify_admin(order))
                loop.close()
                self.send_cors()
                self.send_header("Content-Type","application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"ok":True,"cmd_id":cmd_id}).encode())
            except Exception as e:
                logging.error(f"Erreur POST /commande: {e}")
                self.send_cors(500); self.end_headers()
                self.wfile.write(json.dumps({"ok":False,"error":str(e)}).encode())
        else:
            self.send_cors(404); self.end_headers()

def start_web_server():
    HTTPServer(("0.0.0.0", PORT), WebHandler).serve_forever()

# Menus
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url=get_webapp_url()))],
        [InlineKeyboardButton("📋 Mes commandes", callback_data="mes_commandes")],
        [InlineKeyboardButton("⭐ Avis", callback_data="voir_avis")],
        [InlineKeyboardButton("🎧 Support", callback_data="support")],
        [InlineKeyboardButton("📞 Contact", callback_data="contact")],
    ])

def menu_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Gérer produits",  callback_data="admin_produits")],
        [InlineKeyboardButton("➕ Ajouter produit", callback_data="admin_ajouter")],
        [InlineKeyboardButton("📋 Commandes",       callback_data="admin_commandes")],
        [InlineKeyboardButton("📊 Stats",           callback_data="admin_stats")],
        [InlineKeyboardButton("🎟️ Codes promo",    callback_data="admin_promos")],
        [InlineKeyboardButton("✏️ Message /start",  callback_data="admin_bienvenue")],
        [InlineKeyboardButton("🌐 Voir boutique",   web_app=WebAppInfo(url=get_webapp_url()))],
    ])

def menu_admin_produits():
    data = load()
    kb = [[InlineKeyboardButton(f"✏️ {p['nom']}", callback_data=f"admin_edit_{i}")] for i,p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)

def menu_admin_edit(i):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Nom",         callback_data=f"admin_edit_nom_{i}")],
        [InlineKeyboardButton("📝 Description", callback_data=f"admin_edit_desc_{i}")],
        [InlineKeyboardButton("📸 Photo",       callback_data=f"admin_edit_photo_{i}")],
        [InlineKeyboardButton("🏷️ Badge",      callback_data=f"admin_edit_badge_{i}")],
        [InlineKeyboardButton("🗑️ Supprimer",  callback_data=f"admin_suppr_{i}")],
        [InlineKeyboardButton("⬅️ Retour",      callback_data="admin_produits")],
    ])

def btn_retour():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]])

def menu_statut(cmd_id):
    kb = [[InlineKeyboardButton(s, callback_data=f"statut_{cmd_id}_{i}")] for i,s in enumerate(STATUTS)]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")])
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load()
    u = update.effective_user
    await update.message.reply_text(data["bienvenue"].replace("{prenom}", u.first_name), parse_mode="Markdown", reply_markup=menu_principal())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé."); return
    await update.message.reply_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())

async def repondre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if len(context.args) < 2:
        await update.message.reply_text("Format : `/repondre USER_ID message`", parse_mode="Markdown"); return
    try:
        await update.get_bot().send_message(int(context.args[0]), f"💬 *Boutique :*\n\n{' '.join(context.args[1:])}", parse_mode="Markdown")
        await update.message.reply_text("✅ Envoyé !")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not context.args: await update.message.reply_text("Format : `/broadcast message`", parse_mode="Markdown"); return
    data = load()
    envoyes = 0
    for uid in set([c["user_id"] for c in data["commandes"]]):
        try: await update.get_bot().send_message(uid, f"📢 {' '.join(context.args)}"); envoyes += 1
        except: pass
    await update.message.reply_text(f"✅ Envoyé à {envoyes} clients !")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    data = load()
    uid = q.from_user.id

    if d == "menu": await q.edit_message_text("🏠 Menu", reply_markup=menu_principal())
    elif d == "support": await q.edit_message_text("🎧 Support\n\n📦 Suivi: envoie ton numéro de commande\n📧 contact@alloj arrive69.com", reply_markup=btn_retour())
    elif d == "contact": await q.edit_message_text("📞 Contact\n\n📱 +33 6 00 00 00 00\n📧 contact@alloj arrive69.com", reply_markup=btn_retour())
    elif d == "mes_commandes":
        mes = [c for c in data["commandes"] if c["user_id"] == uid]
        if not mes: await q.edit_message_text("📋 Pas encore de commande.", reply_markup=menu_principal()); return
        texte = "📋 *Tes commandes :*\n\n" + "".join([f"🔖 #{c['id']} — {c.get('total',0)}€\n📍 {c['statut']}\n\n" for c in mes[-5:]])
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=menu_principal())
    elif d == "voir_avis":
        avis = data.get("avis",[])
        texte = "⭐ *Avis :*\n\n" + "".join([f"{'⭐'*a['note']} {a['nom']}\n{a['texte']}\n\n" for a in avis[-5:]]) if avis else "⭐ Pas encore d'avis !"
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]]))
    elif d == "admin_menu" and is_admin(uid): await q.edit_message_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())
    elif d == "admin_produits" and is_admin(uid): await q.edit_message_text("📦 *Produits :*", parse_mode="Markdown", reply_markup=menu_admin_produits())
    elif d == "admin_ajouter" and is_admin(uid):
        context.user_data.update({"nouveau_produit": {}, "ajout_etape": "nom"})
        await q.edit_message_text("➕ *Nouveau produit*\n\n1️⃣ Envoie le *nom* :", parse_mode="Markdown")
    elif d == "admin_stats" and is_admin(uid):
        ca = sum([c.get("total",0) for c in data["commandes"]])
        await q.edit_message_text(f"📊 *Stats :*\n\n📦 Commandes : {len(data['commandes'])}\n💰 CA : {ca}€\n📦 Produits : {len(data['produits'])}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))
    elif d == "admin_commandes" and is_admin(uid):
        commandes = data["commandes"]
        texte = "📋 *Commandes :*\n\n" if commandes else "📋 Aucune commande."
        for c in commandes[-8:]:
            items = ", ".join([f"{i['nom']} x{i['qty']}" for i in c.get("items",[])])
            texte += f"🔖 #{c['id']} — {c['user']}\n📦 {items}\n💰 {c.get('total',0)}€\n📱 {c.get('telephone','—')}\n📍 {c['statut']}\n\n"
        kb = [[InlineKeyboardButton(f"📍 #{c['id']}", callback_data=f"chg_statut_{c['id']}")] for c in commandes[-5:]]
        kb += [[InlineKeyboardButton("🗑️ Vider", callback_data="admin_vider")],[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]
        await q.edit_message_text(texte[:4000], parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("chg_statut_") and is_admin(uid): await q.edit_message_text("📍 Choisir statut :", reply_markup=menu_statut(d.replace("chg_statut_","")))
    elif d.startswith("statut_") and is_admin(uid):
        parts = d.split("_"); cmd_id, statut = parts[1], STATUTS[int(parts[2])]
        for c in data["commandes"]:
            if str(c["id"]) == cmd_id:
                c["statut"] = statut
                try: await q.get_bot().send_message(c["user_id"], f"📦 Commande #{cmd_id}\nStatut : {statut}")
                except: pass
                break
        save(data)
        await q.edit_message_text(f"✅ {statut}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")]]))
    elif d == "admin_vider" and is_admin(uid):
        data["commandes"] = []; save(data)
        await q.edit_message_text("✅ Vidé !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))
    elif d == "admin_promos" and is_admin(uid):
        promos = data.get("codes_promo",{})
        texte = "🎟️ *Codes promo :*\n\n" + "\n".join([f"• `{k}` → -{v}%" for k,v in promos.items()]) + "\n\nAjouter : `AJOUTER_CODE NOM REMISE`"
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))
    elif d == "admin_bienvenue" and is_admin(uid):
        context.user_data["edit_field"] = "bienvenue"
        await q.edit_message_text("✏️ Envoie le nouveau message. Utilise *{prenom}* pour le prénom.", parse_mode="Markdown")
    elif d.startswith("admin_edit_") and all(x not in d for x in ["_nom_","_desc_","_photo_","_badge_"]) and is_admin(uid):
        parts = d.split("_")
        if len(parts) == 3:
            i = int(parts[2]); p = data["produits"][i]
            await q.edit_message_text(f"✏️ *{p['nom']}*\n{p.get('desc','')}", parse_mode="Markdown", reply_markup=menu_admin_edit(i))
    elif d.startswith("admin_suppr_") and is_admin(uid):
        del data["produits"][int(d.split("_")[2])]; save(data)
        await q.edit_message_text("🗑️ Supprimé !", reply_markup=menu_admin_produits())
    elif d.startswith("admin_edit_nom_") and is_admin(uid):
        context.user_data.update({"edit_index": int(d.split("_")[3]), "edit_field": "nom"})
        await q.edit_message_text("✏️ Nouveau *nom* :", parse_mode="Markdown")
    elif d.startswith("admin_edit_desc_") and is_admin(uid):
        context.user_data.update({"edit_index": int(d.split("_")[3]), "edit_field": "desc"})
        await q.edit_message_text("📝 Nouvelle *description* :", parse_mode="Markdown")
    elif d.startswith("admin_edit_photo_") and is_admin(uid):
        context.user_data.update({"edit_index": int(d.split("_")[3]), "edit_field": "photo"})
        await q.edit_message_text("📸 Envoie la *photo* directement :", parse_mode="Markdown")
    elif d.startswith("admin_edit_badge_") and is_admin(uid):
        context.user_data.update({"edit_index": int(d.split("_")[3]), "edit_field": "badge"})
        await q.edit_message_text("🏷️ Badge ou SKIP :", parse_mode="Markdown")

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_message.web_app_data: return
    u = update.effective_user
    data = load()
    try:
        order = json.loads(update.effective_message.web_app_data.data)
        cmd_id = f"CMD{data.get('compteur_commande',1):03d}"
        data["compteur_commande"] = data.get("compteur_commande",1) + 1
        commande = {
            "id": cmd_id, "user": f"{u.first_name} (@{u.username})", "user_id": u.id,
            "items": order.get("items",[]), "produit": ", ".join([i["nom"] for i in order.get("items",[])]),
            "total": order.get("total",0), "remise": order.get("remise",0),
            "adresse": order.get("adresse","—"), "telephone": order.get("telephone","—"),
            "statut": "📦 Commande reçue", "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        data["commandes"].append(commande); save(data)
        items_text = "\n".join([f"  • {i['nom']} x{i['qty']} — {i['prix']}" for i in order.get("items",[])])
        await update.message.reply_text(
            f"✅ *Commande #{cmd_id} confirmée !*\n\n{items_text}\n\n💰 {order.get('total',0)}€\n📍 {order.get('adresse','—')}\n📱 {order.get('telephone','—')}\n💵 Espèces à la livraison 🙏",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        await update.get_bot().send_message(ADMIN_ID,
            f"🛒 *Commande #{cmd_id}!*\n\n👤 {u.first_name} (@{u.username})\n\n{items_text}\n\n💰 {order.get('total',0)}€\n📍 {order.get('adresse','—')}\n📱 {order.get('telephone','—')}\n📅 {commande['date']}\n\n👉 `/repondre {u.id} message`",
            parse_mode="Markdown")
    except Exception as e:
        logging.error(f"webapp_data error: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    u = update.effective_user
    data = load()

    if is_admin(uid) and context.user_data.get("edit_field") == "bienvenue":
        data["bienvenue"] = txt; save(data); context.user_data.pop("edit_field")
        await update.message.reply_text("✅ Mis à jour !", reply_markup=menu_admin()); return

    if is_admin(uid) and "edit_field" in context.user_data and "edit_index" in context.user_data:
        field = context.user_data.pop("edit_field"); i = context.user_data.pop("edit_index")
        data["produits"][i][field] = "" if field == "badge" and txt.upper() == "SKIP" else txt
        save(data)
        await update.message.reply_text(f"✅ Mis à jour !", reply_markup=menu_admin()); return

    if is_admin(uid) and "ajout_etape" in context.user_data:
        etape = context.user_data["ajout_etape"]
        if etape == "nom":
            context.user_data["nouveau_produit"]["nom"] = txt
            context.user_data["ajout_etape"] = "variantes"
            await update.message.reply_text("2️⃣ *Variantes* (une par ligne) :\n`100g - 20€`\n`200g - 50€`", parse_mode="Markdown")
        elif etape == "variantes":
            variantes = [{"quantite": l.split(" - ")[0].strip(), "prix": l.split(" - ")[1].strip()} for l in txt.split("\n") if " - " in l]
            context.user_data["nouveau_produit"].update({"variantes": variantes, "prix": variantes[0]["prix"] if variantes else ""})
            context.user_data["ajout_etape"] = "desc"
            await update.message.reply_text("3️⃣ *Description* :", parse_mode="Markdown")
        elif etape == "desc":
            context.user_data["nouveau_produit"]["desc"] = txt
            context.user_data["ajout_etape"] = "photo"
            await update.message.reply_text("4️⃣ 📸 Envoie la *photo* ou tape SKIP :", parse_mode="Markdown")
        elif etape == "photo":
            context.user_data["nouveau_produit"]["photo"] = "" if txt.upper() == "SKIP" else txt
            context.user_data["ajout_etape"] = "badge"
            await update.message.reply_text("5️⃣ *Badge* (ex: Nouveau) ou SKIP :", parse_mode="Markdown")
        elif etape == "badge":
            context.user_data["nouveau_produit"]["badge"] = "" if txt.upper() == "SKIP" else txt
            data["produits"].append(context.user_data.pop("nouveau_produit"))
            context.user_data.pop("ajout_etape"); save(data)
            await update.message.reply_text("✅ Produit ajouté ! 🎉", reply_markup=menu_admin())
        return

    if is_admin(uid) and txt.startswith("AJOUTER_CODE"):
        parts = txt.split()
        if len(parts) == 3:
            data["codes_promo"][parts[1].upper()] = int(parts[2]); save(data)
            await update.message.reply_text(f"✅ Code `{parts[1].upper()}` -{parts[2]}% ajouté !", parse_mode="Markdown")
        return

    await update.message.reply_text("Voici notre boutique 👇", reply_markup=menu_principal())
    if uid != ADMIN_ID:
        try: await update.get_bot().send_message(ADMIN_ID, f"💬 *{u.first_name} (@{u.username}) :*\n\n{txt}\n\n👉 `/repondre {uid} message`", parse_mode="Markdown")
        except: pass

async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    data = load()
    photo_url = (await (await update.message.photo[-1].get_file())).file_path
    if context.user_data.get("ajout_etape") == "photo":
        context.user_data["nouveau_produit"]["photo"] = photo_url
        context.user_data["ajout_etape"] = "badge"
        await update.message.reply_text("✅ Photo !\n\n5️⃣ *Badge* ou SKIP :", parse_mode="Markdown")
    elif context.user_data.get("edit_field") == "photo" and "edit_index" in context.user_data:
        i = context.user_data.pop("edit_index"); context.user_data.pop("edit_field")
        data["produits"][i]["photo"] = photo_url; save(data)
        await update.message.reply_text("✅ Photo mise à jour !", reply_markup=menu_admin())

def main():
    threading.Thread(target=start_web_server, daemon=True).start()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_cmd))
    app.add_handler(CommandHandler("repondre", repondre_cmd))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot lancé !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

