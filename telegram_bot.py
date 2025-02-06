import os, asyncio, logging
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from telegramify_markdown import markdownify

load_dotenv()

from LLM.agent import app

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Hello!")

@dp.message(F.text)
async def responder(message: types.Message):
    user_id = message.chat.id
    config = {"configurable": {"thread_id": user_id}}
    messages = app.invoke({"messages": [("human", message.text)]}, config=config)
    llm_answer = messages['messages'][-1].content
    escaped_answer = markdownify(llm_answer)
    await message.answer(escaped_answer, parse_mode='MarkdownV2')

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())