#!/usr/bin/env python3
"""
Bot Telegram - Boutique Complète
Fonctionnalités : Admin, Photos, Avis, Codes promo, Statut commandes, Stats
Lance : py -3.11 bot_telegram.py
"""

import json, os, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN   = "8616508368:AAH6P6rlQXU0ZzQl6SSjC9OW8ZEbPkZABHQ"
ADMIN_ID = 8464360679
DATA_FILE = "boutique_data.json"

STATUTS = ["📦 Commande reçue", "✅ Confirmée", "🔄 En préparation", "🚚 En livraison", "✅ Livrée"]

DEFAULT_DATA = {
    "bienvenue": "👋 Bonjour *{prenom}* ! Bienvenue dans notre boutique.\n\nChoisis une option 👇",
    "produits": [
        {"nom": "👕 T-Shirt Premium",           "prix": "25€", "desc": "100% coton, tailles S→XL",          "photo": ""},
        {"nom": "👟 Sneakers Édition Limitée",  "prix": "89€", "desc": "Coloris exclusifs, stock limité",   "photo": ""},
        {"nom": "🎒 Sac à dos Urban",            "prix": "45€", "desc": "Imperméable, 20L",                  "photo": ""},
        {"nom": "🧢 Casquette Logo",             "prix": "18€", "desc": "Ajustable, broderie premium",       "photo": ""},
    ],
    "commandes": [],
    "avis": [],
    "codes_promo": {"BIENVENUE": 10, "VIP20": 20, "ETE25": 25},
    "compteur_commande": 1,
}

# ── Data ───────────────────────────────────────────────────────────────────────
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(uid): return uid == ADMIN_ID

# ── Menus clients ──────────────────────────────────────────────────────────────
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Commander",         callback_data="commander")],
        [InlineKeyboardButton("📦 Voir les produits",  callback_data="produits")],
        [InlineKeyboardButton("📋 Mes commandes",      callback_data="mes_commandes")],
        [InlineKeyboardButton("⭐ Avis clients",        callback_data="voir_avis")],
        [InlineKeyboardButton("🎧 Support",            callback_data="support")],
        [InlineKeyboardButton("📞 Contact",            callback_data="contact")],
    ])

def menu_produits():
    data = load()
    kb = [[InlineKeyboardButton(f"{p['nom']} — {p['prix']}", callback_data=f"produit_{i}")] for i, p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def menu_commander():
    data = load()
    kb = [[InlineKeyboardButton(f"✅ {p['nom']} — {p['prix']}", callback_data=f"acheter_{i}")] for i, p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

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

# ── Menus admin ────────────────────────────────────────────────────────────────
def menu_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Gérer produits",        callback_data="admin_produits")],
        [InlineKeyboardButton("➕ Ajouter produit",       callback_data="admin_ajouter")],
        [InlineKeyboardButton("📋 Commandes",             callback_data="admin_commandes")],
        [InlineKeyboardButton("📊 Statistiques",          callback_data="admin_stats")],
        [InlineKeyboardButton("🎟️ Codes promo",          callback_data="admin_promos")],
        [InlineKeyboardButton("⭐ Avis clients",          callback_data="admin_avis")],
        [InlineKeyboardButton("✏️ Message /start",        callback_data="admin_bienvenue")],
    ])

def menu_admin_produits():
    data = load()
    kb = [[InlineKeyboardButton(f"✏️ {p['nom']} — {p['prix']}", callback_data=f"admin_edit_{i}")] for i, p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour admin", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)

def menu_admin_edit(i):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Nom",          callback_data=f"admin_edit_nom_{i}")],
        [InlineKeyboardButton("💰 Prix",         callback_data=f"admin_edit_prix_{i}")],
        [InlineKeyboardButton("📝 Description",  callback_data=f"admin_edit_desc_{i}")],
        [InlineKeyboardButton("📸 Photo",        callback_data=f"admin_edit_photo_{i}")],
        [InlineKeyboardButton("🗑️ Supprimer",   callback_data=f"admin_suppr_{i}")],
        [InlineKeyboardButton("⬅️ Retour",       callback_data="admin_produits")],
    ])

def menu_statut(cmd_id):
    kb = [[InlineKeyboardButton(s, callback_data=f"statut_{cmd_id}_{i}")] for i, s in enumerate(STATUTS)]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")])
    return InlineKeyboardMarkup(kb)

