"""
解忧树洞 - Vercel Serverless Functions 后端
使用 Neon PostgreSQL（免费云端数据库，数据永久保存）
"""
import os
import json
import secrets
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timezone, timedelta

# ==================== 配置 ====================
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
DATABASE_URL = os.environ.get('DATABASE_URL', '')  # Neon 连接串

TZ = timezone(timedelta(hours=8))  # 北京时间

# ==================== 数据库 ====================
def get_conn():
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL 未配置")
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    try:
        conn = get_conn()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                nickname TEXT NOT NULL,
                mood TEXT NOT NULL,
                text TEXT NOT NULL,
                time TEXT NOT NULL,
                create_time DOUBLE PRECISION NOT NULL,
                comfort TEXT,
                advice TEXT
            )
        ''')
        # 创建时间索引（加速排序查询）
        c.execute('CREATE INDEX IF NOT EXISTS idx_create_time ON messages (create_time DESC)')
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"init_db error: {e}")

# 应用启动时初始化
init_db()

# ==================== 工具 ====================
def now_str():
    now = datetime.now(TZ)
    return (f"{now.year}年{now.month}月{now.day}日 "
            f"{now.hour:02d}:{now.minute:02d}")

REPLY_SET = [
    {
        'comfort': '我完全能体会你此刻的心情，愿意坦诚倾诉就已经十分勇敢，不用强迫自己硬撑，负面情绪本就值得被接纳。',
        'advice': '如果心里压抑，试着给自己10分钟独处时间，深呼吸放空，不用立刻解决所有难题，允许当下的自己脆弱片刻。'
    },
    {
        'comfort': '抱抱你，积攒的委屈和疲惫终于有地方安放了，你已经独自扛了很久，真的辛苦了。',
        'advice': '睡前简单梳理情绪，写下一件今天让你稍微舒心的小事，平衡糟糕的感受，减少精神内耗。'
    },
    {
        'comfort': '不用觉得倾诉是麻烦，树洞会安静接住你所有杂乱的情绪，没有人会评判你的喜怒哀乐。',
        'advice': '情绪上头时不要做重大决定，暂时转移注意力，喝水、散步、听歌都能平缓紧绷的状态。'
    },
    {
        'comfort': '这段难熬的时光只是暂时的，坏情绪不会永远停留，你远比自己想象中更坚强。',
        'advice': '学会适度示弱，不必事事独自承担，寻找身边温和的人偶尔倾诉，不要把心事全部封闭在心底。'
    },
    {
        'comfort': '我明白心里沉甸甸的滋味，把话说出来之后，心里的重量会悄悄减轻不少。',
        'advice': '每天预留一小段只属于自己的时间，做纯粹放松、不带任何目的的小事，好好关照内心。'
    },
    {
        'comfort': '喜怒哀乐都是正常的，不必为低落、烦躁感到愧疚，好好善待当下情绪低落的自己。',
        'advice': '区分情绪和事实，不要被一时的坏感受定义全部生活，事情会随时间慢慢出现转机。'
    },
    {
        'comfort': '谢谢你愿意信任树洞，把藏在心底的话讲出来，往后会慢慢迎来轻松平和的日子。',
        'advice': '减少对完美的苛求，接纳自己的不完美，降低心理期待，会发现生活轻松许多。'
    },
]

# ==================== 工具函数 ====================
def make_response(code, data=None, msg=None):
    body = {'code': code}
    if data is not None:
        body['data'] = data
    if msg is not None:
        body['msg'] = msg
    return {
        'statusCode': 200 if code == 0 else (400 if code == 1 else 401),
        'headers': {
            'Content-Type': 'application/json; charset=utf-8',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type, X-Admin-Password',
            'Access-Control-Allow-Methods': 'GET, POST, DELETE, OPTIONS',
        },
        'body': json.dumps(body, ensure_ascii=False)
    }

def parse_body(event):
    try:
        return json.loads(event.get('body', '{}') or '{}')
    except:
        return {}

# ==================== 路由 ====================
def router(method, path, event):
    # OPTIONS 预检
    if method == 'OPTIONS':
        return make_response(0)

    # 获取留言列表
    if method == 'GET' and path == '/api/messages':
        try:
            conn = get_conn()
            c = conn.cursor(cursor_factory=RealDictCursor)
            c.execute('SELECT * FROM messages ORDER BY create_time DESC LIMIT 50')
            rows = c.fetchall()
            conn.close()
            # 转换 RealDictRow 为普通 dict
            result = []
            for r in rows:
                d = dict(r)
                # create_time 是 float，保持为 float 即可
                result.append(d)
            return make_response(0, data=result)
        except Exception as e:
            return make_response(1, msg=f'读取失败: {str(e)}')

    # 发送留言
    if method == 'POST' and path == '/api/messages':
        try:
            data = parse_body(event)
            nickname = (data.get('nickname') or '').strip()
            mood = (data.get('mood') or '').strip()
            text = (data.get('text') or '').strip()

            if not nickname:
                return make_response(1, msg='请先填写或生成一个匿名昵称')
            if not text:
                return make_response(1, msg='请写下你想倾诉的内容哦')
            if not mood:
                return make_response(1, msg='请先选择一个当下的心情')
            if len(text) < 2:
                return make_response(1, msg='多说一点吧，至少两个字 😊')
            if len(text) > 2000:
                return make_response(1, msg='内容太长啦，请精简到2000字以内')

            import random as rand_mod
            reply = rand_mod.choice(REPLY_SET)
            msg_id = secrets.token_hex(12)
            now_ts = datetime.now(TZ).timestamp()

            conn = get_conn()
            c = conn.cursor()
            c.execute(
                'INSERT INTO messages (id, nickname, mood, text, time, create_time, comfort, advice) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
                (msg_id, nickname, mood, text, now_str(), now_ts,
                 reply['comfort'], reply['advice'])
            )
            conn.commit()
            conn.close()
            return make_response(0, msg='✅ 你的心事已经放进解忧树洞啦！')
        except Exception as e:
            return make_response(1, msg=f'提交失败: {str(e)}')

    # 管理员获取留言
    if method == 'GET' and path == '/api/admin/messages':
        pwd = (event.get('headers', {}).get('x-admin-password', '') or
               event.get('queryStringParameters', {}).get('password', ''))
        if pwd != ADMIN_PASSWORD:
            return make_response(401, msg='密码错误，无权访问')
        try:
            conn = get_conn()
            c = conn.cursor(cursor_factory=RealDictCursor)
            c.execute('SELECT * FROM messages ORDER BY create_time DESC LIMIT 200')
            rows = c.fetchall()
            conn.close()
            result = [dict(r) for r in rows]
            return make_response(0, data=result)
        except Exception as e:
            return make_response(1, msg=f'读取失败: {str(e)}')

    # 管理员删除留言
    if method == 'DELETE' and path.startswith('/api/admin/messages/'):
        msg_id = path.split('/api/admin/messages/')[1]
        pwd = (event.get('headers', {}).get('x-admin-password', '') or
               (parse_body(event).get('password', '')))
        if pwd != ADMIN_PASSWORD:
            return make_response(401, msg='密码错误，无权删除')
        try:
            conn = get_conn()
            c = conn.cursor()
            c.execute('DELETE FROM messages WHERE id = %s', (msg_id,))
            conn.commit()
            deleted = c.rowcount
            conn.close()
            if deleted == 0:
                return make_response(1, msg='未找到该留言')
            return make_response(0, msg='✅ 已删除')
        except Exception as e:
            return make_response(1, msg=f'删除失败: {str(e)}')

    return make_response(1, msg='未知请求')


# ==================== Vercel Serverless Handler ====================
class Handler:
    """Vercel Python Runtime 要求的 handler 类"""
    pass


handler = Handler()

# Vercel 会调用 handler 的这两个方法之一
def __call__(self, event, context):
    method = (event.get('httpMethod') or event.get('method') or 'GET').upper()
    path = event.get('path') or event.get('rawPath') or '/'
    return router(method, path, event)

handler.__call__ = __call__
