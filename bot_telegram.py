#!/usr/bin/env python3
"""
Bot Telegram - Allo J'arrive 69
Commandes via boutons Telegram + Mini App pour afficher produits
"""
import json, os, logging, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN    = "8616508368:AAH6P6rlQXU0ZzQl6SSjC9OW8ZEbPkZABHQ"
ADMIN_ID = 8464360679
DATA_FILE = "boutique_data.json"
WEBAPP_URL = "https://mon-bot-telegram-production-d0ae.up.railway.app/webapp.html"
PORT = int(os.environ.get("PORT", 8080))
STATUTS = ["📦 Commande reçue", "✅ Confirmée", "🔄 En préparation", "🚚 En livraison", "✅ Livrée"]

DEFAULT_DATA = {
    "bienvenue": "👋 Bonjour *{prenom}* ! Bienvenue chez *Allo J'arrive 69* 🚀\n\nChoisis une option 👇",
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

# Serveur web pour la Mini App
class WebHandler(BaseHTTPRequestHandler):
    def log_message(self, *args): pass
    def do_GET(self):
        fname = "webapp.html"
        if os.path.exists(fname):
            with open(fname, "rb") as f: content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404); self.end_headers()

def start_web_server():
    HTTPServer(("0.0.0.0", PORT), WebHandler).serve_forever()

# ── Menus ──────────────────────────────────────────────────────────────────────
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Voir les produits", web_app=WebAppInfo(url=get_webapp_url()))],
        [InlineKeyboardButton("📦 Commander",          callback_data="menu_commander")],
        [InlineKeyboardButton("📋 Mes commandes",      callback_data="mes_commandes")],
        [InlineKeyboardButton("🎧 Support",            callback_data="support")],
        [InlineKeyboardButton("📞 Contact",            callback_data="contact")],
    ])

def menu_produits_commander():
    data = load()
    kb = []
    for i, p in enumerate(data["produits"]):
        kb.append([InlineKeyboardButton(f"{p['nom']}", callback_data=f"cmd_produit_{i}")])
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def menu_variantes(i):
    data = load()
    p = data["produits"][i]
    kb = []
    if p.get("variantes"):
        for vi, v in enumerate(p["variantes"]):
            kb.append([InlineKeyboardButton(f"{v['quantite']} — {v['prix']}", callback_data=f"cmd_variante_{i}_{vi}")])
    else:
        kb.append([InlineKeyboardButton(f"Commander — {p.get('prix','')}", callback_data=f"cmd_variante_{i}_0")])
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu_commander")])
    return InlineKeyboardMarkup(kb)

def btn_retour():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu principal", callback_data="menu")]])

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
    kb = [[InlineKeyboardButton(f"✏️ {p['nom']}", callback_data=f"admin_edit_{i}")] for i, p in enumerate(data["produits"])]
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

def menu_statut(cmd_id):
    kb = [[InlineKeyboardButton(s, callback_data=f"statut_{cmd_id}_{i}")] for i, s in enumerate(STATUTS)]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")])
    return InlineKeyboardMarkup(kb)

# ── Commandes bot ──────────────────────────────────────────────────────────────
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
    if not context.args: return
    data = load()
    envoyes = 0
    for uid in set([c["user_id"] for c in data["commandes"]]):
        try: await update.get_bot().send_message(uid, f"📢 *Boutique :*\n\n{' '.join(context.args)}", parse_mode="Markdown"); envoyes += 1
        except: pass
    await update.message.reply_text(f"✅ Envoyé à {envoyes} clients !")

