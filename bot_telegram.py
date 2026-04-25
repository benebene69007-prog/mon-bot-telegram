#!/usr/bin/env python3
"""
Bot Telegram - Boutique & Support Client avec Panel Admin
Lance : py -3.11 bot_telegram.py
"""

import json
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters, ConversationHandler,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)

TOKEN = "8616508368:AAH6P6rlQXU0ZzQl6SSjC9OW8ZEbPkZABHQ"
ADMIN_ID = 8464360679

DATA_FILE = "boutique_data.json"

# ── États conversation admin ───────────────────────────────────────────────────
ATTENTE_NOM, ATTENTE_PRIX, ATTENTE_DESC = range(3)
EDIT_NOM, EDIT_PRIX, EDIT_DESC = range(3, 6)
ATTENTE_BIENVENUE = 6

# ── Données par défaut ─────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "bienvenue": "👋 Bonjour *{prenom}* ! Bienvenue dans notre boutique.\n\nChoisis une option 👇",
    "produits": [
        {"nom": "👕 T-Shirt Premium",          "prix": "25€", "desc": "100% coton, tailles S→XL"},
        {"nom": "👟 Sneakers Édition Limitée", "prix": "89€", "desc": "Coloris exclusifs, stock limité"},
        {"nom": "🎒 Sac à dos Urban",          "prix": "45€", "desc": "Imperméable, 20L"},
        {"nom": "🧢 Casquette Logo",           "prix": "18€", "desc": "Ajustable, broderie premium"},
    ],
    "commandes": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA.copy()

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    return user_id == ADMIN_ID

# ── Menus clients ──────────────────────────────────────────────────────────────
def menu_principal():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Commander",        callback_data="commander")],
        [InlineKeyboardButton("📦 Voir les produits", callback_data="produits")],
        [InlineKeyboardButton("🎧 Support client",    callback_data="support")],
        [InlineKeyboardButton("📞 Nous contacter",    callback_data="contact")],
        [InlineKeyboardButton("ℹ️ À propos",          callback_data="apropos")],
    ])

def menu_produits():
    data = load_data()
    kb = [[InlineKeyboardButton(f"{p['nom']} — {p['prix']}", callback_data=f"produit_{i}")] for i, p in enumerate(data["produits"])]
    kb.append([InlineKeyboardButton("⬅️ Retour", callback_data="menu")])
    return InlineKeyboardMarkup(kb)

def menu_commander():
    data = load_data()
    kb = [[InlineKeyboardButton(f"✅ {p['nom']}", callback_data=f"acheter_{i}")] for i, p in enumerate(data["produits"])]
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
        [InlineKeyboardButton("📦 Gérer les produits",     callback_data="admin_produits")],
        [InlineKeyboardButton("➕ Ajouter un produit",     callback_data="admin_ajouter")],
        [InlineKeyboardButton("📋 Voir les commandes",     callback_data="admin_commandes")],
        [InlineKeyboardButton("✏️ Modifier le message /start", callback_data="admin_bienvenue")],
        [InlineKeyboardButton("🗑️ Vider les commandes",   callback_data="admin_vider_commandes")],
    ])

def menu_admin_produits():
    data = load_data()
    kb = []
    for i, p in enumerate(data["produits"]):
        kb.append([InlineKeyboardButton(f"✏️ {p['nom']} — {p['prix']}", callback_data=f"admin_edit_{i}")])
    kb.append([InlineKeyboardButton("⬅️ Retour admin", callback_data="admin_menu")])
    return InlineKeyboardMarkup(kb)

def menu_admin_edit(i):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Modifier le nom",         callback_data=f"admin_edit_nom_{i}")],
        [InlineKeyboardButton("💰 Modifier le prix",        callback_data=f"admin_edit_prix_{i}")],
        [InlineKeyboardButton("📝 Modifier la description", callback_data=f"admin_edit_desc_{i}")],
        [InlineKeyboardButton("🗑️ Supprimer ce produit",   callback_data=f"admin_suppr_{i}")],
        [InlineKeyboardButton("⬅️ Retour",                  callback_data="admin_produits")],
    ])

