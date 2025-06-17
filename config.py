import os
import json


def load_config(path='Config.json'):
    cfg = {
        'Discord_Bot_Token': os.getenv('DISCORD_BOT_TOKEN', 'YOURTOKEN'),
        'Gemini_Token': os.getenv('GEMINI_TOKEN', 'YOURTOKEN'),
        'Your_Discord_Id': os.getenv('YOUR_DISCORD_ID', '0'),
        'Memory_Channel': os.getenv('MEMORY_CHANNEL', '')
    }
    try:
        with open(path, 'r') as f:
            file_cfg = json.load(f)
            for key in cfg.keys():
                if key in file_cfg and file_cfg[key] is not None:
                    cfg[key] = file_cfg[key]
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        print('Config.json format error, ignoring file')
    return cfg