# ── Callbacks ──────────────────────────────────────────────────────────────────
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    data = load()
    uid = q.from_user.id
    u = q.from_user

    # ── Navigation ──
    if d == "menu":
        await q.edit_message_text(data["bienvenue"].replace("{prenom}", u.first_name), parse_mode="Markdown", reply_markup=menu_principal())
    elif d == "menu_commander":
        if not data["produits"]:
            await q.edit_message_text("📦 Pas encore de produits disponibles.", reply_markup=btn_retour())
        else:
            await q.edit_message_text("🛍️ *Choisir un produit :*", parse_mode="Markdown", reply_markup=menu_produits_commander())
    elif d == "support":
        await q.edit_message_text("🎧 *Support*\n\n📧 contact@alloj arrive69.com\n📱 +33 6 00 00 00 00", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "contact":
        await q.edit_message_text("📞 *Contact*\n\n📱 +33 6 00 00 00 00\n📧 contact@alloj arrive69.com\n🕐 Lun–Ven 9h–18h", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "mes_commandes":
        mes = [c for c in data["commandes"] if c["user_id"] == uid]
        if not mes:
            await q.edit_message_text("📋 Pas encore de commande.", reply_markup=menu_principal()); return
        texte = "📋 *Tes commandes :*\n\n"
        for c in mes[-5:]:
            texte += f"🔖 #{c['id']} — {c.get('total',0)}€\n📍 {c['statut']}\n\n"
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

    # ── Commande client ──
    elif d.startswith("cmd_produit_"):
        i = int(d.split("_")[2])
        p = data["produits"][i]
        # Afficher photo si disponible
        texte = f"*{p['nom']}*\n\n📝 {p.get('desc','')}\n\n📦 Choisir la quantité :"
        if p.get("photo"):
            try:
                await q.message.reply_photo(photo=p["photo"], caption=texte, parse_mode="Markdown", reply_markup=menu_variantes(i))
                await q.delete_message()
                return
            except: pass
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=menu_variantes(i))

    elif d.startswith("cmd_variante_"):
        parts = d.split("_")
        i, vi = int(parts[2]), int(parts[3])
        p = data["produits"][i]
        if p.get("variantes") and len(p["variantes"]) > vi:
            v = p["variantes"][vi]
            nom_cmd = f"{p['nom']} ({v['quantite']})"
            prix_cmd = v["prix"]
        else:
            nom_cmd = p["nom"]
            prix_cmd = p.get("prix", "")
        context.user_data["cmd_nom"] = nom_cmd
        context.user_data["cmd_prix"] = prix_cmd
        context.user_data["cmd_etape"] = "quantite"
        await q.edit_message_text(
            f"✅ *{nom_cmd}* — {prix_cmd}\n\n🔢 Combien d'unités veux-tu ?\n(envoie un chiffre ex: 1, 2, 3...)",
            parse_mode="Markdown"
        )

    # ── Admin ──
    elif d == "admin_menu" and is_admin(uid):
        await q.edit_message_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())
    elif d == "admin_produits" and is_admin(uid):
        await q.edit_message_text("📦 *Produits :*", parse_mode="Markdown", reply_markup=menu_admin_produits())
    elif d == "admin_ajouter" and is_admin(uid):
        context.user_data.update({"nouveau_produit": {}, "ajout_etape": "nom"})
        await q.edit_message_text("➕ *Nouveau produit*\n\n1️⃣ Envoie le *nom* :", parse_mode="Markdown")
    elif d == "admin_stats" and is_admin(uid):
        ca = sum([c.get("total", 0) for c in data["commandes"]])
        await q.edit_message_text(f"📊 *Stats :*\n\n📦 Commandes : {len(data['commandes'])}\n💰 CA : {ca}€\n📦 Produits : {len(data['produits'])}", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))
    elif d == "admin_commandes" and is_admin(uid):
        commandes = data["commandes"]
        texte = "📋 *Commandes :*\n\n" if commandes else "📋 Aucune commande."
        for c in commandes[-8:]:
            texte += f"🔖 #{c['id']} — {c['user']}\n📦 {c.get('produit','')}\n💰 {c.get('total','')} | x{c.get('quantite',1)}\n📱 {c.get('telephone','—')}\n📍 {c.get('adresse','—')}\n📌 {c['statut']}\n\n"
        kb = [[InlineKeyboardButton(f"📍 #{c['id']}", callback_data=f"chg_statut_{c['id']}")] for c in commandes[-5:]]
        kb += [[InlineKeyboardButton("🗑️ Vider", callback_data="admin_vider")], [InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]
        await q.edit_message_text(texte[:4000], parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))
    elif d.startswith("chg_statut_") and is_admin(uid):
        await q.edit_message_text("📍 Choisir statut :", reply_markup=menu_statut(d.replace("chg_statut_", "")))
    elif d.startswith("statut_") and is_admin(uid):
        parts = d.split("_"); cmd_id, statut = parts[1], STATUTS[int(parts[2])]
        for c in data["commandes"]:
            if str(c["id"]) == cmd_id:
                c["statut"] = statut
                try: await q.get_bot().send_message(c["user_id"], f"📦 *Commande #{cmd_id}*\nStatut : {statut}", parse_mode="Markdown")
                except: pass
                break
        save(data)
        await q.edit_message_text(f"✅ {statut}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")]]))
    elif d == "admin_vider" and is_admin(uid):
        data["commandes"] = []; save(data)
        await q.edit_message_text("✅ Vidé !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))
    elif d == "admin_promos" and is_admin(uid):
        promos = data.get("codes_promo", {})
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
        await q.edit_message_text("🏷️ Badge (ex: Nouveau) ou SKIP :", parse_mode="Markdown")

# ── Messages ───────────────────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    u = update.effective_user
    data = load()

    # Admin: modifier bienvenue
    if is_admin(uid) and context.user_data.get("edit_field") == "bienvenue":
        data["bienvenue"] = txt; save(data); context.user_data.pop("edit_field")
        await update.message.reply_text("✅ Mis à jour !", reply_markup=menu_admin()); return

    # Admin: modifier champ produit
    if is_admin(uid) and "edit_field" in context.user_data and "edit_index" in context.user_data:
        field = context.user_data.pop("edit_field"); i = context.user_data.pop("edit_index")
        data["produits"][i][field] = "" if field == "badge" and txt.upper() == "SKIP" else txt
        save(data)
        await update.message.reply_text("✅ Mis à jour !", reply_markup=menu_admin()); return

    # Admin: ajouter produit
    if is_admin(uid) and "ajout_etape" in context.user_data:
        etape = context.user_data["ajout_etape"]
        if etape == "nom":
            context.user_data["nouveau_produit"]["nom"] = txt
            context.user_data["ajout_etape"] = "variantes"
            await update.message.reply_text("2️⃣ *Variantes* (une par ligne) :\nEx: `100g - 20€`\n`200g - 50€`\n`1kg - 300€`", parse_mode="Markdown")
        elif etape == "variantes":
            variantes = []
            for l in txt.split("\n"):
                l = l.strip()
                if " - " in l:
                    parts = l.split(" - ", 1)
                    variantes.append({"quantite": parts[0].strip(), "prix": parts[1].strip()})
            context.user_data["nouveau_produit"].update({"variantes": variantes, "prix": variantes[0]["prix"] if variantes else ""})
            context.user_data["ajout_etape"] = "desc"
            recap = "\n".join([f"  • {v['quantite']} → {v['prix']}" for v in variantes])
            await update.message.reply_text(f"✅ Variantes :\n{recap}\n\n3️⃣ *Description* :", parse_mode="Markdown")
        elif etape == "desc":
            context.user_data["nouveau_produit"]["desc"] = txt
            context.user_data["ajout_etape"] = "photo"
            await update.message.reply_text("4️⃣ 📸 Envoie la *photo* directement ou tape SKIP :", parse_mode="Markdown")
        elif etape == "photo":
            context.user_data["nouveau_produit"]["photo"] = "" if txt.upper() == "SKIP" else txt
            context.user_data["ajout_etape"] = "badge"
            await update.message.reply_text("5️⃣ *Badge* (ex: Nouveau, Hot) ou SKIP :", parse_mode="Markdown")
        elif etape == "badge":
            context.user_data["nouveau_produit"]["badge"] = "" if txt.upper() == "SKIP" else txt
            data["produits"].append(context.user_data.pop("nouveau_produit"))
            context.user_data.pop("ajout_etape"); save(data)
            await update.message.reply_text("✅ Produit ajouté ! 🎉", reply_markup=menu_admin())
        return

    # Admin: code promo
    if is_admin(uid) and txt.startswith("AJOUTER_CODE"):
        parts = txt.split()
        if len(parts) == 3:
            data["codes_promo"][parts[1].upper()] = int(parts[2]); save(data)
            await update.message.reply_text(f"✅ Code `{parts[1].upper()}` -{parts[2]}% ajouté !", parse_mode="Markdown")
        return

    # Client: parcours commande
    if context.user_data.get("cmd_etape") == "quantite":
        try:
            quantite = int(txt)
            if quantite < 1: raise ValueError()
        except:
            await update.message.reply_text("❌ Envoie un chiffre (ex: 1, 2, 3...)"); return
        context.user_data["cmd_quantite"] = quantite
        context.user_data["cmd_etape"] = "promo"
        await update.message.reply_text(
            f"✅ *{context.user_data['cmd_nom']}* x{quantite}\n💰 {context.user_data['cmd_prix']}\n\n🎟️ Tu as un code promo ? Envoie-le ou tape *NON*",
            parse_mode="Markdown"
        )
        return

    if context.user_data.get("cmd_etape") == "promo":
        code = txt.strip().upper()
        remise = 0
        if code != "NON" and code in data.get("codes_promo", {}):
            remise = data["codes_promo"][code]
            await update.message.reply_text(f"🎉 Code valide ! -{remise}% appliqué !")
        elif code != "NON":
            await update.message.reply_text("❌ Code invalide, on continue sans remise.")
        context.user_data["cmd_remise"] = remise
        context.user_data["cmd_etape"] = "adresse"
        await update.message.reply_text("📍 Envoie ton *adresse de livraison* :", parse_mode="Markdown")
        return

    if context.user_data.get("cmd_etape") == "adresse":
        context.user_data["cmd_adresse"] = txt
        context.user_data["cmd_etape"] = "telephone"
        await update.message.reply_text("📱 Envoie ton *numéro de téléphone* :", parse_mode="Markdown")
        return

    if context.user_data.get("cmd_etape") == "telephone":
        nom = context.user_data.get("cmd_nom", "")
        prix = context.user_data.get("cmd_prix", "")
        quantite = context.user_data.get("cmd_quantite", 1)
        adresse = context.user_data.get("cmd_adresse", "")
        remise = context.user_data.get("cmd_remise", 0)
        telephone = txt

        cmd_id = f"CMD{data.get('compteur_commande',1):03d}"
        data["compteur_commande"] = data.get("compteur_commande",1) + 1
        commande = {
            "id": cmd_id, "user": f"{u.first_name} (@{u.username})", "user_id": uid,
            "produit": nom, "quantite": quantite, "total": prix, "remise": remise,
            "adresse": adresse, "telephone": telephone,
            "statut": "📦 Commande reçue", "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        data["commandes"].append(commande); save(data)

        # Vider
        for k in ["cmd_etape","cmd_nom","cmd_prix","cmd_quantite","cmd_adresse","cmd_remise"]:
            context.user_data.pop(k, None)

        # Confirmation client
        await update.message.reply_text(
            f"✅ *Commande #{cmd_id} confirmée !*\n\n"
            f"📦 {nom} x{quantite}\n💰 {prix}\n"
            f"🎟️ Remise : {remise}%\n📍 {adresse}\n📱 {telephone}\n"
            f"💵 Paiement en espèces à la livraison 🙏",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        # Notification admin
        await update.get_bot().send_message(
            ADMIN_ID,
            f"🛒 *Nouvelle commande #{cmd_id} !*\n\n"
            f"👤 {u.first_name} (@{u.username})\n🆔 `{uid}`\n\n"
            f"📦 {nom} x{quantite}\n💰 {prix}\n"
            f"🎟️ Remise : {remise}%\n📍 {adresse}\n📱 {telephone}\n"
            f"📅 {commande['date']}\n\n"
            f"👉 `/repondre {uid} votre message`",
            parse_mode="Markdown"
        )
        return

    # Message libre
    await update.message.reply_text("Voici notre boutique 👇", reply_markup=menu_principal())
    if uid != ADMIN_ID:
        try: await update.get_bot().send_message(ADMIN_ID, f"💬 *{u.first_name} (@{u.username}) :*\n\n{txt}\n\n👉 `/repondre {uid} message`", parse_mode="Markdown")
        except: pass

# ── Photos admin ───────────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    data = load()
    photo = update.message.photo[-1]
    file = await photo.get_file()
    photo_url = file.file_path  # URL publique Telegram

    if context.user_data.get("ajout_etape") == "photo":
        context.user_data["nouveau_produit"]["photo"] = photo_url
        context.user_data["ajout_etape"] = "badge"
        await update.message.reply_text("✅ Photo !\n\n5️⃣ *Badge* (ex: Nouveau) ou SKIP :", parse_mode="Markdown")
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
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot Allo J'arrive 69 lancé !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
