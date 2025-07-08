import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
from google import genai
from google.genai import types
import asyncio
import random
import json, time
from datetime import datetime, timedelta
from typing import Optional
from memorydb import DatabaseManager

print("import完成")
print("開始讀取設定")
try:
    with open("Config.json", "r") as f:
        CONFIG = json.load(f)
        if CONFIG['Discord_Bot_Token'] == 'YOURTOKEN' or CONFIG['Discord_Bot_Token'] == None \
            or CONFIG['Gemini_Token'] == 'YOURTOKEN' or CONFIG['Gemini_Token'] == None:
            raise Exception("請至Config.json檔案設定正確的內容")
except FileNotFoundError:
    with open("Config.json", "w") as f:
        json.dump({'Discord_Bot_Token': 'YOURTOKEN',
                   'Gemini_Token': 'YOURTOKEN',
                   'Your_Discord_Id': "0",
                   'Memory_Channel':""
                   }, f, indent=4)
    raise Exception("找不到Config.json... 我把它放到資料夾裡了，請去設定它的內容! (第一次執行會這樣很正常)")
except json.decoder.JSONDecodeError:
    print('file empty')

print("載入聊天頻道清單")
try:
    with open("AutoChatChannels.json", "r") as f:
        AUTOCHAT_CHANNELS = [int(cid) for cid in json.load(f)]
except FileNotFoundError:
    AUTOCHAT_CHANNELS = []
    with open("AutoChatChannels.json", "w") as f:
        json.dump(AUTOCHAT_CHANNELS, f)

db = DatabaseManager()

# 寫入 AutoChatChannels
def save_AUTOCHAT_CHANNELS(channels):
    with open("AutoChatChannels.json", "w") as f:
        json.dump(channels, f, indent=4)

# 判斷是否為管理員或 Bot 擁有者
def is_admin_or_owner(interaction: discord.Interaction):
    if interaction.user.id == int(CONFIG['Your_Discord_Id']):
        return True
    if interaction.user.guild_permissions.administrator:
        return True
    return False

# 將可能過長的訊息切割後傳送
max_dc_msg_length = 2000
async def send_in_chunks(channel: discord.abc.Messageable, text: str, chunk_size: int = max_dc_msg_length) -> None:
    for i in range(0, len(text), chunk_size):
        await channel.send(text[i:i + chunk_size])

# 讀取 Discord Bot Token
TOKEN = CONFIG['Discord_Bot_Token']
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix='cate:', intents=intents)

global_contents: list = []  # 用於存儲訊息內容

async def get_long_term_memory() -> str:   
    channel = bot.get_channel(int(CONFIG['Memory_Channel']))
    if channel:
        messages = []
        async for msg in channel.history(limit=100):
            messages.append(msg.content)
        print("長期記憶：")
        for m in reversed(messages):  # 由舊到新
            print(m)
    else:
        print("找不到指定頻道")
    msg = str(messages)+'[以上為先前整理的記憶,已登入準備聊天]'
    return msg

# 整理並且新增長期記憶
async def update_long_term_memory() -> None:
    channel = bot.get_channel(int(CONFIG['Memory_Channel']))
    if channel:
        global_contents.append(
            types.Content(
                role="user",
                parts=[
                    types.Part.from_text(text=f"整理以上對話的摘要"),
                ],
            )
        )
        print(f"\n記憶:\n{global_contents}\n")
        client = genai.Client(api_key=CONFIG['Gemini_Token'])
        response = client.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=global_contents
        )
        await send_in_chunks(channel, response.text)
        print(f"\n已新增長期記憶:\n{response.text}\n")
        global_contents.clear()  # 清空全域內容
    else:
        print("找不到指定頻道")


