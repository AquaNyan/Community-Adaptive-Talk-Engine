import sqlite3
import threading
from datetime import datetime
from typing import Optional, Any

class DatabaseManager:
    def __init__(self, db_file:str='memory.db') -> None:
        self.db_file = db_file
        self.lock = threading.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_file)


    def _init_db(self) -> None:
        with self._connect() as conn:
            c = conn.cursor()

            # 建立 core_memories 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS core_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # 建立 servers 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    server_id INTEGER PRIMARY KEY,
                    server_name TEXT,
                    note TEXT,
                    api_key TEXT
                )
            ''')

            # 建立 server_memories 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS server_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    server_id INTEGER,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE
                )
            ''')

            # 建立 channels 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS channels (
                    channel_id INTEGER PRIMARY KEY,
                    channel_name TEXT,
                    note TEXT,
                    server_id INTEGER,
                    mode TEXT,
                    FOREIGN KEY (server_id) REFERENCES servers(server_id) ON DELETE CASCADE
                )
            ''')

            # 建立 channel_memories 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS channel_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_id INTEGER,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
                )
            ''')

            # 建立 users 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    user_name TEXT,
                    nickname TEXT,
                    birthday TEXT,  -- 格式：YYYY-MM-DD 或 --MM-DD
                    note TEXT,
                    api_key TEXT,
                    warning_count INTEGER DEFAULT 0,
                    ignore BOOLEAN DEFAULT FALSE
                )
            ''')

            # 建立 user_memories 表
            c.execute('''
                CREATE TABLE IF NOT EXISTS user_memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    content TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
                )
            ''')

            print("資料庫初始化完成。")


    def _format_birthday(self, birthday: str) -> Optional[str]:
        if not birthday:
            return None
        birthday = birthday.strip().replace('/', '-')
        parts = birthday.split('-')
        if len(parts) == 3:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        elif len(parts) == 2:
            return f"--{int(parts[0]):02d}-{int(parts[1]):02d}"
        return None


    def add_core_memory(self, content: str) -> str:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    INSERT INTO core_memories (content)
                    VALUES (?)
                ''', (content,))
                conn.commit()
                return "已新增核心記憶。"
        except sqlite3.Error as e:
            return f"新增核心記憶時發生錯誤: {e}"


    def upsert_server(self, server_id: int, server_name: str, note: Optional[str] = None) -> str:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    INSERT INTO servers (server_id, server_name, note)
                    VALUES (?, ?, ?)
                ''', (server_id, server_name, note))
                conn.commit()
                return f"已新增伺服器 {server_id}。"
        except sqlite3.Error as e:
            return f"新增伺服器 {server_id} 時發生錯誤: {e}"

    def add_server_memory(self, server_id: int, content: str) -> str:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    INSERT INTO server_memories (server_id, content)
                    VALUES (?, ?)
                ''', (server_id, content))
                conn.commit()
                return f"已新增伺服器 {server_id} 的記憶。"
        except sqlite3.Error as e:
            return f"新增伺服器 {server_id} 的記憶時發生錯誤: {e}"


    def upsert_channel(self, channel_id: int, channel_name: str = None, note: Optional[str] = None, server_id: int = None,mode: Optional[str] = None) -> str:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    INSERT INTO channels (channel_id, channel_name, note, server_id, mode)
                    VALUES (?, ?, ?, ?, ?)
                ''', (channel_id, channel_name, note, server_id, mode))
                conn.commit()
                return f"已新增頻道 {channel_id}。"
        except sqlite3.Error as e:
            return f"新增頻道 {channel_id} 時發生錯誤: {e}"

    def add_channel_memory(self, channel_id: int, content: str) -> str:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    INSERT INTO channel_memories (channel_id, content)
                    VALUES (?, ?)
                ''', (channel_id, content))
                conn.commit()
                return f"已新增頻道 {channel_id} 的記憶。"
        except sqlite3.Error as e:
            return f"新增頻道 {channel_id} 的記憶時發生錯誤: {e}"


    def upsert_user(self, user_id: int, user_name: Optional[str] = None, nickname: Optional[str] = None,
                        birthday: Optional[str] = None, note: Optional[str] = None, api_key: Optional[str] = None,
                        warning_count: int = None, ignore: bool = None) -> str:
        birthday = self._format_birthday(birthday)
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()

                # 檢查是否存在
                c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                exists = c.fetchone()

                if exists:
                    # 更新
                    c.execute('''
                        UPDATE users
                        SET user_name = COALESCE(?, user_name),
                            nickname = COALESCE(?, nickname),
                            birthday = COALESCE(?, birthday),  -- 格式：YYYY-MM-DD 或 --MM-DD
                            note = COALESCE(?, note),
                            api_key = COALESCE(?, api_key),
                            warning_count = COALESCE(?, warning_count),
                            ignore = COALESCE(?, ignore)
                        WHERE user_id = ?
                    ''', (user_name, nickname, birthday, note, api_key, user_id, warning_count, ignore))
                    conn.commit()
                    return f"已更新使用者 {user_id}"
                else:
                    # 新增
                    c.execute('''
                        INSERT INTO users (user_id, user_name, nickname, birthday, note, api_key, warning_count, ignore)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (user_id, user_name, nickname, birthday, note, api_key, warning_count, ignore))
                    conn.commit()
                    return f"已新增使用者 {user_id}"
        except sqlite3.Error as e:
            return f"新增或更新使用者 {user_id} 時發生錯誤: {e}"

    def add_user_warning(self, user_id: int):
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    UPDATE users
                    SET warning_count = warning_count + 1
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return f"已為使用者 {user_id} 增加警告。"
        except sqlite3.Error as e:
            return f"增加使用者 {user_id} 的警告時發生錯誤: {e}"
    
    def ignore_user(self, user_id: int, ignore: bool):
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute('''
                    UPDATE users
                    SET ignore = ?
                    WHERE user_id = ?
                ''', (ignore, user_id))
                conn.commit()
                return f"已{'忽略' if ignore else '取消忽略'}使用者 {user_id}。"
        except sqlite3.Error as e:
            return f"更新使用者 {user_id} 忽略狀態時發生錯誤: {e}"

    def add_user_memory(self, user_id: int, content: str):
            try:
                with self._connect() as conn:
                    conn: sqlite3.Connection
                    c = conn.cursor()
                # 插入 user_memory
                c.execute('''
                    INSERT INTO user_memories (user_id, content)
                    VALUES (?, ?)
                ''', (user_id, content))
                conn.commit()
                return f"已新增使用者 {user_id} 的記憶。"
            except sqlite3.Error as e:
                return f"新增使用者 {user_id} 的記憶時發生錯誤: {e}"


    def get_user_api_key(self, user_id: int) -> Optional[str]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                if row:
                    return row[0]
                return None
        except sqlite3.Error as e:
            print(f"查詢使用者 {user_id} 的 API 金鑰時發生錯誤: {e}")
            return None

    def get_server_api_key(self, server_id: int) -> Optional[str]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT api_key FROM servers WHERE user_id = ?", (server_id,))
                row = c.fetchone()
                if row:
                    return row[0]
                return None
        except sqlite3.Error as e:
            print(f"查詢伺服器 {server_id} 的 API 金鑰時發生錯誤: {e}")
            return None

    def get_user_memories(self, user_id: int) -> Optional[list]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM user_memories WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
                rows = c.fetchall()
                rows = rows[::-1]  # 反轉順序，最新的在最前面
                return [{'content': row[2], 'timestamp': row[3]} for row in rows]
        except sqlite3.Error as e:
            print(f"查詢使用者 {user_id} 的記憶時發生錯誤: {e}")
            return None

    def get_user(self, user_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                memories = self.get_user_memories(user_id)
                if row:
                    return {
                        'user_id': row[0],
                        'user_name': row[1],
                        'nickname': row[2],
                        'birthday': row[3],
                        'note': row[4],
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢使用者 {user_id} 時發生錯誤: {e}")
            return None


    def get_server_memories(self, server_id: int) -> Optional[list]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM server_memories WHERE server_id = ? ORDER BY id DESC LIMIT 10", (server_id,))
                rows = c.fetchall()
                rows = rows[::-1]  # 反轉順序，最新的在最前面
                return [{'content': row[2], 'timestamp': row[3]} for row in rows]
        except sqlite3.Error as e:
            print(f"查詢伺服器 {server_id} 的記憶時發生錯誤: {e}")
            return None

    def get_server(self, server_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,))
                row = c.fetchone()
                if row:
                    return {
                        'server_id': row[0],
                        'server_name': row[1],
                        'note': row[2],
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢伺服器 {server_id} 時發生錯誤: {e}")
            return None

    def get_channel_memories(self, channel_id: int) -> Optional[list]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute(
                    "SELECT * FROM channel_memories WHERE channel_id = ? ORDER BY id DESC LIMIT 10", (channel_id,))
                rows = c.fetchall()
                rows = rows[::-1]  # 反轉順序，最新的在最前面
                return [{'content': row[2], 'timestamp': row[3]} for row in rows]
        except sqlite3.Error as e:
            print(f"查詢頻道 {channel_id} 的記憶時發生錯誤: {e}")
            return None

    def get_channel(self, channel_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
                row = c.fetchone()
                if row:
                    return {
                        'channel_id': row[0],
                        'channel_name': row[1],
                        'note': row[2],
                        'server_id': row[3],
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢頻道 {channel_id} 時發生錯誤: {e}")
            return None

    def get_core_memories(self) -> Optional[list]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM core_memories ORDER BY id DESC LIMIT 10")
                rows = c.fetchall()
                rows = rows[::-1]  # 反轉順序，最新的在最前面
                return [{'content': row[1], 'timestamp': row[2]} for row in rows]
        except sqlite3.Error as e:
            print(f"查詢核心記憶時發生錯誤: {e}")
            return None

    def get_serverid_by_channel(self, channel_id: int) -> Optional[int]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT server_id FROM channels WHERE channel_id = ?", (channel_id,))
                row = c.fetchone()
                if row:
                    return row[0]
                return None
        except sqlite3.Error as e:
            print(f"查詢頻道 {channel_id} 的伺服器 ID 時發生錯誤: {e}")
            return None

    def get_user_and_memories(self, user_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = c.fetchone()
                memories = self.get_user_memories(user_id)
                if not memories:
                    memories = []
                if row:
                    return {
                        'user_id': row[0],
                        'user_name': row[1],
                        'nickname': row[2],
                        'birthday': row[3],
                        'note': row[4],
                        'memories': memories,
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢使用者 {user_id} 和記憶時發生錯誤: {e}")
            return None

    def get_channel_and_memories(self, channel_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM channels WHERE channel_id = ?", (channel_id,))
                row = c.fetchone()
                memories = self.get_channel_memories(channel_id)
                if not memories:
                    memories = []
                if row:
                    return {
                        'channel_id': row[0],
                        'channel_name': row[1],
                        'note': row[2],
                        'server_id': row[3],
                        'memories': memories,
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢頻道 {channel_id} 和記憶時發生錯誤: {e}")
            return None
    
    def get_server_and_memories(self, server_id: int) -> Optional[dict]:
        try:
            with self._connect() as conn:
                conn: sqlite3.Connection
                c = conn.cursor()
                c.execute("SELECT * FROM servers WHERE server_id = ?", (server_id,))
                row = c.fetchone()
                memories = self.get_server_memories(server_id)
                if not memories:
                    memories = []
                if row:
                    return {
                        'server_id': row[0],
                        'server_name': row[1],
                        'note': row[2],
                        'memories': memories,
                    }
                return None
        except sqlite3.Error as e:
            print(f"查詢伺服器 {server_id} 和記憶時發生錯誤: {e}")
            return None

    def get_users_memories_from_list(self, user_ids: list) -> list:
        if not user_ids:
            return []
        memories:list = []
        for id in user_ids:
            if not isinstance(id, int):
                raise ValueError(f"Invalid user_id: {id}. Must be an integer.")
            memories.append(f'{self.get_user(id)}memories: {self.get_user_memories(id)}')
        return memories

    def get_channels_memories_from_list(self, channel_ids: list) -> list:
        if not channel_ids:
            return []
        memories:list = []
        for id in channel_ids:
            if not isinstance(id, int):
                raise ValueError(f"Invalid channel_id: {id}. Must be an integer.")
            memories.append(f'{self.get_channel(id)}memories: {self.get_channel_memories(id)}')
        return memories
    
    def get_servers_list_from_channels_list(self, channel_ids: list) -> list:
        if not channel_ids:
            return []
        servers:list = []
        for id in channel_ids:
            if not isinstance(id, int):
                raise ValueError(f"Invalid channel_id: {id}. Must be an integer.")
            server_id = self.get_serverid_by_channel(id)
            if server_id is not None and server_id not in servers:
                servers.append(server_id)
        return servers
    
    def get_servers_memories_from_list(self, server_ids: list) -> list:
        if not server_ids:
            return []
        memories:list = []
        for id in server_ids:
            if not isinstance(id, int):
                raise ValueError(f"Invalid server_id: {id}. Must be an integer.")
            memories.append(f'{self.get_server(id)}memories: {self.get_server_memories(id)}')
        return memories

if __name__ == '__main__':

    db = DatabaseManager()

    # 範例：新增或更新一位使用者
    db.upsert_user(
        user_id=111111111111111112,
        user_name='TestUser',
        nickname='測試',
        birthday='2000-01-02',
        api_key='abcd1234'
    )
    db.upsert_user(
        user_id=111111111111111114,
        user_name='TestUser4',
        birthday='1/2',
    )
    db.upsert_server(
        server_id=111111111111111114,
        server_name='TestServer'
    )
    db.upsert_channel(
        channel_id=111111111111111114,
        channel_name='TestChannel',
        server_id=111111111111111114
    )
    db.add_channel_memory(
        channel_id=111111111111111114,
        content='這是頻道的記憶內容。'
    )

    # print(db.get_api_key(111111111111111112))
    # print(db.get_user(111111111111111114))
    # print(db.get_user_and_memories(111111111111111114))
    # print(db.get_channel(111111111111111114))
    # print(db.get_server(111111111111111114))
    user_ids = [111111111111111112, 111111111111111114]
    print(db.get_users_memories_from_list(user_ids))