# ── Commandes client ───────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load()
    u = update.effective_user
    texte = data["bienvenue"].replace("{prenom}", u.first_name)
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Commandes :*\n\n/start — Menu\n/produits — Produits\n/commander — Commander\n"
        "/mescommandes — Mes commandes\n/support — Support\n/contact — Contact",
        parse_mode="Markdown"
    )

async def produits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 *Nos produits :*", parse_mode="Markdown", reply_markup=menu_produits())

async def commander_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍️ *Commander :*", parse_mode="Markdown", reply_markup=menu_commander())

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 *Support*", parse_mode="Markdown", reply_markup=menu_support())

async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Contact :*\n\n📧 contact@maboutique.com\n📱 +33 6 00 00 00 00\n🕐 Lun–Ven 9h–18h",
        parse_mode="Markdown", reply_markup=btn_retour()
    )

async def mescommandes_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load()
    uid = update.effective_user.id
    mes = [c for c in data["commandes"] if c["user_id"] == uid]
    if not mes:
        await update.message.reply_text("📋 Tu n'as pas encore de commande.", reply_markup=menu_principal())
        return
    texte = "📋 *Tes commandes :*\n\n"
    for c in mes[-5:]:
        texte += f"🔖 #{c['id']} — {c['produit']} ({c['prix']})\n📍 Statut : {c['statut']}\n\n"
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    await update.message.reply_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())

