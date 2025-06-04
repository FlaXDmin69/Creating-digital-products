import os
import asyncio
import pdfkit
import qrcode
import base64
from io import BytesIO
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.filters import Command
from datetime import datetime

# === Настройки ===
API_TOKEN = '6699273034:AAHfxYiiVNQ4WVDCmzLhJXZp4dRa-P4XDa4'  # Замените на ваш токен
WKHTMLTOPDF_PATH = r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe'

# === Инициализация ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# === Клавиатура ===
doc_type_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Кассовый чек")],
        [KeyboardButton(text="Онлайн-оплата")]
    ], resize_keyboard=True
)

# === Состояния ===
user_states = {}

# === Генерация QR-кода в base64 ===
def generate_qr_code_base64(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(str(data))
    img = qr.make_image(fill_color="black", back_color="white")
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffered.getvalue()).decode("utf-8")

# === Генерация логотипа в base64 ===
def get_logo_base64():
    logo_path = "logo.png"
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as image_file:
        return "data:image/png;base64," + base64.b64encode(image_file.read()).decode("utf-8")

# === Команды ===
@router.message(Command("start"))
async def send_welcome(message: Message):
    await message.answer("Выберите тип документа:", reply_markup=doc_type_keyboard)

# === Обработка выбора типа документа ===
@router.message(F.text.in_(["Кассовый чек", "Онлайн-оплата"]))
async def choose_doc_type(message: Message):
    user_id = message.from_user.id
    doc_type = message.text

    user_states[user_id] = {
        'step': 0,
        'type': doc_type,
        'data': {}
    }

    if doc_type == "Кассовый чек":
        await message.answer("Введите номер чека:")
    elif doc_type == "Онлайн-оплата":
        await message.answer("Введите ФИО получателя:")

# === Обработка данных ===
@router.message()
async def process_input(message: Message):
    user_id = message.from_user.id

    if user_id not in user_states:
        await message.answer("Начните с /start")
        return

    state = user_states[user_id]
    doc_type = state['type']
    data = state['data']

    if doc_type == "Кассовый чек":
        await handle_receipt(message, state)
    elif doc_type == "Онлайн-оплата":
        await handle_online_payment(message, state)

# === Обработка кассового чека ===
async def handle_receipt(message: Message, state):
    step = state['step']
    data = state['data']
    user_id = message.from_user.id

    if step == 0:
        receipt_number = message.text.strip()
        data['receipt_number'] = receipt_number
        await message.answer("Введите название организации:")
        state['step'] = 1

    elif step == 1:
        data['company_name'] = message.text
        await message.answer("Введите ИНН:")
        state['step'] = 2

    elif step == 2:
        data['inn'] = message.text
        await message.answer("Введите адрес:")
        state['step'] = 3

    elif step == 3:
        data['address'] = message.text
        await message.answer("Введите дату и время (или отправьте 'сейчас'):")
        state['step'] = 4

    elif step == 4:
        if message.text.lower() == "сейчас":
            data['date_time'] = datetime.now().strftime("%d.%m.%Y %H:%M")
        else:
            data['date_time'] = message.text
        await message.answer("Введите ФИО кассира:")
        state['step'] = 5

    elif step == 5:
        data['cashier'] = message.text
        await message.answer("Введите товары в формате:\nМолоко 50.00 1\nЧай Липтон 150.00 2")
        state['step'] = 6

    elif step == 6:
        items = []
        try:
            for line in message.text.split('\n'):
                parts = line.strip().split()
                if len(parts) < 3:
                    raise ValueError(f"Неверный формат строки: {line}")
                price_str = parts[-2]
                qty_str = parts[-1]
                try:
                    price = float(price_str.replace(',', '.'))
                    quantity = int(qty_str)
                except (ValueError, IndexError):
                    raise ValueError(f"Неверное количество или цена: {line}")
                name = ' '.join(parts[:-2])
                items.append((name, price, quantity))
            data['items'] = items

            # Генерация HTML
            html_content = generate_receipt_html(data)
            # Передача номера чека в generate_pdf
            await generate_pdf(user_id, html_content, data['receipt_number'])
            del user_states[user_id]

        except Exception as e:
            await message.answer(f"Ошибка в формате ввода: {str(e)}\n"
                                 "Попробуйте ещё раз в формате:\n"
                                 "Молоко 50.00 1\n"
                                 "Чай Липтон 150.00 2")

