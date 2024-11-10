import os
import json
import random
import telebot
from telebot import types

TELEGRAM_TOKEN = "7009538379:AAEsfwZBY29puj9NSwi99aVvpDXn2k76vr4"

bot = telebot.TeleBot(TELEGRAM_TOKEN)

if not os.path.exists("orders.json"):
    with open("orders.json", "w") as file:
        json.dump([], file)

game_keys = {
    1: ["KEY-A1", "KEY-A2", "KEY-A3", "KEY-A4", "KEY-A5"],
    2: ["KEY-B1", "KEY-B2", "KEY-B3", "KEY-B4", "KEY-B5"],
    3: ["KEY-C1", "KEY-C2", "KEY-C3", "KEY-C4", "KEY-C5"]
}


def initiate_payment(user_id, amount):
    payment_id = f"PAY-{random.randint(1000, 9999)}"
    payment_status = random.choice(["success", "failed"])
    return payment_id, payment_status


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    catalog_btn = types.KeyboardButton("Каталог")
    cart_btn = types.KeyboardButton("Кошик")
    profile_btn = types.KeyboardButton("Профіль")
    support_btn = types.KeyboardButton("Підтримка")
    markup.add(catalog_btn, cart_btn, profile_btn, support_btn)
    bot.send_message(message.chat.id, "Ласкаво просимо до магазину ключів для ігор!", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text == "Каталог")
def show_catalog(message, game_id=1):
    with open("games.json", "r") as file:
        games = json.load(file)

    game = next((g for g in games if g['id'] == game_id), None)
    if game:
        markup = types.InlineKeyboardMarkup()
        add_to_cart_btn = types.InlineKeyboardButton("Додати в кошик", callback_data=f"add_{game['id']}")
        next_game_btn = types.InlineKeyboardButton("Наступна", callback_data=f"next_{game_id + 1}")
        back_btn = types.InlineKeyboardButton("Назад", callback_data="back_to_main")
        markup.add(add_to_cart_btn, next_game_btn, back_btn)

        game_message = f"{game['name']}\n{game['description']}\nКатегорія: {game['category']}\nЦіна: {game['price']} грн"
        bot.send_message(message.chat.id, game_message, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data.startswith("next_"))
def next_game(call):
    next_game_id = int(call.data.split("_")[1])
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_catalog(call.message, game_id=next_game_id)
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: message.text == "Кошик")
def view_cart(message):
    with open("orders.json", "r") as file:
        orders = json.load(file)

    user_orders = [order for order in orders if
                   order['user_id'] == message.from_user.id and order['status'] == "in_cart"]
    if user_orders:
        cart_message = "Ваш кошик:\n"
        total_price = 0
        for order in user_orders:
            with open("games.json", "r") as games_file:
                games = json.load(games_file)
            game = next((g for g in games if g['id'] == order['game_id']), None)
            cart_message += f"{game['name']} - {game['price']} грн\n"
            total_price += game['price']
        cart_message += f"Загальна сума: {total_price} грн"
        checkout_button = types.InlineKeyboardButton("Оформити замовлення", callback_data="checkout")
        back_button = types.InlineKeyboardButton("Назад", callback_data="back_to_main")
        markup = types.InlineKeyboardMarkup().add(checkout_button, back_button)
        bot.send_message(message.chat.id, cart_message, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "Ваш кошик порожній.")


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_"))
def add_to_cart(call):
    game_id = int(call.data.split("_")[1])
    new_order = {"user_id": call.from_user.id, "game_id": game_id, "status": "in_cart", "key": None}

    with open("orders.json", "r") as file:
        orders = json.load(file)
    orders.append(new_order)

    with open("orders.json", "w") as file:
        json.dump(orders, file)

    bot.answer_callback_query(call.id, "Гру додано до кошика!")


@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def checkout(call):
    with open("orders.json", "r") as file:
        orders = json.load(file)

    user_orders = [order for order in orders if order['user_id'] == call.from_user.id and order['status'] == "in_cart"]
    if not user_orders:
        bot.send_message(call.message.chat.id, "Ваш кошик порожній.")
        return

    total_price = sum(
        next(g['price'] for g in json.load(open('games.json')) if g['id'] == order['game_id']) for order in user_orders)

    # Ініціалізуємо фіктивну оплату
    payment_id, payment_status = initiate_payment(call.from_user.id, total_price)

    if payment_status == "success":
        order_messages = []
        for order in user_orders:
            available_keys = game_keys.get(order['game_id'], [])
            if available_keys:
                selected_key = random.choice(available_keys)
                order['key'] = selected_key
                order['status'] = "purchased"
                available_keys.remove(selected_key)
                order_messages.append(
                    f"Ключ для {next(g['name'] for g in json.load(open('games.json')) if g['id'] == order['game_id'])}: {selected_key}")

        with open("orders.json", "w") as file:
            json.dump(orders, file)

        bot.send_message(call.message.chat.id, "Оплата успішна! Дякуємо за покупку.\n\n" + "\n".join(order_messages))
    else:
        bot.send_message(call.message.chat.id, "Оплата не вдалася. Будь ласка, спробуйте ще раз.")

    bot.answer_callback_query(call.id)


@bot.callback_query_handler(func=lambda call: call.data == "back_to_main")
def back_to_main(call):
    send_welcome(call.message)
    bot.answer_callback_query(call.id)


@bot.message_handler(func=lambda message: message.text == "Профіль")
def view_profile(message):
    with open("orders.json", "r") as file:
        orders = json.load(file)

    purchased_orders = [order for order in orders if
                        order['user_id'] == message.from_user.id and order['status'] == "purchased"]
    if purchased_orders:
        profile_message = f"Ім'я користувача: {message.from_user.first_name}\nВаші покупки:\n"
        for order in purchased_orders:
            game = next(g for g in json.load(open('games.json')) if g['id'] == order['game_id'])
            profile_message += f"{game['name']} - {game['price']} грн\n"
        bot.send_message(message.chat.id, profile_message)
    else:
        bot.send_message(message.chat.id, "У вас немає придбаних ігор.")


@bot.message_handler(func=lambda message: message.text == "Підтримка")
def support(message):
    bot.send_message(message.chat.id, "Якщо виникли питання, звертайтесь до @flud1r")


bot.polling()