# ── Callbacks ──────────────────────────────────────────────────────────────────
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    data = load()
    uid = q.from_user.id

    # ── Navigation client ──
    if d == "menu":
        await q.edit_message_text("🏠 *Menu principal*", parse_mode="Markdown", reply_markup=menu_principal())
    elif d == "produits":
        await q.edit_message_text("📦 *Nos produits :*", parse_mode="Markdown", reply_markup=menu_produits())
    elif d == "commander":
        await q.edit_message_text("🛍️ *Commander :*\n\n💵 Paiement en espèces à la livraison", parse_mode="Markdown", reply_markup=menu_commander())
    elif d == "support":
        await q.edit_message_text("🎧 *Support*", parse_mode="Markdown", reply_markup=menu_support())
    elif d == "contact":
        await q.edit_message_text("📞 *Contact :*\n\n📧 contact@maboutique.com\n📱 +33 6 00 00 00 00\n🕐 Lun–Ven 9h–18h", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "suivi":
        await q.edit_message_text("📦 Envoie ton numéro de commande (ex: #CMD001)", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "retour":
        await q.edit_message_text("🔄 *Retour & Échange*\n\n• Sous 14 jours\n• Article en état d'origine\nEnvoie ton numéro de commande.", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "faq":
        await q.edit_message_text("❓ *FAQ :*\n\n🚚 Livraison : 3–5 jours\n💵 Paiement : espèces à la livraison\n🔄 Retour : 14 jours", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "agent":
        await q.edit_message_text("💬 *Agent*\n\n📧 support@maboutique.com\n⏳ Réponse sous 2h", parse_mode="Markdown", reply_markup=btn_retour())

    elif d == "mes_commandes":
        mes = [c for c in data["commandes"] if c["user_id"] == uid]
        if not mes:
            await q.edit_message_text("📋 Tu n'as pas encore de commande.", reply_markup=menu_principal())
        else:
            texte = "📋 *Tes commandes :*\n\n"
            for c in mes[-5:]:
                texte += f"🔖 #{c['id']} — {c['produit']} ({c['prix']})\n📍 {c['statut']}\n\n"
            await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

    elif d == "voir_avis":
        avis = data.get("avis", [])
        if not avis:
            texte = "⭐ *Avis clients*\n\nPas encore d'avis. Sois le premier !"
        else:
            texte = "⭐ *Avis clients :*\n\n"
            for a in avis[-5:]:
                texte += f"{'⭐' * a['note']} — {a['nom']}\n_{a['texte']}_\n\n"
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✍️ Laisser un avis", callback_data="laisser_avis")],
                [InlineKeyboardButton("⬅️ Retour", callback_data="menu")],
            ])
        )

    elif d == "laisser_avis":
        context.user_data["avis_etape"] = "note"
        await q.edit_message_text(
            "⭐ *Donne une note :*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⭐", callback_data="note_1"),
                InlineKeyboardButton("⭐⭐", callback_data="note_2"),
                InlineKeyboardButton("⭐⭐⭐", callback_data="note_3"),
                InlineKeyboardButton("⭐⭐⭐⭐", callback_data="note_4"),
                InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="note_5"),
            ]])
        )

    elif d.startswith("note_"):
        note = int(d.split("_")[1])
        context.user_data["avis_note"] = note
        context.user_data["avis_etape"] = "texte"
        await q.edit_message_text(f"{'⭐' * note}\n\nMaintenant écris ton commentaire :")

    elif d.startswith("produit_"):
        i = int(d.split("_")[1])
        p = data["produits"][i]
        texte = f"*{p['nom']}*\n\n💰 Prix : {p['prix']}\n📝 {p['desc']}\n\n💵 Paiement en espèces à la livraison"
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Commander", callback_data=f"acheter_{i}")],
            [InlineKeyboardButton("⬅️ Retour", callback_data="produits")],
        ])
        if p.get("photo"):
            try:
                await q.message.reply_photo(photo=p["photo"], caption=texte, parse_mode="Markdown", reply_markup=kb)
                await q.delete_message()
            except:
                await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=kb)
        else:
            await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=kb)

    elif d.startswith("acheter_"):
        i = int(d.split("_")[1])
        p = data["produits"][i]
        context.user_data["commande_produit"] = i
        context.user_data["commande_etape"] = "promo"
        await q.edit_message_text(
            f"🛍️ *{p['nom']}* — {p['prix']}\n\n🎟️ Tu as un code promo ? Envoie-le !\nSinon tape *NON*",
            parse_mode="Markdown"
        )

    # ── Admin navigation ──
    elif d == "admin_menu" and is_admin(uid):
        await q.edit_message_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())

    elif d == "admin_produits" and is_admin(uid):
        await q.edit_message_text("📦 *Produits :*", parse_mode="Markdown", reply_markup=menu_admin_produits())

    elif d == "admin_stats" and is_admin(uid):
        commandes = data["commandes"]
        total = len(commandes)
        ca = 0
        for c in commandes:
            try:
                ca += int(c["prix"].replace("€","").strip())
            except: pass
        livrees = len([c for c in commandes if "Livrée" in c["statut"]])
        texte = (
            f"📊 *Statistiques :*\n\n"
            f"📦 Commandes totales : {total}\n"
            f"✅ Livrées : {livrees}\n"
            f"💰 CA estimé : {ca}€\n"
            f"⭐ Avis reçus : {len(data.get('avis', []))}\n"
            f"🎟️ Codes promo actifs : {len(data.get('codes_promo', {}))}"
        )
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_commandes" and is_admin(uid):
        commandes = data["commandes"]
        if not commandes:
            texte = "📋 Aucune commande."
        else:
            texte = "📋 *Commandes :*\n\n"
            for c in commandes[-10:]:
                texte += f"🔖 #{c['id']} — {c['user']} → {c['produit']} ({c['prix']})\n📍 {c['statut']}\n\n"
        kb = []
        for c in commandes[-5:]:
            kb.append([InlineKeyboardButton(f"📍 Changer statut #{c['id']}", callback_data=f"chg_statut_{c['id']}")])
        kb.append([InlineKeyboardButton("🗑️ Vider tout", callback_data="admin_vider")])
        kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")])
        await q.edit_message_text(texte, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))

    elif d.startswith("chg_statut_") and is_admin(uid):
        cmd_id = d.replace("chg_statut_", "")
        await q.edit_message_text(f"📍 Choisir le statut pour #{cmd_id} :", reply_markup=menu_statut(cmd_id))

    elif d.startswith("statut_") and is_admin(uid):
        parts = d.split("_")
        cmd_id = parts[1]
        statut_idx = int(parts[2])
        nouveau_statut = STATUTS[statut_idx]
        for c in data["commandes"]:
            if str(c["id"]) == str(cmd_id):
                c["statut"] = nouveau_statut
                # Notifie le client
                try:
                    await q.get_bot().send_message(
                        c["user_id"],
                        f"📦 *Mise à jour de ta commande #{cmd_id}*\n\n"
                        f"Produit : {c['produit']}\n"
                        f"Nouveau statut : {nouveau_statut}",
                        parse_mode="Markdown"
                    )
                except: pass
                break
        save(data)
        await q.edit_message_text(f"✅ Statut mis à jour : {nouveau_statut}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_commandes")]]))

    elif d == "admin_vider" and is_admin(uid):
        data["commandes"] = []
        save(data)
        await q.edit_message_text("✅ Commandes vidées !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_promos" and is_admin(uid):
        promos = data.get("codes_promo", {})
        texte = "🎟️ *Codes promo actifs :*\n\n"
        for code, remise in promos.items():
            texte += f"• `{code}` → -{remise}%\n"
        texte += "\nPour ajouter un code, envoie : `AJOUTER_CODE NOM REMISE`\nEx: `AJOUTER_CODE NOEL30 30`"
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_avis" and is_admin(uid):
        avis = data.get("avis", [])
        if not avis:
            texte = "⭐ Aucun avis."
        else:
            texte = "⭐ *Avis reçus :*\n\n"
            for a in avis:
                texte += f"{'⭐'*a['note']} {a['nom']} : {a['texte']}\n"
        await q.edit_message_text(texte, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_bienvenue" and is_admin(uid):
        context.user_data["edit_field"] = "bienvenue"
        await q.edit_message_text(
            f"✏️ Envoie le nouveau message de bienvenue.\nUtilise *{{prenom}}* pour le prénom.\n\nActuel :\n{data['bienvenue']}",
            parse_mode="Markdown"
        )

    elif d == "admin_ajouter" and is_admin(uid):
        context.user_data["nouveau_produit"] = {}
        context.user_data["ajout_etape"] = "nom"
        await q.edit_message_text("➕ *Nouveau produit*\n\nEnvoie le *nom* :", parse_mode="Markdown")

    elif d.startswith("admin_edit_") and "_nom_" not in d and "_prix_" not in d and "_desc_" not in d and "_photo_" not in d and is_admin(uid):
        parts = d.split("_")
        if len(parts) == 3:
            i = int(parts[2])
            p = data["produits"][i]
            await q.edit_message_text(
                f"✏️ *{p['nom']}*\n💰 {p['prix']}\n📝 {p['desc']}",
                parse_mode="Markdown", reply_markup=menu_admin_edit(i)
            )

    elif d.startswith("admin_suppr_") and is_admin(uid):
        i = int(d.split("_")[2])
        del data["produits"][i]
        save(data)
        await q.edit_message_text("🗑️ Produit supprimé !", reply_markup=menu_admin_produits())

    elif d.startswith("admin_edit_nom_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "nom"
        await q.edit_message_text("✏️ Envoie le nouveau *nom* :", parse_mode="Markdown")

    elif d.startswith("admin_edit_prix_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "prix"
        await q.edit_message_text("💰 Envoie le nouveau *prix* (ex: 30€) :", parse_mode="Markdown")

    elif d.startswith("admin_edit_desc_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "desc"
        await q.edit_message_text("📝 Envoie la nouvelle *description* :", parse_mode="Markdown")

    elif d.startswith("admin_edit_photo_") and is_admin(uid):
        context.user_data["edit_index"] = int(d.split("_")[3])
        context.user_data["edit_field"] = "photo"
        await q.edit_message_text("📸 Envoie la *photo* du produit :", parse_mode="Markdown")

# ── Messages texte ─────────────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    uid = update.effective_user.id
    u = update.effective_user
    data = load()

    # ── Admin : modifier bienvenue ou champ produit ──
    if is_admin(uid) and context.user_data.get("edit_field") == "bienvenue":
        data["bienvenue"] = txt
        save(data)
        context.user_data.pop("edit_field")
        await update.message.reply_text("✅ Message mis à jour !", reply_markup=menu_admin())
        return

    if is_admin(uid) and "edit_field" in context.user_data and "edit_index" in context.user_data:
        field = context.user_data.pop("edit_field")
        i = context.user_data.pop("edit_index")
        data["produits"][i][field] = txt
        save(data)
        p = data["produits"][i]
        await update.message.reply_text(f"✅ Mis à jour !\n\n*{p['nom']}*\n💰 {p['prix']}\n📝 {p['desc']}", parse_mode="Markdown", reply_markup=menu_admin())
        return

    # ── Admin : ajouter produit ──
    if is_admin(uid) and "ajout_etape" in context.user_data:
        etape = context.user_data["ajout_etape"]
        if etape == "nom":
            context.user_data["nouveau_produit"]["nom"] = txt
            context.user_data["ajout_etape"] = "prix"
            await update.message.reply_text("💰 Envoie le *prix* (ex: 30€) :", parse_mode="Markdown")
        elif etape == "prix":
            context.user_data["nouveau_produit"]["prix"] = txt
            context.user_data["ajout_etape"] = "desc"
            await update.message.reply_text("📝 Envoie la *description* :", parse_mode="Markdown")
        elif etape == "desc":
            context.user_data["nouveau_produit"]["desc"] = txt
            context.user_data["nouveau_produit"]["photo"] = ""
            context.user_data["ajout_etape"] = "photo"
            await update.message.reply_text("📸 Envoie une *photo* du produit (ou tape SKIP pour ignorer) :", parse_mode="Markdown")
        elif etape == "photo":
            context.user_data["nouveau_produit"]["photo"] = ""
            data["produits"].append(context.user_data.pop("nouveau_produit"))
            context.user_data.pop("ajout_etape")
            save(data)
            await update.message.reply_text("✅ Produit ajouté !", reply_markup=menu_admin())
        return

    # ── Admin : code promo ──
    if is_admin(uid) and txt.startswith("AJOUTER_CODE"):
        parts = txt.split()
        if len(parts) == 3:
            code, remise = parts[1], parts[2]
            data["codes_promo"][code.upper()] = int(remise)
            save(data)
            await update.message.reply_text(f"✅ Code `{code.upper()}` -{remise}% ajouté !", parse_mode="Markdown", reply_markup=menu_admin())
        return

    # ── Client : code promo lors d'une commande ──
    if context.user_data.get("commande_etape") == "promo":
        i = context.user_data.get("commande_produit")
        p = data["produits"][i]
        code = txt.strip().upper()
        remise = 0
        if code != "NON" and code in data.get("codes_promo", {}):
            remise = data["codes_promo"][code]
            await update.message.reply_text(f"🎉 Code valide ! -{remise}% appliqué !")
        elif code != "NON":
            await update.message.reply_text("❌ Code invalide, on continue sans remise.")

        context.user_data["commande_remise"] = remise
        context.user_data["commande_etape"] = "adresse"
        await update.message.reply_text("📍 Envoie ton *adresse de livraison* :", parse_mode="Markdown")
        return

    if context.user_data.get("commande_etape") == "adresse":
        adresse = txt
        i = context.user_data.get("commande_produit")
        p = data["produits"][i]
        remise = context.user_data.get("commande_remise", 0)

        try:
            prix_num = int(p["prix"].replace("€","").strip())
            prix_final = int(prix_num * (1 - remise/100))
            prix_affiche = f"{prix_final}€"
            if remise:
                prix_affiche = f"~~{p['prix']}~~ → {prix_final}€ (-{remise}%)"
        except:
            prix_affiche = p["prix"]

        cmd_id = data.get("compteur_commande", 1)
        data["compteur_commande"] = cmd_id + 1
        commande = {
            "id": f"CMD{cmd_id:03d}",
            "user": f"{u.first_name} (@{u.username})",
            "user_id": uid,
            "produit": p["nom"],
            "prix": p["prix"],
            "remise": remise,
            "adresse": adresse,
            "statut": STATUTS[0],
            "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
        }
        data["commandes"].append(commande)
        save(data)

        context.user_data.pop("commande_etape", None)
        context.user_data.pop("commande_produit", None)
        context.user_data.pop("commande_remise", None)

        await update.message.reply_text(
            f"✅ *Commande #{commande['id']} confirmée !*\n\n"
            f"📦 {p['nom']}\n"
            f"💰 Prix : {prix_affiche}\n"
            f"📍 Livraison : {adresse}\n"
            f"💵 Paiement en espèces à la livraison\n\n"
            f"Tu recevras des notifications pour le suivi. 🙏",
            parse_mode="Markdown", reply_markup=menu_principal()
        )
        try:
            await update.get_bot().send_message(
                ADMIN_ID,
                f"🛒 *Nouvelle commande #{commande['id']} !*\n\n"
                f"👤 {u.first_name} (@{u.username})\n"
                f"📦 {p['nom']} — {p['prix']}\n"
                f"📍 {adresse}\n"
                f"🎟️ Remise : {remise}%\n"
                f"📅 {commande['date']}",
                parse_mode="Markdown"
            )
        except: pass
        return

    # ── Avis client ──
    if context.user_data.get("avis_etape") == "texte":
        note = context.user_data.pop("avis_note", 5)
        context.user_data.pop("avis_etape")
        avis = {"nom": u.first_name, "note": note, "texte": txt, "date": datetime.now().strftime("%d/%m/%Y")}
        data["avis"].append(avis)
        save(data)
        await update.message.reply_text(f"{'⭐'*note} Merci pour ton avis !", reply_markup=menu_principal())
        return

    # ── Messages libres ──
    mots = txt.lower()
    if any(m in mots for m in ("bonjour","salut","hello","bonsoir","coucou")):
        await update.message.reply_text("👋 Bonjour ! Comment puis-je t'aider ?", reply_markup=menu_principal())
    elif any(m in mots for m in ("prix","tarif","combien")):
        await update.message.reply_text("💰 Nos produits :", reply_markup=menu_produits())
    elif any(m in mots for m in ("commander","acheter","achat")):
        await update.message.reply_text("🛍️ Commander :", reply_markup=menu_commander())
    elif any(m in mots for m in ("livraison","délai","expédition")):
        await update.message.reply_text("🚚 Livraison en 3–5 jours. Paiement en espèces à la livraison.", reply_markup=btn_retour())
    elif any(m in mots for m in ("retour","remboursement","échange")):
        await update.message.reply_text("🔄 Retours sous 14 jours.", reply_markup=btn_retour())
    else:
        await update.message.reply_text("Merci 😊 Voici ce que je peux faire :", reply_markup=menu_principal())
        # Transfère le message à l'admin
        if uid != ADMIN_ID:
            try:
                await update.get_bot().send_message(
                    ADMIN_ID,
                    f"💬 *Message de {u.first_name} (@{u.username}) :*\n\n{txt}\n\n"
                    f"👉 Pour répondre : `/repondre {uid} votre message`",
                    parse_mode="Markdown"
                )
            except: pass

# ── Photos (admin) ─────────────────────────────────────────────────────────────
async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid): return
    if context.user_data.get("edit_field") == "photo" and "edit_index" in context.user_data:
        i = context.user_data.pop("edit_index")
        context.user_data.pop("edit_field")
        photo_id = update.message.photo[-1].file_id
        data = load()
        data["produits"][i]["photo"] = photo_id
        save(data)
        await update.message.reply_text("✅ Photo mise à jour !", reply_markup=menu_admin())
    elif context.user_data.get("ajout_etape") == "photo":
        photo_id = update.message.photo[-1].file_id
        context.user_data["nouveau_produit"]["photo"] = photo_id
        data = load()
        data["produits"].append(context.user_data.pop("nouveau_produit"))
        context.user_data.pop("ajout_etape")
        save(data)
        await update.message.reply_text("✅ Produit ajouté avec photo !", reply_markup=menu_admin())

# ── Répondre à un client ───────────────────────────────────────────────────────
async def repondre_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Format : `/repondre USER_ID message`\n\nEx: `/repondre 123456789 Votre commande est prête !`",
            parse_mode="Markdown"
        )
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
        await update.message.reply_text("⛔ Accès refusé.")
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
    await update.message.reply_text(f"✅ Message envoyé à {envoyes} clients !")

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",         start))
    app.add_handler(CommandHandler("help",          help_cmd))
    app.add_handler(CommandHandler("produits",      produits_cmd))
    app.add_handler(CommandHandler("commander",     commander_cmd))
    app.add_handler(CommandHandler("support",       support_cmd))
    app.add_handler(CommandHandler("contact",       contact_cmd))
    app.add_handler(CommandHandler("mescommandes",  mescommandes_cmd))
    app.add_handler(CommandHandler("admin",         admin_cmd))
    app.add_handler(CommandHandler("repondre",      repondre_cmd))
    app.add_handler(CommandHandler("broadcast",     broadcast_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.PHOTO, photo_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot lancé ! Appuie sur Ctrl+C pour arrêter.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