# === Генерация HTML с base64 изображениями ===
def generate_receipt_html(data):
    # Генерация QR-кода как base64
    qr_data = f"receipt_id={data['receipt_number']}, company={data['company_name']}"
    qr_base64 = generate_qr_code_base64(qr_data)

    # Логотип как base64
    logo_base64 = get_logo_base64()

    html = f"""
    <div style="text-align: center;">
        {f'<img src="{logo_base64}" width="100" style="margin-bottom: 10px;">' if logo_base64 else ''}
    </div>
    <h1 style="text-align: center;">Кассовый чек №{data['receipt_number']}</h1>
    <p style="text-align: center;">ООО {data['company_name']}</p>
    <p style="text-align: center;">ИНН {data['inn']}</p>
    <p style="text-align: center;">Адрес: {data['address']}</p>
    <p style="text-align: center;">Дата; Время: {data['date_time']}</p>
    <p style="text-align: center;">Кассир: {data['cashier']}</p>
    <hr>
    """
    total = 0
    for item in data['items']:
        name, price, qty = item
        subtotal = price * qty
        html += f"<p>{name} {price:.2f} × {qty} = {subtotal:.2f}</p>"
        total += subtotal
    html += f"<hr><p><b>Итого: {total:.2f}</b></p>"
    html += f'<div style="text-align: center;"><img src="{qr_base64}" width="100" style="margin-top: 20px;"></div>'
    return html

# === Генерация HTML для онлайн-оплаты с base64 ===
def generate_payment_html(data):
    qr_data = f"recipient={data['recipient']}, amount={data['amount']}"
    qr_base64 = generate_qr_code_base64(qr_data)

    logo_base64 = get_logo_base64()

    html = f"""
    <div style="text-align: center;">
        {f'<img src="{logo_base64}" width="100" style="margin-bottom: 10px;">' if logo_base64 else ''}
    </div>
    <h1 style="text-align: center;">Онлайн-оплата</h1>
    <p style="text-align: center;">ФИО получателя: {data['recipient']}</p>
    <p style="text-align: center;">Сумма: {data['amount']}</p>
    <p style="text-align: center;">Сообщение: {data['message_text']}</p>
    <div style="text-align: center;"><img src="{qr_base64}" width="100" style="margin-top: 20px;"></div>
    """
    return html

# === Асинхронная генерация и отправка PDF с папкой по номеру чека ===
async def generate_pdf(user_id, html_content, receipt_number=None):
    try:
        if not os.path.exists(WKHTMLTOPDF_PATH):
            await bot.send_message(user_id, "Ошибка: wkhtmltopdf не найден. Проверьте установку программы.")
            return

        # Если указан номер чека, используем его как имя папки
        if receipt_number:
            # Очистка номера чека от недопустимых символов для названия папки
            safe_receipt = "".join(c for c in receipt_number if c.isalnum() or c in (" ", "_", "-")).strip()
            temp_dir = f"check_{safe_receipt}"
        else:
            temp_dir = f"temp_{user_id}"

        os.makedirs(temp_dir, exist_ok=True)

        html_path = os.path.join(temp_dir, "receipt.html")
        pdf_path = os.path.join(temp_dir, "receipt.pdf")

        with open(html_path, "w", encoding='utf-8') as f:
            f.write(html_content)

        config = pdfkit.configuration(wkhtmltopdf=WKHTMLTOPDF_PATH)
        options = {
            'encoding': 'UTF-8',
            'page-size': 'A4',
            'margin-top': '10mm',
            'margin-right': '10mm',
            'margin-bottom': '10mm',
            'margin-left': '10mm',
            'log-level': 'warn'  # Уменьшаем вывод логов
        }

        pdfkit.from_file(html_path, pdf_path, configuration=config, options=options)

        if os.path.exists(pdf_path):
            await bot.send_document(user_id, InputFile(pdf_path))

        # Очистка
        os.remove(html_path)
        os.remove(pdf_path)
        os.rmdir(temp_dir)

    except Exception as e:
        await bot.send_message(user_id, f"Ошибка при создании PDF: {str(e)}")
        print(f"PDF Error: {str(e)}")

        # Попытка удалить папку, если ошибка
        try:
            if os.path.exists(temp_dir):
                os.rmdir(temp_dir)
        except Exception as e:
            print(f"Не удалось удалить папку: {str(e)}")

# === Обработка онлайн-оплаты ===
async def handle_online_payment(message: Message, state):
    step = state['step']
    data = state['data']
    user_id = message.from_user.id

    if step == 0:
        data['recipient'] = message.text
        await message.answer("Введите сумму:")
        state['step'] = 1

    elif step == 1:
        data['amount'] = message.text
        await message.answer("Введите сообщение для получателя:")
        state['step'] = 2

    elif step == 2:
        data['message_text'] = message.text
        html_content = generate_payment_html(data)
        await generate_pdf(user_id, html_content)  # Без номера чека
        del user_states[user_id]

# === Регистрация роутера ===
dp.include_router(router)

# === Запуск бота ===
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())