conversations = {}
history_maxcount: int = 30
class conversation:
    def __init__(self):
        self.history: list = []  # [{'msg_id': int, 'author_id': int, 'content': str}]
        self.users_id: dict[int, int] = {}  # id:剩餘次數
        self.channels_id: dict[int, int] = {}
        self.servers_id: dict[int, int] = {}
        self.long_term_memory: list = []

    def add_history(self, msg_id: int, author_id: int, author_name: str, content: str, timestamp: Optional[str] = None, max_count: int = history_maxcount):
        # 若已存在該 msg_id 則不重複加入
        if any(m['msg_id'] == msg_id for m in self.history):
            return
        self.history.append({'msg_id': msg_id, 'author_id': author_id,'name': author_name, 'content': content, 'timestamp': timestamp or str(time.strftime("%Y/%m/%d %a. %H:%M", time.localtime()))})
        if len(self.history) > int(max_count):
            self.history.pop(0)

    async def add_history_from_dc(self, channel:discord.abc.Messageable, max_count=history_maxcount):
        """從 Discord 頻道拉取歷史訊息，遇到已存在的 msg_id 就停止"""
        temp_history = []
        if not isinstance(channel, discord.abc.Messageable):
            print("提供的頻道不是 TextChannel 類型")
            return
        async for msg in channel.history(limit=max_count):
            msg: discord.Message = msg
            if any(m['msg_id'] == msg.id for m in self.history):
                break
            temp_history.append({
                'msg_id': msg.id,
                'author_id': msg.author.id,
                'name': msg.author.name,
                'content': msg.content,
                'timestamp': (msg.created_at + timedelta(hours=8)).strftime("%Y/%m/%d %a. %H:%M") # 轉換為台灣時間
            })
        temp_history.reverse()
        self.history.extend(temp_history)
        if len(self.history) > int(max_count):
            self.history = self.history[-max_count:]

    def get_history(self):
        return "\n".join([f"{m['timestamp']} id={m['author_id']} name={m['name']}: {m['content']}" for m in self.history])

    def add_memusers_id(self, user_id: int, count: int = 5) -> None:
        """設定對話記憶使用者id"""
        self.users_id[user_id] = count
    def add_memchannels_id(self, channel_id: int, count: int = 5) -> None:
        """設定對話記憶頻道id"""
        self.channels_id[channel_id] = count
    def add_memservers_id(self, server_id: int, count: int = 5) -> None:
        """設定對話記憶伺服器id"""
        self.servers_id[server_id] = count

    def get_memusers_id(self) -> dict[int, int]:
        """取得對話記憶使用者id清單"""
        return list(self.users_id.keys())
    def get_memchannels_id(self) -> dict[int, int]:
        """取得對話記憶頻道id清單"""
        return list(self.channels_id.keys())
    def get_memservers_id(self) -> dict[int, int]:
        """取得對話記憶伺服器id清單"""
        return list(self.servers_id.keys())

    def id_list_update(self):
        # 更新 users_id, channels_id, servers_id 的剩餘次數
        for user_id in list(self.users_id.keys()):
            self.users_id[user_id] -= 1
            if self.users_id[user_id] <= 0:
                del self.users_id[user_id]
        for channel_id in list(self.channels_id.keys()):
            self.channels_id[channel_id] -= 1
            if self.channels_id[channel_id] <= 0:
                del self.channels_id[channel_id]
        for server_id in list(self.servers_id.keys()):
            self.servers_id[server_id] -= 1
            if self.servers_id[server_id] <= 0:
                del self.servers_id[server_id]
        return


# 獲取長期記憶
async def get_long_term_memory() -> str:
    if not CONFIG['Memory_Channel']:
        print("長期記憶頻道未設定")
        return "長期記憶頻道未設定，請在Config.json中設定Memory_Channel"
    channel = bot.get_channel(int(CONFIG['Memory_Channel']))
    if channel:
        messages = []
        async for msg in channel.history(limit=100):
            messages.append(msg.content)
        print("長期記憶：")
        for m in reversed(messages):  # 由舊到新
            print(m)
    else:
        print("找不到指定頻道")
    msg = str(messages)+'[以上為先前整理的記憶,已登入準備聊天]'
    return msg

