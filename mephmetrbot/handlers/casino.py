import random
import asyncio
from aiogram import Router
from aiogram.types import Message
from datetime import datetime, timedelta
from mephmetrbot.handlers.models import Users
from mephmetrbot.config import bot, LOGS_CHAT_ID
from aiogram.filters.command import Command, CommandObject
import pytz

router = Router()

async def get_user(user_id):
    user, _ = await Users.get_or_create(id=user_id)
    return user

@router.message(Command('casino'))
async def casino_command(message: Message, command: CommandObject):
    if message.chat.id != message.from_user.id:
        await message.reply('📛️️ Эта команда работает только в ЛС с ботом!')
        return

    args = command.args
    user_id = message.from_user.id
    user = await get_user(user_id)
    bot_user = await get_user(1)
    bot_balance = bot_user.drug_count

    now = datetime.now(pytz.utc)
    today = now.date()



    if not user.vip:
        if user.last_casino:
            cooldown = timedelta(seconds=15)

            if user.last_casino.tzinfo is None:
                last_casino = pytz.utc.localize(user.last_casino)
            else:
                last_casino = user.last_casino

            if now - last_casino < cooldown:
                remaining_time = cooldown - (now - last_casino)
                await message.reply(f"🕑 <b>Подождите еще</b> <code>{remaining_time.seconds}</code> <b>секунд перед повторным использованием команды.</b>", parse_mode='HTML')
                return

        user.last_casino = now
        await user.save()

    else:
        if user.last_casino:
            cooldown = timedelta(seconds=5)

            if user.last_casino.tzinfo is None:
                last_casino = pytz.utc.localize(user.last_casino)
            else:
                last_casino = user.last_casino

            if now - last_casino < cooldown:
                remaining_time = cooldown - (now - last_casino)
                await message.reply(
                    f"🕑 <b>Подождите еще</b> <code>{remaining_time.seconds}</code> <b>секунд перед повторным использованием команды.</b>",
                    parse_mode='HTML')
                return

        user.last_casino = now
        await user.save()



    if not args:
        await message.reply("🛑 Укажи ставку и коэффициент автостопа ракетки! Пример:\n<code>/casino 10 2</code>",
                            parse_mode='HTML')
        return

    parts = args.split()

    if len(parts) < 2:
        await message.reply("🛑 Укажи ставку и коэффициент автостопа ракетки! Пример:\n<b>/casino 10 2</b>",
                            parse_mode='HTML')
        return

    try:
        bet = int(parts[0])
        target_multiplier = float(parts[1])
    except ValueError:
        await message.reply("🛑 <b>Ставка должна быть целым числом, а коэффициент числом!</b>", parse_mode='HTML')
        return

    if target_multiplier < 1.1:
        await message.reply("🛑 Минимальный коэффициент автостопа: <code>1.1x</code>", parse_mode='HTML')
        return

    if bet < 10:
        await message.reply("🛑 Ставка должна быть больше <code>10</code> гр.", parse_mode='HTML')
        return

    if not user:
        await message.reply('❌ Профиль не найден')
        return

    if user.last_game_day != today:
        user.game_count = 0
        user.last_game_day = today
        await user.save()

    if user.game_count >= 20 and user.vip == 0 and user.is_admin == 0 and user.is_tester == 0:
        await message.reply(
            "🛑 <b>Ты достиг дневного лимита игр в казино. Приобрети</b> <code>VIP-статус</code> <b>для снятия ограничений.</b>",
            parse_mode='HTML')
        return

    drug_count = user.drug_count

    if bet > drug_count:
        await message.reply("🛑 <b>Твоя ставка больше твоего баланса!</b>", parse_mode='HTML')
        return

    if bot_balance <= bet:
        await message.reply("🛑 <b>У бота недостаточно средств для проведения игры. Попробуй позже.</b>",
                            parse_mode='HTML')
        return

    user.drug_count -= bet
    user.game_count += 1
    if user.game_count > 20:
        user.game_count = 20
    await user.save()

    dice_message = await message.reply("<b>🚀 Начинаем игру... Ракетка взлетает!</b>", parse_mode='HTML')
    await asyncio.sleep(2)

    if not user.vip:
        random_number = random.uniform(0, 1)
        if random_number < 0.30:
            random_multiplier = 0 # 30%
        elif random_number < 0.60:
            random_multiplier = round(random.uniform(1, 1.9), 2)  # 40%
        elif random_number < 0.90:
            random_multiplier = round(random.uniform(2, 3), 2)  # 30%
        else:
            random_multiplier = round(random.uniform(3, 6), 2)  # 5%
    else:
        random_number = random.uniform(0, 1)
        if random_number < 0.15: # 15%
            random_multiplier = 0
        elif random_number < 0.75:
            random_multiplier = round(random.uniform(1, 1.9), 2)  # 70%
        elif random_number < 1.25:
            random_multiplier = round(random.uniform(2, 3), 2)  # 50%
        else:
            random_multiplier = round(random.uniform(3, 6), 2)  # 10%

    current_multiplier = 0
    result_message = ''

    if current_multiplier == random_multiplier:
        await dice_message.edit_text(f"🚀 <b>Коэффициент</b>: <code>{current_multiplier}x</code>", parse_mode='HTML')
        new_balance = round(user.drug_count, 1)
        if not (user.is_admin or user.is_tester):
            new_bot_balance = round(bot_balance + bet, 1)
            bot_user.drug_count = new_bot_balance
            await bot_user.save()

        if user.vip != 1:
            result_message += f'❌ Твоя ставка не сыграла. Повезёт в следующий раз! Твой новый баланс: <code>{new_balance}</code> гр.\nОставшееся количество спинов: <code>{20 - int(user.game_count)}</code>'
        else:
            result_message += f'❌ Твоя ставка не сыграла. Повезёт в следующий раз! Твой новый баланс: <code>{new_balance}</code> гр.'

        await bot.send_message(
            LOGS_CHAT_ID,
            f"<b>🎰 #CASINO - #LOSE</b>\n\n"
            f"<b>👤 User:</b> <code>{message.from_user.first_name}</code>\n"
            f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
            f"<b>💸 Bet:</b> <code>{bet}</code>\n"
            f"<b>🎯 Target Multiplier:</b> <code>{target_multiplier}</code>\n"
            f"<b>📉 Actual Multiplier:</b> <code>{random_multiplier}</code>\n"
            f"<b>💊 Drug Count:</b> <code>{new_balance}</code>\n\n"
            f"<a href='tg://user?id={user_id}'>🔗 Mention</a>",
            parse_mode='HTML'
        )

        user.last_casino = now
        await user.save()
        await dice_message.edit_text(result_message, parse_mode='HTML')
        return

    while current_multiplier < random_multiplier:
        current_multiplier = round(current_multiplier + 0.2, 2)
        if current_multiplier > random_multiplier:
            current_multiplier = random_multiplier
        await dice_message.edit_text(f"🚀 <b>Коэффициент</b>: <code>{current_multiplier}x</code>", parse_mode='HTML')
        await asyncio.sleep(0.5)

    result_message = f"🚀 Итоговый коэффициент: <code>{random_multiplier}x</code>. "

    if random_multiplier >= target_multiplier:
        win_amount = round(bet * target_multiplier, 1)
        if win_amount > bot_balance:
            await message.reply("🛑 <b>Бот не может выплатить выигрыш. Попробуй позже.</b>", parse_mode='HTML')
        else:
            new_balance = round(user.drug_count + win_amount, 1)
            if not (user.is_admin or user.is_tester):
                new_bot_balance = round(bot_balance - win_amount, 1)
                bot_user.drug_count = new_bot_balance
                await bot_user.save()

            if user.vip != 1:
                result_message += f'🎉 Поздравляем, вы выиграли <code>{win_amount}</code> гр. Ваш новый баланс: <code>{new_balance}</code> гр.\nОставшееся количество спинов: <code>{20 - int(user.game_count)}</code>'
            else:
                result_message += f'🎉 Поздравляем, вы выиграли <code>{win_amount}</code> гр. Ваш новый баланс: <code>{new_balance}</code> гр.'

            user.drug_count = new_balance
            await bot.send_message(
                LOGS_CHAT_ID,
                f"<b>🎰 #CASINO - #WIN</b>\n\n"
                f"<b>👤 User:</b> <code>{message.from_user.first_name}</code>\n"
                f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
                f"<b>💸 Bet:</b> <code>{bet}</code>\n"
                f"<b>🎯 Target Multiplier:</b> <code>{target_multiplier}</code>\n"
                f"<b>📉 Actual Multiplier:</b> <code>{random_multiplier}</code>\n"
                f"<b>💊 Drug Count:</b> <code>{new_balance}</code>\n\n"
                f"<a href='tg://user?id={user_id}'>🔗 Mention</a>",
                parse_mode='HTML'
            )

    else:
        new_balance = round(user.drug_count, 1)
        if not (user.is_admin or user.is_tester):
            new_bot_balance = round(bot_balance + bet, 1)
            bot_user.drug_count = new_bot_balance
            await bot_user.save()

        if user.vip != 1:
            result_message += f'❌ Твоя ставка не сыграла. Повезёт в следующий раз! Твой новый баланс: <code>{new_balance}</code> гр.\nОставшееся количество спинов: <code>{20 - int(user.game_count)}</code>'
        else:
            result_message += f'❌ Твоя ставка не сыграла. Повезёт в следующий раз! Твой новый баланс: <code>{new_balance}</code> гр.'

        await bot.send_message(
            LOGS_CHAT_ID,
            f"<b>🎰 #CASINO - #LOSE</b>\n\n"
            f"<b>👤 User:</b> <code>{message.from_user.first_name}</code>\n"
            f"<b>🆔 ID:</b> <code>{user_id}</code>\n"
            f"<b>💸 Bet:</b> <code>{bet}</code>\n"
            f"<b>🎯 Target Multiplier:</b> <code>{target_multiplier}</code>\n"
            f"<b>📉 Actual Multiplier:</b> <code>{random_multiplier}</code>\n"
            f"<b>💊 Drug Count:</b> <code>{new_balance}</code>\n\n"
            f"<a href='tg://user?id={user_id}'>🔗 Mention</a>",
            parse_mode='HTML'
        )

    user.last_casino = now
    await user.save()
    await dice_message.edit_text(result_message, parse_mode='HTML')


