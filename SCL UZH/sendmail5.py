import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler
import requests
import logging
import re
import html2text
import json
import datetime


BOT_TOKEN = "6299749652:AAFbuB_LWiP2HdktVpyUH-NcFs8OAfd1kXo"
ELASTIC_API_KEY = "1B09FB3140BFC76FD8B76C155ECCDBB00CB0FD2BA752DB654BF12794EA213E6BFAD5525CA2563A08624782D1CE10140F"
STRATO_EMAIL_ADDRESS = "student-project@blockchainpresence.net"

def load_templates(context):
    templates = {}
    for filename in os.listdir('templates'):
        with open(os.path.join('templates', filename), 'r') as file:
            content = file.read()
            button_title = re.search(
                r'{ButtonTitle:\s*([^\n]+)}', content).group(1).strip()
            subject = re.search(
                r'{Subject:\s*([^\n]+)}', content).group(1).strip()
            content = re.sub(
                r'{(ButtonTitle|Subject):\s*[^\n]*\n}', '', content)
            templates[filename] = {
                'content': content, 'button_title': button_title, 'subject': subject}
    context.bot_data['templates'] = templates


def load_template(context, template_name):
    template = context.bot_data['templates'][template_name].copy()
    return template


def store_sent_email(to_email, chosen_template, user_name):
    sent_emails_file = 'sent_emails.json'
    max_data_sets = 50

    if os.path.exists(sent_emails_file):
        with open(sent_emails_file, 'r') as file:
            sent_emails = json.load(file)
            if len(sent_emails) >= max_data_sets:
                sent_emails = sent_emails[-(max_data_sets - 1):]
    else:
        sent_emails = []

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    sent_email_data = {
        "to_email": to_email,
        "subject": chosen_template['button_title'],  # Store the button title instead of subject
        "timestamp": timestamp,
        "user_name": user_name
    }
    sent_emails.append(sent_email_data)

    with open(sent_emails_file, 'w') as file:
        if len(sent_emails) > max_data_sets:
            sent_emails = sent_emails[-max_data_sets:]
        json.dump(sent_emails, file, indent=4, ensure_ascii=True)
        file.write('\n')

def mail(update: Update, context: CallbackContext):
    templates_dir = 'templates'
    templates = [f for f in os.listdir(templates_dir) if f.endswith('.txt')]
    if not templates:
        return update.message.reply_text('No templates found.')
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(context.bot_data['templates'][t]['button_title'], callback_data=f'template_{t}') for t in templates[:len(templates)//2]],
        [InlineKeyboardButton(context.bot_data['templates'][t]['button_title'], callback_data=f'template_{t}') for t in templates[len(templates)//2:]]
    ])

    update.message.reply_text('Choose a template:', reply_markup=reply_markup)


def template_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    template_name = query.data.split('_')[1]
    context.user_data['template_name'] = template_name
    query.answer()
    missing_vars = re.findall(
        r'{(\w+)}', context.bot_data['templates'][template_name]['content'])
    context.user_data['missing_vars'] = missing_vars
    query.edit_message_text(
        f"Selected template: {context.bot_data['templates'][template_name]['button_title']}\n\nPlease enter the required information separated by commas: {', '.join(missing_vars)}")
    context.user_data['template'] = load_template(context, template_name)
    context.user_data['state'] = 'info'

def info_received(update: Update, context: CallbackContext):
    info = update.message.text.split(',')
    if len(info) != len(context.user_data['missing_vars']):
        update.message.reply_text(
            f'Please enter exactly {len(context.user_data["missing_vars"])} values separated by a comma: {", ".join(context.user_data["missing_vars"])}')
        return
    context.user_data['info'] = dict(zip(context.user_data['missing_vars'], info))
    update.message.reply_text("Please enter the receiver's email address:")
    context.user_data['state'] = 'email'


def email_received(update: Update, context: CallbackContext):
    email = update.message.text
    context.user_data['email'] = email
    context.user_data['state'] = 'preview'

    template = context.user_data['template']
    email_body = template['content']
    for var, value in context.user_data['info'].items():
        email_body = email_body.replace(f"{{{var}}}", value)
    email_body = re.sub(r'{(Subject|ButtonTitle):.*}', '', email_body)
    email_body = f"<!DOCTYPE html><html><body>{email_body}</body></html>"
    text_body = html2text.html2text(email_body)
    text_body = re.sub(
        r'\|\s+!\[image description\]\(https://i.imgur.com/nTgZcwa.png\)', '', text_body)
    text_body = re.sub(r'---', '', text_body)
    text_body = re.sub(r'# Smart Contracts Lab', '', text_body)
    text_body = re.sub(r'\(C\) 2023 Smart Contracts Lab', '', text_body)
    preview = f"Subject: {template['subject']}\n\n{text_body.strip()}\n\nTo: {email}"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Send", callback_data="send_email")],
        [InlineKeyboardButton("Edit", callback_data="edit")],  # Add this line
        [InlineKeyboardButton("Scrap", callback_data="scrap_email")],
    ])
    update.message.reply_text(preview, reply_markup=reply_markup)