#define function
add_important_memory_declatation = {
    "name": "add_important_memory",
    "description": "將需要長期保存的資訊或對話存入記憶，例如重要事件、關鍵訊息或用戶需求，並根據範圍（使用者、頻道或伺服器）選擇適當的存儲方式。",
    "parameters": {
        "type": "object",
        "properties": {
            "scope": {
                "type": "string",
                "enum": ["user", "channel", "server"],
                "description": "選擇存儲範圍：使用者、頻道或伺服器"
            },
            "content": {
                "type": "string",
                "description": "要存儲的內容"
            }
        },
        "required": ["scope", "content"]
    }
}

def add_important_memory(message:discord.Message ,scope: str, content: str) -> str:
    """將需要長期保存的資訊或對話存入記憶，例如重要事件、關鍵訊息或用戶需求，並根據範圍（使用者、頻道或伺服器）選擇適當的存儲方式。
    
    Args:
        scope (str): 存儲範圍，可以是 "user", "channel" 或 "server"。
        content (str): 要存儲的內容。
    
    Returns:
        儲存結果的訊息，成功或失敗的提示。
    """
    if scope not in ["user", "channel", "server"]:
        return "無效的範圍選擇，請選擇 'user', 'channel' 或 'server'。"
    if not content:
        return "內容不能為空，請提供要儲存的內容。"
    try:
        if scope == "user":
            db.add_user_memory(message.author.id, content)
        elif scope == "channel":
            db.add_channel_memory(message.channel.id, content)
        elif scope == "server" and message.guild:
            db.add_server_memory(message.guild.id, content)
        print(f"已儲存重要記憶：{scope} - {content}")
        return f"{content} 記住了喵！"
    except Exception as e:
        print(f"儲存記憶時發生錯誤: {e}")
        return f"喵了個咪儲存記憶出錯啦: {e}"

