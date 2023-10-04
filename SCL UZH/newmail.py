from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler, Filters
import markdown
import html2text
import re
import requests
import logging
import json
import datetime
import os
import time

BOT_TOKEN = "6299749652:AAFbuB_LWiP2HdktVpyUH-NcFs8OAfd1kXo"
ELASTIC_API_KEY = "1B09FB3140BFC76FD8B76C155ECCDBB00CB0FD2BA752DB654BF12794EA213E6BFAD5525CA2563A08624782D1CE10140F"
STRATO_EMAIL_ADDRESS = "student-project@blockchainpresence.net"

HTML_TEMPLATE_BEFORE = """
<!DOCTYPE html>
<html>
  <table width="100%" style="background-color: #FFFFFF; color: #1F2937;">
    <tr>
      <td style="padding: 20px;">
"""

HTML_TEMPLATE_AFTER = """
      </td>
    </tr>
  </table>
</html>
"""


def newmail(update: Update, context: CallbackContext):
    update.message.reply_text(
        "Please enter the receiver's email address and the subject separated by a comma:")
    context.user_data['state'] = 'newmail_info'


def newmail_info_received(update: Update, context: CallbackContext):
    info = update.message.text.split(',')
    if len(info) != 2:
        update.message.reply_text(
            'Please enter the email address and subject separated by a comma:')
        return

    context.user_data['email'], context.user_data['subject'] = info[0].strip(
    ), info[1].strip()

    instructions = "Please enter the email body. \n\nTo make text <b>bold</b>, wrap it in <b>&lt;b&gt;</b> and <b>&lt;/b&gt;</b> tags."
    update.message.reply_text(instructions, parse_mode='HTML')

    context.user_data['state'] = 'newmail_body'


def newmail_body_received(update: Update, context: CallbackContext):
    email_body = update.message.text
    email_body_html = markdown.markdown(email_body)
    email_body_html = HTML_TEMPLATE_BEFORE + email_body_html + HTML_TEMPLATE_AFTER
    email_body_html = re.sub(r'---', '', email_body_html)
    context.user_data['email_body'] = email_body_html

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Send", callback_data="newmail_send_email")],
        [InlineKeyboardButton("Edit", callback_data="newmail_edit_options")],
        [InlineKeyboardButton("Scrap", callback_data="newmail_scrap_email")],
    ])
    recipient_email = context.user_data['email']
    email_subject = context.user_data['subject']
    email_preview = f"Subject: {email_subject}\n\n{email_body}\n\nTo: {recipient_email}"
    update.message.reply_text(email_preview, reply_markup=reply_markup)
    context.user_data['state'] = 'newmail_preview'


def store_sent_email(to_email, subject, user_name):
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
        "subject": subject,
        "timestamp": timestamp,
        "user_name": user_name
    }
    sent_emails.append(sent_email_data)

    with open(sent_emails_file, 'w') as file:
        if len(sent_emails) > max_data_sets:
            sent_emails = sent_emails[-max_data_sets:]
        json.dump(sent_emails, file, indent=4, ensure_ascii=True)
        file.write('\n')


def newmail_send_email(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    email_body = context.user_data['email_body']
    subject = context.user_data['subject']
    to_email = context.user_data['email']
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # Get the user's name from the update object
    user_name = update.effective_user.full_name

    # Pass the user's name to the store_sent_email function
    store_sent_email(to_email, subject, user_name)

    # Your email sending code here
    data = {
        "apikey": ELASTIC_API_KEY,
        "from": STRATO_EMAIL_ADDRESS,
        "to": to_email,
        "subject": subject,
        "bodyHtml": email_body,
        "isTransactional": "true"
    }
    response = requests.post(
        "https://api.elasticemail.com/v2/email/send", data=data)
    logging.info(f'Elastic Email API response: {response.text}')

    if response.status_code == 200:
        query.edit_message_text('Email sent successfully!')
    else:
        query.edit_message_text(f'Error sending email: {response.text}')


def newmail_scrap_email(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('Email scrapped!')


def newmail_edit_options(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "Edit Subject", callback_data="newmail_edit_subject")],
        [InlineKeyboardButton(
            "Edit Mail", callback_data="newmail_edit_recipient")],
    ])
    query.edit_message_text('Choose an option to edit:',
                            reply_markup=reply_markup)


def newmail_edit_subject(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text('Please enter the new subject:')
    context.user_data['state'] = 'edit_subject'


def newmail_edit_recipient(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Please enter the new recipient's email address:")
    context.user_data['state'] = 'edit_recipient'


def newmail_process_message(update: Update, context: CallbackContext):
    state = context.user_data.get('state')
    if state == 'newmail_info':
        newmail_info_received(update, context)
    elif state == 'newmail_body':
        newmail_body_received(update, context)
    elif state == 'edit_subject':
        context.user_data['subject'] = update.message.text
        show_email_preview(update, context)
        # Set the state to 'newmail_preview' after editing the subject
        context.user_data['state'] = 'newmail_preview'
    elif state == 'edit_recipient':
        context.user_data['email'] = update.message.text
        show_email_preview(update, context)
        # Set the state to 'newmail_preview' after editing the recipient
        context.user_data['state'] = 'newmail_preview'
    elif state == 'edit_body':
        # Reuse to show the updated preview
        newmail_body_received(update, context)


def show_email_preview(update: Update, context: CallbackContext):
    email_body = context.user_data['email_body']
    email_body_text = html2text.html2text(email_body)
    # Remove the '---' and extra spaces from the email preview text
    email_body_text = email_body_text.replace('---', '').strip()

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("Send", callback_data="newmail_send_email")],
        [InlineKeyboardButton("Edit", callback_data="newmail_edit_options")],
        [InlineKeyboardButton("Scrap", callback_data="newmail_scrap_email")],
    ])
    recipient_email = context.user_data['email']
    email_subject = context.user_data['subject']
    email_preview = f"Subject: {email_subject}\n\n{email_body_text}\n\nTo: {recipient_email}"
    update.message.reply_text(email_preview, reply_markup=reply_markup)
    context.user_data['state'] = 'newmail_preview'


def reset_user_data(context: CallbackContext):
    context.user_data.pop('state', None)
    context.user_data.pop('template_name', None)
    context.user_data.pop('missing_vars', None)
    context.user_data.pop('info', None)
    context.user_data.pop('email', None)
    context.user_data.pop('template', None)


def main2():
    updater = Updater(BOT_TOKEN)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler("newmail", newmail))
    dispatcher.add_handler(CallbackQueryHandler(
        newmail_send_email, pattern="newmail_send_email"))
    dispatcher.add_handler(CallbackQueryHandler(
        newmail_scrap_email, pattern="newmail_scrap_email"))
    dispatcher.add_handler(CallbackQueryHandler(
        newmail_edit_options, pattern="newmail_edit_options"))
    dispatcher.add_handler(CallbackQueryHandler(
        newmail_edit_subject, pattern="newmail_edit_subject"))
    dispatcher.add_handler(CallbackQueryHandler(
        newmail_edit_recipient, pattern="newmail_edit_recipient"))
    dispatcher.add_handler(MessageHandler(
        Filters.text & (~Filters.command), newmail_process_message))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main2()
