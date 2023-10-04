import json
import datetime
import os
import webbrowser
from fpdf import FPDF
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, CallbackContext, CallbackQueryHandler
from io import BytesIO
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
from PIL import Image, ImageDraw, ImageFont
from telegram.ext import Filters

# Read sent emails from file
def read_sent_emails(file_path):
    with open(file_path, 'r') as file:
        sent_emails = json.load(file)
    return sent_emails

def handle_search(update, context):
    keyboard = [
        [InlineKeyboardButton("By subject", callback_data='search_subject')],
        [InlineKeyboardButton("By email address", callback_data='search_email')],
        [InlineKeyboardButton("Back", callback_data='back_to_menu')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please choose a search criterion:", reply_markup=reply_markup)

def handle_search_subject(update, context):
    keyboard = [
        [InlineKeyboardButton("Back", callback_data='back_to_search')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please enter the subject to search for:", reply_markup=reply_markup)

def handle_search_email(update, context):
    keyboard = [
        [InlineKeyboardButton("Back", callback_data='back_to_search')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query = update.callback_query
    query.answer()
    query.edit_message_text(text="Please enter the email address to search for:", reply_markup=reply_markup)

def handle_subject_search(update, context):
    subject = update.message.text
    sent_emails = read_sent_emails('sent_emails.json')
    df = pd.DataFrame(sent_emails)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['subject'] == subject]
    if df.empty:
        update.message.reply_text("No emails found with that subject.")
    else:
        message = ""
        for _, row in df.iterrows():
            message += f"{row['user_name']} sent a {row['subject']} to {row['to_email']} at {row['timestamp'].strftime('%d.%m.%Y %H:%M')}\n"
        update.message.reply_text(message.strip())

def handle_email_search(update, context):
    email = update.message.text
    sent_emails = read_sent_emails('sent_emails.json')
    df = pd.DataFrame(sent_emails)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df[df['to_email'] == email]
    if df.empty:
        update.message.reply_text("No emails found with that email address.")
    else:
        message = ""
        for _, row in df.iterrows():
            message += f"{row['user_name']} sent a {row['subject']} to {row['to_email']} at {row['timestamp'].strftime('%d.%m.%Y %H:%M')}\n"
        update.message.reply_text(message.strip())

def sent(update, context):
    keyboard = [
        [InlineKeyboardButton("Plots", callback_data='summary_1')],
        [InlineKeyboardButton("Last 5", callback_data='summary_2')],
        [InlineKeyboardButton("Search", callback_data='search')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    update.message.reply_text('Please choose an option:', reply_markup=reply_markup)

def generate_summary(update, sent_emails, summary_type):
    # Convert to DataFrame and parse timestamps
    query = update.callback_query
    text_message = ""
    df = pd.DataFrame(sent_emails)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Add week number column
    df['week_number'] = df['timestamp'].dt.isocalendar().week

    # Filter for the last two weeks
    two_weeks_ago = datetime.now() - timedelta(weeks=2)
    df_last_two_weeks = df[df['timestamp'] >= two_weeks_ago]

    if summary_type == 'summary_1':
        # Generate an overview with two plots and a list of the last emails sent out.
        fig, axes = plt.subplots(2, 1, figsize=(10, 10))

        color_scheme = '#006837'
        
        # Plot number of emails per subject for the last two weeks
        df_last_two_weeks['subject'].value_counts().plot(kind='bar', ax=axes[0], color=color_scheme)
        axes[0].set_title('Number of emails per subject (last two weeks)')
        axes[0].set_facecolor('white') # Set background color to white

        # Plot number of emails sent out per week number
        df['week_number'].value_counts().sort_index().plot(kind='bar', ax=axes[1], color=color_scheme)
        axes[1].set_title('Number of emails per week number')
        axes[1].set_facecolor('white') # Set background color to white

        fig.tight_layout()
        
        # Save the figure to a BytesIO object
        buf = BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        
        return buf

    elif summary_type == 'summary_2':
        # Just display the 5 last entries from the JSON file.
        last_entries = df.tail(5)
        if last_entries.empty:
            return "There are no recent email entries."
        text_message = ""
        for _, row in last_entries.iterrows():
            text_message += f"{row['user_name']} sent a {row['subject']} to {row['to_email']} at {row['timestamp'].strftime('%d.%m.%Y %H:%M')}\n"
    
        return text_message        

def handle_summary(update, context):
    summary_type = update.callback_query.data

    sent_emails = read_sent_emails('sent_emails.json')
    summary_response = generate_summary(update, sent_emails, summary_type)

    if summary_type == 'summary_2':
        context.bot.send_message(chat_id=update.effective_chat.id, text=summary_response)
    elif summary_type == 'summary_3':
        context.bot.send_document(chat_id=update.effective_chat.id, document=summary_response)
    else:
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=summary_response)

def handle_back_to_menu(update, context):
    query = update.callback_query
    query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Plots", callback_data='summary_1')],
        [InlineKeyboardButton("Last 5", callback_data='summary_2')],
        [InlineKeyboardButton("Search", callback_data='search')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    query.edit_message_text('Please choose an option:', reply_markup=reply_markup)

def handle_back_to_search(update, context):
    query = update.callback_query
    query.answer()
    handle_search(update, context)

def main3():
    BOT_TOKEN = "6299749652:AAFbuB_LWiP2HdktVpyUH-NcFs8OAfd1kXo"
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('sent', sent))
    dp.add_handler(CallbackQueryHandler(handle_summary, pattern='^summary_'))
    dp.add_handler(CallbackQueryHandler(handle_search, pattern='^search$'))
    dp.add_handler(CallbackQueryHandler(handle_search_subject, pattern='^search_subject$'))
    dp.add_handler(CallbackQueryHandler(handle_search_email, pattern='^search_email$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_subject_search))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_email_search))
    dp.add_handler(CallbackQueryHandler(handle_back_to_menu, pattern='^back_to_menu$'))
    dp.add_handler(CallbackQueryHandler(handle_back_to_search, pattern='^back_to_search$'))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main3()