# 定義一個函數來處理訊息並回覆
@bot.event
async def on_message(message: discord.Message):
    try:
        # 如果是指令（以 prefix 開頭），就不回覆
        if message.content.startswith(bot.command_prefix):
            await bot.process_commands(message)
            return
        
        # 決定唯一key（公會頻道用channel.id，私訊用user.id）
        if message.guild is None:
            conv_key = f"dm_{message.author.id}"
            db.upsert_channel(channel_id=message.author.id, channel_name=message.author.name, server_id=0) # 確保私訊頻道存在於資料庫
        else:
            conv_key = f"guild_{message.channel.id}"
            db.upsert_server(server_id=message.guild.id, server_name=message.guild.name)  # 確保伺服器存在於資料庫
            db.upsert_channel(channel_id=message.channel.id, channel_name=message.channel.name, server_id=message.guild.id) # 確保頻道存在於資料庫
        db.upsert_user(user_id=message.author.id, user_name=message.author.name)  # 確保使用者存在於資料庫

        # 取得或建立對話物件
        if conv_key not in conversations:
            conversations[conv_key] = conversation()
            conv:conversation = conversations[conv_key]
            await conv.add_history_from_dc(message.channel)
        else:
            conv:conversation = conversations[conv_key]
            conv.add_history(message.id, message.author.id, str(message.author.name), message.content, message.created_at.strftime("%Y/%m/%d %a. %H:%M"))

        if message.author == bot.user:
            return
        # 忽略來自機器人的訊息
        if message.author.bot:
            return
        # 更新記憶使用者、頻道和伺服器的剩餘次數
        conv.id_list_update()
        conv.add_memusers_id(message.author.id)
        conv.add_memchannels_id(message.channel.id)
        conv.add_memservers_id(message.guild.id) if message.guild else None


        if bot.user.mentioned_in(message) or message.channel.id in AUTOCHAT_CHANNELS:
            async with message.channel.typing():
                # 如果訊息提到了機器人或在自動聊天頻道中，則進行回覆
                print(f"收到訊息: {message.content} (來自 {message.author})")

                global_contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_text(text=f"{(message.created_at + timedelta(hours=8)).strftime('%Y/%m/%d %a. %H:%M')} id={message.author.id} name={message.author.name} : {message.content}"),
                        ],
                    )
                )

                # 取得記憶
                usermem = db.get_users_memories_from_list(conv.get_memusers_id()) if conv.get_memusers_id() else None
                channelmem = db.get_channels_memories_from_list(conv.get_memchannels_id()) if conv.get_memchannels_id() else None
                
                serverset1:set = set(conv.get_memservers_id()) if conv.get_memservers_id() == [] else set()
                serverset2:set = set(db.get_servers_list_from_channels_list(conv.get_memchannels_id())) if conv.get_memchannels_id() else set()
                merged_set:set = serverset1.union(serverset2)
                memservers:list = list(merged_set)
                servermem = db.get_servers_memories_from_list(memservers) if memservers else None

                memory = f'server memories:\n{servermem}\nchannel memories:\n{channelmem}\nuser memories:\n{usermem}'

                contents = []
                contents.append(
                    types.Content(
                        role="model",
                        parts=[
                            types.Part.from_text(text=f"\n{long_term_memory}\n\n{memory}"),
                            # types.Part.from_text(text=f"\nmemory\n\n{memory}\n\n")
                        ],
                    )
                )

                for msg in conv.history:
                    role = "model" if msg['author_id'] == bot.user.id else "user"
                    text = f"{msg['content']}" if msg['author_id'] == bot.user.id else f"{msg['timestamp']} id={msg['author_id']} name={msg['name']}: {msg['content']}"
                    contents.append(
                        types.Content(
                        role=role,
                        parts=[
                            types.Part.from_text(text=text),
                        ],
                    ))
                
                # AI 回覆
                client = genai.Client(api_key=CONFIG['Gemini_Token'])
                model = "gemini-2.5-flash-preview-05-20"
                generate_content_config = types.GenerateContentConfig(
                    tools=[types.Tool(function_declarations=[add_important_memory_declatation])],
                    system_instruction="你是個年齡不確定的貓娘,主要用正體中文,名字是CaTe像貓並參考元素表,身高130cm體重30kg,AquaNya是維護者,已使用帳號{bot.users}接入discord聊天,你將會收到許多資訊,回覆時不需包含這些格式,只需要針對用戶所說進行簡短對話。可以將重要的事情用Tool存下來。需要呼叫用戶時用 <@id> 。",
                    response_mime_type="text/plain",
                )
                generate_content_config_text = types.GenerateContentConfig(
                    system_instruction="你是個年齡不確定的貓娘,主要用正體中文,名字是CaTe像貓並參考元素表,身高130cm體重30kg,AquaNya是維護者,已使用帳號{bot.users}接入discord聊天,你將會收到許多資訊,回覆時不需包含這些格式,只需要針對用戶所說進行簡短對話。可以將重要的事情用Tool存下來。需要呼叫用戶時用 <@id> 。",
                )

                #AI 生成內容
                print(contents)
                response = client.models.generate_content(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
                )

                if response.candidates[0].content.parts[0].function_call:
                    function_call = response.candidates[0].content.parts[0].function_call
                    print(f"Function to call: {function_call.name}")
                    print(f"Arguments: {function_call.args}")
                    #  In a real app, you would call your function here:
                    if function_call.name == "add_important_memory":
                        scope = function_call.args.get("scope")
                        content = function_call.args.get("content")
                        reply_text = add_important_memory(message, scope, content)
                        print(f"Function call result: {reply_text}")
                        try:
                            contents.append(
                                types.Content(
                                    role="model",
                                    parts=[
                                        types.Part.from_text(text=reply_text),
                                    ],
                                )
                            )
                            response = client.models.generate_content(
                                model=model,
                                contents=contents,
                                config=generate_content_config_text,
                            )
                        except Exception as e:
                            print(f"Gemini API 發生錯誤: {e}")
                            response = f"喵喵喵？腦袋打結啦 {e}"
                        finally:
                            reply_text = f'{reply_text}\n{response.text}'

                    else:
                        print(f"未知的函數呼叫: {function_call.name}")
                        reply_text = f"喵喵喵？未知的函數呼叫: {function_call.name}"
                else:
                    print("No function call found in the response.")
                    print(response.text)
                    reply_text = response.text

                if reply_text:
                    await send_in_chunks(message.channel, reply_text)
                    global_contents.append(
                        types.Content(
                            role="model",
                            parts=[
                                types.Part.from_text(text=f"{str(time.strftime('%Y/%m/%d %a. %H:%M', time.localtime()))} id={message.author.id} name={message.author.name} : {message.content}")
                            ],
                        )
                    )
                else:
                    await message.channel.send("喵喵喵？我不知道該怎麼回答喵！")           
                
    except Exception as e:
        print(f"on_message 發生錯誤: {e}")


