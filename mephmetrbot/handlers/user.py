from aiogram import Router, F
import random
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardButton, CallbackQuery
from aiogram.filters.command import Command, CommandObject
from aiogram.utils.keyboard import InlineKeyboardBuilder
from mephmetrbot.handlers.models import Users, Clans
from mephmetrbot.config import bot, LOGS_CHAT_ID
from datetime import datetime, timedelta
import asyncio
from aiogram.exceptions import TelegramBadRequest

router = Router()

async def update_user_balance_and_drug_count(user_id: int, new_balance: int, new_drug_count: int):
    user = await Users.get(id=user_id)
    user.balance = new_balance
    user.drug_count = new_drug_count
    await user.save()

async def get_user(user_id):
    user, _ = await Users.get_or_create(id=user_id)
    return user

async def update_user_drug_count(user_id: int, new_count: int):
    user = await Users.get(id=user_id)
    user.drug_count = new_count
    await user.save()

@router.message(Command('profile'))
async def profile_command(message: Message):
    user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    user = await get_user(user_id)

    if not user:
        await message.reply('❌ Профиль не найден')
        return

    if user == '7266772626':
        bot_user = await get_user(1)
        await message.reply(f"🤖 <b>Это Бот</b>\n🌿 <b>Баланс бота:</b> <i>{bot_user.drug_count}</i> грамм.",parse_mode='HTML')

    clan_name = None
    if user.clan_member:
        clan = await Clans.get_or_none(id=user.clan_member)
        clan_name = clan.clan_name if clan else None

    full_name = message.from_user.full_name if user_id == message.from_user.id else message.reply_to_message.from_user.full_name
    
    if user.balance is None:
        user.balance = 0

    user_info = (
        f"👤 <b>Имя:</b> <i>{full_name}</i>\n"
        f"🆔 <b>ID пользователя:</b> <code>{user_id}</code>\n"
    )

    balances = (
        f"🌿 <b>Снюхано:</b> <i>{user.drug_count}</i> грамм.\n"
        f"💸 <b>Баланс крипты:</b> <i>{user.balance}</i> <b>$MEF</b>"
    )

    if clan_name:
        user_info = f"{user_info}👥 <b>Клан:</b> <b>{clan_name}</b>\n\n{balances}"
    else:
        user_info = f'{user_info}{balances}'

    if user.is_banned:
        user_info = f"❌ <b>ЛИКВИДИРОВАН</b>\nПричина: <code>{user.ban_reason}</code>\n\n{user_info}"
    elif user.is_admin:
        user_info = f"🛡️ <b>Администратор</b>\n\n{user_info}"
    elif user.is_tester:
        user_info = f"💻 <b>Тестер</b>\n\n{user_info}"
    elif user.vip:
        user_info = f"👑 <b>VIP-статус</b>\n\n{user_info}"
    

    await message.reply(user_info, parse_mode='HTML')


@router.message(Command('botprofile'))
async def botprofile(message: Message):
    bot_user = await get_user(1)
    await message.reply(f"🤖 <b>Это Бот</b>\n🌿 <b>Баланс бота:</b> <i>{bot_user.drug_count}</i> грамм.", parse_mode='HTML')

@router.message(Command('shop'))
async def shop(message: Message):
    user_id = message.from_user.id

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🌿 25 грамм - 💸 2000 $MEF", callback_data="buy_25"),
        InlineKeyboardButton(text="🌿 50 грамм - 💸 3500 $MEF", callback_data="buy_50"),
        InlineKeyboardButton(text="🌿 100 грамм - 💸 6500 $MEF", callback_data="buy_100"),
        width=1
    )

    await message.answer(f"<b>🧙‍♂️ Здарова, ты попал на черный рынок, здесь ты можешь купить весь мой ассортимент.</b>", reply_markup=builder.as_markup(), parse_mode='HTML')


@router.callback_query(F.data.startswith('buy_'))
async def handle_purchase_callback(callback_query: CallbackQuery):
    action = callback_query.data.split('_')[1]
    user_id = callback_query.from_user.id
    print(action)
    match action:
        case '25':
            await handle_purchase(callback_query, user_id, 25, 2000)
        case '50':
            await handle_purchase(callback_query, user_id, 50, 3500)
        case '100':
            await handle_purchase(callback_query, user_id, 100, 6500)
        case _:
            return

