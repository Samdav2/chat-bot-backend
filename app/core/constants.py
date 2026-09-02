"""
Central FAQ Commands and Responses for Telegram Bot.
"""

FAQ_COMMANDS = {
    "faq_deposit": {
        "title": "💳 How to Deposit?",
        "response": (
            "Click the “Top up” button and select to pay with bank transfer or cryptocurrency, "
            "after that enter the amount you want to deposit and click the “Proceed to payment” button "
            "an account details we be generated for you to make payment to"
        )
    },
    "faq_cancel": {
        "title": "❌ How to cancel order?",
        "response": (
            "To cancel an order, watch this 1-minute video tutorial on how to cancel your order\n"
            "https://youtube.com/shorts/2ix4ZsYsl2A?si=YvcKaAqj_kD_jJrc"
        )
    },
    "faq_no_code": {
        "title": "📩 Why am not receiving code?",
        "response": (
            "Make sure you on VPN and set location to the country number you want to buy. "
            "You also have options to buy from different ID if a particular ID is not sending code or out of stock"
        )
    },
    "faq_vpn": {
        "title": "🌐 Is it compulsory to use VPN or Proxy?",
        "response": (
            "Yes, we recommend using a VPN or proxy when opening a foreign account to help avoid code delays and immediate suspension."
        )
    },
    "faq_wa_biz": {
        "title": "📱 Can I use WhatsApp Business to open account?",
        "response": (
            "we recommend you use the normal Whatsapp not Whatsapp business if you want to open a whatsapp account to avoid immediate suspesion"
        )
    },
    "faq_bank_refund": {
        "title": "🏦 Can i get refund to my bank account?",
        "response": (
            "As outlined in our Terms of Service, refund to bank account is non-refundable which you agree to when signing up, "
            "For more details, please refer to our Terms of Service here —> https://falconotp.com/tos"
        )
    },
    "faq_payment_rejected": {
        "title": "⚠️ Why is my payment been rejected?",
        "response": (
            "Make sure you transfer the exact amount you see on the payment page, Do not send more or less than the specified amount."
        )
    },
    "faq_code_refund": {
        "title": "🔄 Can I get a refund if the number I bought doesn’t receive code?",
        "response": (
            "Yes! Just Cancel the number, the money we be automatically refund to your balance"
        )
    },
    "faq_refunds_available": {
        "title": "💰 Are refunds available?",
        "response": (
            "Absolutely! We have a simple rule: If you buy a number but the SMS never arrives, the system automatically refunds the money to your balance. You only pay for actual results."
        )
    },
}


def get_faq_inline_keyboard() -> dict:
    """Build Telegram inline keyboard for FAQ commands + 'Other question' support escalation button."""
    keyboard = []
    for key, item in FAQ_COMMANDS.items():
        keyboard.append([{"text": item["title"], "callback_data": key}])
    
    # 'Other question' button triggers customer support escalation
    keyboard.append([{"text": "❓ Other question", "callback_data": "request_support"}])
    return {"inline_keyboard": keyboard}