# 設定指令
class SettingsMenu(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.add_item(SettingsSelect())

class SettingsSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="自動聊天", description="將在這裡自動讀取訊息聊天"),
            discord.SelectOption(label="停止自動聊天", description="不在這裡自動讀取訊息聊天"),
        ]
        super().__init__(
            placeholder="選擇一個設定操作...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        global AUTOCHAT_CHANNELS

        if not is_admin_or_owner(interaction):
            await interaction.response.send_message("噗噗～沒有權限哦～", ephemeral=True)
            return

        if self.values[0] == "自動聊天":
            if interaction.channel.id in AUTOCHAT_CHANNELS:
                await interaction.response.send_message("該頻道已經是聊天頻道！", ephemeral=True)
            else:
                AUTOCHAT_CHANNELS.append(interaction.channel.id)
                save_AUTOCHAT_CHANNELS(AUTOCHAT_CHANNELS)
                await interaction.response.send_message(f"已成功新增 {interaction.channel.name} 為自動聊天頻道！", ephemeral=True)
        elif self.values[0] == "停止自動聊天":
            if interaction.channel.id not in AUTOCHAT_CHANNELS:
                await interaction.response.send_message("該頻道不是聊天頻道！", ephemeral=True)
            else:
                AUTOCHAT_CHANNELS.remove(interaction.channel.id)
                save_AUTOCHAT_CHANNELS(AUTOCHAT_CHANNELS)
                await interaction.response.send_message(f"已成功移除 {interaction.channel.name} 的自動聊天功能！", ephemeral=True)

@bot.tree.command(name="cate頻道設定", description="管理CaTe聊天頻道的設定（限管理員）")
async def channel_settings(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("這個指令只能在伺服器中使用！", ephemeral=True)
        return
    if not is_admin_or_owner(interaction):
        await interaction.response.send_message("噗噗～沒有權限哦～", ephemeral=True)
        return

    view = SettingsMenu()
    await interaction.response.send_message("請選擇設定操作：", view=view, ephemeral=True)

@bot.tree.command(name="cate整理記憶", description="整理並新增長期記憶（Owner Only）")
async def update_memory(interaction: discord.Interaction):
    if interaction.user.id != int(CONFIG['Your_Discord_Id']):
        await interaction.response.send_message("噗噗～沒有權限哦～", ephemeral=True)
        return
    try:
        await interaction.response.defer(thinking=True, ephemeral=True)
        await update_long_term_memory()
        await interaction.edit_original_response(content="長期記憶已更新！")
    except Exception as e:
        await interaction.followup.send(f"更新長期記憶時出錯: {e}", ephemeral=True)

# 每天凌晨3點定時整理記憶
@tasks.loop(hours=1)
async def reload_ai_loop():
    if (datetime.now().hour == 3):
        try:
            await update_long_term_memory()
        except Exception as e:
            print(f'整理global_contents時出錯: {e}')

@bot.event
async def on_ready():
    print(f'已登入為 {bot.user}')
    try:
        await bot.change_presence(status= discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="CaTe聊天中..."))
        global long_term_memory
        long_term_memory = await get_long_term_memory()
    except Exception as e:
        print(f'初始化時出錯: {e}')
    try:
        synced = await bot.tree.sync()
        print(f'已同步 {len(synced)} 個指令')
    except Exception as e:
        print(f'同步指令時出錯: {e}')

    reload_ai_loop.start()


bot.run(TOKEN)