async def handle_purchase(callback_query: CallbackQuery, user_id: int, amount: int, cost: int):
    user = await get_user(user_id)

    if user.balance >= cost:
        new_balance = user.balance - cost
        new_drug_count = user.drug_count + amount
        await update_user_balance_and_drug_count(user_id, new_balance, new_drug_count)
        await bot.answer_callback_query(callback_query.id, text=f"😈 Спасибо за покупку кентишка. Ты купил {amount} грамм за {cost} $MEF.", show_alert=True)
    else:
        await bot.answer_callback_query(callback_query.id, text="❌ Недостаточно крипты для покупки.", show_alert=True)

@router.message(Command('give'))
async def give_command(message: Message, command: CommandObject):
    user_id = message.from_user.id
    user = await get_user(user_id)
    try:
        args = command.args.split(' ', maxsplit=1)
    except:
        await message.reply('❌ Не указаны аргументы, укажи сколько грамм хочешь передать челику')
        return

    try:
        value = int(args[0])
    except ValueError:
        await message.reply('❌ Введи целое число')
        return

    recipient_id = message.reply_to_message.from_user.id if message.reply_to_message else None
    if recipient_id == 7266772626:
        await message.reply('❌ Вы не можете передать средства боту')
        return

    recipient = await get_user(recipient_id)
    if not recipient:
        await message.reply('❌ Пользователь не найден')
        return

    if value <= 0:
        await message.reply('❌ Значение должно быть положительным и больше нуля')
        return

    if user.drug_count < value:
        await message.reply('❌ Недостаточно граммов мефа для передачи')
        return

    commission = round(value * 0.10)
    net_value = value - commission
    bot_user = await get_user(1)
    if not bot_user:
        bot_user = await Users.create(id=1, drug_count=0)


    if user.vip == 0:

        recipient.drug_count += net_value
        user.drug_count -= value
        bot_user.drug_count += commission

        await recipient.save()
        await user.save()
        await bot_user.save()

        await bot.send_message(
            LOGS_CHAT_ID,
            f"<b>#GIVE</b>\n\nfirst_name: <code>{message.from_user.first_name}</code>\n"
            f"user_id: <code>{recipient_id}</code>\nvalue: <code>{net_value}</code>\n"
            f"Commission: <code>{commission}</code>\n\n<a href='tg://user?id={recipient_id}'>mention</a>",
            parse_mode='HTML'
        )

        recipient_full_name = message.reply_to_message.from_user.full_name if message.reply_to_message else ""

        await message.reply(
            f"✅ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a> <i>подарил(-а) {value} гр. мефа</i> "
            f"<a href='tg://user?id={recipient_id}'>{recipient_full_name}</a>!\nКомиссия: <code>{commission}</code> гр. мефа\n"
            f"Получено <code>{net_value}</code> гр. мефа.",
            parse_mode='HTML'
        )

    else:
        recipient.drug_count += value
        user.drug_count -= value

        await recipient.save()
        await user.save()
        await bot_user.save()

        await bot.send_message(
            LOGS_CHAT_ID,
            f"<b>#GIVE</b>\n\nfirst_name: <code>{message.from_user.first_name}</code>\n"
            f"user_id: <code>{recipient_id}</code>\nvalue: <code>{value}</code>\n",
            parse_mode='HTML'
        )

        recipient_full_name = message.reply_to_message.from_user.full_name if message.reply_to_message else ""

        await message.reply(
            f"✅ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a> <i>подарил(-а) {value} гр. мефа</i> "
            f"<a href='tg://user?id={recipient_id}'>{recipient_full_name}</a>!\n"
            f"Получено <code>{value}</code> гр. мефа.",
            parse_mode='HTML'
        )

