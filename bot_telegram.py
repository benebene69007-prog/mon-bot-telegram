#!/usr/bin/env python3
"""
Bot Telegram - Allo J'arrive 69 - Mini App
Lance : py -3.11 bot_telegram.py
"""

import json, os, logging
from datetime import datetime
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN     = "8616508368:AAH6P6rlQXU0ZzQl6SSjC9OW8ZEbPkZABHQ"
ADMIN_ID  = 8464360679
DATA_FILE = "boutique_data.json"
WEBAPP_URL = "https://mon-bot-telegram-production-d0ae.up.railway.app/webapp.html"

STATUTS = ["📦 Commande reçue", "✅ Confirmée", "🔄 En préparation", "🚚 En livraison", "✅ Livrée"]

DEFAULT_DATA = {
    "bienvenue": "👋 Bonjour *{prenom}* ! Bienvenue chez *Allo J'arrive 69* 🚀\n\nClique ci-dessous pour voir notre boutique 👇",
    "produits": [],
    "commandes": [],
    "avis": [],
    "codes_promo": {"BIENVENUE": 10, "VIP20": 20},
    "compteur_commande": 1,
}

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(uid): return uid == ADMIN_ID

def get_webapp_url():
    data = load()
    produits = data.get("produits", [])
    promos = data.get("codes_promo", {})
    produits_json = quote(json.dumps(produits, ensure_ascii=False))
    promos_json = quote(json.dumps(promos, ensure_ascii=False))
    return f"{WEBAPP_URL}?products={produits_json}&promos={promos_json}"

def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Ouvrir la boutique", web_app=WebAppInfo(url=get_webapp_url()))],
        [InlineKeyboardButton("📋 Mes commandes",      callback_data="mes_commandes")],
        [InlineKeyboardButton("⭐ Avis clients",        callback_data="voir_avis")],
        [InlineKeyboardButton("🎧 Support",            callback_data="support")],
        [InlineKeyboardButton("📞 Contact",            callback_data="contact")],
    ])

def menu_support():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Suivi de commande", callback_data="suivi")],
        [InlineKeyboardButton("🔄 Retour / Échange",  callback_data="retour")],
        [InlineKeyboardButton("❓ FAQ",                callback_data="faq")],
        [InlineKeyboardButton("💬 Parler à un agent", callback_data="agent")],
        [InlineKeyboardButton("⬅️ Retour",            callback_data="menu")],
    ])

def btn_retour():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour au menu", callback_data="menu")]])

def menu_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Gérer produits",     callback_data="admin_produits")],
        [InlineKeyboardButton("➕ Ajouter produit",    callback_data="admin_ajouter")],
        [InlineKeyboardButton("📋 Commandes",          callback_data="admin_commandes")],
        [InlineKeyboardButton("📊 Statistiques",       callback_data="admin_stats")],
        [InlineKeyboardButton("🎟️ Codes promo",       callback_data="admin_promos")],
        [InlineKeyboardButton("⭐ Avis clients",       callback_data="admin_avis")],
        [InlineKeyboardButton("✏️ Message /start",     callback_data="admin_bienvenue")],
        [InlineKeyboardButton("🌐 Voir la boutique",   web_app=WebAppInfo(url=get_webapp_url()))],
    ])

def menu_admin_produits():
    data = load()
    kb = [[InlineKeyboardButton(f"✏️ {p['nom']} — {p['prix']}€", callback_data=f"admin_edit_{i}")] for i, p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour admin", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)

def menu_admin_edit(i):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Nom",         callback_data=f"admin_edit_nom_{i}")],
        [InlineKeyboardButton("💰 Prix",        callback_data=f"admin_edit_prix_{i}")],
        [InlineKeyboardButton("📝 Description", callback_data=f"admin_edit_desc_{i}")],
        [InlineKeyboardButton("📸 Photo (URL)", callback_data=f"admin_edit_photo_{i}")],
        [InlineKeyboardButton("🏷️ Badge",      callback_data=f"admin_edit_badge_{i}")],
        [InlineKeyboardButton("🗑️ Supprimer",  callback_data=f"admin_suppr_{i}")],
        [InlineKeyboardButton("⬅️ Retour",      callback_data="admin_produits")],
    ])