# ── Commandes client ───────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    u = update.effective_user
    texte = data["bienvenue"].replace("{prenom}", u.first_name)
    await update.message.reply_text(texte, parse_mode="Markdown", reply_markup=menu_principal())

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Commandes :*\n\n/start — Menu principal\n/produits — Nos produits\n"
        "/commander — Passer une commande\n/support — Support\n/contact — Nous joindre",
        parse_mode="Markdown"
    )

async def produits_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📦 *Nos produits :*", parse_mode="Markdown", reply_markup=menu_produits())

async def commander_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🛍️ *Commander :*", parse_mode="Markdown", reply_markup=menu_commander())

async def support_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎧 *Support client*", parse_mode="Markdown", reply_markup=menu_support())

async def contact_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📞 *Contact :*\n\n📧 contact@maboutique.com\n📱 +33 6 00 00 00 00\n🕐 Lun–Ven 9h–18h",
        parse_mode="Markdown", reply_markup=btn_retour()
    )

# ── Commande admin ─────────────────────────────────────────────────────────────
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Accès refusé.")
        return
    await update.message.reply_text(
        "🔧 *Panel Admin*\n\nQue veux-tu faire ?",
        parse_mode="Markdown", reply_markup=menu_admin()
    )

# ── Callbacks ──────────────────────────────────────────────────────────────────
async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data
    data = load_data()
    uid = q.from_user.id

    # ── Navigation client ──
    if d == "menu":
        await q.edit_message_text("🏠 *Menu principal*", parse_mode="Markdown", reply_markup=menu_principal())
    elif d == "produits":
        await q.edit_message_text("📦 *Nos produits :*", parse_mode="Markdown", reply_markup=menu_produits())
    elif d == "commander":
        await q.edit_message_text("🛍️ *Commander :*", parse_mode="Markdown", reply_markup=menu_commander())
    elif d == "support":
        await q.edit_message_text("🎧 *Support client*", parse_mode="Markdown", reply_markup=menu_support())
    elif d == "contact":
        await q.edit_message_text(
            "📞 *Contact :*\n\n📧 contact@maboutique.com\n📱 +33 6 00 00 00 00\n🕐 Lun–Ven 9h–18h",
            parse_mode="Markdown", reply_markup=btn_retour()
        )
    elif d == "apropos":
        await q.edit_message_text(
            "ℹ️ *À propos :*\n\nBoutique en ligne mode urbaine.\n🌟 Qualité · 🚚 Livraison rapide · 🔄 Retour facile",
            parse_mode="Markdown", reply_markup=btn_retour()
        )
    elif d.startswith("produit_"):
        i = int(d.split("_")[1])
        p = data["produits"][i]
        await q.edit_message_text(
            f"*{p['nom']}*\n\n💰 Prix : {p['prix']}\n📝 {p['desc']}\n\nSouhaites-tu commander ?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Commander", callback_data=f"acheter_{i}")],
                [InlineKeyboardButton("⬅️ Retour", callback_data="produits")],
            ])
        )
    elif d.startswith("acheter_"):
        i = int(d.split("_")[1])
        p = data["produits"][i]
        u = q.from_user
        # Enregistre la commande
        commande = {"user": f"{u.first_name} (@{u.username})", "user_id": u.id, "produit": p["nom"], "prix": p["prix"]}
        data["commandes"].append(commande)
        save_data(data)
        # Notifie l'admin
        try:
            await q.get_bot().send_message(
                ADMIN_ID,
                f"🛒 *Nouvelle commande !*\n\n👤 Client : {u.first_name} (@{u.username})\n"
                f"📦 Produit : {p['nom']}\n💰 Prix : {p['prix']}\n\n"
                f"Réponds-lui directement sur Telegram !",
                parse_mode="Markdown"
            )
        except Exception:
            pass
        await q.edit_message_text(
            f"✅ *Commande initiée !*\n\nArticle : {p['nom']}\nPrix : {p['prix']}\n\n"
            "📩 Envoie-nous ton adresse et ta taille.\nUn agent te contacte sous 24h. 🙏",
            parse_mode="Markdown", reply_markup=btn_retour()
        )
    elif d == "suivi":
        await q.edit_message_text("📦 *Suivi*\n\nEnvoie ton numéro de commande (ex: #CMD12345)", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "retour":
        await q.edit_message_text("🔄 *Retour & Échange*\n\n• Sous 14 jours\n• Article en état d'origine\n\nEnvoie ton numéro de commande.", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "faq":
        await q.edit_message_text("❓ *FAQ :*\n\n🚚 Livraison : 3–5 jours\n💳 CB, PayPal, virement\n🔄 Retour : 14 jours", parse_mode="Markdown", reply_markup=btn_retour())
    elif d == "agent":
        await q.edit_message_text("💬 *Agent*\n\n📧 support@maboutique.com\n⏳ Réponse sous 2h", parse_mode="Markdown", reply_markup=btn_retour())

    # ── Panel admin ──
    elif d == "admin_menu" and is_admin(uid):
        await q.edit_message_text("🔧 *Panel Admin*", parse_mode="Markdown", reply_markup=menu_admin())

    elif d == "admin_produits" and is_admin(uid):
        await q.edit_message_text("📦 *Gérer les produits :*\n\nClique sur un produit pour le modifier.",
                                   parse_mode="Markdown", reply_markup=menu_admin_produits())

    elif d == "admin_commandes" and is_admin(uid):
        if not data["commandes"]:
            texte = "📋 *Commandes :*\n\nAucune commande pour l'instant."
        else:
            texte = "📋 *Commandes reçues :*\n\n"
            for i, c in enumerate(data["commandes"], 1):
                texte += f"{i}. {c['user']} → {c['produit']} ({c['prix']})\n"
        await q.edit_message_text(texte, parse_mode="Markdown",
                                   reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d == "admin_vider_commandes" and is_admin(uid):
        data["commandes"] = []
        save_data(data)
        await q.edit_message_text("✅ Commandes vidées !", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Retour", callback_data="admin_menu")]]))

    elif d.startswith("admin_edit_") and not any(x in d for x in ["nom_", "prix_", "desc_"]) and is_admin(uid):
        parts = d.split("_")
        if len(parts) == 3:
            i = int(parts[2])
            p = data["produits"][i]
            await q.edit_message_text(
                f"✏️ *{p['nom']}*\n💰 {p['prix']}\n📝 {p['desc']}\n\nQue veux-tu faire ?",
                parse_mode="Markdown", reply_markup=menu_admin_edit(i)
            )

    elif d.startswith("admin_suppr_") and is_admin(uid):
        i = int(d.split("_")[2])
        del data["produits"][i]
        save_data(data)
        await q.edit_message_text("🗑️ Produit supprimé !", reply_markup=menu_admin_produits())

    elif d.startswith("admin_edit_nom_") and is_admin(uid):
        i = int(d.split("_")[3])
        context.user_data["edit_index"] = i
        context.user_data["edit_field"] = "nom"
        await q.edit_message_text(f"✏️ Envoie le *nouveau nom* du produit :", parse_mode="Markdown")

    elif d.startswith("admin_edit_prix_") and is_admin(uid):
        i = int(d.split("_")[3])
        context.user_data["edit_index"] = i
        context.user_data["edit_field"] = "prix"
        await q.edit_message_text(f"💰 Envoie le *nouveau prix* (ex: 30€) :", parse_mode="Markdown")

    elif d.startswith("admin_edit_desc_") and is_admin(uid):
        i = int(d.split("_")[3])
        context.user_data["edit_index"] = i
        context.user_data["edit_field"] = "desc"
        await q.edit_message_text(f"📝 Envoie la *nouvelle description* :", parse_mode="Markdown")

    elif d == "admin_ajouter" and is_admin(uid):
        context.user_data["nouveau_produit"] = {}
        context.user_data["ajout_etape"] = "nom"
        await q.edit_message_text("➕ *Nouveau produit*\n\nEnvoie le *nom* du produit :", parse_mode="Markdown")

    elif d == "admin_bienvenue" and is_admin(uid):
        context.user_data["edit_field"] = "bienvenue"
        await q.edit_message_text(
            "✏️ Envoie le nouveau message de bienvenue.\n\nUtilise *{prenom}* pour le prénom du client.\n\n"
            f"Actuel :\n{data['bienvenue']}", parse_mode="Markdown"
        )

# ── Messages texte ─────────────────────────────────────────────────────────────
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    uid = update.effective_user.id
    data = load_data()

    # ── Traitement admin en cours ──
    if is_admin(uid) and "edit_field" in context.user_data:
        field = context.user_data.pop("edit_field")

        if field == "bienvenue":
            data["bienvenue"] = txt
            save_data(data)
            await update.message.reply_text("✅ Message de bienvenue mis à jour !", reply_markup=menu_admin())
            return

        i = context.user_data.pop("edit_index", None)
        if i is not None:
            data["produits"][i][field] = txt
            save_data(data)
            p = data["produits"][i]
            await update.message.reply_text(
                f"✅ Produit mis à jour !\n\n*{p['nom']}*\n💰 {p['prix']}\n📝 {p['desc']}",
                parse_mode="Markdown", reply_markup=menu_admin()
            )
            return

    # ── Ajout produit étape par étape ──
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
            data["produits"].append(context.user_data.pop("nouveau_produit"))
            context.user_data.pop("ajout_etape")
            save_data(data)
            await update.message.reply_text("✅ Produit ajouté !", reply_markup=menu_admin())
        return

    # ── Messages clients ──
    mots = txt.lower()
    if any(m in mots for m in ("bonjour","salut","hello","bonsoir","coucou")):
        await update.message.reply_text("👋 Bonjour ! Comment puis-je t'aider ?", reply_markup=menu_principal())
    elif any(m in mots for m in ("prix","tarif","combien")):
        await update.message.reply_text("💰 Nos produits :", reply_markup=menu_produits())
    elif any(m in mots for m in ("commander","acheter","achat")):
        await update.message.reply_text("🛍️ Que veux-tu commander ?", reply_markup=menu_commander())
    elif any(m in mots for m in ("livraison","délai","expédition")):
        await update.message.reply_text("🚚 Livraison en 3–5 jours ouvrés. Suivi inclus par email.", reply_markup=btn_retour())
    elif any(m in mots for m in ("retour","remboursement","échange")):
        await update.message.reply_text("🔄 Retours acceptés sous 14 jours.", reply_markup=btn_retour())
    elif any(m in mots for m in ("contact","email","téléphone")):
        await update.message.reply_text("📞 contact@maboutique.com | +33 6 00 00 00 00", reply_markup=btn_retour())
    else:
        await update.message.reply_text(
            "Merci pour ton message 😊 Voici ce que je peux faire :",
            reply_markup=menu_principal()
        )

# ── Main ───────────────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",     start))
    app.add_handler(CommandHandler("help",      help_cmd))
    app.add_handler(CommandHandler("produits",  produits_cmd))
    app.add_handler(CommandHandler("commander", commander_cmd))
    app.add_handler(CommandHandler("support",   support_cmd))
    app.add_handler(CommandHandler("contact",   contact_cmd))
    app.add_handler(CommandHandler("admin",     admin_cmd))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("✅ Bot lancé ! Appuie sur Ctrl+C pour arrêter.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