@router.message(Command('work'))
async def work_command(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    if user.balance is None:
        user.balance = 0

    last_work = user.last_work
    now = datetime.now()

    if last_work:
        last_work = last_work.replace(tzinfo=None)

    if last_work and (now - last_work).total_seconds() < 21600:
        remaining_time = timedelta(hours=6) - (now - last_work)
        remaining_hours = remaining_time.seconds // 3600
        remaining_minutes = (remaining_time.seconds % 3600) // 60

        if remaining_hours > 0:
            await message.reply(
                f'⏳ Ты недавно ходил прятать <b>закладку</b>, подожди <code>{remaining_hours} часов</code> и <code>{remaining_minutes} минут.</code>',
                parse_mode='HTML')
        else:
            await message.reply(
                f'⏳ Ты недавно ходил прятать <b>закладку</b>, подожди <code>{remaining_minutes} минут.</code>',
                parse_mode='HTML')


        return

    if random.randint(1, 100) > 50:
        count = random.randint(500, 1300)
        user.balance += count
        user.last_work = datetime.now()
        await user.save()
        await message.reply(f"🌿 {message.from_user.first_name}, ты пошёл в лес и <b>спрятал закладку</b>, тебя никто не спалил, ты заработал <code>{count} $MEF.</code>", parse_mode='HTML')
    else:
        user.last_work = datetime.now()
        await user.save()
        await message.reply(f"❌ <b>{message.from_user.first_name}</b>, тебя <b>спалил мент</b> и <b>дал тебе по ебалу</b>\n⏳ Следующая попытка доступна через <b>12 часов.</b>", parse_mode='HTML')



@router.message(Command('find'))
async def find_command(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    drug_count, last_find = user.drug_count, user.last_find
    now = datetime.now()

    if last_find:
        last_find = last_find.replace(tzinfo=None)

    if last_find and (now - last_find).total_seconds() < 21600:
        remaining_time = timedelta(hours=6) - (now - last_find)
        remaining_hours = remaining_time.days * 24 + remaining_time.seconds // 3600
        remaining_minutes = (remaining_time.seconds % 3600) // 60

        if remaining_hours > 0:
            await message.reply(
                f'⏳ <b>Ты недавно ходил за кладом, подожди</b> <code>{remaining_hours} часов</code> <b>и</b> <code>{remaining_minutes} минут.</code>',parse_mode='HTML')
        else:
            await message.reply(
                f'⏳ <b>Ты недавно ходил за кладом, подожди</b> <code>{remaining_minutes} минут.</code>',
                parse_mode='HTML')
        return

    if random.randint(1, 100) > 50:
        count = random.randint(2, 10)
        user.drug_count += count
        user.last_find = datetime.now()
        user.last_use_time = datetime.fromtimestamp(0)
        await user.save()
        await message.reply(f"👍 {message.from_user.first_name}, ты пошёл в лес и <b>нашел клад</b>, там лежало <code>{count} гр.</code> мефчика!\n🌿 Твое время команды /drug обновлено", parse_mode='HTML')
    else:
        if drug_count > 1:
            count = random.randint(1, round(drug_count))
        else:
            count = 0
        user.drug_count -= count
        user.last_find = datetime.now()
        await user.save()
        if count != 0:
            await message.reply(f"❌ <b>{message.from_user.first_name}</b>, тебя <b>спалил мент</b> и <b>дал тебе по ебалу</b>\n🌿 Тебе нужно откупиться, мент предложил взятку в размере <code>{count} гр.</code>\n⏳ Следующая попытка доступна через <b>6 часов.</b>", parse_mode='HTML')
        else:
            await message.reply(f"❌ <b>{message.from_user.first_name}</b>, тебя <b>спалил мент</b> и <b>дал тебе по ебалу</b>\n⏳ Следующая попытка доступна через <b>6 часов.</b>", parse_mode='HTML')

@router.message(Command('top'))
async def top_command(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)

    top_users = await Users.all().order_by('-drug_count')

    if top_users:
        response = "🔝ТОП 10 ЛЮТЫХ МЕФЕДРОНЩИКОВ В МИРЕ🔝:\n\n"
        valid_user_ids = {user.id for user in top_users if user.id != 1 and user.drug_count > 0 and user.is_tester != True and user.is_admin != True}

        async def fetch_user_info(user_id):
            try:
                return (user_id, await bot.get_chat(user_id))
            except TelegramBadRequest:
                return (user_id, None)

        user_infos = await asyncio.gather(
            *[fetch_user_info(valid_user_id) for valid_user_id in valid_user_ids]
        )

        user_info_dict = {info_id: info for info_id, info in user_infos if info}

        counter = 1
        for user in top_users:
            if user.id == 1:
                continue
            drug_count = user.drug_count
            user_info = user_info_dict.get(user.id, None)
            if user_info:
                if user_info.full_name == 'Group' or user_info.full_name == 'Channel':
                    continue
                if counter == 11:
                    break
                else:
                    response += f"{counter}) *{user_info.full_name}*: `{drug_count} гр. мефа`\n"
                    counter += 1

        if counter == 1:
            await message.reply('Никто еще не принимал меф.')
        else:
            await message.reply(response, parse_mode='markdown')
    else:
        await message.reply('Никто еще не принимал меф.')

@router.message(Command('take'))
async def take_command(message: Message, state: FSMContext):
    user = await get_user(message.from_user.id)
    reply_msg = message.reply_to_message
    if reply_msg:
        if reply_msg.from_user.id == 7266772626:
            await message.reply(f'❌ Вы не можете забрать меф у бота')
            return
        if reply_msg.from_user.id != message.from_user.id:
            victim = await get_user(reply_msg.from_user.id)
            if not victim or user.drug_count <= 1 or victim.drug_count <= 1:
                await message.reply('❌ У вас или у жертвы недостаточно мефа.')
                return
            last_time_data = await state.get_data()
            last_time = last_time_data.get('time') if last_time_data else None

            if last_time and (datetime.now() - datetime.fromisoformat(last_time)).total_seconds() < 86400:
                await message.reply("❌ Нельзя пиздить меф так часто! Ты сможешь спиздить меф через 1 день.")
                return

            variables = ['noticed', 'hit', 'pass']
            randomed = random.choice(variables)
            if randomed == 'noticed':
                user.drug_count -= 1
                await message.reply('❌ <b>Жертва тебя заметила</b>, и ты решил убежать. Спиздить меф не получилось. Пока ты бежал, <b>ты потерял</b> <code>1 гр.</code>', parse_mode='HTML')
            elif randomed == 'hit':
                user.drug_count -= 1
                await message.reply('❌ <b>Жертва тебя заметила</b>, и пизданула тебя бутылкой по башке. Спиздить меф не получилось. <b>Жертва достала из твоего кармана</b> `1 гр.`', parse_mode='HTML')
            elif randomed == 'pass':
                victim.drug_count -= 1
                user.drug_count += 1
                await victim.save()
                victim_user_id = reply_msg.from_user.id
                await message.reply(f"✅ <a href='tg://user?id={message.from_user.id}'>{message.from_user.first_name}</a> <b>спиздил(-а) один грамм мефа</b> у <a href='tg://user?id={victim_user_id}'>{reply_msg.from_user.first_name}</a>!", parse_mode='HTML')
            await state.update_data(time=datetime.now().isoformat())
            await user.save()
    else:
        await message.reply('❌ Ответьте на сообщение, чтобы забрать меф.')


@router.message(Command('bonus'))
async def bonus_command(message: Message):
    user = await get_user(message.from_user.id)

    if user.bonus:
        await message.reply("<b>🛑 Вы уже получали свой стартовый бонус!</b>", parse_mode='HTML')
        return

    user.drug_count += 20
    user.bonus = True
    await user.save()

    await message.reply(
        f"🎉 <b>Ты получил стартовый бонус в размере 20 грамм! Твой новый баланс:</b> <code>{user.drug_count} грамм.</code>", parse_mode='HTML')


@router.message(Command('vipbonus'))
async def vipbonus_command(message: Message):
    user = await get_user(message.from_user.id)

    if user.vip == 0 or user.vip is None:
        await message.reply("<b>🛑 Вы не имеете VIP-статуса!</b>", parse_mode='HTML')
        return

    now = datetime.now()
    today = now.date()

    if user.vip_bonus != today:
        user.drug_count += 50
        user.vip_bonus = today

        await user.save()
        await message.reply(
            f"🎉 <b>Ты получил бонус в размере 50 грамм! Твой новый баланс:</b> <code>{user.drug_count} грамм.</code>", parse_mode='HTML')

    else:
        await message.reply("<b>🛑 Вы уже получали сегодня бонус!</b>", parse_mode='HTML')


games = {}

@router.message(Command('play'))
async def play_command(message: Message):
    user_id = message.from_user.id
    user = await get_user(message.from_user.id)
    if user_id in games:
        await message.reply("❌ <b>Вы уже начали игру. Подождите, пока завершится текущая игра.</b>", parse_mode='HTML')
        return

    last_play = user.last_play
    now = datetime.now()

    if last_play:
        last_play = last_play.replace(tzinfo=None)

    if last_play and (now - last_play).total_seconds() < 3600:
        remaining_time = timedelta(hours=1) - (now - last_play)
        remaining_hours = remaining_time.seconds // 3600
        remaining_minutes = (remaining_time.seconds % 3600) // 60

        if remaining_hours > 0:
            await message.reply(f'<b>⏳ Ты недавно играл, подожди</b> <code>{remaining_hours} часов</code> <b>и</b><code>{remaining_minutes} минут.</code>', parse_mode='HTML')
        else:
            await message.reply(f'<b>⏳ Ты недавно играл, подожди </b><code>{remaining_minutes} минут.</code>', parse_mode='HTML')
        return


    secret_number = random.randint(1, 10)
    games[user_id] = secret_number

    await message.reply("🎮 <b>Игра началась! Угадай число от 1 до 10. Напиши его прямо сюда.</b>", parse_mode='HTML')

@router.message()
async def process_guess(message: Message):
    user_id = message.from_user.id
    user = await get_user(message.from_user.id)
    if user_id not in games:
        return


    try:
        guess = int(message.text)
    except ValueError:
        await message.reply("<b>❌ Пожалуйста, введи число от 1 до 10!</b>", parse_mode='HTML')
        return

    secret_number = games[user_id]

    if guess == secret_number:
        reward = random.randint(1, 20)
        user.drug_count += reward
        user.last_play = datetime.now()
        await user.save()
        await message.reply(f"🎉 <b>Поздравляю! Ты угадал число и выиграл</b> <code>{reward} гр!</code>\nТвой новый баланс <code>{user.drug_count} гр.</code>", parse_mode='HTML')
    else:
        await message.reply(f"😢 <b>Увы, ты не угадал. Загаданное число было</b> <code>{secret_number}</code>. <b>Попробуй снова!</b>", parse_mode='HTML')
        user.last_play = datetime.now()
        await user.save()

    del games[user_id]


@router.message(Command('drug'))
async def drug_command(message: Message):
    user = await get_user(message.from_user.id)
    drug_count, last_use_time = user.drug_count, user.last_use_time
    now = datetime.now()

    if last_use_time:
        last_use_time = last_use_time.replace(tzinfo=None)

    if last_use_time and (now - last_use_time).total_seconds() < 3600:
        remaining_time = timedelta(hours=1) - (now - last_use_time)
        await message.reply(f"❌ <b>{message.from_user.first_name}</b>, <i>ты уже нюхал(-а)!</i>\n🌿 Всего снюхано <code>{drug_count} грамм</code> мефедрона\n\n⏳ Следующую дорогу начертим через <code>{remaining_time.seconds // 60} минут.</code>", parse_mode='HTML')
        return

    if random.randint(0, 100) < 5:
        await message.reply(f"💀 <b>{message.from_user.first_name}</b>, <i>ты поймал(-а) передоз!</i>\n🚑 <i>Тебя отвезли в рехаб,</i> весь твой баланс <b>был сброшен</b>\n\n⏳ Тебя отпустят через <code>1 час.</code>", parse_mode='HTML')
        user.last_use_time = now
        user.drug_count = 0
        await user.save()
        return
    elif random.randint(0, 100) < 40:
        await message.reply(f"🧂 <b>{message.from_user.first_name}</b>, <i>ты просыпал(-а) весь мефчик!</i>\n🌿 Всего снюхано <code>{drug_count}</code> грамм мефедрона\n\n⏳ Следующую дорогу начертим через <code>1 час.</code>", parse_mode='HTML')
        user.last_use_time = now    
        await user.save()
        return
    else:
        count = random.randint(1, 10)
        user.drug_count += count
        user.last_use_time = now
        await user.save()
        await message.reply(f"👍 <b>{message.from_user.first_name}</b>, <i>ты занюхнул(-а) {count} грамм мефчика!</i>\n🌿 Всего снюхано <code>{user.drug_count}</code> грамм мефедрона\n\n⏳ Следующую дорогу начертим через <code>1 час.</code>", parse_mode='HTML')


@router.message(Command('help'))
async def help_command(message: Message):
    await message.reply('''Все команды бота:
                        
<code>/profile</code> - <b>посмотреть профиль игрока</b>
<code>/drug</code> - <b>принять мефик</b>
<code>/top</code> - <b>топ торчей мира</b>
<code>/take</code> - <b>спиздить мефик у ближнего</b>
<code>/give</code> - <b>поделиться мефиком</b>
<code>/casino</code> - <b>казино</b>
<code>/find</code> - <b>сходить за кладом</b>
<code>/work</code> - <b>оставить закладку</b>
<code>/shop</code> - <b>купить граммы за крипту</b>                    
<code>/about</code> - <b>узнать подробнее о боте</b>
<code>/clancreate</code> - <b>создать клан</b>
<code>/deposit</code> - <b>пополнить баланс клана</b>
<code>/withdraw</code> - <b>вывести средства с клана</b>
<code>/clantop</code> - <b>топ 10 кланов по состоянию баланса</b>
<code>/clanbalance</code> - <b>баланс клана</b>
<code>/claninfo</code> - <b>о клане</b>
<code>/claninvite</code> - <b>пригласить в клан</b>
<code>/clankick</code> - <b>кикнуть из клана</b>
<code>/clanleave</code> - <b>добровольно выйти из клана</b>
<code>/clandisband</code> - <b>распустить клан</b>
<code>/botprofile</code> - <b>профиль бота (резерв казино)</b>
<code>/buymeph</code> - <b>купить граммы за донат</b>
<code>/buyvip</code> - <b>покупка VIP-статуса</b>
<code>/bonus</code> - <b>бонус для каждого игрока</b>
<code>/vipbonus</code> - <b>бонус для каждого VIP-игрока</b>
    ''', parse_mode='HTML')

@router.message(Command('grach'))
async def start_command(message: Message):
    await message.reply("грач хуесос")

@router.message(Command('rules'))
async def start_command(message: Message):
    await message.reply('''Правила пользования mephmetrbot:
<b>1) Мультиаккаунтинг - бан навсегда и обнуление всех аккаунтов
2) Использование любых уязвимостей бота - бан до исправления и возможное обнуление
3) Запрещена реклама через топ кланов и топ юзеров - выговор, после бан с обнулением
4) Запрещена продажа валюты между игроками - обнуление и бан</b>

<b>Бот не имеет никакого отношения к реальности. Все совпадения случайны.
Создатели не пропагандируют наркотики и против их распространения и употребления.
Употребление, хранение и продажа является уголовно наказуемой</b>
*Сообщить о багах вы можете администраторам* (<b>команда</b> <code>/about</code>)''', parse_mode='HTML')

@router.message(Command('start'))
async def start_command(message: Message, command: CommandObject):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='📢 Канал', url='https://t.me/mefmetrch'),
        InlineKeyboardButton(text='💰 Донат', url='https://t.me/mefmetrch'),
        InlineKeyboardButton(text='💬 Чат', url='https://t.me/mephmetrchat')
    )
    await message.reply("👋 <b>Здарова шныр</b>, этот бот сделан для того, чтобы <b>считать</b> сколько <b>грамм мефедрончика</b> ты снюхал\n\n🛑 Внимание, это всего лишь игровой бот, здесь не продают меф. Не стоит писать об этом мне, ваши попытки приобрести наркотические вещества - будут переданы правохранительным органам.\n\n🧑‍💻 Бот разработан <b>vccuser.t.me</b> и <b>vccleak.t.me</b>", reply_markup=builder.as_markup(), parse_mode='HTML')


@router.message(Command('about'))
async def about_command(message: Message):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text='📢 Канал', url='https://t.me/mefmetrch'),
        InlineKeyboardButton(text='💰 Донат', url='https://t.me/mefmetrch'),
        InlineKeyboardButton(text='💬 Чат', url='https://t.me/mephmetrchat')
    )
    await message.reply("🧑‍💻 Бот разработан vccuser.t.me и vccleak.t.me", reply_markup=builder.as_markup())
