"""
解忧树洞 - 后端服务（Neon PostgreSQL 版）
- 云端数据库存储留言，多设备共享
- 管理员密码保护后台
- 前后端一体化，直接返回 HTML
"""
import os
import json
import time
import secrets
import psycopg2
from datetime import datetime, timezone, timedelta
from flask import Flask, request, jsonify, Response
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ==================== 配置 ====================
ADMIN_PWD = os.environ.get('ADMIN_PASSWORD', 'admin123')
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://neondb_owner:npg_8jWxGPhOdU0M@ep-damp-hill-aykqd8bu.c-5.us-east-2.aws.neon.tech/neondb?sslmode=require')

# ==================== 数据库 ====================
def get_db():
    conn = psycopg2.connect(DATABASE_URL)
    return conn

def init_db():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('''
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
        cur.execute('CREATE INDEX IF NOT EXISTS idx_create_time ON messages (create_time DESC)')
        conn.commit()
        cur.close()
        conn.close()
        print('DB initialized')
    except Exception as e:
        print('DB init error:', e)

init_db()

# ==================== 工具 ====================
def now_str():
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    return f'{now.year}年{now.month}月{now.day}日 {now.hour:02d}:{now.minute:02d}'

REPLY_SET = [
    {'comfort': '我完全能体会你此刻的心情，愿意坦诚倾诉就已经十分勇敢，不用强迫自己硬撑，负面情绪本就值得被接纳。', 'advice': '如果心里压抑，试着给自己10分钟独处时间，深呼吸放空，不用立刻解决所有难题，允许当下的自己脆弱片刻。'},
    {'comfort': '抱抱你，积攒的委屈和疲惫终于有地方安放了，你已经独自扛了很久，真的辛苦了。', 'advice': '睡前简单梳理情绪，写下一件今天让你稍微舒心的小事，平衡糟糕的感受，减少精神内耗。'},
    {'comfort': '不用觉得倾诉是麻烦，树洞会安静接住你所有杂乱的情绪，没有人会评判你的喜怒哀乐。', 'advice': '情绪上头时不要做重大决定，暂时转移注意力，喝水、散步、听歌都能平缓紧绷的状态。'},
    {'comfort': '这段难熬的时光只是暂时的，坏情绪不会永远停留，你远比自己想象中更坚强。', 'advice': '学会适度示弱，不必事事独自承担，寻找身边温和的人偶尔倾诉，不要把心事全部封闭在心底。'},
    {'comfort': '我明白心里沉甸甸的滋味，把话说出来之后，心里的重量会悄悄减轻不少。', 'advice': '每天预留一小段只属于自己的时间，做纯粹放松、不带任何目的的小事，好好关照内心。'},
    {'comfort': '喜怒哀乐都是正常的，不必为低落、烦躁感到愧疚，好好善待当下情绪低落的自己。', 'advice': '区分情绪和事实，不要被一时的坏感受定义全部生活，事情会随时间慢慢出现转机。'},
    {'comfort': '谢谢你愿意信任树洞，把藏在心底的话讲出来，往后会慢慢迎来轻松平和的日子。', 'advice': '减少对完美的苛求，接纳自己的不完美，降低心理期待，会发现生活轻松许多。'},
]

import random

# ==================== 前端 HTML ====================
HTML_CONTENT = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>解忧树洞</title>
<style>
:root{--bg:#1a1a2e;--card:rgba(255,255,255,0.96);--primary:#6a5acd;--primary-light:#8b74d8;--gold:#ffd700;--text:#444;--text-light:#999;--danger:#ff6b6b;--shadow:0 10px 30px rgba(0,0,0,0.35);--radius:26px}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;min-height:100vh;background:radial-gradient(circle at 10% 10%,rgba(255,255,255,0.35) 0 8%,transparent 9%),radial-gradient(circle at 90% 18%,rgba(255,255,255,0.22) 0 6%,transparent 7%),linear-gradient(180deg,#1a1a2e 0%,#16213e 45%,#0f3460 70%,#e8d5ff 100%);padding:18px;animation:bgNight 12s ease-in-out infinite alternate;position:relative;overflow-x:hidden;color:var(--text);line-height:1.6}
@keyframes bgNight{0%{background:radial-gradient(circle at 10% 10%,rgba(255,255,255,0.35) 0 8%,transparent 9%),radial-gradient(circle at 90% 18%,rgba(255,255,255,0.22) 0 6%,transparent 7%),linear-gradient(180deg,#1a1a2e 0%,#16213e 45%,#0f3460 70%,#e8d5ff 100%)}50%{background:radial-gradient(circle at 15% 14%,rgba(255,255,255,0.4) 0 10%,transparent 11%),radial-gradient(circle at 85% 22%,rgba(255,255,255,0.28) 0 7%,transparent 8%),linear-gradient(180deg,#1e1e3f 0%,#1a2a4a 45%,#123a66 70%,#f0dcff 100%)}100%{background:radial-gradient(circle at 10% 10%,rgba(255,255,255,0.35) 0 8%,transparent 9%),radial-gradient(circle at 90% 18%,rgba(255,255,255,0.22) 0 6%,transparent 7%),linear-gradient(180deg,#1a1a2e 0%,#16213e 45%,#0f3460 70%,#e8d5ff 100%)}}
.star{position:absolute;width:2px;height:2px;background:#fff;border-radius:50%;animation:twinkle 3s ease-in-out infinite}
.star:nth-child(1){top:8%;left:12%;animation-delay:0s}.star:nth-child(2){top:12%;left:30%;animation-delay:.5s}.star:nth-child(3){top:6%;left:60%;animation-delay:1s}.star:nth-child(4){top:18%;left:80%;animation-delay:1.5s}.star:nth-child(5){top:22%;left:18%;animation-delay:2s}.star:nth-child(6){top:30%;left:50%;animation-delay:.8s}.star:nth-child(7){top:10%;left:75%;animation-delay:1.2s}.star:nth-child(8){top:25%;left:8%;animation-delay:1.8s}
@keyframes twinkle{0%,100%{opacity:.3}50%{opacity:1}}
.grass{position:fixed;bottom:0;left:0;width:100%;height:180px;background:linear-gradient(180deg,transparent 0%,#5a8f7b 30%,#3f6b58 100%);z-index:0;pointer-events:none}
.firefly{position:absolute;width:10px;height:10px;background:rgba(255,255,150,0.8);border-radius:50%;box-shadow:0 0 10px rgba(255,255,150,0.8);animation:firefly 8s ease-in-out infinite;z-index:1}
.firefly:nth-child(9){left:10%;bottom:120px;animation-delay:0s}.firefly:nth-child(10){left:30%;bottom:100px;animation-delay:2s}.firefly:nth-child(11){left:55%;bottom:130px;animation-delay:4s}.firefly:nth-child(12){left:80%;bottom:90px;animation-delay:6s}.firefly:nth-child(13){left:18%;bottom:140px;animation-delay:1s}.firefly:nth-child(14){left:42%;bottom:115px;animation-delay:2.7s}.firefly:nth-child(15){left:68%;bottom:132px;animation-delay:5s}.firefly:nth-child(16){left:88%;bottom:102px;animation-delay:7.3s}.firefly:nth-child(17){left:25%;bottom:90px;animation-delay:.4s}.firefly:nth-child(18){left:60%;bottom:142px;animation-delay:3.4s}.firefly:nth-child(19){left:5%;bottom:130px;animation-delay:1.5s}.firefly:nth-child(20){left:48%;bottom:95px;animation-delay:4.2s}.firefly:nth-child(21){left:75%;bottom:145px;animation-delay:6.2s}.firefly:nth-child(22){left:35%;bottom:122px;animation-delay:2.2s}.firefly:nth-child(23){left:92%;bottom:118px;animation-delay:7.8s}.firefly:nth-child(24){left:12%;bottom:98px;animation-delay:.7s}.firefly:nth-child(25){left:52%;bottom:138px;animation-delay:3.8s}.firefly:nth-child(26){left:82%;bottom:125px;animation-delay:6.6s}
@keyframes firefly{0%,100%{transform:translateY(0) translateX(0);opacity:.4}50%{transform:translateY(-30px) translateX(15px);opacity:1}}
.wrap{max-width:760px;margin:0 auto;position:relative;z-index:2;padding-bottom:40px}
.top-deco{text-align:center;margin-bottom:24px;padding-top:10px}
.tree{font-size:52px;animation:treeSway 6s ease-in-out infinite;filter:drop-shadow(0 0 12px rgba(255,255,200,0.6))}
@keyframes treeSway{0%,100%{transform:rotate(-2deg)}50%{transform:rotate(2deg)}}
h1{text-align:center;font-size:42px;color:#fffaf2;letter-spacing:6px;margin-bottom:8px;font-weight:800;animation:titleGlow 2.2s ease-in-out infinite alternate}
@keyframes titleGlow{from{text-shadow:0 0 8px #fff,0 0 15px #ffdd88,0 0 25px #ffc866,0 0 35px #ffbb44}to{text-shadow:0 0 12px #fff,0 0 25px #ffdd99,0 0 40px #ffcc77,0 0 55px #ffbf55}}
.subtitle{text-align:center;color:#d6c7ff;font-size:15px;line-height:1.6}
.divider{display:flex;justify-content:center;align-items:center;gap:10px;margin:24px 0}
.divider span{color:var(--gold);font-size:18px}
.divider-line{width:60px;height:2px;background:linear-gradient(90deg,transparent,rgba(255,215,0,0.6),transparent)}
.card{background:var(--card);border-radius:var(--radius);padding:24px;margin-bottom:18px;box-shadow:var(--shadow);border:1px solid rgba(255,255,255,0.8)}
.card-title{font-size:20px;color:var(--primary);margin-bottom:14px;display:flex;align-items:center;gap:8px}
.mood-list{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.mood-item{text-align:center;padding:10px 4px;background:#f7f3ff;border-radius:16px;cursor:pointer;border:2px solid transparent;transition:all .2s}
.mood-item:hover{transform:translateY(-3px);background:#e9ddff}
.mood-item.active{border-color:var(--primary);background:#e9ddff;box-shadow:0 0 0 4px rgba(106,90,205,0.15)}
.mood-item span{font-size:28px;display:block;margin-bottom:4px}
.mood-item p{font-size:12px;color:#555}
.nickname-box{display:flex;gap:10px;margin-bottom:16px}
.nickname-box input{flex:1;padding:12px 14px;border:1px solid #d6c7ff;border-radius:12px;background:#fcfbff;font-size:15px;color:var(--text);outline:none;font-family:inherit}
.nickname-box input:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(106,90,205,0.15)}
.nickname-box button{padding:12px 16px;border:none;border-radius:12px;background:var(--primary);color:#fff;font-size:14px;cursor:pointer;font-family:inherit;white-space:nowrap}
.nickname-box button:hover{background:var(--primary-light)}
textarea{width:100%;min-height:130px;border:1px solid #d6c7ff;border-radius:16px;padding:16px;font-size:15px;color:var(--text);outline:none;background:#fcfbff;transition:all .3s;resize:vertical;font-family:inherit;line-height:1.7}
textarea:focus{border-color:var(--primary);box-shadow:0 0 0 4px rgba(106,90,205,0.15)}
.submit-btn{width:100%;margin-top:16px;padding:15px;border:none;border-radius:16px;background:linear-gradient(90deg,var(--primary),var(--primary-light));color:#fff;font-size:17px;font-family:inherit;cursor:pointer;transition:all .3s}
.submit-btn:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(106,90,205,0.35)}
.submit-btn:disabled{opacity:.6;cursor:not-allowed;transform:none}
.game-area{margin-top:6px}
.game-status{display:flex;justify-content:space-between;margin-bottom:12px;font-size:16px;color:#555}
.hole-wrap{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:20px 0}
.hole{background:#b89676;height:90px;border-radius:50% 50% 35% 35%;position:relative;overflow:hidden}
.mole{position:absolute;bottom:-60px;left:50%;transform:translateX(-50%);font-size:48px;transition:bottom .2s ease;cursor:pointer;user-select:none}
.mole.show{bottom:5px}
.game-operate{text-align:center;margin-top:10px}
.game-operate button{padding:12px 28px;border:none;border-radius:12px;background:linear-gradient(90deg,var(--primary),var(--primary-light));color:#fff;font-size:16px;font-family:inherit;cursor:pointer}
.my-posts-header{font-size:16px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;justify-content:space-between}
.post-count-badge{background:#ede9ff;color:var(--primary);padding:3px 12px;border-radius:12px;font-size:13px;font-weight:600}
.post-card{background:#f7f3ff;border-radius:16px;padding:16px;margin-bottom:14px;border-left:4px solid var(--primary)}
.post-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.post-mood{font-size:26px}
.post-time{font-size:12px;color:var(--text-light)}
.post-nickname{font-size:13px;color:var(--primary);font-weight:600;margin-bottom:4px}
.post-content{color:var(--text);line-height:1.7;font-size:15px;white-space:pre-wrap;word-break:break-word;margin-bottom:8px}
.reply-box{background:#ede9ff;padding:12px;border-radius:12px;font-size:14px;color:#553c9a;line-height:1.6;margin-bottom:8px}
.suggestion-box{background:#fffaf2;padding:12px;border-radius:12px;font-size:14px;color:#b8860b;line-height:1.6;border-left:4px solid var(--gold)}
.empty-state{text-align:center;color:#aaa;padding:36px 0;font-size:15px}
.empty-state .icon{font-size:42px;margin-bottom:10px}
.footer{text-align:center;margin-top:30px;color:#d6c7ff;font-size:14px;line-height:1.7}
.admin-btn{position:fixed;right:18px;bottom:18px;width:56px;height:56px;border-radius:50%;background:linear-gradient(135deg,var(--primary),var(--primary-light));color:#fff;border:none;font-size:24px;cursor:pointer;box-shadow:0 4px 12px rgba(0,0,0,0.35);z-index:10;display:flex;align-items:center;justify-content:center}
.admin-btn:hover{transform:scale(1.05)}
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:80;align-items:flex-end;justify-content:center}
.modal-overlay.show{display:flex}
.modal-panel{background:#fffaf2;border-radius:24px 24px 0 0;width:100%;max-width:500px;max-height:80vh;overflow-y:auto;padding:24px 20px;box-shadow:0 10px 30px rgba(0,0,0,0.35)}
.modal-panel h3{color:var(--primary);font-size:20px;margin-bottom:12px}
.modal-panel p{color:#555;line-height:1.8;font-size:15px;margin-bottom:14px}
.modal-panel input{width:100%;padding:12px 14px;border:1px solid #d6c7ff;border-radius:12px;background:#fcfbff;font-size:15px;color:var(--text);outline:none;margin-bottom:12px;font-family:inherit}
.modal-panel input:focus{border-color:var(--primary)}
.modal-panel button{padding:12px 24px;border:none;border-radius:12px;background:linear-gradient(90deg,var(--primary),var(--primary-light));color:#fff;font-size:15px;cursor:pointer;margin:4px;font-family:inherit}
.modal-panel button:hover{transform:translateY(-1px);box-shadow:0 4px 12px rgba(106,90,205,0.3)}
.login-error{color:var(--danger);font-size:13px;margin-top:8px;text-align:center}
.stat-row{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin-bottom:14px}
.stat-card{background:#f8f9fa;border-radius:14px;padding:14px;text-align:center}
.stat-card .big{font-size:26px;font-weight:800;color:var(--primary)}
.stat-card .small{font-size:11px;color:var(--text-light);margin-top:2px}
.admin-post-card{background:#f7f3ff;border-radius:14px;padding:14px;margin-bottom:10px;border-left:4px solid var(--primary)}
.admin-post-card .post-text{font-size:14px;line-height:1.6;margin-bottom:6px;color:var(--text)}
.admin-post-card .meta{font-size:11px;color:var(--text-light);display:flex;gap:10px;flex-wrap:wrap}
.export-bar{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.export-btn{padding:8px 16px;border-radius:20px;border:none;font-size:13px;font-weight:600;cursor:pointer;font-family:inherit;background:var(--text);color:#fff}
.export-btn:hover{opacity:.85}
.delete-btn{padding:6px 14px;border:none;border-radius:8px;background:var(--danger);color:#fff;font-size:13px;cursor:pointer;font-family:inherit;margin-top:8px}
.delete-btn:hover{opacity:.85}
.logout-link{display:block;text-align:center;margin-top:14px;font-size:13px;color:var(--text-light);cursor:pointer;text-decoration:underline}
.toast{position:fixed;top:30px;left:50%;transform:translateX(-50%) translateY(-120px);background:rgba(0,0,0,0.85);color:#fff;padding:14px 28px;border-radius:14px;font-size:15px;z-index:999;transition:transform .3s cubic-bezier(0.34,1.56,0.64,1);box-shadow:0 8px 24px rgba(0,0,0,0.2);pointer-events:none}
.toast.show{transform:translateX(-50%) translateY(0)}
@media(max-width:480px){body{padding:12px}h1{font-size:32px}.mood-list{grid-template-columns:repeat(3,1fr)}.card{padding:16px}}
</style>
</head>
<body>
<div class="star"></div><div class="star"></div><div class="star"></div><div class="star"></div>
<div class="star"></div><div class="star"></div><div class="star"></div><div class="star"></div>
<div class="grass"></div>
<div class="firefly"></div><div class="firefly"></div><div class="firefly"></div><div class="firefly"></div>
<div class="firefly"></div><div class="firefly"></div><div class="firefly"></div><div class="firefly"></div>
<div class="firefly"></div><div class="firefly"></div><div class="firefly"></div><div class="firefly"></div>
<div class="firefly"></div><div class="firefly"></div><div class="firefly"></div><div class="firefly"></div>
<div class="firefly"></div><div class="firefly"></div><div class="firefly"></div><div class="firefly"></div>
<div class="wrap" id="app">
<div class="top-deco"><div class="tree">🌳</div></div>
<h1>解忧树洞</h1>
<p class="subtitle">夜色温柔，心事也可以轻轻安放。<br />把烦恼说出来，让树洞替你接住。</p>
<div class="divider"><div class="divider-line"></div><span>✨</span><div class="divider-line"></div></div>
<div class="card" id="miniGame">
<h2 class="card-title">🎮 即时解压 · 打地鼠</h2>
<p style="color:#666;margin-bottom:10px;font-size:14px;">压力无处释放？点击地鼠，把烦恼一起打掉！</p>
<div class="game-area">
<div class="game-status"><div>当前得分：<strong id="score">0</strong></div><div>剩余时间：<strong id="time">30</strong>s</div></div>
<div class="hole-wrap" id="holeWrap">
<div class="hole"><div class="mole">🐹</div></div><div class="hole"><div class="mole">🐹</div></div>
<div class="hole"><div class="mole">🐹</div></div><div class="hole"><div class="mole">🐹</div></div>
<div class="hole"><div class="mole">🐹</div></div><div class="hole"><div class="mole">🐹</div></div>
</div>
<div class="game-operate"><button onclick="startGame()">🎯 开启30秒解压对局</button></div>
</div>
</div>
<div class="card" id="newPost">
<h2 class="card-title">💌 写下你的烦恼</h2>
<p style="color:#666;margin-bottom:12px;font-size:14px;">选择你当下的心情：</p>
<div class="mood-list" id="moodSelector">
<div class="mood-item" data-mood="🤩"><span>🤩</span><p>兴奋</p></div><div class="mood-item" data-mood="😊"><span>😊</span><p>愉悦</p></div>
<div class="mood-item" data-mood="😌"><span>😌</span><p>平静</p></div><div class="mood-item" data-mood="😔"><span>😔</span><p>低落</p></div>
<div class="mood-item" data-mood="😢"><span>😢</span><p>难过</p></div><div class="mood-item" data-mood="🥺"><span>🥺</span><p>委屈</p></div>
<div class="mood-item" data-mood="😠"><span>😠</span><p>愤怒</p></div><div class="mood-item" data-mood="😩"><span>😩</span><p>疲惫</p></div>
<div class="mood-item" data-mood="😰"><span>😰</span><p>焦虑</p></div><div class="mood-item" data-mood="😱"><span>😱</span><p>慌张</p></div>
<div class="mood-item" data-mood="😒"><span>😒</span><p>无奈</p></div><div class="mood-item active" data-mood="🥱"><span>🥱</span><p>倦怠</p></div>
</div>
<p style="color:#666;margin:16px 0 8px;font-size:14px;">你的匿名昵称：</p>
<div class="nickname-box">
<input id="nickname" type="text" placeholder="点击随机生成，也可以自己改" />
<button onclick="generateNickname()">🎲 随机生成</button>
</div>
<textarea id="content" placeholder="在这里写下你想说的话... 也许是工作里的委屈，也许是生活中的小烦恼，也许只是想找一个安静的地方放空。写完这一页，就让烦恼暂时留在这里吧。" maxlength="2000"></textarea>
<button class="submit-btn" onclick="submitPost()">🌙 提交到解忧树洞</button>
</div>
<div class="card" id="myPostsCard">
<div class="my-posts-header"><span>🌙 大家的心事</span><span class="post-count-badge" id="myCount">0条</span></div>
<div id="myPostsContainer"></div>
<div class="empty-state" id="emptyState"><div class="icon">🌱</div><p>这里还没有留言，成为第一个把心事放进树洞的人吧。</p></div>
</div>
<div class="footer">愿你在这里得到片刻放松<br />解忧树洞 · 接住你的每一种情绪</div>
</div>
<button class="admin-btn" onclick="openAdmin()">🔐</button>
<div class="modal-overlay" id="adminModal"><div class="modal-panel" id="adminPanel"></div></div>
<div class="modal-overlay" id="gameModal"><div class="modal-panel" style="border-radius:24px;text-align:center;"><h3>🌟 你玩得太棒啦！</h3><p id="modalText">地鼠都被你打跑了，烦恼也一起被打掉啦。</p><button onclick="closeGameModal()">知道啦</button></div></div>
<div class="toast" id="toast"></div>
<script>
const ADMIN_PWD='admin123';
const funnyNames=['下班第一名','奶茶续命选手','今天也不想上班','情绪偷偷藏好了','树洞特派员','烦恼粉碎机','快乐失踪人口','压力山大人','只想躺着放空','今天也很努力','委屈但不说','愤怒的小云朵','疲惫小星星','焦虑收藏家','无奈体验官','打工人代言人','摸鱼冠军候选人','情绪管理员','深夜思考选手','温柔吐槽家'];
let currentMood='🥱',adminPasswordCache='',adminLoggedIn=false,adminPostsCache=[];
function init(){if(!document.getElementById('nickname').value)generateNickname();document.getElementById('moodSelector').addEventListener('click',function(e){const item=e.target.closest('.mood-item');if(!item)return;this.querySelectorAll('.mood-item').forEach(i=>i.classList.remove('active'));item.classList.add('active');currentMood=item.dataset.mood});document.getElementById('content').addEventListener('keydown',function(e){if((e.ctrlKey||e.metaKey)&&e.key==='Enter')submitPost()});document.getElementById('adminModal').addEventListener('click',function(e){if(e.target===this)closeAdmin()});document.getElementById('gameModal').addEventListener('click',function(e){if(e.target===this)closeGameModal()});loadPosts()}
async function loadPosts(){const c=document.getElementById('myPostsContainer'),e=document.getElementById('emptyState');c.innerHTML='<div class="empty-state"><p>⏳ 加载中...</p></div>';try{const r=await fetch('/api/messages'),d=await r.json();if(d.code!==0)throw new Error(d.msg);const l=d.data||[];document.getElementById('myCount').textContent=l.length+'条';if(l.length===0){c.innerHTML='';e.style.display='block'}else{e.style.display='none';c.innerHTML=l.map(p=>`<div class="post-card"><div class="post-header"><div class="post-mood">${p.mood}</div><div class="post-time">${p.time||''}</div></div><div class="post-nickname">🎭 ${escapeHtml(p.nickname)}</div><div class="post-content">${escapeHtml(p.text)}</div><div class="reply-box">💛 树洞暖心安慰：${escapeHtml(p.comfort||'愿你被温柔对待')}</div><div class="suggestion-box">💡 情绪疏导小建议：${escapeHtml(p.advice||'好好照顾自己')}</div></div>`).join('')}}catch(err){console.error(err);c.innerHTML='<div class="empty-state"><p>⚠️ 连接服务器失败，请刷新重试</p></div>'}}
async function submitPost(){const content=document.getElementById('content').value.trim(),nickname=document.getElementById('nickname').value.trim();if(!nickname){showToast('😅 请先填写或生成一个匿名昵称');return}if(!content){showToast('😅 写点什么再提交吧~');return}if(content.length<2){showToast('😅 多说一点吧，至少两个字~');return}const btn=document.querySelector('.submit-btn');btn.disabled=true;btn.textContent='⏳ 提交中...';try{const r=await fetch('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({nickname,mood:currentMood,text:content})}),d=await r.json();if(d.code!==0){showToast('❌ '+(d.msg||'提交失败'));return}document.getElementById('content').value='';showToast('✅ 你的心事已经放进解忧树洞啦！');await loadPosts()}catch(err){showToast('❌ 网络异常')}finally{btn.disabled=false;btn.textContent='🌙 提交到解忧树洞'}}
function openAdmin(){document.getElementById('adminModal').classList.add('show');renderAdminPanel()}
function closeAdmin(){document.getElementById('adminModal').classList.remove('show')}
function renderAdminPanel(){const p=document.getElementById('adminPanel');if(!adminLoggedIn){p.innerHTML=`<h3>🔐 管理员登录</h3><p>请输入管理员密码进入后台，查看所有留言并管理不当内容。</p><input type="password" id="adminPwd" placeholder="输入密码" autocomplete="off"><div style="text-align:center;"><button onclick="adminLogin()">确认进入</button><button onclick="closeAdmin()" style="background:#999;">取消</button></div><div class="login-error" id="loginError"></div>`}else{renderDashboard()}}
async function adminLogin(){const pwd=document.getElementById('adminPwd').value;try{const r=await fetch('/api/admin/messages',{headers:{'X-Admin-Password':pwd}}),d=await r.json();if(d.code!==0){document.getElementById('loginError').textContent='❌ 密码错误，请重试';return}adminLoggedIn=true;adminPasswordCache=pwd;adminPostsCache=d.data||[];renderDashboard()}catch(err){document.getElementById('loginError').textContent='❌ 网络异常'}}
function renderDashboard(){const p=document.getElementById('adminPanel'),posts=adminPostsCache,moodDist={};posts.forEach(x=>{moodDist[x.mood]=(moodDist[x.mood]||0)+1});p.innerHTML=`<h3>🗂️ 树洞后台管理</h3><p>所有留言（云端数据库，多设备共享）</p><div class="stat-row"><div class="stat-card"><div class="big">${posts.length}</div><div class="small">总留言数</div></div><div class="stat-card"><div class="big">${Object.keys(moodDist).length}</div><div class="small">情绪种类</div></div></div><div style="margin-bottom:14px;"><strong style="font-size:13px;">情绪分布</strong><div style="display:flex;gap:6px;margin-top:6px;flex-wrap:wrap;">${Object.entries(moodDist).sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<span style="background:#f0f0f0;padding:4px 10px;border-radius:12px;font-size:12px;">${k} ×${v}</span>`).join('')}</div></div><div class="export-bar"><button class="export-btn" onclick="exportAll()">📥 导出CSV</button></div><div id="adminPostList">${renderAdminPosts()}</div><div class="logout-link" onclick="logoutAdmin()">退出管理后台</div>`}
function renderAdminPosts(){const list=[...adminPostsCache].reverse();if(list.length===0)return'<div class="empty-state"><p>暂无留言</p></div>';return list.map(p=>`<div class="admin-post-card"><div class="post-text">${escapeHtml(p.text)}</div><div class="meta"><span>${p.mood}</span><span>🎭 ${escapeHtml(p.nickname)}</span><span>${p.time||''}</span></div><button class="delete-btn" onclick="deletePost('${p.id}')">🗑️ 删除这条</button></div>`).join('')}
async function deletePost(id){if(!confirm('确定删除？'))return;try{const r=await fetch('/api/admin/messages/'+encodeURIComponent(id),{method:'DELETE',headers:{'X-Admin-Password':adminPasswordCache}}),d=await r.json();if(d.code!==0){showToast('❌ 删除失败');return}showToast('✅ 已删除');adminPostsCache=adminPostsCache.filter(p=>p.id!==id);renderDashboard();await loadPosts()}catch(err){showToast('❌ 网络异常')}}
function logoutAdmin(){adminLoggedIn=false;adminPostsCache=[];renderAdminPanel()}
function exportAll(){if(adminPostsCache.length===0){showToast('📭 暂无数据');return}const csv=['时间,匿名昵称,情绪,内容,树洞安慰,疏导建议',...adminPostsCache.map(p=>`"${p.time||''}","${p.nickname}","${p.mood}","${(p.text||'').replace(/"/g,'""')}","${(p.comfort||'').replace(/"/g,'""')}","${(p.advice||'').replace(/"/g,'""')}"`)].join('\\n');const blob=new Blob(['\\uFEFF'+csv],{type:'text/csv;charset=utf-8'});const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`解忧树洞_${new Date().toISOString().slice(0,10)}.csv`;a.click();URL.revokeObjectURL(a.href);showToast('📥 已导出')}
let gameScore=0,gameTime=30,gameTimer=null,moleTimer=null,gameRunning=false;const holes=document.querySelectorAll('.mole'),scoreDom=document.getElementById('score'),timeDom=document.getElementById('time'),gameModalEl=document.getElementById('gameModal'),modalTextEl=document.getElementById('modalText');
holes.forEach(m=>{m.addEventListener('click',function(){if(!gameRunning)return;if(this.classList.contains('show')){gameScore++;scoreDom.textContent=gameScore;this.classList.remove('show')}})});
function showRandomMole(){holes.forEach(m=>m.classList.remove('show'));const r=Math.floor(Math.random()*holes.length);holes[r].classList.add('show');setTimeout(()=>{holes[r].classList.remove('show')},650)}
function startGame(){if(gameRunning)return;gameScore=0;gameTime=30;gameRunning=true;scoreDom.textContent=gameScore;timeDom.textContent=gameTime;clearInterval(gameTimer);clearInterval(moleTimer);gameTimer=setInterval(()=>{gameTime--;timeDom.textContent=gameTime;if(gameTime<=0){clearInterval(gameTimer);clearInterval(moleTimer);gameRunning=false;holes.forEach(m=>m.classList.remove('show'));modalTextEl.innerHTML='🌟 你玩得太棒啦！<br/><br/>本次得分：<strong>'+gameScore+' 分</strong><br/><br/>地鼠都被你打跑了，烦恼也一起被打掉啦。';gameModalEl.classList.add('show')}},1000);moleTimer=setInterval(showRandomMole,800);showRandomMole()}
function closeGameModal(){gameModalEl.classList.remove('show')}
function generateNickname(){document.getElementById('nickname').value=funnyNames[Math.floor(Math.random()*funnyNames.length)]}
function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML}
function showToast(msg){const t=document.getElementById('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),2200)}
init();
</script>
</body>
</html>'''

# ==================== 路由 ====================
@app.route('/')
def index():
    return Response(HTML_CONTENT, mimetype='text/html; charset=utf-8')

@app.route('/api/messages', methods=['GET'])
def get_messages():
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, nickname, mood, text, time, comfort, advice FROM messages ORDER BY create_time DESC LIMIT 100')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        data = [{'id': r[0], 'nickname': r[1], 'mood': r[2], 'text': r[3], 'time': r[4], 'comfort': r[5], 'advice': r[6]} for r in rows]
        return jsonify({'code': 0, 'data': data})
    except Exception as e:
        return jsonify({'code': 1, 'msg': '读取失败: ' + str(e)}), 500

@app.route('/api/messages', methods=['POST'])
def post_message():
    try:
        body = request.get_json() or {}
        nickname = (body.get('nickname') or '').strip()
        mood = (body.get('mood') or '').strip()
        text = (body.get('text') or '').strip()

        if not nickname:
            return jsonify({'code': 1, 'msg': '请填写昵称'}), 400
        if not text:
            return jsonify({'code': 1, 'msg': '请填写内容'}), 400
        if not mood:
            return jsonify({'code': 1, 'msg': '请选择心情'}), 400
        if len(text) < 2:
            return jsonify({'code': 1, 'msg': '多说一点吧，至少两个字 😊'}), 400
        if len(text) > 2000:
            return jsonify({'code': 1, 'msg': '内容太长啦，请精简到2000字以内'}), 400

        reply = random.choice(REPLY_SET)
        msg_id = secrets.token_hex(12)
        now_ts = time.time()

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            'INSERT INTO messages (id, nickname, mood, text, time, create_time, comfort, advice) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
            (msg_id, nickname, mood, text, now_str(), now_ts, reply['comfort'], reply['advice'])
        )
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({'code': 0, 'msg': '✅ 提交成功！'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': '提交失败: ' + str(e)}), 500

@app.route('/api/admin/messages', methods=['GET'])
def admin_get_messages():
    pwd = request.headers.get('X-Admin-Password', '') or request.args.get('password', '')
    if pwd != ADMIN_PWD:
        return jsonify({'code': 1, 'msg': '密码错误，无权访问'}), 401
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SELECT id, nickname, mood, text, time, comfort, advice FROM messages ORDER BY create_time DESC LIMIT 200')
        rows = cur.fetchall()
        cur.close()
        conn.close()
        data = [{'id': r[0], 'nickname': r[1], 'mood': r[2], 'text': r[3], 'time': r[4], 'comfort': r[5], 'advice': r[6]} for r in rows]
        return jsonify({'code': 0, 'data': data})
    except Exception as e:
        return jsonify({'code': 1, 'msg': '读取失败: ' + str(e)}), 500

@app.route('/api/admin/messages/<path:msg_id>', methods=['DELETE'])
def admin_delete_message(msg_id):
    pwd = request.headers.get('X-Admin-Password', '')
    if pwd != ADMIN_PWD:
        return jsonify({'code': 1, 'msg': '密码错误，无权删除'}), 401
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute('DELETE FROM messages WHERE id = %s', (msg_id,))
        conn.commit()
        deleted = cur.rowcount
        cur.close()
        conn.close()
        if deleted == 0:
            return jsonify({'code': 1, 'msg': '未找到该留言'}), 404
        return jsonify({'code': 0, 'msg': '✅ 已删除'})
    except Exception as e:
        return jsonify({'code': 1, 'msg': '删除失败: ' + str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