def menu_statut(cmd_id):
    kb = [[InlineKeyboardButton(s, callback_data=f"statut_{cmd_id}_{i}")] for i, s in enumerate(STATUTS)]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")])
    return InlineKeyboardMarkup(kb)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load()
    u = update.effective_user
    texte = data["bienvenue"].replace("{prenom}", u.first_name)
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    await update.message.reply_text("🔧 *Panel Admin — Allo J'arrive 69*", parse_mode="Markdown", reply_markup=menu_admin())

async def repondre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) < 2:
        await update.message.reply_text("Format : `/repondre USER_ID message`", parse_mode="Markdown")
        return
    try:
        user_id = int(context.args[0])
        message = " ".join(context.args[1:])
        await update.get_bot().send_message(user_id, f"💬 *Message de la boutique :*\n\n{message}", parse_mode="Markdown")
        await update.message.reply_text("✅ Message envoyé !")
    except Exception as e:
        await update.message.reply_text(f"❌ Erreur : {e}")

async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Format : `/broadcast message`", parse_mode="Markdown")
        return
    message = " ".join(context.args)
    data = load()
    users = list(set([c["user_id"] for c in data["commandes"]]))
    envoyes = 0
    for uid in users:
        try:
            await update.get_bot().send_message(uid, f"📢 *Message de la boutique :*\n\n{message}", parse_mode="Markdown")
            envoyes += 1
        except: pass
    await update.message.reply_text(f"✅ Envoyé à {envoyes} clients !")

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    data = load()
    uid = q.from_user.id

    if d == "menu":
        await q.edit_message_text("🏠 *Menu principal*", parse_mode="Markdown", reply_markup=menu_principal())
    elif d == "support":
        await q.edit_message_text("🎧 *Support*", parse_mode="Markdown", reply_markup=menu_support())
    elif d == "contact":
        await q.edit_message_text("📞 *Contact :*\n\n📧 contact@alloj arrive69.com\n📱 +33 6 00 00 00 00\n🕐 Lun–Ven 9h–18h", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "suivi":
        await q.edit_message_text("📦 Envoie ton numéro de commande (ex: #CMD001)", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "retour":
        await q.edit_message_text("🔄 Retours sous 14 jours. Envoie ton numéro de commande.", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "faq":
        await q.edit_message_text("❓ *FAQ :*\n\n🚚 Livraison rapide\n💵 Paiement en espèces\n🔄 Retour : 14 jours", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "agent":
        await q.edit_message_text("💬 Décris ton problème ici et on te répond rapidement !", reply_markup=btn_retour())

    elif d == "mes_commandes":
        mes = [c for c in data["commandes"] if c["user_id"] == uid]
        if not mes:
            await q.edit_message_text("📋 Tu n'as pas encore de commande.", reply_markup=menu_principal())
        else:
            texte = "📋 *Tes commandes :*\n\n"
            for c in mes[-5:]:
                texte += f"🔖 #{c['id']} — {c['produit']}\n💰 {c['total']}€\n📍 {c['statut']}\n\n"
            await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

    elif d == "voir_avis":
        avis = data.get("avis", [])
        texte = "⭐ *Avis clients :*\n\n" + ("".join([f"{'⭐'*a['note']} {a['nom']}\n_{a['texte']}_\n\n" for a in avis[-5:]])) if avis else "⭐ Pas encore d'avis !"
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="menu")]]))

    elif d == "admin_menu" and is_admin(uid):
        await q.edit_message_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())

    elif d == "admin_produits" and is_admin(uid):
        await q.edit_message_text("📦 *Produits :*\nClique pour modifier.", parse_mode="Markdown", reply_markup=menu_admin_produits())

    elif d == "admin_ajouter" and is_admin(uid):
        context.user_data["nouveau_produit"] = {}
        context.user_data["ajout_etape"] = "nom"
        await q.edit_message_text("➕ *Nouveau produit*\n\n1️⃣ Envoie le *nom* du produit :", parse_mode="Markdown")

    elif d == "admin_stats" and is_admin(uid):
        commandes = data["commandes"]
        ca = sum([c.get("total", 0) for c in commandes])
        texte = (f"📊 *Statistiques :*\n\n"
                 f"📦 Commandes : {len(commandes)}\n"
                 f"💰 CA total : {ca}€\n"
                 f"⭐ Avis : {len(data.get('avis', []))}\n"
                 f"🎟️ Codes promo : {len(data.get('codes_promo', {}))}\n"
                 f"📦 Produits : {len(data.get('produits', []))}")
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_commandes" and is_admin(uid):
        commandes = data["commandes"]
        if not commandes:
            texte = "📋 Aucune commande."
        else:
            texte = "📋 *Commandes :*\n\n"
            for c in commandes[-8:]:
                items = ", ".join([f"{i['nom']} x{i['qty']}" for i in c.get("items", [])])
                texte += f"🔖 #{c['id']} — {c['user']}\n📦 {items}\n💰 {c.get('total',0)}€\n📱 {c.get('telephone','—')}\n📍 {c['statut']}\n\n"
        kb = [[InlineKeyboardButton(f"📍 Statut #{c['id']}", callback_data=f"chg_statut_{c['id']}")] for c in commandes[-5:]]
        kb.append([InlineKeyboardButton("🗑️ Vider", callback_data="admin_vider")])
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
        await q.edit_message_text(texte[:4000], parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("chg_statut_") and is_admin(uid):
        cmd_id = d.replace("chg_statut_", "")
        await q.edit_message_text(f"📍 Statut pour #{cmd_id} :", reply_markup=menu_statut(cmd_id))

    elif d.startswith("statut_") and is_admin(uid):
        parts = d.split("_")
        cmd_id = parts[1]
        nouveau_statut = STATUTS[int(parts[2])]
        for c in data["commandes"]:
            if str(c["id"]) == str(cmd_id):
                c["statut"] = nouveau_statut
                try:
                    await q.get_bot().send_message(c["user_id"], f"📦 *Commande #{cmd_id}*\nNouveau statut : {nouveau_statut}", parse_mode="Markdown")
                except: pass
                break
        save(data)
        await q.edit_message_text(f"✅ Statut : {nouveau_statut}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")]]))

    elif d == "admin_vider" and is_admin(uid):
        data["commandes"] = []
        save(data)
        await q.edit_message_text("✅ Commandes vidées !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_promos" and is_admin(uid):
        promos = data.get("codes_promo", {})
        texte = "🎟️ *Codes promo :*\n\n" + "\n".join([f"• `{k}` → -{v}%" for k, v in promos.items()])
        texte += "\n\nPour ajouter : `AJOUTER_CODE NOM REMISE`"
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_avis" and is_admin(uid):
        avis = data.get("avis", [])
        texte = "⭐ *Avis :*\n\n" + "\n".join([f"{'⭐'*a['note']} {a['nom']} : {a['texte']}" for a in avis]) if avis else "⭐ Aucun avis."
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_bienvenue" and is_admin(uid):
        context.user_data["edit_field"] = "bienvenue"
        await q.edit_message_text(f"✏️ Envoie le nouveau message de bienvenue.\nUtilise *{{prenom}}* pour le prénom.", parse_mode="Markdown")

    elif d.startswith("admin_edit_") and "_nom_" not in d and "_prix_" not in d and "_desc_" not in d and "_photo_" not in d and "_badge_" not in d and is_admin(uid):
        parts = d.split("_")
        if len(parts) == 3:
            i = int(parts[2])
            p = data["produits"][i]
            await q.edit_message_text(f"✏️ *{p['nom']}*\n💰 {p['prix']}€\n📝 {p['desc']}", parse_mode="Markdown", reply_markup=menu_admin_edit(i))

    elif d.startswith("admin_suppr_") and is_admin(uid):
        i = int(d.split("_")[2])
        del data["produits"][i]
        save(data)
        await q.edit_message_text("🗑️ Supprimé !", reply_markup=menu_admin_produits())

    elif d.startswith("admin_edit_nom_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "nom"
        await q.edit_message_text("✏️ Envoie le nouveau *nom* :", parse_mode="Markdown")

    elif d.startswith("admin_edit_prix_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "prix"
        await q.edit_message_text("💰 Envoie le nouveau *prix* en chiffre (ex: 30) :", parse_mode="Markdown")

    elif d.startswith("admin_edit_desc_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "desc"
        await q.edit_message_text("📝 Envoie la nouvelle *description* :", parse_mode="Markdown")

    elif d.startswith("admin_edit_photo_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "photo"
        await q.edit_message_text("📸 Envoie le *lien URL* de la photo (https://...)", parse_mode="Markdown")

    elif d.startswith("admin_edit_badge_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "badge"
        await q.edit_message_text("🏷️ Envoie le *badge* (ex: Nouveau, -20%, Hot...) ou RIEN pour supprimer :", parse_mode="Markdown")

async def webapp_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reçoit les commandes depuis la Mini App"""
    if not update.effective_message.web_app_data:
        return
    data_str = update.effective_message.web_app_data.data
    u = update.effective_user
    data = load()
    try:
        order = json.loads(data_str)
        cmd_id = f"CMD{data.get('compteur_commande', 1):03d}"
        data["compteur_commande"] = data.get("compteur_commande", 1) + 1
        commande = {
            "id": cmd_id,
            "user": f"{u.first_name} (@{u.username})",
            "user_id": u.id,
            "items": order.get("items", []),
            "produit": ", ".join([i["nom"] for i in order.get("items", [])]),
            "total": order.get("total", 0),
            "remise": order.get("remise", 0),
            "adresse": order.get("adresse", "—"),
            "telephone": order.get("telephone", "—"),
            "statut": "📦 Commande reçue",
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        data["commandes"].append(commande)
        save(data)

        items_text = "\n".join([f"  • {i['nom']} x{i['qty']} = {i['prix']}€" for i in order.get("items", [])])
        await update.message.reply_text(
            f"✅ *Commande #{cmd_id} confirmée !*\n\n"
            f"{items_text}\n\n"
            f"💰 Total : {order.get('total', 0)}€\n"
            f"📍 {order.get('adresse', '—')}\n"
            f"📱 {order.get('telephone', '—')}\n"
            f"💵 Paiement en espèces à la livraison\n\n"
            f"Tu recevras une notification pour le suivi ! 🙏",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        await update.get_bot().send_message(
            ADMIN_ID,
            f"🛒 *Nouvelle commande #{cmd_id} !*\n\n"
            f"👤 {u.first_name} (@{u.username})\n"
            f"🆔 `{u.id}`\n\n"
            f"{items_text}\n\n"
            f"💰 Total : {order.get('total', 0)}€\n"
            f"🎟️ Remise : {order.get('remise', 0)}%\n"
            f"📍 {order.get('adresse', '—')}\n"
            f"📱 {order.get('telephone', '—')}\n"
            f"📅 {commande['date']}\n\n"
            f"👉 Répondre : `/repondre {u.id} votre message`",
            parse_mode="Markdown"
        )
    except Exception as e:
        logging.error(f"Erreur commande webapp: {e}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    uid = update.effective_user.id
    u = update.effective_user
    data = load()

    if is_admin(uid) and context.user_data.get("edit_field") == "bienvenue":
        data["bienvenue"] = txt
        save(data)
        context.user_data.pop("edit_field")
        await update.message.reply_text("✅ Message mis à jour !", reply_markup=menu_admin())
        return

    if is_admin(uid) and "edit_field" in context.user_data and "edit_index" in context.user_data:
        field = context.user_data.pop("edit_field")
        i = context.user_data.pop("edit_index")
        if field == "badge" and txt.upper() == "RIEN":
            data["produits"][i][field] = ""
        elif field == "prix":
            try: data["produits"][i][field] = int(txt)
            except: data["produits"][i][field] = txt
        else:
            data["produits"][i][field] = txt
        save(data)
        p = data["produits"][i]
        await update.message.reply_text(f"✅ Mis à jour !\n\n*{p['nom']}* — {p['prix']}€\n{p['desc']}", parse_mode="Markdown", reply_markup=menu_admin())
        return

    if is_admin(uid) and "ajout_etape" in context.user_data:
        etape = context.user_data["ajout_etape"]
        if etape == "nom":
            context.user_data["nouveau_produit"]["nom"] = txt
            context.user_data["ajout_etape"] = "prix"
            await update.message.reply_text("2️⃣ Envoie le *prix* en chiffre (ex: 30) :", parse_mode="Markdown")
        elif etape == "prix":
            try: context.user_data["nouveau_produit"]["prix"] = int(txt)
            except: context.user_data["nouveau_produit"]["prix"] = txt
            context.user_data["ajout_etape"] = "desc"
            await update.message.reply_text("3️⃣ Envoie la *description* :", parse_mode="Markdown")
        elif etape == "desc":
            context.user_data["nouveau_produit"]["desc"] = txt
            context.user_data["ajout_etape"] = "photo"
            await update.message.reply_text("4️⃣ Envoie le *lien URL* de la photo (ou tape SKIP) :", parse_mode="Markdown")
        elif etape == "photo":
            context.user_data["nouveau_produit"]["photo"] = "" if txt.upper() == "SKIP" else txt
            context.user_data["ajout_etape"] = "badge"
            await update.message.reply_text("5️⃣ Envoie un *badge* (ex: Nouveau, Hot, -20%) ou tape SKIP :", parse_mode="Markdown")
        elif etape == "badge":
            context.user_data["nouveau_produit"]["badge"] = "" if txt.upper() == "SKIP" else txt
            data["produits"].append(context.user_data.pop("nouveau_produit"))
            context.user_data.pop("ajout_etape")
            save(data)
            await update.message.reply_text("✅ Produit ajouté ! Il apparaît maintenant dans la boutique 🎉", reply_markup=menu_admin())
        return

    if is_admin(uid) and txt.startswith("AJOUTER_CODE"):
        parts = txt.split()
        if len(parts) == 3:
            data["codes_promo"][parts[1].upper()] = int(parts[2])
            save(data)
            await update.message.reply_text(f"✅ Code `{parts[1].upper()}` -{parts[2]}% ajouté !", parse_mode="Markdown")
        return

    mots = txt.lower()
    if any(m in mots for m in ("bonjour","salut","hello","bonsoir","coucou")):
        await update.message.reply_text(f"👋 Bonjour ! Bienvenue chez Allo J'arrive 69 🚀", reply_markup=menu_principal())
    else:
        await update.message.reply_text("Voici notre boutique 👇", reply_markup=menu_principal())
        if uid != ADMIN_ID:
            try:
                await update.get_bot().send_message(ADMIN_ID,
                    f"💬 *Message de {u.first_name} (@{u.username}) :*\n\n{txt}\n\n👉 `/repondre {uid} votre message`",
                    parse_mode="Markdown")
            except: pass

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",      start))
    app.add_handler(CommandHandler("admin",      admin_cmd))
    app.add_handler(CommandHandler("repondre",   repondre_cmd))
    app.add_handler(CommandHandler("broadcast",  broadcast_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, webapp_data))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot Allo J'arrive 69 lancé !")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