def edit_selected(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Edit Subject", callback_data="edit_subject")],
        [InlineKeyboardButton("Edit Mail", callback_data="edit_mail")],
    ])
    query.edit_message_text(
        "Select the information you want to edit:", reply_markup=reply_markup)


def show_email_preview(update: Update, context: CallbackContext):
    template = context.user_data['template']
    email_body = template['content']
    for var, value in context.user_data['info'].items():
        email_body = email_body.replace(f"{{{var}}}", value)
    email_body = re.sub(r'{(Subject|ButtonTitle):.*}', '', email_body)
    email_body = f"<!DOCTYPE html><html><body>{email_body}</body></html>"
    text_body = html2text.html2text(email_body)
    text_body = re.sub(
        r'\|\s+!\[image description\]\(https://i.imgur.com/nTgZcwa.png\)', '', text_body)
    text_body = re.sub(r'---', '', text_body)
    text_body = re.sub(r'# Smart Contracts Lab', '', text_body)
    text_body = re.sub(r'\(C\) 2023 Smart Contracts Lab', '', text_body)
    preview = f"Subject: {template['subject']}\n\n{text_body.strip()}\n\nTo: {context.user_data['email']}"

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Send", callback_data="send_email")],
        [InlineKeyboardButton("Edit", callback_data="edit")],
        [InlineKeyboardButton("Scrap", callback_data="scrap_email")],
    ])
    update.message.reply_text(preview, reply_markup=reply_markup)

def edit_subject(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data["state"] = "edit_subject"
    query.edit_message_text("Please enter the new subject:")
    return

    query = update.callback_query
    query.answer()
    context.user_data["state"] = "edit_text"
    query.message.reply_text("Please edit the text below and send it back:", quote=True)
    query.message.reply_text(context.user_data["template"]["content"], quote=True)

def edit_mail(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    context.user_data["state"] = "edit_mail"
    query.edit_message_text("Please enter the new email address:")
    return

def process_edit(update: Update, context: CallbackContext):
    state = context.user_data.get("state")
    if state == "edit_subject":
        new_subject = update.message.text
        context.user_data["template"]["subject"] = new_subject
    elif state == "edit_text":
        new_text = update.message.text
        context.user_data["template"]["content"] = new_text
    elif state == "edit_mail":
        new_email = update.message.text
        context.user_data["email"] = new_email

    context.user_data["state"] = "preview"
    show_email_preview(update, context)


def process_message(update: Update, context: CallbackContext):
    state = context.user_data.get('state')
    if state == 'info':
        info_received(update, context)
    elif state == 'email':
        email_received(update, context)
    elif state == 'edit_subject' or state == 'edit_mail':
        process_edit(update, context)

def send_email(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    template_name = context.user_data['template_name']
    template = load_template(context, template_name)
    subject = template['button_title']  # Access the button title instead of subject
    email_body = template['content']

    for var, value in context.user_data['info'].items():
        email_body = email_body.replace(f"{{{var}}}", value)
    email_body = re.sub(r'{Subject:.*}', '', email_body)
    email_body = re.sub(r'{ButtonTitle:.*}', '', email_body)

    to_email = context.user_data['email']
    user_name = update.effective_user.full_name  # Get the user's name from the update object
    store_sent_email(to_email, template, user_name)  # Pass the template instead of subject
    data = {"apikey": ELASTIC_API_KEY, "from": STRATO_EMAIL_ADDRESS, "to": to_email,
            "subject": subject, "bodyHtml": email_body, "isTransactional": "true"}
    response = requests.post(
        "https://api.elasticemail.com/v2/email/send", data=data)
    logging.info(f'Elastic Email API response: {response.text}')
    if response.status_code == 200:
        query.edit_message_text('Email sent successfully!')
    else:
        query.edit_message_text(f'Error sending email: {response.text}')
    reset_user_data(context)

def scrap_email(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('Email scrapped!')
    reset_user_data(context)


def reset_user_data(context):
    context.user_data.pop('state', None)
    context.user_data.pop('template_name', None)
    context.user_data.pop('missing_vars', None)
    context.user_data.pop('info', None)
    context.user_data.pop('email', None)
    context.user_data.pop('template', None)

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    context = updater.dispatcher
    load_templates(context)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('mail', mail))
    dp.add_handler(CallbackQueryHandler(
        template_selected, pattern='^template_'))
    dp.add_handler(CallbackQueryHandler(edit_selected, pattern='^edit$'))
    dp.add_handler(CallbackQueryHandler(
        edit_subject, pattern='^edit_subject$'))
    dp.add_handler(CallbackQueryHandler(edit_mail, pattern='^edit_mail$'))
    dp.add_handler(CallbackQueryHandler(send_email, pattern='^send_email$'))
    dp.add_handler(CallbackQueryHandler(scrap_email, pattern='^scrap_email$'))
    dp.add_handler(MessageHandler(None, process_message))
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
