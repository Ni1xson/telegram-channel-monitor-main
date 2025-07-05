# -*- coding: utf-8 -*-
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from database.db import Database
from monitor.client import TelegramMonitorClient
from database.models import Filter
from config.config import Config
from admin_bot.keyboards.keyboards import AdminKeyboards
from admin_bot.utils.states import FilterStates
from admin_bot.utils import send_menu_message
from aiogram.filters import Command
logger = logging.getLogger(__name__)

router = Router()


@router.message(F.text == "📝 Управление фильтрами")
async def filters_menu(message: Message, state: FSMContext):
    """Меню управления фильтрами"""
    await state.clear()

    if message.from_user.id not in Config.ALLOWED_USERS:
        return

    await send_menu_message(
        message,
        "📝 <b>Управление фильтрами</b>\n\nВыберите действие:",
        reply_markup=AdminKeyboards.filters_menu(),
    )


@router.callback_query(F.data == "filter_add")
async def start_add_filter(callback: CallbackQuery, state: FSMContext):
    """Начало добавления фильтра"""
    await state.set_state(FilterStates.waiting_name)

    await callback.message.edit_text(
        "📝 <b>Добавление фильтра</b>\n\n"
        "Введите название фильтра (например: 'Новости', 'Реклама', 'Скидки'):",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(FilterStates.waiting_name)
async def process_filter_name(message: Message, state: FSMContext):
    """Обработка названия фильтра"""
    if len(message.text) > 100:
        await message.answer("❌ Название слишком длинное. Максимум 100 символов.")
        return

    await state.update_data(name=message.text)
    await state.set_state(FilterStates.waiting_keywords)

    await message.answer(
        "🔤 <b>Ключевые слова</b>\n\n"
        "Введите ключевые слова через запятую:\n"
        "Примеры:\n"
        "• <code>скидка, акция, распродажа</code>\n"
        "• <code>новости, новость</code>\n"
        "• <code>Bitcoin, BTC, криптовалюта</code>\n\n"
        "💡 Можно использовать как отдельные слова, так и фразы.",
        reply_markup=AdminKeyboards.cancel(),
        parse_mode="HTML",
    )


@router.message(FilterStates.waiting_keywords)
async def process_filter_keywords(message: Message, state: FSMContext):
    """Обработка ключевых слов"""
    # Разбираем ключевые слова
    keywords = [kw.strip() for kw in message.text.split(",") if kw.strip()]

    if not keywords:
        await message.answer("❌ Введите хотя бы одно ключевое слово.")
        return

    if len(keywords) > 50:
        await message.answer("❌ Слишком много ключевых слов. Максимум 50.")
        return

    await state.update_data(keywords=keywords)

    # Показываем типы логики
    await message.answer(
        "🧠 <b>Тип логики фильтра</b>\n\n"
        "Выберите, как будет работать фильтр:\n\n"
        "• <b>Содержит</b> – сообщение содержит любое ключевое слово. "
        "Пример: <i>«Сегодня скидка!»</i> для <code>скидка, акция</code>.\n"
        "• <b>Точное совпадение</b> – ищет точные слова, без частей. "
        "Пример: <code>btc</code> найдёт 'btc', но не 'bitcoin'.\n"
        "• <b>Все слова</b> – в тексте должны быть все слова из списка. "
        "Пример: <code>купить, btc</code> → «купить btc сейчас».\n"
        "• <b>Фраза</b> – совпадает полная фраза с порядком слов. "
        "Пример: <code>купить btc</code>.\n"
        "• <b>Регулярное выражение</b> – поиск по regex. "
        "Пример: <code>\\d+% скидка</code>.\n"
        "• <b>Не содержит</b> – исключает сообщения с этими словами. "
        "Пример: слово <code>реклама</code> игнорируется.",
        reply_markup=AdminKeyboards.filter_logic_types(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("logic_"))
async def process_filter_logic(callback: CallbackQuery, state: FSMContext):
    """Обработка типа логики"""
    logic_type = callback.data.replace("logic_", "")
    await state.update_data(logic_type=logic_type)

    # Спрашиваем про регистр
    await callback.message.edit_text(
        "🔤 <b>Учитывать регистр?</b>\n\n"
        "Различать ли большие и маленькие буквы?\n\n"
        "• <b>Да</b> - 'Bitcoin' и 'bitcoin' будут разными словами\n"
        "• <b>Нет</b> - 'Bitcoin' и 'bitcoin' будут одинаковыми",
        reply_markup=AdminKeyboards.boolean_choice(
            "Да (учитывать)",
            "Нет (не учитывать)",
            "case_sensitive_true",
            "case_sensitive_false",
        ),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("case_sensitive_"))
async def process_case_sensitive(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Обработка чувствительности к регистру"""
    case_sensitive = callback.data == "case_sensitive_true"
    await state.update_data(case_sensitive=case_sensitive)

    # Спрашиваем про порядок слов (только для некоторых типов)
    data = await state.get_data()
    logic_type = data.get("logic_type", "contains")

    if logic_type in ["all_words", "phrase"]:
        await callback.message.edit_text(
            "📝 <b>Порядок слов важен?</b>\n\n"
            "Должны ли слова идти в определенном порядке?\n\n"
            "• <b>Да</b> - 'купить bitcoin' ≠ 'bitcoin купить'\n"
            "• <b>Нет</b> - порядок не важен",
            reply_markup=AdminKeyboards.boolean_choice(
                "Да (важен)", "Нет (не важен)", "word_order_true", "word_order_false"
            ),
            parse_mode="HTML",
        )
    else:
        # Для других типов порядок не важен
        await state.update_data(word_order_matters=False)
        await finalize_filter_creation(callback, state, db, monitor_client)

    await callback.answer()


@router.callback_query(F.data.startswith("word_order_"))
async def process_word_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Обработка важности порядка слов"""
    word_order_matters = callback.data == "word_order_true"
    await state.update_data(word_order_matters=word_order_matters)

    await finalize_filter_creation(callback, state, db, monitor_client)
    await callback.answer()


async def finalize_filter_creation(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Завершение создания фильтра"""
    data = await state.get_data()

    # Создаем объект фильтра
    user_id = callback.from_user.id
    filter_obj = Filter(
        user_id=user_id,
        name=data["name"],
        keywords=data["keywords"],
        logic_type=data["logic_type"],
        case_sensitive=data["case_sensitive"],
        word_order_matters=data["word_order_matters"],
        enabled=True,
    )

    # Сохраняем в базу данных
    filter_id = await db.add_filter(filter_obj)

    if filter_id:
        # Показываем сводку
        logic_names = {
            "contains": "Содержит",
            "exact": "Точное совпадение",
            "all_words": "Все слова",
            "phrase": "Фраза",
            "regex": "Регулярное выражение",
            "not_contains": "Не содержит",
        }

        summary_text = f"""
✅ <b>Фильтр создан!</b>

📝 <b>Название:</b> {data['name']}
🔤 <b>Ключевые слова:</b> {', '.join(data['keywords'])}
🧠 <b>Тип логики:</b> {logic_names.get(data['logic_type'], data['logic_type'])}
🔤 <b>Учитывать регистр:</b> {'Да' if data['case_sensitive'] else 'Нет'}
📝 <b>Порядок слов важен:</b> {'Да' if data['word_order_matters'] else 'Нет'}

🆔 <b>ID фильтра:</b> {filter_id}
        """

        await callback.message.edit_text(
            summary_text, reply_markup=AdminKeyboards.filters_menu(), parse_mode="HTML"
        )

        if monitor_client:
            await monitor_client.reload_filters(user_id)

    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка создания фильтра</b>\n\n"
            "Попробуйте еще раз или обратитесь к администратору.",
            reply_markup=AdminKeyboards.filters_menu(),
            parse_mode="HTML",
        )

    await state.clear()


@router.callback_query(F.data == "filter_list")
async def show_filters_list(callback: CallbackQuery, db: Database):
    """Показать список фильтров"""
    user_id = callback.from_user.id
    filters = await db.get_user_filters(user_id, enabled_only=False)

    if not filters:
        await callback.message.edit_text(
            "📝 <b>Список фильтров</b>\n\n"
            "У вас пока нет фильтров.\n"
            "Создайте первый фильтр, нажав 'Добавить фильтр'.",
            reply_markup=AdminKeyboards.filters_menu(),
            parse_mode="HTML",
        )
        await callback.answer()
        return

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

    # Формируем список
    text_lines = ["📝 <b>Ваши фильтры:</b>\n"]

    for i, filter_obj in enumerate(filters, 1):
        status = "✅" if filter_obj.enabled else "❌"
        keywords_preview = ", ".join(filter_obj.keywords[:3])
        if len(filter_obj.keywords) > 3:
            keywords_preview += f" и еще {len(filter_obj.keywords) - 3}"

        text_lines.append(
            f"{i}. {status} <b>{filter_obj.name}</b>\n"
            f"   🔤 {keywords_preview}\n"
            f"   🆔 ID: {filter_obj.id}\n"
        )

    # Создаем inline клавиатуру для взаимодействия с фильтрами
    keyboard = []
    for filter_obj in filters[:10]:  # Показываем только первые 10
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{'✅' if filter_obj.enabled else '❌'} {filter_obj.name[:20]}",
                    callback_data=f"filter_show_{filter_obj.id}",
                )
            ]
        )

    keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="back_main")])

    await callback.message.edit_text(
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_show_"))
async def show_filter_details(callback: CallbackQuery, db: Database):
    """Показать детали фильтра"""
    filter_id = int(callback.data.replace("filter_show_", ""))

    user_id = callback.from_user.id
    # Получаем фильтр из базы
    filters = await db.get_user_filters(user_id, enabled_only=False)
    filter_obj = next((f for f in filters if f.id == filter_id), None)

    if not filter_obj:
        await callback.answer("❌ Фильтр не найден", show_alert=True)
        return

    logic_names = {
        "contains": "Содержит",
        "exact": "Точное совпадение",
        "all_words": "Все слова",
        "phrase": "Фраза",
        "regex": "Регулярное выражение",
        "not_contains": "Не содержит",
    }

    created = (
        filter_obj.created_at.strftime("%d.%m.%Y %H:%M")
        if filter_obj.created_at
        else "Неизвестно"
    )
    details_text = f"""
📝 <b>Фильтр: {filter_obj.name}</b>

🆔 <b>ID:</b> {filter_obj.id}
📊 <b>Статус:</b> {'✅ Включен' if filter_obj.enabled else '❌ Отключен'}

🔤 <b>Ключевые слова:</b>
{', '.join(filter_obj.keywords)}

🧠 <b>Тип логики:</b> {logic_names.get(filter_obj.logic_type, filter_obj.logic_type)}
🔤 <b>Учитывать регистр:</b> {'Да' if filter_obj.case_sensitive else 'Нет'}
📝 <b>Порядок слов важен:</b> {'Да' if filter_obj.word_order_matters else 'Нет'}

📅 <b>Создан:</b> {created}
    """

    await callback.message.edit_text(
        details_text,
        reply_markup=AdminKeyboards.filter_actions(filter_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("filter_toggle_"))
async def toggle_filter(
    callback: CallbackQuery,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Включить/отключить фильтр"""
    filter_id = int(callback.data.replace("filter_toggle_", ""))

    # Получаем текущий статус
    user_id = callback.from_user.id
    filters = await db.get_user_filters(user_id, enabled_only=False)
    filter_obj = next((f for f in filters if f.id == filter_id), None)

    if not filter_obj:
        await callback.answer("❌ Фильтр не найден", show_alert=True)
        return

    # Переключаем статус
    new_status = not filter_obj.enabled
    success = await db.update_filter(filter_id, enabled=new_status)

    if success:
        status_text = "включен" if new_status else "отключен"
        await callback.answer(f"✅ Фильтр {status_text}", show_alert=True)

        # Обновляем отображение
        await show_filter_details(callback, db)

        if monitor_client:
            await monitor_client.reload_filters(user_id)
    else:
        await callback.answer("❌ Ошибка обновления фильтра", show_alert=True)


@router.callback_query(F.data.startswith("filter_delete_"))
async def confirm_delete_filter(callback: CallbackQuery):
    """Подтверждение удаления фильтра"""
    filter_id = int(callback.data.replace("filter_delete_", ""))

    await callback.message.edit_text(
        "❓ <b>Удаление фильтра</b>\n\n"
        "Вы уверены, что хотите удалить фильтр?\n"
        "Это действие нельзя отменить.",
        reply_markup=AdminKeyboards.confirmation("delete_filter", filter_id),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_filter_"))
async def delete_filter(
    callback: CallbackQuery,
    db: Database,
    monitor_client: TelegramMonitorClient,
):
    """Удаление фильтра"""
    filter_id = int(callback.data.replace("confirm_delete_filter_", ""))

    user_id = callback.from_user.id
    success = await db.delete_filter(filter_id, user_id)

    if success:
        await callback.message.edit_text(
            "✅ <b>Фильтр удален</b>\n\n" "Фильтр успешно удален из системы.",
            reply_markup=AdminKeyboards.filters_menu(),
            parse_mode="HTML",
        )

        if monitor_client:
            await monitor_client.reload_filters(user_id)
    else:
        await callback.message.edit_text(
            "❌ <b>Ошибка удаления</b>\n\n"
            "Не удалось удалить фильтр. Попробуйте еще раз.",
            reply_markup=AdminKeyboards.filters_menu(),
            parse_mode="HTML",
        )

    await callback.answer()


@router.callback_query(F.data == "filter_reload")
async def reload_filters(
    callback: CallbackQuery, monitor_client: TelegramMonitorClient
):
    """Перезагрузка фильтров"""
    if monitor_client:
        await monitor_client.reload_filters(callback.from_user.id)

    await callback.answer("🔄 Фильтры перезагружены", show_alert=True)


@router.callback_query(F.data == "filter_cancel")
async def cancel_filter_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия с фильтром"""
    await state.clear()
    await callback.message.edit_text(
        "📝 <b>Управление фильтрами</b>\n\nВыберите действие:",
        reply_markup=AdminKeyboards.filters_menu(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    if message.from_user.id not in Config.ALLOWED_USERS:
        await message.answer("❌ У вас нет доступа к этому боту.")
        return

    help_text = """
🆘 <b>Справка по использованию</b>

<b>📝 Фильтры и 📢 Каналы:</b>
• Общий список для всех админов!
• Любой админ может добавить, удалить, очистить или обновить список фильтров и каналов.
• <b>Кнопки:</b>
  ➕ Добавить — добавить новый фильтр/канал
  📋 Список — показать все фильтры/каналы
  🔄 Обновить список — вручную обновить отображение
  🗑 Очистить все — удалить все фильтры/каналы
• <b>Кнопки каналов:</b> теперь показывают @username, если есть, иначе название, иначе ID.

<b>⚙️ Мониторинг:</b>
• Включается только если есть хотя бы один фильтр и канал.
• Все действия с фильтрами и каналами влияют на работу мониторинга для всех админов.

<b>👤 User-клиент:</b>
• Показывает, под каким Telegram-аккаунтом подключён бот.
• Имя отображается вместо ID, если оно известно.

<b>📊 Статус:</b>
• Статус системы честно отражает состояние всех компонентов.
• Если что-то не работает — смотри подсказки в статусе.

<b>🔧 Команды:</b>
/start — главное меню
/help — эта справка
/status — статус и статистика

<b>❓ FAQ:</b>
• <b>Почему не вижу каналы/фильтры друга?</b> — Теперь всё общее, любые изменения видны всем.
• <b>Почему мониторинг не включается?</b> — Должен быть хотя бы один активный фильтр и канал.
• <b>Что делать, если что-то не работает?</b> — Перезапустите бота или обратитесь к администратору.
    """

    await send_menu_message(message, help_text, reply_markup=AdminKeyboards.back_main())
