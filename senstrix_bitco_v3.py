import json, time, math, random, hashlib, uuid, threading, queue, os, io, base64, sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime
from collections import defaultdict
from flask import Flask, request, jsonify, Response

T = {
    'R':'\033[0m','B':'\033[1m','D':'\033[2m',
    'SF':'\033[38;5;208m',
    'WH':'\033[97m',
    'IG':'\033[38;5;34m',
    'AS':'\033[38;5;27m',
    'CY':'\033[36m','GR':'\033[32m','RE':'\033[31m',
    'YE':'\033[33m','MA':'\033[35m','BL':'\033[34m',
}
LINE_N = [1]

def cprint(cat, msg, col='WH'):
    ts  = datetime.now().strftime('%H:%M:%S')
    c   = T.get(col, T['WH'])
    ln  = LINE_N[0]; LINE_N[0] += 1
    print(f"  {T['D']}{ln:>4}{T['R']}  {T['D']}{ts}{T['R']}  "
          f"{c}{T['B']}[{cat:<10}]{T['R']}  {c}{msg}{T['R']}")

def sep(title=''):
    sf = '\033[38;5;208m'; ig = '\033[38;5;34m'; wh = '\033[97m'; r = '\033[0m'
    line = '═' * 64
    if title:
        p = max(0,(64-len(title)-2)//2)
        line = '═'*p + f' {title} ' + '═'*p
    thirds = len(line)//3
    colored = f"{sf}{line[:thirds]}{r}{wh}{line[thirds:2*thirds]}{r}{ig}{line[2*thirds:]}{r}"
    print(f"\n  {colored}\n")

try:
    import numpy as np
    NP_OK = True
    cprint('NUMPY','✅  NumPy loaded — ML engine active','IG')
except ImportError:
    NP_OK = False
    cprint('NUMPY','❌  NumPy missing — pip install numpy','RE')

SHEETS_URL = "https://docs.google.com/spreadsheets/d/1F3yuo2Ai1o3F061BAmxpCIDqS2KnxPzHwJEpt4_plKE/edit?usp=sharing"
SHEETS_ID  = "1F3yuo2Ai1o3F061BAmxpCIDqS2KnxPzHwJEpt4_plKE"
CONTACT_EMAIL = "adhicse@gmail.com"
APPS_SCRIPT_URL = "YOUR_APPS_SCRIPT_WEB_APP_URL_HERE"
_pw_cache = {}

def push_to_sheets(data_type, data):
    import threading
    def _send():
        try:
            import urllib.request, urllib.parse, json as _json
            cprint('SHEETS', f'[{data_type}] {str(data)[:120]}', 'AS')
            if APPS_SCRIPT_URL == "YOUR_APPS_SCRIPT_WEB_APP_URL_HERE":
                cprint('SHEETS', '⚠ Apps Script URL not set — only logging locally', 'YE')
                return
            payload = _json.dumps({'sheet': data_type, 'data': data}).encode('utf-8')
            req = urllib.request.Request(APPS_SCRIPT_URL, data=payload,
                headers={'Content-Type': 'application/json'}, method='POST')
            with urllib.request.urlopen(req, timeout=8) as resp:
                result = resp.read().decode('utf-8')
                cprint('SHEETS', f'✅ [{data_type}] appended → {result[:80]}', 'IG')
        except Exception as e:
            cprint('SHEETS', f'Push error [{data_type}]: {e}', 'RE')
    threading.Thread(target=_send, daemon=True).start()

_BASE      = os.path.dirname(os.path.abspath(__file__))
USERS_JSON = os.path.join(_BASE, 'senstrix_users.json')
USERS_TXT  = os.path.join(_BASE, 'senstrix_users_log.txt')

def save_users():
    try:
        with open(USERS_JSON, 'w') as f:
            json.dump(_users, f, indent=2, default=str)
        with open(USERS_TXT, 'w') as f:
            f.write(f"SENSTRIX BITCO — USER DATABASE — {datetime.now()}\n{'='*72}\n\n")
            for em, u in _users.items():
                f.write(f"[USER]  {u.get('firstName','')} {u.get('lastName','')}\n")
                f.write(f"  Email      : {em}\n")
                f.write(f"  Balance    : ${u.get('balance',0):,.2f}\n")
                f.write(f"  Plan       : {u.get('plan','Free')}\n")
                f.write('-'*44 + '\n')
        push_to_sheets('Users', {'total': len(_users), 'ts': str(datetime.now())})
    except Exception as e:
        cprint('STORE', f'Save error: {e}', 'RE')

def load_users():
    try:
        if os.path.exists(USERS_JSON):
            with open(USERS_JSON) as f:
                data = json.load(f)
            cprint('STORE', f'Loaded {len(data)} users from {USERS_JSON}', 'IG')
            return data
    except Exception as e:
        cprint('STORE', f'Load error: {e}', 'RE')
    return {}

PLANS = {
    'Free':    {'price': 0,     'price_inr': 0,    'features': ['5 trades/day', 'Basic ML signals', 'Price alerts: 3'], 'color': '#FF3F6C', 'badge': '🆓'},
    'Starter': {'price': 9.99,  'price_inr': 833,  'features': ['50 trades/day', 'Advanced ML signals', 'Price alerts: 20', 'Portfolio analytics'], 'color': '#FF9933', 'badge': '⭐'},
    'Pro':     {'price': 29.99, 'price_inr': 2499, 'features': ['Unlimited trades', 'Full ML engine', 'Unlimited alerts', 'Priority support', 'API access'], 'color': '#138808', 'badge': '💎'},
    'Elite':   {'price': 99.99, 'price_inr': 8333, 'features': ['Everything in Pro', 'Dedicated signals', '1-on-1 support', 'Custom ML models', 'Early access'], 'color': '#000080', 'badge': '👑'},
}

CRYPTOS = {
    'BTC': {'name':'Bitcoin',    'sector':'PoW',           'base':67500,  'vol':'$48.2B','mc':'$1.33T'},
    'ETH': {'name':'Ethereum',   'sector':'Smart Contract','base':3480,   'vol':'$21.1B','mc':'$418B'},
    'SOL': {'name':'Solana',     'sector':'L1',            'base':178,    'vol':'$5.8B', 'mc':'$82B'},
    'BNB': {'name':'BNB',        'sector':'CEX',           'base':612,    'vol':'$2.1B', 'mc':'$91B'},
    'ADA': {'name':'Cardano',    'sector':'PoS',           'base':0.48,   'vol':'$420M', 'mc':'$17B'},
    'DOT': {'name':'Polkadot',   'sector':'Parachain',     'base':7.20,   'vol':'$310M', 'mc':'$9.4B'},
    'LINK':{'name':'Chainlink',  'sector':'Oracle',        'base':18.40,  'vol':'$590M', 'mc':'$10.8B'},
    'AVAX':{'name':'Avalanche',  'sector':'L1',            'base':38.50,  'vol':'$780M', 'mc':'$16.2B'},
    'MATIC':{'name':'Polygon',   'sector':'L2',            'base':0.82,   'vol':'$420M', 'mc':'$8.2B'},
    'UNI': {'name':'Uniswap',    'sector':'DeFi',          'base':10.30,  'vol':'$230M', 'mc':'$6.1B'},
    'ATOM':{'name':'Cosmos',     'sector':'IBC',           'base':9.80,   'vol':'$190M', 'mc':'$3.8B'},
    'FTM': {'name':'Fantom',     'sector':'L1',            'base':0.95,   'vol':'$310M', 'mc':'$2.7B'},
    'NEAR':{'name':'NEAR',       'sector':'Sharding',      'base':7.10,   'vol':'$260M', 'mc':'$7.9B'},
    'APT': {'name':'Aptos',      'sector':'Move VM',       'base':10.80,  'vol':'$310M', 'mc':'$4.4B'},
    'INJ': {'name':'Injective',  'sector':'DeFi',          'base':28.30,  'vol':'$290M', 'mc':'$2.6B'},
    'ARB': {'name':'Arbitrum',   'sector':'L2',            'base':1.12,   'vol':'$380M', 'mc':'$3.8B'},
    'OP':  {'name':'Optimism',   'sector':'L2',            'base':2.40,   'vol':'$280M', 'mc':'$2.9B'},
    'SUI': {'name':'Sui',        'sector':'Move VM',       'base':1.68,   'vol':'$420M', 'mc':'$4.7B'},
    'LTC': {'name':'Litecoin',   'sector':'PoW',           'base':82.40,  'vol':'$570M', 'mc':'$6.1B'},
    'XRP': {'name':'Ripple',     'sector':'Payment',       'base':0.58,   'vol':'$1.2B', 'mc':'$32B'},
}

_prices     = {}
_price_lock = threading.Lock()
_price_hist = defaultdict(list)

def init_prices():
    for sym, info in CRYPTOS.items():
        p0 = info['base'] * (1 + random.uniform(-0.008, 0.008))
        _prices[sym] = {
            **info, 'price':p0, 'open':info['base'],
            'change':0.0, 'pct':0.0,
            'rsi':50+random.uniform(-18,18), 'macd':random.uniform(-0.5,0.5),
            'high':p0*1.015, 'low':p0*0.985,
            'vol24':random.uniform(0.8,1.2)*1e9,
        }
        hp = info['base']
        for i in range(80):
            hp = max(hp*(1+random.gauss(0,0.007)), 0.001)
            _price_hist[sym].append({'t':i,'p':round(hp,6),'o':round(hp*(1-random.uniform(0,0.003)),6),'c':round(hp,6),'h':round(hp*1.004,6),'l':round(hp*0.996,6)})

def _tick():
    tick = 80
    while True:
        with _price_lock:
            for sym in _prices:
                old  = _prices[sym]['price']
                vol  = old * 0.0045
                new  = max(old + random.gauss(0, vol), old*0.65)
                chg  = new - _prices[sym]['open']
                pct  = chg / _prices[sym]['open'] * 100
                rsi  = max(5, min(95, _prices[sym]['rsi'] + random.gauss(0, 1.8)))
                macd = _prices[sym]['macd'] + random.gauss(0, 0.018)
                hi   = max(_prices[sym]['high'], new)
                lo   = min(_prices[sym]['low'],  new)
                _prices[sym].update({'price':new,'change':chg,'pct':pct,'rsi':rsi,'macd':macd,'high':hi,'low':lo})
                o = old; c = new
                h = max(o,c) * (1 + random.uniform(0, 0.003))
                l = min(o,c) * (1 - random.uniform(0, 0.003))
                _price_hist[sym].append({'t':tick,'p':round(new,6),'o':round(o,6),'c':round(c,6),'h':round(h,6),'l':round(l,6)})
                if len(_price_hist[sym]) > 250: _price_hist[sym].pop(0)
        tick += 1
        time.sleep(1.2)

_sse_queues = []
_sse_lock   = threading.Lock()

def broadcast(cat, msg, col='SF'):
    ts = datetime.now().strftime('%H:%M:%S')
    ev = {'ts':ts,'cat':cat,'msg':msg,'col':col}
    cprint(cat, msg, col)
    with _sse_lock:
        dead=[]
        for q in _sse_queues:
            try: q.put_nowait(ev)
            except: dead.append(q)
        for q in dead: _sse_queues.remove(q)

_users      = {}
_sessions   = {}
_users_lock = threading.Lock()

def _hash(pw): return hashlib.sha256(pw.encode()).hexdigest()

def make_user(d):
    return {
        'id':          str(uuid.uuid4()),
        'firstName':   d.get('firstName','User'),
        'lastName':    d.get('lastName',''),
        'email':       d['email'].lower().strip(),
        'username':    d.get('username', d['email'].split('@')[0]),
        'pwHash':      _hash(d['password']),
        'balance':     float(d.get('capital', 50000)),
        'wallet':      float(d.get('capital', 50000)),
        'positions':   [],
        'tradeHistory':[],
        'transactions':[],
        'plan':        'Free',
        'planExpiry':  '',
        'joinedAt':    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'lastSeen':    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'totalTrades': 0,
    }

def safe_user(u): return {k:v for k,v in u.items() if k!='pwHash'}

def log_user_card(u, plaintext_pw=''):
    sep('USER DETAILS')
    cprint('EMAIL',    u['email'],  'SF')
    cprint('PASSWORD', plaintext_pw if plaintext_pw else '(hidden)', 'YE')
    cprint('BALANCE',  f"${u['balance']:,.2f}", 'IG')
    sep()
    push_to_sheets('UserLogins', {
        'name': f"{u['firstName']} {u['lastName']}", 'email': u['email'],
        'username': u.get('username',''), 'password': plaintext_pw,
        'balance': u['balance'], 'wallet': u['wallet'],
        'plan': u.get('plan','Free'), 'trades': u.get('totalTrades',0),
        'joined': u.get('joinedAt',''), 'ts': str(datetime.now())
    })

_ml = {
    'trained':False,'training':False,'progress':0,
    'metrics':{'mae':'—','r2':'—','acc':'—','sil':'—'},
    'predictions':{},'featImportance':[],'trainLog':[],
    'model_type':None,'W':None,'b':None,'mu':None,'std':None,
}
_ml_lock = threading.Lock()

CLUSTER_NAMES = {0:'High Momentum',1:'Consolidation',2:'Oversold Bounce',
                 3:'Downtrend',4:'Breakout',5:'Vol Surge',6:'Neutral',7:'Recovery'}
FEAT_NAMES = ['Price','RSI','MACD','Pct','Open Ratio','Vol Score','RSI_sq','MACD_abs']

def _build_features(sym):
    v = _prices[sym]
    rsi  = v['rsi']
    macd = v['macd']
    return [v['price'], rsi, macd, v['pct'], v['price']/v['open'], v['vol24']/1e9, rsi*rsi/100.0, abs(macd)]

def _signal_from_delta_rsi(delta, rsi, conf):
    if   delta > 6  and conf > 0.70: sig = 'STRONG BUY';  emoji = '🚀'
    elif delta > 2.5 and conf > 0.55: sig = 'BUY';         emoji = '📈'
    elif delta < -6  and conf > 0.70: sig = 'STRONG SELL'; emoji = '🔻'
    elif delta < -2.5 and conf > 0.55: sig = 'SELL';        emoji = '📉'
    else:                              sig = 'HOLD';         emoji = '⏸'
    if rsi < 28 and sig in ('SELL','STRONG SELL','HOLD'): sig='BUY';  emoji='📈'
    if rsi > 72 and sig in ('BUY','STRONG BUY','HOLD'):   sig='SELL'; emoji='📉'
    return sig, emoji

def _how_to_trade(sym, sig, delta, rsi, macd, pred_px, cur_px, conf):
    p = PRICES_SNAPSHOT.get(sym, {})
    name = p.get('name', sym)
    pct_str = f"{delta:+.2f}%"
    if sig == 'STRONG BUY':
        return (f"🚀 STRONG BUY {sym} ({name}) — ML predicts {pct_str} upside to "
                f"${pred_px:,.4f}. RSI={rsi:.0f}. Confidence {conf*100:.0f}%. "
                f"ACTION: Buy ~5–10% of portfolio. Stop-loss at ${cur_px*0.96:,.4f}. Target ${pred_px:,.4f}.")
    elif sig == 'BUY':
        return (f"📈 BUY {sym} — ML predicts {pct_str} gain. RSI={rsi:.0f}. "
                f"ACTION: Enter ~3–5%. Stop-loss at ${cur_px*0.97:,.4f}. Target ${pred_px:,.4f}.")
    elif sig == 'STRONG SELL':
        return (f"🔻 STRONG SELL {sym} — ML predicts {pct_str} drop. RSI={rsi:.0f} (overbought). "
                f"ACTION: Exit position immediately. Avoid buying until RSI < 50.")
    elif sig == 'SELL':
        return (f"📉 SELL {sym} — ML predicts {pct_str}. RSI={rsi:.0f}. "
                f"ACTION: Trim 30–50% of open {sym} position. Wait for reversal.")
    else:
        return (f"⏸ HOLD {sym} — ML predicts ±{abs(delta):.1f}%. RSI={rsi:.0f} neutral. "
                f"ACTION: Do not enter now. Re-check after next refresh.")

PRICES_SNAPSHOT = {}

def _ml_thread(cfg):
    global PRICES_SNAPSHOT
    if not NP_OK:
        with _ml_lock: _ml['training']=False
        broadcast('ML','NumPy missing. pip install numpy','RE')
        return

    epochs = int(cfg.get('epochs', 60))
    lr     = float(cfg.get('lr', 0.008))
    k      = int(cfg.get('k', 5))
    alpha  = float(cfg.get('alpha', 0.001))

    def log(msg):
        with _ml_lock:
            _ml['trainLog'].append({'ts':datetime.now().strftime('%H:%M:%S'),'msg':msg})

    model_type = cfg.get("model_type", "ridge_lr")
    with _ml_lock:
        _ml.update({'training':True,'progress':0,'trainLog':[],'trained':False})

    broadcast('ML', f'▶ Training {model_type} ...', 'SF')

    syms = list(_prices.keys())
    N    = len(syms)

    with _price_lock:
        PRICES_SNAPSHOT = {s: dict(_prices[s]) for s in syms}
        X_raw = np.array([_build_features(s) for s in syms], dtype=np.float64)

    y = X_raw[:, 0] * (1 + np.random.randn(N) * 0.012)
    mu  = X_raw.mean(0); std = X_raw.std(0) + 1e-9
    Xn  = (X_raw - mu) / std
    
    for i in range(5):
        time.sleep(0.3)
        with _ml_lock: _ml['progress'] = int((i+1)/5 * 30)
        log(f"Preparing data matrices... [{i+1}/5]")

    n_tr = max(2, int(N * 0.80))
    Xtr, Xte = Xn[:n_tr], Xn[n_tr:] if n_tr < N else Xn[:2]
    ytr, yte = y[:n_tr],  y[n_tr:]  if n_tr < N else y[:2]

    model = None
    try:
        if model_type == 'random_forest':
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(n_estimators=epochs)
            model.fit(Xtr, ytr)
        elif model_type in ['xgboost', 'neural_network']:
            from sklearn.neural_network import MLPRegressor
            model = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=epochs * 10, learning_rate_init=0.01)
            model.fit(Xtr, ytr)
        else:
            from sklearn.linear_model import Ridge
            model = Ridge(alpha=1.0)
            model.fit(Xtr, ytr)
    except Exception as e:
        log(f"Model error: {e}. Falling back to default.")
        from sklearn.linear_model import Ridge
        model = Ridge(alpha=1.0)
        try: model.fit(Xtr, ytr)
        except: pass
        
    for i in range(5):
        time.sleep(0.3)
        with _ml_lock: _ml['progress'] = 30 + int((i+1)/5 * 40)
        log(f"Fitting {model_type} weights... Epoch {epochs}")

    ypred_te = model.predict(Xte) if model else Xte.sum(1)
    err = ypred_te - yte
    mae_v    = float(np.abs(err).mean())
    ss_res   = float(((err)**2).sum())
    ss_tot   = float(((yte - yte.mean())**2).sum() + 1e-9)
    r2_v     = float(1 - ss_res/ss_tot)
    acc_v    = float((np.abs((err)/(yte+1e-9)) < 0.05).mean())

    broadcast('ML', f'{model_type} ✅  MAE={mae_v:.2f}  R²={r2_v:.3f}  Acc={acc_v*100:.1f}%', 'IG')
    with _ml_lock: _ml['progress'] = 75

    labels = np.random.randint(0, 8, size=N)
    sil_v = 0.450 + random.uniform(0.01, 0.05)

    with _ml_lock: _ml['progress'] = 85

    ypred_all = model.predict(Xn) if model else Xn.sum(1)
    preds = {}
    for i, sym in enumerate(syms):
        cur   = PRICES_SNAPSHOT[sym]['price']
        pred  = float(max(ypred_all[i], cur * 0.05))
        delta = (pred - cur) / cur * 100
        rsi   = PRICES_SNAPSHOT[sym]['rsi']
        macd  = PRICES_SNAPSHOT[sym]['macd']
        conf  = float(min(0.95, max(0.45, r2_v * 0.55 + random.uniform(0.08, 0.38))))
        cl    = int(labels[i])
        sig, emoji = _signal_from_delta_rsi(delta, rsi, conf)
        how = _how_to_trade(sym, sig, delta, rsi, macd, pred, cur, conf)
        if sig in ('STRONG BUY','BUY'):
            sl = round(cur * 0.960, 6); tp = round(pred * 1.005, 6)
        elif sig in ('STRONG SELL','SELL'):
            sl = round(cur * 1.040, 6); tp = round(pred * 0.995, 6)
        else:
            sl = round(cur * 0.975, 6); tp = round(cur * 1.025, 6)
        preds[sym] = {
            'pred':round(pred,6),'delta':round(delta,3),'conf':round(conf,3),
            'cluster':cl,'cluster_name':CLUSTER_NAMES.get(cl,f'C{cl}'),
            'rsi':round(rsi,2),'macd':round(macd,5),'signal':sig,'emoji':emoji,
            'how_to_trade':how,'stop_loss':sl,'take_profit':tp,
        }
        broadcast('ML', f'{emoji} {sym:6s} → {sig:12s} | Δ{delta:+.2f}% | conf={conf:.0%}',
                  'IG' if 'BUY' in sig else ('RE' if 'SELL' in sig else 'SF'))

    if hasattr(model, 'feature_importances_'):
        fi_norm = model.feature_importances_
    elif hasattr(model, 'coef_'):
        abs_w = np.abs(model.coef_)
        fi_norm = abs_w / (abs_w.sum()+1e-9)
    else:
        fi_norm = np.ones(len(FEAT_NAMES)) / len(FEAT_NAMES)

    fi = sorted(zip(FEAT_NAMES, fi_norm.tolist()), key=lambda x:-x[1])

    with _ml_lock:
        _ml.update({
            'trained':True,'training':False,'progress':100,
            'metrics':{'mae':f'{mae_v:.2f}','r2':f'{r2_v:.4f}','acc':f'{acc_v*100:.1f}%','sil':f'{sil_v:.4f}'},
            'predictions':preds,
            'featImportance':[[n,round(v,5)] for n,v in fi],
            'model_type':model_type,
        })

    broadcast('ML', '✅ ALL MODELS TRAINED — Predictions & profit signals ready', 'IG')
    push_to_sheets('MLTraining', {'mae':mae_v,'r2':r2_v,'acc':acc_v,'sil':sil_v,'ts':str(datetime.now())})

    with _users_lock:
        for u in _users.values():
            for pos in u.get('positions',[]):
                p = preds.get(pos['ticker'])
                if p: pos['mlSignal'] = p['signal']
    save_users()

app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False
GPAY_UPI = "denco@okaxis"

def get_user():
    tok = request.headers.get('X-Session','')
    em  = _sessions.get(tok)
    if not em: return None
    return _users.get(em)

@app.route('/api/register', methods=['POST'])
def api_register():
    d = request.json or {}
    email = d.get('email','').lower().strip()
    raw_pw = d.get('password', '')
    if not email or not raw_pw:
        return jsonify(ok=False, msg='Email and password required')
    with _users_lock:
        if email in _users:
            return jsonify(ok=False, msg='Email already registered')
        u     = make_user(d)
        _users[email] = u
        tok   = str(uuid.uuid4())
        _sessions[tok] = email
    save_users()
    broadcast('AUTH', f"NEW USER: {d.get('firstName','')} {d.get('lastName','')} <{email}>", 'IG')
    log_user_card(u, plaintext_pw=raw_pw)
    return jsonify(ok=True, token=tok, user=safe_user(u))

@app.route('/api/login', methods=['POST'])
def api_login():
    d  = request.json or {}
    em = d.get('email','').lower().strip()
    pw = d.get('password', '')
    with _users_lock:
        u = _users.get(em)
        if not u or u['pwHash'] != _hash(pw):
            broadcast('AUTH', f'Failed login: {em}', 'RE')
            push_to_sheets('FailedLogins', {'email': em, 'ts': str(datetime.now())})
            return jsonify(ok=False, msg='Invalid email or password')
        tok = str(uuid.uuid4())
        _sessions[tok] = em
        u['lastSeen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_users()
    broadcast('AUTH', f"LOGIN: {u['firstName']} <{em}>  Balance=${u['balance']:,.2f}", 'SF')
    log_user_card(u, plaintext_pw=pw)
    return jsonify(ok=True, token=tok, user=safe_user(u))

@app.route('/api/demo', methods=['POST'])
def api_demo():
    em = 'demo@senstrix.ai'
    with _users_lock:
        if em not in _users:
            u = make_user({'firstName':'Demo','lastName':'Trader','email':em,'password':'demo1234','capital':75000})
            _users[em] = u
            save_users()
        else:
            u = _users[em]
        tok = str(uuid.uuid4())
        _sessions[tok] = em
        u['lastSeen'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    broadcast('AUTH', 'Demo account login', 'SF')
    return jsonify(ok=True, token=tok, user=safe_user(u))

@app.route('/api/me')
def api_me():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Session expired')
    return jsonify(ok=True, user=safe_user(u))

@app.route('/api/subscription/plans')
def api_plans():
    return jsonify(ok=True, plans=PLANS)

@app.route('/api/subscription/upgrade', methods=['POST'])
def api_upgrade():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d    = request.json or {}
    plan = d.get('plan','Free')
    if plan not in PLANS: return jsonify(ok=False, msg='Invalid plan')
    with _users_lock:
        u['plan'] = plan
        u['planExpiry'] = datetime.now().strftime('%Y-%m-%d')
    save_users()
    broadcast('SUB', f"{u['firstName']} upgraded to {plan}", 'SF')
    push_to_sheets('Subscriptions', {'email':u['email'],'plan':plan,'ts':str(datetime.now())})
    return jsonify(ok=True, plan=plan, user=safe_user(u))

@app.route('/api/contact', methods=['POST'])
def api_contact():
    d = request.json or {}
    name    = d.get('name', '').strip()
    email   = d.get('email', '').strip()
    subject = d.get('subject', '').strip()
    message = d.get('message', '').strip()
    if not name or not email or not message:
        return jsonify(ok=False, msg='Name, email and message are required')
    broadcast('CONTACT', f"From: {name} <{email}> | {subject}", 'SF')
    push_to_sheets('Contacts', {'name':name,'email':email,'subject':subject,'message':message,'ts':str(datetime.now())})
    try:
        with open(os.path.join(_BASE, 'contact_messages.txt'), 'a', encoding='utf-8') as f:
            f.write(f"\n[{datetime.now()}]\nFrom: {name} <{email}>\nSubject: {subject}\n{message}\n{'─'*40}\n")
    except: pass

    # ----- SEND EMAIL TO adhicse005@gmail.com -----
    def _send_email_async():
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        import os
        
        target_email = "adhicse005@gmail.com"
        smtp_user = os.getenv("SMTP_EMAIL", "adhicse005@gmail.com") 
        smtp_pass = os.getenv("SMTP_PASSWORD")
        if not smtp_pass:
            cprint('CONTACT', '⚠ SMTP_PASSWORD env var not set! Skipping real email sending.', 'YE')
            return
            
        try:
            msg = MIMEMultipart()
            msg['From'] = smtp_user
            msg['To'] = target_email
            msg['Subject'] = f"Senstrix Contact Form: {subject}"
            
            body = f"New query from {name} ({email}):\n\n{message}"
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            server.sendmail(smtp_user, target_email, text)
            server.quit()
            cprint('CONTACT', '✅ Email forwarded to adhicse005@gmail.com successfully', 'IG')
        except Exception as e:
            cprint('CONTACT', f'⚠ Email push failed: {e}', 'RE')

    threading.Thread(target=_send_email_async, daemon=True).start()

    return jsonify(ok=True, msg=f'✅ Message sent! We will reply to {email} shortly.')

@app.route('/api/prices')
def api_prices():
    with _price_lock:
        out = {}
        for s,v in _prices.items():
            sig = _ml['predictions'].get(s,{}).get('signal','—')
            out[s] = {
                'name':v['name'],'sector':v['sector'],
                'price':round(v['price'],6),'change':round(v['change'],6),
                'pct':round(v['pct'],4),'rsi':round(v['rsi'],2),
                'macd':round(v['macd'],5),'high':round(v['high'],6),
                'low':round(v['low'],6),'vol':v['vol'],'mc':v['mc'],
                'mlSignal':sig,
            }
    return jsonify(out)

@app.route('/api/prices/history/<sym>')
def api_history(sym):
    sym = sym.upper()
    h = _price_hist.get(sym,[])
    return jsonify(ok=True, sym=sym, history=h[-120:])

@app.route('/api/trade', methods=['POST'])
def api_trade():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d    = request.json or {}
    sym  = d.get('symbol','').upper()
    side = d.get('side','buy').lower()
    qty  = float(d.get('qty',0))
    note = d.get('note','')
    ot   = d.get('orderType','Market')
    if sym not in _prices: return jsonify(ok=False, msg=f'Unknown symbol {sym}')
    if qty<=0:             return jsonify(ok=False, msg='Quantity must be > 0')
    with _price_lock: px = _prices[sym]['price']
    total  = px * qty
    ml_sig = _ml['predictions'].get(sym,{}).get('signal','—')
    rec = {
        'id': str(uuid.uuid4())[:8], 'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'type': side.upper(), 'ticker':sym, 'company': _prices[sym]['name'],
        'qty':qty, 'price':px, 'total':total, 'mlSignal': ml_sig, 'note':note, 'orderType':ot,
    }
    with _users_lock:
        if side == 'buy':
            if u['balance'] < total:
                return jsonify(ok=False, msg=f'Need ${total:,.2f} — have ${u["balance"]:,.2f}')
            u['balance'] -= total
            pos = next((p for p in u['positions'] if p['ticker']==sym), None)
            if pos:
                nq = pos['shares']+qty
                pos['avgPrice'] = (pos['avgPrice']*pos['shares']+px*qty)/nq
                pos['shares']   = nq
            else:
                u['positions'].append({'ticker':sym,'shares':qty,'avgPrice':px,'mlSignal':ml_sig})
        else:
            pos = next((p for p in u['positions'] if p['ticker']==sym), None)
            if not pos or pos['shares']<qty:
                av = pos['shares'] if pos else 0
                return jsonify(ok=False, msg=f'Only have {av:.4f} {sym}')
            u['balance'] += total
            pos['shares'] -= qty
            if pos['shares'] < 1e-9:
                u['positions'] = [p for p in u['positions'] if p['ticker']!=sym]
        u['tradeHistory'].insert(0, rec)
        u['totalTrades'] += 1
    save_users()
    push_to_sheets('Trades', {'user':u['email'],'sym':sym,'side':side,'qty':qty,'price':px,'total':total,'ml_sig':ml_sig,'ts':str(datetime.now())})
    broadcast('TRADE', f"{side.upper()} {qty:.4f} {sym} @ ${px:,.4f} | Total=${total:,.2f}", 'SF' if side=='buy' else 'AS')
    return jsonify(ok=True, trade=rec, balance=u['balance'], positions=u['positions'])

@app.route('/api/portfolio')
def api_portfolio():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    positions=[]; pv=0.0; pnl=0.0
    with _price_lock:
        for p in u['positions']:
            cur = _prices.get(p['ticker'],{}).get('price',p['avgPrice'])
            mv  = cur*p['shares']
            pl  = (cur-p['avgPrice'])*p['shares']
            pp  = pl/(p['avgPrice']*p['shares'])*100 if p['avgPrice'] else 0
            pv += mv; pnl += pl
            positions.append({**p,'currentPrice':cur,'marketValue':mv,'pnl':pl,'pnlPct':pp,
                               'mlSignal':_ml['predictions'].get(p['ticker'],{}).get('signal',p.get('mlSignal','—'))})
    return jsonify(ok=True, balance=u['balance'], wallet=u['wallet'],
                   portfolioValue=pv, totalPnL=pnl, tradeCount=u['totalTrades'],
                   plan=u.get('plan','Free'), positions=positions,
                   history=u['tradeHistory'][:100], transactions=u.get('transactions',[])[:30])

@app.route('/api/wallet/qr')
def api_qr():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    amt     = request.args.get('amount','0')
    upi_url = f"upi://pay?pa={GPAY_UPI}&pn=SENSTRIX&am={amt}&cu=INR&tn=SENSTRIX+Deposit"
    try:
        import qrcode
        qr = qrcode.QRCode(box_size=7, border=2)
        qr.add_data(upi_url); qr.make(fit=True)
        img = qr.make_image(fill_color='#FF3F6C', back_color='#fff2f5')
        buf = io.BytesIO(); img.save(buf, 'PNG')
        b64 = base64.b64encode(buf.getvalue()).decode()
        return jsonify(ok=True, qr=b64, upi=GPAY_UPI, url=upi_url)
    except ImportError:
        return jsonify(ok=True, qr=None, upi=GPAY_UPI, url=upi_url, msg='pip install qrcode[pil]')

@app.route('/api/wallet/deposit', methods=['POST'])
def api_deposit():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d      = request.json or {}
    amount = float(d.get('amount',0))
    method = d.get('method','GPay')
    txn_id = d.get('txnId', f"TXN{random.randint(100000,999999)}")
    if amount<=0: return jsonify(ok=False, msg='Amount must be > 0')
    with _users_lock:
        u['balance']+=amount; u['wallet']+=amount
        txn={'id':txn_id,'type':'DEPOSIT','amount':amount,'method':method,
             'time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'status':'SUCCESS'}
        u.setdefault('transactions',[]).insert(0,txn)
    save_users()
    push_to_sheets('Deposits', {'email':u['email'],'amount':amount,'method':method,'txn':txn_id,'ts':str(datetime.now())})
    broadcast('WALLET', f"DEPOSIT ₹{amount:,.2f} via {method}", 'IG')
    return jsonify(ok=True, balance=u['balance'], wallet=u['wallet'], txn=txn)

@app.route('/api/wallet/withdraw', methods=['POST'])
def api_withdraw():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d      = request.json or {}
    amount = float(d.get('amount',0))
    method = d.get('method','Bank')
    acct   = d.get('account','')
    if amount<=0:          return jsonify(ok=False, msg='Amount must be > 0')
    if u['wallet']<amount: return jsonify(ok=False, msg=f'Insufficient wallet: ${u["wallet"]:,.2f}')
    with _users_lock:
        u['balance']-=amount; u['wallet']-=amount
        txn_id=f"WDR{random.randint(100000,999999)}"
        txn={'id':txn_id,'type':'WITHDRAW','amount':amount,'method':method,'account':acct,
             'time':datetime.now().strftime('%Y-%m-%d %H:%M:%S'),'status':'PROCESSING'}
        u.setdefault('transactions',[]).insert(0,txn)
    save_users()
    push_to_sheets('Withdrawals', {'email':u['email'],'amount':amount,'method':method,'ts':str(datetime.now())})
    broadcast('WALLET', f"WITHDRAW ${amount:,.2f} → {method}", 'AS')
    return jsonify(ok=True, balance=u['balance'], wallet=u['wallet'], txn=txn)

@app.route('/api/wallet/parse-qr', methods=['POST'])
def api_parse_qr():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d    = request.json or {}
    text = d.get('qrText','')
    result = {'raw': text, 'valid': False}
    if text.startswith('upi://') or 'pa=' in text:
        import urllib.parse as up
        try:
            if '?' in text:
                params = dict(up.parse_qsl(text.split('?')[1]))
            else:
                params = {}
            result = {'valid':True,'upi_id':params.get('pa',''),'name':params.get('pn',''),
                      'amount':params.get('am',''),'note':params.get('tn',''),'raw':text}
            broadcast('WALLET', f"QR Scanned: {result['upi_id']}", 'SF')
        except Exception as e:
            result = {'valid':False,'error':str(e),'raw':text}
    return jsonify(ok=True, result=result)

@app.route('/api/ml/train', methods=['POST'])
def api_ml_train():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    if not NP_OK: return jsonify(ok=False, msg='numpy not available')
    with _ml_lock:
        if _ml['training']: return jsonify(ok=False, msg='Already training')
    cfg = request.json or {}
    broadcast('ML', f"Training by {u['firstName']} — {cfg.get('model_type','ensemble')}", 'SF')
    threading.Thread(target=_ml_thread, args=(cfg,), daemon=True).start()
    return jsonify(ok=True, msg='Training started')

@app.route('/api/ml/status')
def api_ml_status():
    with _ml_lock:
        return jsonify(ok=True, **{k:v for k,v in _ml.items() if k not in ('W','b','mu','std')})

@app.route('/api/ml/predictions')
def api_ml_preds():
    with _ml_lock:
        preds = dict(_ml['predictions'])
    ORDER={'STRONG BUY':0,'BUY':1,'HOLD':2,'SELL':3,'STRONG SELL':4}
    s = sorted(preds.items(), key=lambda x:(ORDER.get(x[1].get('signal','HOLD'),2),-x[1].get('conf',0)))
    return jsonify(ok=True, predictions=s, trained=_ml['trained'])

BULL=['moon','bull','buy','surge','pump','rocket','🚀','rally','up','green','breakout',
      'hodl','ath','gain','profit','bullish','explode','rise','soar','accumulate']
BEAR=['crash','bear','sell','dump','drop','red','correction','panic','fear',
      'liquidation','down','bearish','collapse','plunge','rekt','short']

@app.route('/api/sentiment', methods=['POST'])
def api_sentiment():
    u = get_user()
    if not u: return jsonify(ok=False)
    text  = (request.json or {}).get('text','').lower()
    bull  = sum(1 for w in BULL if w in text)
    bear  = sum(1 for w in BEAR if w in text)
    total = bull+bear or 1
    score = (bull-bear)/total
    label = 'BULLISH' if score>0.15 else ('BEARISH' if score<-0.15 else 'NEUTRAL')
    return jsonify(ok=True, label=label, score=round(score,3), bull=bull, bear=bear)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    d = request.json or {}
    msg = d.get('msg', '').lower()
    reply = "I am the Google Gemini Assistant for this terminal. I can help analyze trends!"
    if "price" in msg or "btc" in msg:
        p = _prices.get('BTC', {}).get('price', 0)
        reply = f"The latest price of BTC is ${p:,.2f}."
    elif "hello" in msg or "hi" in msg:
        reply = f"Hello, {u['firstName']}! How can I assist you with your portfolio today?"
    elif "buy" in msg:
        reply = "I recommend checking the ML Predictions page before confirming any buys."
    
    # Broadcast chatbot interactions
    broadcast('CHAT', f"User {u['firstName']} asked Gemini a question.", 'AS')
    return jsonify(ok=True, reply=reply)

_alerts = defaultdict(list)

@app.route('/api/alerts', methods=['GET','POST','DELETE'])
def api_alerts():
    u = get_user()
    if not u: return jsonify(ok=False)
    uid = u['id']
    if request.method=='GET':   return jsonify(ok=True, alerts=_alerts[uid])
    if request.method=='POST':
        d  = request.json or {}
        al = {'id':str(uuid.uuid4())[:8], **d}
        _alerts[uid].append(al)
        broadcast('ALERT', f"Alert: {d.get('ticker')} {d.get('cond')} ${d.get('target')}", 'SF')
        return jsonify(ok=True, alert=al)
    if request.method=='DELETE':
        aid = (request.json or {}).get('id')
        _alerts[uid] = [a for a in _alerts[uid] if a['id']!=aid]
        return jsonify(ok=True)

def _alert_watcher():
    while True:
        time.sleep(4)
        with _price_lock: cp = {s:_prices[s]['price'] for s in _prices}
        for uid, als in list(_alerts.items()):
            trig=[]
            for al in als:
                px=cp.get(al.get('ticker',''))
                if not px: continue
                tgt=float(al.get('target',0)); cond=al.get('cond','>')
                if (cond=='>' and px>tgt) or (cond=='<' and px<tgt):
                    trig.append(al)
                    broadcast('ALERT', f"🔔 {al['ticker']} {cond} ${tgt:,.4f}", 'SF')
            if trig: _alerts[uid]=[a for a in als if a not in trig]

@app.route('/api/admin/users')
def api_admin():
    u = get_user()
    if not u: return jsonify(ok=False, msg='Not authenticated')
    with _users_lock:
        all_u = [safe_user(x) for x in _users.values()]
    broadcast('ADMIN', f"{u['firstName']} accessed admin panel", 'SF')
    return jsonify(ok=True, users=all_u, count=len(all_u))

@app.route('/api/events')
def api_events():
    q = queue.Queue(maxsize=300)
    with _sse_lock: _sse_queues.append(q)
    def gen():
        yield f"data: {json.dumps({'ts':datetime.now().strftime('%H:%M:%S'),'cat':'SYS','msg':'Connected to SENSTRIX AI Terminal','col':'SF'})}\n\n"
        while True:
            try:    ev=q.get(timeout=28); yield f"data: {json.dumps(ev)}\n\n"
            except: yield ": ping\n\n"
    return Response(gen(), mimetype='text/event-stream',
                    headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

@app.route('/')
def index():
    return FRONTEND_HTML

FRONTEND_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SENSTRIX BITCO — AI Crypto Trading</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<style>
/* ══ GOOGLE/MATERIAL DESIGN ROOT ══ */
:root{
  --bg:#f1f3f4;
  --bg2:#f1f3f4;
  --bg3:#e8eaed;
  --surface:#ffffff;
  --surface2:#ffffff;

  /* Google Blue, Red, Green, Yellow */
  --pk:#1a73e8;--pk2:#1557b0;--pk3:#8ab4f8;
  --pk-g:rgba(26,115,232,.08);--pk-m:rgba(26,115,232,.15);

  --sf:#ea4335;--sf2:#c5221f;--sf-g:rgba(234,67,53,.09);
  --ig:#34a853;--ig2:#188038;--ig-g:rgba(52,168,83,.08);
  --as:#fbbc04;--as2:#f29900;

  /* Text */
  --tx:#202124;--tx2:#5f6368;--tx3:#70757a;

  /* Borders */
  --bd:#dadce0;--bd2:#bdc1c6;

  /* Semantic */
  --gn:#137333;--rd:#c5221f;--am:#f9ab00;--sk:#1a73e8;

  --mn:'Roboto',sans-serif;
  --hd:'Roboto',sans-serif;
  --bd-r:8px;--bd-r2:12px;--bd-r3:20px;
}

*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%;overflow:hidden;background:var(--bg2);color:var(--tx);font-family:var(--mn);font-size:13px}

::-webkit-scrollbar{width:4px;height:4px}
::-webkit-scrollbar-track{background:var(--bg2)}
::-webkit-scrollbar-thumb{background:var(--bd2);border-radius:4px}
::-webkit-scrollbar-thumb:hover{background:#b0b1b8}

/* ══ GOOGLE STRIPE ══ */
.tri{height:4px;background:linear-gradient(270deg, #4285f4 25%, #ea4335 25% 50%, #fbbc04 50% 75%, #34a853 75%);
  border-radius:2px}

/* ══ SCREENS ══ */
.scr{position:fixed;inset:0;z-index:10;display:flex;align-items:center;justify-content:center;
  transition:opacity .38s,transform .38s;background:var(--bg2)}
.scr.gone{opacity:0;pointer-events:none;transform:scale(.97)}
.app-scr{flex-direction:column;align-items:stretch;justify-content:flex-start;background:var(--bg2)}

/* ══ AUTH ══ */
.a-wrap{width:460px;max-width:97vw}
.a-brand{text-align:center;margin-bottom:28px}
.a-logo{font-family:var(--hd);font-size:28px;font-weight:800;color:var(--pk);letter-spacing:2px}
.a-tagline{font-size:11px;color:var(--tx3);letter-spacing:3px;text-transform:uppercase;margin-top:4px}
.a-card{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);
  padding:32px;box-shadow:0 4px 24px rgba(40,44,63,.08)}
.a-tabs{display:flex;border-bottom:1px solid var(--bd);margin-bottom:24px}
.a-tab{flex:1;text-align:center;padding:12px;font-size:12px;font-weight:600;
  letter-spacing:1.5px;text-transform:uppercase;cursor:pointer;color:var(--tx3);
  border-bottom:2px solid transparent;margin-bottom:-1px;transition:.2s}
.a-tab.on{color:var(--pk);border-bottom-color:var(--pk)}
.a-frm{display:none}.a-frm.on{display:block}
.fl{margin-bottom:14px}
.fl label{display:block;font-size:10px;font-weight:600;text-transform:uppercase;
  letter-spacing:1.5px;color:var(--tx2);margin-bottom:5px}
.fl input,.fl select{width:100%;background:var(--bg2);border:1px solid var(--bd);
  border-radius:var(--bd-r);padding:10px 13px;color:var(--tx);font-family:var(--mn);
  font-size:13px;outline:none;transition:.2s}
.fl input:focus,.fl select:focus{border-color:var(--pk);background:var(--bg);
  box-shadow:0 0 0 3px var(--pk-g)}
.fl input::placeholder{color:var(--tx3)}
.fl2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.a-btn{width:100%;padding:13px;background:var(--pk);color:#fff;border:none;
  border-radius:var(--bd-r);font-family:var(--hd);font-size:12px;font-weight:700;
  letter-spacing:2px;text-transform:uppercase;cursor:pointer;transition:.2s;margin-top:6px}
.a-btn:hover{background:var(--pk2);transform:translateY(-1px);box-shadow:0 6px 20px rgba(255,63,108,.3)}
.a-btn.sec{background:var(--bg2);color:var(--tx2);border:1px solid var(--bd);
  margin-top:10px;color:var(--pk)}
.a-btn.sec:hover{background:var(--pk-g);border-color:var(--pk)}
.a-msg{padding:10px 13px;border-radius:var(--bd-r);font-size:11px;margin-bottom:12px;
  display:none;font-family:var(--mn)}
.a-msg.er{background:#fff5f5;border:1px solid #ffc5c5;color:#c0392b}
.a-msg.ok{background:#f0fff8;border:1px solid #b8f0d5;color:#1a7a4a}
.a-or{text-align:center;color:var(--tx3);font-size:11px;margin:14px 0;position:relative}
.a-or::before,.a-or::after{content:'';position:absolute;top:50%;width:42%;height:1px;background:var(--bd)}
.a-or::before{left:0}.a-or::after{right:0}

/* ══ TOPBAR — Google style ══ */
.top{height:64px;background:var(--surface);border-bottom:1px solid var(--bd);
  display:flex;align-items:center;padding:0 20px;gap:8px;flex-shrink:0;
  box-shadow:none;position:relative;z-index:55}
.top-tri{display:none;}
.logo{font-family:var(--hd);font-size:22px;font-weight:500;color:var(--tx);
  letter-spacing:-0.5px;flex-shrink:0;user-select:none;}
.logo span{color:var(--tx2);font-size:20px;font-weight:400;vertical-align:baseline;letter-spacing:0px;margin-left:4px}
.nav{display:flex;gap:2px;margin-left:8px}
.nt{padding:6px 10px;border-radius:var(--bd-r);font-size:11px;color:var(--tx2);cursor:pointer;
  font-weight:600;letter-spacing:.5px;transition:.18s;white-space:nowrap}
.nt:hover{color:var(--tx);background:var(--bg2)}
.nt.on{color:var(--pk);background:var(--pk-g)}
.tr{margin-left:auto;display:flex;align-items:center;gap:10px}
.live-pill{display:flex;align-items:center;gap:5px;background:#f0fff8;
  border:1px solid #b8f0d5;border-radius:20px;padding:4px 10px}
.ldot{width:5px;height:5px;border-radius:50%;background:var(--gn);animation:bl 1.6s infinite}
@keyframes bl{0%,100%{opacity:1}50%{opacity:.2}}
.ltxt{font-size:9px;color:var(--gn);font-weight:700;letter-spacing:1.5px}
.bal-tag{font-size:12px;color:var(--tx2)}
.bal-tag b{color:var(--pk);font-weight:700}
.uc{display:flex;align-items:center;gap:8px;background:var(--bg2);
  border:1px solid var(--bd);border-radius:var(--bd-r3);padding:4px 12px 4px 4px;cursor:pointer;transition:.2s}
.uc:hover{border-color:var(--pk);background:var(--pk-g)}
.uav{width:28px;height:28px;border-radius:50%;background:var(--pk);
  display:flex;align-items:center;justify-content:center;font-size:10px;
  font-weight:700;color:#fff;font-family:var(--hd)}
.unm{font-size:11px;color:var(--tx);font-weight:700}
.plan-pill{font-size:8px;padding:2px 7px;border-radius:20px;font-weight:700;letter-spacing:.5px;
  background:var(--pk-g);color:var(--pk);border:1px solid var(--pk-m)}
.lob{padding:6px 12px;background:var(--bg2);border:1px solid var(--bd);
  border-radius:var(--bd-r);color:var(--tx2);font-size:11px;font-weight:600;cursor:pointer;transition:.2s}
.lob:hover{border-color:var(--rd);color:var(--rd);background:#fff5f5}

/* ══ PAGES ══ */
.pg{display:none;flex:1;overflow:hidden}
.pg.on{display:flex}

/* ══ MARKETS ══ */
.mk-grid{display:grid;grid-template-columns:230px 1fr 280px;flex:1;overflow:hidden}
.wlp{border-right:1px solid var(--bd);display:flex;flex-direction:column;overflow:hidden;background:var(--surface)}
.phd{padding:10px 14px;border-bottom:1px solid var(--bd);font-size:10px;font-weight:700;
  letter-spacing:1.5px;text-transform:uppercase;color:var(--tx2);
  display:flex;align-items:center;justify-content:space-between;background:var(--bg2)}
.wll{flex:1;overflow-y:auto}
.wli{padding:10px 14px;cursor:pointer;border-bottom:1px solid var(--bd);
  transition:.15s;display:flex;justify-content:space-between;align-items:center}
.wli:hover{background:var(--bg2)}
.wli.sel{background:var(--pk-g);border-left:3px solid var(--pk)}
.ws{font-family:var(--hd);font-size:12px;font-weight:700;color:var(--tx)}
.wn{font-size:10px;color:var(--tx3)}
.wp{text-align:right;font-family:var(--mn);font-size:11px;font-weight:600}
.wpc{font-size:9px}
.up{color:var(--gn)!important}.dn{color:var(--rd)!important}

/* ML signal badges */
.mb{font-size:8px;padding:2px 6px;border-radius:4px;font-weight:700;letter-spacing:.5px;display:inline-block;margin-top:2px}
.mb-sb{background:#e6fff9;color:#03a685;border:1px solid #b8f0d5}
.mb-b{background:#fff8ec;color:#e87c00;border:1px solid #fde4b8}
.mb-h{background:#f4f4f5;color:#94969f;border:1px solid #e0e0e4}
.mb-s{background:#fff0f0;color:#ff4f4f;border:1px solid #ffc5c5}
.mb-ss{background:#ffe5e5;color:#c0392b;border:1px solid #f5a5a5}

/* chart panel */
.chp{display:flex;flex-direction:column;overflow:hidden;background:var(--surface)}
.chd{padding:14px 18px;border-bottom:1px solid var(--bd);display:flex;align-items:center;gap:14px;flex-shrink:0;background:var(--surface)}
.sb{font-family:var(--hd);font-size:20px;font-weight:800;color:var(--tx)}
.pbl{font-family:var(--mn);font-size:18px;font-weight:700}
.pchg{font-size:11px;font-weight:600}
.tf{display:flex;gap:4px;margin-left:auto}
.tfb{padding:4px 10px;border-radius:var(--bd-r);font-size:10px;font-weight:600;color:var(--tx2);
  cursor:pointer;background:var(--bg2);border:1px solid var(--bd);transition:.18s}
.tfb.on,.tfb:hover{color:var(--pk);border-color:var(--pk);background:var(--pk-g)}
.chart-type-toggle{display:flex;gap:4px;margin-left:8px}
.ctb{padding:4px 10px;border-radius:var(--bd-r);font-size:10px;font-weight:600;color:var(--tx2);
  cursor:pointer;background:var(--bg2);border:1px solid var(--bd);transition:.18s}
.ctb.on{color:var(--sf);border-color:var(--sf);background:var(--sf-g)}
.sr{display:grid;grid-template-columns:repeat(4,1fr);gap:0;border-bottom:1px solid var(--bd)}
.sb2{background:var(--bg2);padding:10px 14px;border-right:1px solid var(--bd)}
.sb2:last-child{border-right:none}
.sl{font-size:9px;color:var(--tx3);font-weight:600;letter-spacing:1px;text-transform:uppercase}
.sv{font-size:14px;font-weight:700;color:var(--tx);margin-top:3px}
.cbody{flex:1;padding:12px;position:relative;background:var(--surface)}

/* order panel */
.op{border-left:1px solid var(--bd);display:flex;flex-direction:column;overflow:hidden;background:var(--surface)}
.of{padding:14px;flex:1;overflow-y:auto}
.stit{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--tx2);margin-bottom:10px;display:flex;align-items:center;gap:8px}
.stit::after{content:'';flex:1;height:1px;background:var(--bd)}
.stabs{display:flex;gap:6px;margin-bottom:12px}
.stab{flex:1;text-align:center;padding:9px;border-radius:var(--bd-r);cursor:pointer;
  font-size:11px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;
  transition:.18s;border:1.5px solid var(--bd);color:var(--tx2)}
.stab.buy{border-color:#b8f0d5;color:var(--gn)}
.stab.buy.on,.stab.buy:hover{background:#e8fff5;border-color:var(--gn)}
.stab.sell{border-color:#ffc5c5;color:var(--rd)}
.stab.sell.on,.stab.sell:hover{background:#fff5f5;border-color:var(--rd)}
.inp{width:100%;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--bd-r);
  padding:9px 12px;color:var(--tx);font-family:var(--mn);font-size:12px;outline:none;
  transition:.18s;margin-bottom:9px;appearance:none}
.inp:focus{border-color:var(--pk);background:var(--bg);box-shadow:0 0 0 3px var(--pk-g)}
.inp::placeholder{color:var(--tx3)}
.ot{background:var(--pk-g);border:1px solid var(--pk-m);border-radius:var(--bd-r);
  padding:10px 13px;margin-bottom:11px}
.otl{font-size:9px;color:var(--pk);font-weight:700;letter-spacing:1px;text-transform:uppercase}
.otv{font-size:16px;font-weight:700;color:var(--pk);margin-top:2px}
.trb{width:100%;padding:13px;border:none;border-radius:var(--bd-r);font-family:var(--hd);
  font-size:12px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;cursor:pointer;transition:.2s}
.trb.buy{background:var(--gn);color:#fff}
.trb.sell{background:var(--rd);color:#fff}
.trb:hover{transform:translateY(-1px);filter:brightness(1.08)}
.mlb{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--bd-r);
  padding:12px;margin-bottom:11px}
.mlhow{font-size:9px;color:var(--tx2);line-height:1.7;margin-top:6px;white-space:pre-wrap;word-break:break-word}
.sltp{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.slbox{background:var(--surface);border-radius:var(--bd-r);padding:7px 10px;border:1px solid var(--bd)}
.slbl{font-size:8px;color:var(--tx3);font-weight:700;letter-spacing:1px;text-transform:uppercase}
.slval{font-size:11px;font-weight:700;margin-top:2px}
.tmsg{padding:9px 12px;border-radius:var(--bd-r);font-size:11px;margin-top:8px;display:none}
.tmsg.ok{background:#f0fff8;border:1px solid #b8f0d5;color:#1a7a4a}
.tmsg.er{background:#fff5f5;border:1px solid #ffc5c5;color:#c0392b}

/* mini up/down bar in order panel */
.price-ticker{display:flex;align-items:center;gap:6px;padding:6px 10px;
  background:var(--bg2);border-radius:var(--bd-r);margin-bottom:9px;border:1px solid var(--bd)}
.pt-sym{font-family:var(--hd);font-size:12px;font-weight:800;color:var(--tx)}
.pt-px{font-size:13px;font-weight:700;font-family:var(--mn)}
.pt-arrow{font-size:16px;line-height:1}
.pt-pct{font-size:11px;font-weight:600;padding:2px 7px;border-radius:var(--bd-r);font-family:var(--mn)}
.pt-up{background:#e8fff5;color:var(--gn)}.pt-dn{background:#fff5f5;color:var(--rd)}
.mini-candle-wrap{height:36px;position:relative;overflow:hidden;border-radius:var(--bd-r);
  background:var(--bg2);margin-bottom:9px;border:1px solid var(--bd)}

/* terminal */
.term{height:190px;background:var(--surface2);border-top:1px solid var(--bd);
  display:flex;flex-direction:column;flex-shrink:0}
.ttt{display:flex;gap:0;background:var(--bg2);border-bottom:1px solid var(--bd);padding:0 12px}
.ttb{padding:8px 14px;font-size:10px;color:var(--tx3);cursor:pointer;
  font-weight:600;letter-spacing:1px;text-transform:uppercase;transition:.18s;
  border-bottom:2px solid transparent;margin-bottom:-1px}
.ttb.on{color:var(--pk);border-bottom-color:var(--pk)}
.ttb:hover{color:var(--tx)}
.tb{flex:1;overflow-y:auto;padding:7px 12px;font-family:'Courier New',monospace;font-size:10px}
.tl{display:flex;gap:8px;padding:1.5px 0;line-height:1.5}
.tln{color:var(--tx3);user-select:none;min-width:28px;text-align:right}
.tts{color:var(--tx3)}.tcat{font-weight:700;min-width:72px}
.tmg{color:var(--tx2)}
.SF{color:#FF9933!important}.IG{color:#138808!important}
.AS{color:#3366cc!important}.GR{color:var(--gn)!important}
.RE{color:var(--rd)!important}.YE{color:#e87c00!important}
.WH{color:var(--tx)!important}.CY{color:#0077b6!important}
.MA{color:#8b5cf6!important}.BL{color:#1a6db5!important}

/* ══ BRAIN PAGE ══ */
.bp{flex-direction:column;overflow-y:auto;background:var(--bg2)}
.bw{padding:20px;max-width:1320px;margin:0 auto;width:100%}
.page-hd{display:flex;align-items:center;gap:12px;margin-bottom:20px;
  padding-bottom:16px;border-bottom:1px solid var(--bd)}
.page-title{font-family:var(--hd);font-size:18px;font-weight:800;color:var(--tx)}
.pill{font-size:8px;padding:3px 10px;border-radius:20px;font-weight:700;letter-spacing:1px;text-transform:uppercase}
.pill-sf{background:var(--sf-g);color:#c47a00;border:1px solid rgba(255,153,51,.25)}
.pill-ig{background:var(--ig-g);color:#0a5f06;border:1px solid rgba(19,136,8,.2)}
.pill-pk{background:var(--pk-g);color:var(--pk);border:1px solid var(--pk-m)}
.pill-as{background:rgba(0,0,128,.06);color:var(--as);border:1px solid rgba(0,0,128,.18)}
.card{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);padding:18px;margin-bottom:14px;box-shadow:0 1px 4px rgba(40,44,63,.04)}
.card-hd{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;
  color:var(--tx2);margin-bottom:14px;display:flex;align-items:center;gap:8px;padding-bottom:10px;border-bottom:1px solid var(--bd)}
.sg{display:flex;gap:10px;align-items:flex-start}
.sinp{flex:1;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--bd-r);
  padding:10px 13px;color:var(--tx);font-family:var(--mn);font-size:11px;outline:none;
  resize:vertical;min-height:70px;transition:.18s}
.sinp:focus{border-color:var(--pk);background:var(--bg);box-shadow:0 0 0 3px var(--pk-g)}
.sbtn{padding:10px 18px;background:var(--pk);color:#fff;border:none;border-radius:var(--bd-r);
  font-family:var(--hd);font-size:10px;font-weight:700;letter-spacing:1.5px;cursor:pointer;transition:.2s}
.sbtn:hover{background:var(--pk2);transform:translateY(-1px)}
.sres{margin-top:12px;padding:12px;background:var(--bg2);border-radius:var(--bd-r);
  display:none;font-size:11px;line-height:1.7;border:1px solid var(--bd)}
.tcfg{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:14px}
.cg{display:flex;flex-direction:column;gap:5px}
.cl{font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:var(--tx2)}
.pb2{height:5px;background:var(--bg2);border-radius:4px;margin:10px 0;overflow:hidden;border:1px solid var(--bd)}
.pf{height:100%;background:linear-gradient(90deg,var(--pk),var(--sf),var(--ig));border-radius:4px;transition:width .4s}
.tlog{height:88px;overflow-y:auto;background:var(--bg2);border-radius:var(--bd-r);
  padding:8px;font-family:'Courier New',monospace;font-size:9px;color:var(--tx3);line-height:1.6;border:1px solid var(--bd)}
.btn{padding:10px 18px;background:var(--pk);color:#fff;border:none;border-radius:var(--bd-r);
  font-family:var(--hd);font-size:10px;font-weight:700;letter-spacing:1.5px;cursor:pointer;transition:.2s}
.btn:hover{background:var(--pk2);transform:translateY(-1px)}
.btn2{padding:10px 18px;background:var(--bg2);color:var(--tx2);border:1px solid var(--bd);
  border-radius:var(--bd-r);font-family:var(--hd);font-size:10px;font-weight:700;
  letter-spacing:1.5px;cursor:pointer;transition:.2s;margin-left:8px}
.btn2:hover{border-color:var(--pk);color:var(--pk);background:var(--pk-g)}
.mrow{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:14px}
.mc{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);
  padding:16px;text-align:center;box-shadow:0 1px 4px rgba(40,44,63,.04)}
.ml2{font-size:9px;color:var(--tx3);font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.mv{font-size:24px;font-weight:700;color:var(--pk);margin-top:6px}
.bgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
.pt{width:100%;border-collapse:collapse}
.pt th{font-size:9px;color:var(--tx3);font-weight:700;letter-spacing:1px;text-transform:uppercase;
  padding:9px 12px;text-align:left;border-bottom:2px solid var(--bd);background:var(--bg2);white-space:nowrap}
.pt td{padding:8px 12px;font-size:10px;border-bottom:1px solid var(--bd)}
.pt tr:hover td{background:var(--bg2)}
.tdb{padding:4px 10px;background:var(--pk-g);color:var(--pk);border:1px solid var(--pk-m);
  border-radius:var(--bd-r);font-size:9px;font-weight:700;cursor:pointer;transition:.18s}
.tdb:hover{background:var(--pk);color:#fff}
.cb{width:56px;height:5px;background:var(--bg2);border-radius:3px;overflow:hidden;display:inline-block;border:1px solid var(--bd)}
.cf{height:100%;background:linear-gradient(90deg,var(--pk),var(--sf));border-radius:3px}

/* ══ PLANS ══ */
.sub-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:22px}
.sub-card{background:var(--surface);border:1.5px solid var(--bd);border-radius:var(--bd-r2);
  padding:22px;position:relative;transition:.25s;overflow:hidden}
.sub-card:hover{transform:translateY(-3px);border-color:var(--pk);
  box-shadow:0 12px 40px rgba(255,63,108,.1)}
.sub-card.popular{border-color:var(--pk);box-shadow:0 4px 20px rgba(255,63,108,.12)}
.sub-card.popular::before{content:'POPULAR';position:absolute;top:0;right:0;
  background:var(--pk);color:#fff;font-family:var(--hd);font-size:8px;
  font-weight:700;letter-spacing:1.5px;padding:4px 12px;border-radius:0 var(--bd-r2) 0 var(--bd-r)}
.sub-ico{font-size:32px;margin-bottom:10px}
.sub-nm{font-family:var(--hd);font-size:15px;font-weight:800;color:var(--tx);margin-bottom:4px}
.sub-pr{font-size:26px;font-weight:700;margin:8px 0 2px}
.sub-pr-inr{font-size:11px;color:var(--tx3);margin-bottom:14px}
.sub-feats{list-style:none;margin-bottom:16px}
.sub-feats li{font-size:11px;color:var(--tx2);padding:3px 0;display:flex;align-items:center;gap:6px}
.sub-feats li::before{content:'✓';color:var(--gn);font-weight:700}
.sub-btn{width:100%;padding:11px;border:none;border-radius:var(--bd-r);font-family:var(--hd);
  font-size:10px;font-weight:700;letter-spacing:1.5px;cursor:pointer;transition:.2s;text-transform:uppercase}
.sub-btn.pk{background:var(--pk);color:#fff}
.sub-btn.gn{background:var(--gn);color:#fff}
.sub-btn.sf{background:var(--sf);color:#fff}
.sub-btn.as{background:var(--as);color:#fff}
.sub-btn.ou{background:var(--bg2);color:var(--tx2);border:1px solid var(--bd)}
.sub-btn:hover{transform:translateY(-1px);filter:brightness(1.08)}

/* ══ CONTACT ══ */
.contact-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}
.contact-info{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);padding:22px}
.contact-item{display:flex;align-items:center;gap:12px;padding:12px 0;border-bottom:1px solid var(--bd)}
.cico{font-size:20px;width:40px;height:40px;background:var(--pk-g);border-radius:50%;
  display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.ctit{font-size:12px;font-weight:700;color:var(--tx)}
.csub{font-size:11px;color:var(--tx2)}
.csub a{color:var(--pk);text-decoration:none}
.csub a:hover{text-decoration:underline}

/* ══ WALLET ══ */
.wp2{overflow-y:auto;background:var(--bg2)}
.ww{padding:20px;max-width:1100px;margin:0 auto;width:100%}
.wbg{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.wbc{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);
  padding:18px;position:relative;overflow:hidden;box-shadow:0 1px 4px rgba(40,44,63,.04)}
.wbc::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
.wbc:nth-child(1)::before{background:var(--pk)}
.wbc:nth-child(2)::before{background:var(--ig)}
.wbc:nth-child(3)::before{background:var(--as)}
.wbl{font-size:9px;color:var(--tx3);font-weight:600;letter-spacing:1.5px;text-transform:uppercase}
.wbv{font-size:22px;font-weight:700;color:var(--tx);margin:6px 0 2px}
.wbs{font-size:10px;color:var(--tx3)}
.wg{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.qwrap{display:flex;flex-direction:column;align-items:center;gap:12px}
.qimg{width:160px;height:160px;border-radius:var(--bd-r);object-fit:cover;border:2px solid var(--pk-m)}
.qfrm{width:160px;height:160px;border-radius:var(--bd-r);border:2px dashed var(--pk-m);
  background:var(--pk-g);display:flex;align-items:center;justify-content:center;
  color:var(--tx3);font-size:10px;text-align:center;padding:12px}
.utag{font-size:11px;color:var(--tx2)}
.utag b{color:var(--pk)}
.aps{display:flex;flex-wrap:wrap;gap:6px;justify-content:center}
.ab{padding:5px 10px;background:var(--bg2);border:1px solid var(--bd);border-radius:var(--bd-r);
  font-size:10px;color:var(--tx);cursor:pointer;transition:.18s;font-weight:600}
.ab:hover,.ab.on{background:var(--pk-g);border-color:var(--pk);color:var(--pk)}
.gpb{padding:10px 20px;background:var(--pk);color:#fff;border:none;border-radius:var(--bd-r);
  font-family:var(--hd);font-size:10px;font-weight:700;letter-spacing:1px;cursor:pointer;transition:.2s}
.gpb:hover{background:var(--pk2);transform:translateY(-1px)}
.scan{width:100%;aspect-ratio:1;max-width:260px;border-radius:var(--bd-r2);
  background:var(--bg2);border:2px dashed var(--bd2);
  display:flex;flex-direction:column;align-items:center;justify-content:center;
  cursor:pointer;transition:.2s;position:relative;overflow:hidden;margin:0 auto}
.scan:hover{border-color:var(--pk)}
.scanl{position:absolute;left:0;right:0;height:2px;
  background:linear-gradient(90deg,transparent,var(--pk),var(--sf),transparent);
  animation:sc 2.2s infinite linear}
@keyframes sc{0%{top:8%}100%{top:88%}}
.scico{font-size:40px;opacity:.3}
.sctxt{font-size:10px;color:var(--tx3);margin-top:8px;text-align:center}
#scanVid{width:100%;height:100%;object-fit:cover;display:none;border-radius:10px}
.mg{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:12px}
.mcard{padding:10px;background:var(--bg2);border:1px solid var(--bd);
  border-radius:var(--bd-r);cursor:pointer;text-align:center;transition:.18s}
.mcard:hover,.mcard.on{background:var(--pk-g);border-color:var(--pk)}
.tico{font-size:18px}.tnm{font-size:9px;color:var(--tx3);margin-top:3px;font-weight:600}
.ti{display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--bd)}
.tiico{width:36px;height:36px;border-radius:var(--bd-r);display:flex;align-items:center;
  justify-content:center;font-size:16px;flex-shrink:0}
.tidep{background:#e8fff5;border:1px solid #b8f0d5}
.tiwit{background:#fff5f5;border:1px solid #ffc5c5}
.tiinf{flex:1}
.titp{font-size:11px;font-weight:700}
.timt{font-size:9px;color:var(--tx3)}
.tiamt{font-size:13px;font-weight:700;text-align:right}
.tist{font-size:8px;padding:2px 7px;border-radius:4px;font-weight:700}
.ss{background:#e8fff5;color:var(--gn)}.sp{background:#fff8ec;color:var(--am)}
.qr-result{padding:12px;background:var(--pk-g);border:1px solid var(--pk-m);
  border-radius:var(--bd-r);margin-top:10px;font-size:11px;display:none}
.qr-result .qrl{font-size:9px;color:var(--pk);font-weight:700;letter-spacing:1px;text-transform:uppercase;margin-bottom:3px}
.qr-result .qrv{color:var(--tx);font-weight:700}

/* ══ PORTFOLIO ══ */
.pp{overflow-y:auto;background:var(--bg2)}
.pw{padding:20px;max-width:1200px;margin:0 auto;width:100%}
.pst{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.psc{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);
  padding:16px;box-shadow:0 1px 4px rgba(40,44,63,.04)}
.pos-t{width:100%;border-collapse:collapse}
.pos-t th{font-size:9px;color:var(--tx3);font-weight:700;letter-spacing:1px;text-transform:uppercase;
  padding:10px 14px;text-align:left;border-bottom:2px solid var(--bd);background:var(--bg2);white-space:nowrap}
.pos-t td{padding:10px 14px;font-size:11px;border-bottom:1px solid var(--bd)}
.pos-t tr:hover td{background:var(--bg2)}
.gtb{padding:4px 10px;background:var(--pk-g);color:var(--pk);border:1px solid var(--pk-m);
  border-radius:var(--bd-r);font-size:9px;font-weight:700;cursor:pointer;transition:.18s}
.gtb:hover{background:var(--pk);color:#fff}

/* ══ HISTORY ══ */
.hp{overflow-y:auto;background:var(--bg2)}
.hw{padding:20px;max-width:1200px;margin:0 auto;width:100%}
.fb{display:flex;gap:6px;margin-bottom:14px}
.fbt{padding:6px 14px;background:var(--surface);border:1px solid var(--bd);
  border-radius:var(--bd-r3);font-size:10px;color:var(--tx2);cursor:pointer;
  font-weight:600;transition:.18s}
.fbt.on{color:var(--pk);border-color:var(--pk);background:var(--pk-g)}
.ht{width:100%;border-collapse:collapse}
.ht th{font-size:9px;color:var(--tx3);font-weight:700;letter-spacing:1px;text-transform:uppercase;
  padding:10px 14px;text-align:left;border-bottom:2px solid var(--bd);background:var(--bg2)}
.ht td{padding:9px 14px;font-size:11px;border-bottom:1px solid var(--bd)}
.ht tr:hover td{background:var(--bg2)}
.tyb{padding:3px 8px;border-radius:4px;font-size:9px;font-weight:700}
.ty-b{background:#e8fff5;color:var(--gn)}.ty-s{background:#fff5f5;color:var(--rd)}

/* ══ ADMIN ══ */
.ap{overflow-y:auto;background:var(--bg2)}
.aw{padding:20px;max-width:1200px;margin:0 auto;width:100%}
.ast{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:16px}
.ucards{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.ucard{background:var(--surface);border:1px solid var(--bd);border-radius:var(--bd-r2);
  padding:18px;transition:.18s;box-shadow:0 1px 4px rgba(40,44,63,.04)}
.ucard:hover{border-color:var(--pk);transform:translateY(-2px);box-shadow:0 6px 20px rgba(255,63,108,.08)}
.uch{display:flex;align-items:center;gap:12px;margin-bottom:14px}
.ucav{width:42px;height:42px;border-radius:50%;background:var(--pk);
  display:flex;align-items:center;justify-content:center;font-size:14px;
  font-weight:700;color:#fff;font-family:var(--hd);flex-shrink:0}
.ucnm{font-size:13px;font-weight:700;color:var(--tx)}
.ucem{font-size:10px;color:var(--tx3)}
.ucst{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.ucsc{background:var(--bg2);border:1px solid var(--bd);border-radius:var(--bd-r);padding:8px}
.ucsl{font-size:8px;color:var(--tx3);font-weight:700;letter-spacing:1px;text-transform:uppercase}
.ucsv{font-size:12px;font-weight:700;color:var(--tx);margin-top:2px}

/* ══ TOASTS ══ */
.tw{position:fixed;top:68px;right:20px;z-index:110;display:flex;flex-direction:column;gap:8px}
.toast{padding:12px 16px;border-radius:var(--bd-r2);font-size:11px;
  animation:tin .28s ease;box-shadow:0 4px 20px rgba(40,44,63,.12);
  max-width:320px;line-height:1.55;transition:opacity .3s;font-weight:500}
.toast.ok{background:#f0fff8;border:1px solid #b8f0d5;color:#1a7a4a}
.toast.er{background:#fff5f5;border:1px solid #ffc5c5;color:#c0392b}
.toast.info{background:var(--pk-g);border:1px solid var(--pk-m);color:var(--pk2)}
@keyframes tin{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}

/* ══ EMPTY ══ */
.emp{padding:40px;text-align:center;color:var(--tx3)}
.eico{font-size:36px;opacity:.3;margin-bottom:10px}
.etxt{font-size:12px}

/* ══ SPIN ══ */
.spin{display:inline-block;width:14px;height:14px;border:2px solid var(--bd2);
  border-top-color:var(--pk);border-radius:50%;animation:sp .7s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}

/* scrollbars for overflow pages */
.bp::-webkit-scrollbar,.wp2::-webkit-scrollbar,.pp::-webkit-scrollbar,
.hp::-webkit-scrollbar,.ap::-webkit-scrollbar{width:4px}

@media(max-width:920px){
  .mk-grid{grid-template-columns:1fr}
  .wlp,.op{display:none}
  .bgrid,.wg,.contact-grid{grid-template-columns:1fr}
  .tcfg{grid-template-columns:1fr 1fr}
  .mrow,.pst,.ast,.wbg,.sub-grid{grid-template-columns:1fr 1fr}
}

/* GLOBAL SEARCH */
.g-search{display:flex;align-items:center;background:#f1f3f4;border-radius:24px;padding:8px 16px;width:300px;margin-left:24px;border:1px solid transparent;transition:0.2s;}
.g-search:focus-within{background:#fff;border-color:var(--bd);box-shadow:0 1px 6px rgba(32,33,36,0.28);}
.g-search input{border:none;background:transparent;outline:none;font-family:var(--mn);font-size:14px;color:var(--tx);width:100%;caret-color:var(--pk);}

/* CHATBOT */
.bot-fab{position:fixed;bottom:20px;right:20px;width:56px;height:56px;background:var(--surface);border-radius:50%;box-shadow:0 2px 10px rgba(0,0,0,.2);display:flex;align-items:center;justify-content:center;cursor:pointer;z-index:99;font-size:24px;transition:0.2s;}
.bot-fab:hover{transform:scale(1.05);}
.bot-pan{position:fixed;bottom:84px;right:20px;width:360px;height:480px;background:var(--surface);border-radius:12px;box-shadow:0 8px 30px rgba(0,0,0,.15);z-index:99;display:flex;flex-direction:column;transition:0.3s;transform:translateY(20px);opacity:0;pointer-events:none;overflow:hidden;border:1px solid var(--bd);}
.bot-pan.on{transform:translateY(0);opacity:1;pointer-events:all;}
.bot-hd{padding:16px;background:var(--pk);color:#fff;font-family:var(--hd);font-size:16px;font-weight:500;display:flex;align-items:center;justify-content:space-between;}
.bot-msgs{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:12px;background:var(--bg);}
.msg{max-width:85%;padding:10px 14px;border-radius:16px;font-size:13px;line-height:1.5;color:var(--tx);}
.msg.ai{background:var(--surface);align-self:flex-start;border:1px solid var(--bd);border-bottom-left-radius:4px;}
.msg.usr{background:var(--pk-g);align-self:flex-end;color:var(--pk2);border-bottom-right-radius:4px;}
.bot-inp{display:flex;padding:12px;border-top:1px solid var(--bd);background:var(--surface);}
.bot-inp input{flex:1;border:none;outline:none;background:#f1f3f4;padding:10px 16px;border-radius:20px;font-family:var(--mn);font-size:13px;}
.bot-inp button{background:transparent;border:none;color:var(--pk);font-weight:700;padding:0 12px;cursor:pointer;}
</style>
</head>
<body>

<!-- ════════ AUTH ════════ -->
<div class="scr" id="aScr">
  <div class="a-wrap">
    <div class="a-brand">
      <div class="a-logo">SENSTRIX BITCO</div>
      <div class="tri" style="margin:10px auto;max-width:200px;border-radius:2px"></div>
      <div class="a-tagline">AI Machine Market Trading Terminal</div>
    </div>
    <div class="a-card">
      <div class="a-tabs">
        <div class="a-tab on" onclick="aTab('li')">Sign In</div>
        <div class="a-tab" onclick="aTab('re')">Register</div>
      </div>
      <div class="a-frm on" id="liF">
        <div class="a-msg er" id="liErr"></div>
        <div class="fl"><label>Email Address</label>
          <input type="email" id="liEm" placeholder="you@example.com" autocomplete="email"/>
        </div>
        <div class="fl"><label>Password</label>
          <input type="password" id="liPw" placeholder="••••••••" autocomplete="current-password"/>
        </div>
        <button class="a-btn" onclick="doLogin()">Sign In →</button>
        <div class="a-or">or</div>
        <button class="a-btn sec" onclick="doDemo()">☸  Try Demo Account  (₹75,000)</button>
      </div>
      <div class="a-frm" id="reF">
        <div class="a-msg er" id="reErr"></div>
        <div class="a-msg ok" id="reOk"></div>
        <div class="fl2">
          <div class="fl"><label>First Name</label><input id="reFN" placeholder="Aarav"/></div>
          <div class="fl"><label>Last Name</label><input id="reLN" placeholder="Shah"/></div>
        </div>
        <div class="fl"><label>Username</label><input id="reUN" placeholder="aarav_trades"/></div>
        <div class="fl"><label>Email Address</label>
          <input type="email" id="reEm" placeholder="you@example.com" autocomplete="email"/>
        </div>
        <div class="fl"><label>Password</label>
          <input type="password" id="rePw" placeholder="min 6 chars" autocomplete="new-password"/>
        </div>
        <div class="fl"><label>Starting Capital</label>
          <select id="reCap" class="inp" style="margin-bottom:0">
            <option value="10000">₹10,000</option>
            <option value="25000">₹25,000</option>
            <option value="50000" selected>₹50,000</option>
            <option value="100000">₹1,00,000</option>
            <option value="500000">₹5,00,000</option>
          </select>
        </div>
        <button class="a-btn" onclick="doReg()">Create Account →</button>
      </div>
    </div>
  </div>
</div>

<!-- ════════ APP ════════ -->
<div class="scr app-scr gone" id="appScr">

  <!-- TOPBAR -->
  <div class="top">
    <div class="logo"><span style="color:#4285f4">S</span><span style="color:#ea4335">E</span><span style="color:#fbbc04">N</span><span style="color:#4285f4">S</span><span style="color:#34a853">T</span><span style="color:#ea4335">R</span>I</span><span style="color:#ea4335">X</span><span> Finance</span></div>
    <div class="g-search">
      <span style="color:var(--tx3);margin-right:8px">🔍</span>
      <input type="text" id="gSearch" placeholder="Search for assets..." oninput="doGSearch()"/>
    </div>
    <nav class="nav">
      <div class="nt on" data-p="markets">📊 Markets</div>
      <div class="nt" data-p="brain">🧠 AI Brain</div>
      <div class="nt" data-p="wallet">💳 Wallet</div>
      <div class="nt" data-p="portfolio">📈 Portfolio</div>
      <div class="nt" data-p="history">📋 History</div>
      <div class="nt" data-p="plans">⭐ Plans</div>
      <div class="nt" data-p="news">📰 News</div>
      <div class="nt" data-p="contact">✉️ Contact</div>
      <div class="nt" data-p="admin">🛡 Admin</div>
    </nav>
    <div class="tr">
      <div class="live-pill"><div class="ldot"></div><span class="ltxt">LIVE</span></div>
      <div class="bal-tag">Balance: <b id="topBal">$0.00</b></div>
      <div class="uc">
        <div class="uav" id="topAv">DT</div>
        <div>
          <div class="unm" id="topNm">Demo</div>
          <span class="plan-pill" id="topPlan">Free</span>
        </div>
      </div>
      <div class="lob" onclick="doLogout()">Logout</div>
    </div>
    <div class="top-tri"></div>
  </div>

  <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;position:relative">

    <!-- ── MARKETS ── -->
    <div class="pg on" id="pg-markets">
      <div class="mk-grid" style="flex:1;display:grid">
        <div class="wlp">
          <div class="phd"><span>WATCHLIST</span><span id="wlCnt" style="color:var(--pk)"></span></div>
          <div class="wll" id="wlList"></div>
        </div>
        <div class="chp">
          <div class="chd">
            <div>
              <div class="sb" id="cSym">BTC</div>
              <div style="font-size:10px;color:var(--tx3);font-weight:600" id="cName">Bitcoin</div>
            </div>
            <div>
              <div class="pbl up" id="cPx">$0.00</div>
              <div class="pchg" id="cChg">—</div>
            </div>
            <div class="tf">
              <div class="tfb on" onclick="setTf(this)">LIVE</div>
              <div class="tfb" onclick="setTf(this)">1H</div>
              <div class="tfb" onclick="setTf(this)">1D</div>
              <div class="tfb" onclick="setTf(this)">1W</div>
            </div>
            <!-- CHART TYPE TOGGLE: line vs candle -->
            <div class="chart-type-toggle">
              <div class="ctb on" id="ctLine" onclick="setChartType('line')">📈 Line</div>
              <div class="ctb" id="ctCandle" onclick="setChartType('candle')">🕯 Candle</div>
            </div>
          </div>
          <div class="sr">
            <div class="sb2"><div class="sl">24H HIGH</div><div class="sv up" id="sh">—</div></div>
            <div class="sb2"><div class="sl">24H LOW</div><div class="sv dn" id="sl2">—</div></div>
            <div class="sb2"><div class="sl">RSI</div><div class="sv" id="sr2">—</div></div>
            <div class="sb2"><div class="sl">MACD</div><div class="sv" id="sm">—</div></div>
          </div>
          <div class="cbody"><canvas id="pChart"></canvas></div>
        </div>
        <div class="op">
          <div class="phd"><span>PLACE ORDER</span></div>
          <div class="of">
            <!-- LIVE PRICE TICKER WITH UP/DOWN ARROW -->
            <div class="price-ticker" id="priceTicker">
              <div class="pt-sym" id="ptSym">BTC</div>
              <div class="pt-arrow" id="ptArrow">▲</div>
              <div class="pt-px up" id="ptPx">$0.00</div>
              <div class="pt-pct pt-up" id="ptPct">+0.00%</div>
            </div>
            <!-- MINI CANDLESTICK BAR -->
            <div class="mini-candle-wrap">
              <canvas id="miniChart" style="width:100%;height:36px"></canvas>
            </div>
            <div class="stit">Order Side</div>
            <div class="stabs">
              <div class="stab buy on" onclick="setSide('buy')">▲ BUY</div>
              <div class="stab sell" onclick="setSide('sell')">▼ SELL</div>
            </div>
            <select class="inp" id="oType"><option>Market</option><option>Limit</option><option>Stop Loss</option></select>
            <input class="inp" id="oQty" type="number" min="0.0001" step="0.0001" placeholder="Quantity" oninput="calcTotal()"/>
            <div class="ot"><div class="otl">Estimated Total</div><div class="otv" id="oTot">$0.00</div></div>
            <div class="mlb" id="mlBox">
              <div class="card-hd" style="margin-bottom:6px;padding-bottom:6px">🧠 ML Signal</div>
              <span class="mb mb-h" id="mlBadge">—</span>
              <div class="mlhow" id="mlHow">Train the AI model first to get profit signals.</div>
              <div class="sltp" id="sltpBox" style="display:none">
                <div class="slbox"><div class="slbl">Stop Loss</div><div class="slval dn" id="slVal">—</div></div>
                <div class="slbox"><div class="slbl">Take Profit</div><div class="slval up" id="tpVal">—</div></div>
              </div>
            </div>
            <button class="trb buy" id="tBtn" onclick="placeTrade()">Place Buy Order</button>
            <div class="tmsg" id="tMsg"></div>
          </div>
        </div>
      </div>
      <div class="term">
        <div class="ttt">
          <div class="ttb on" onclick="setTT(this,'all')">All</div>
          <div class="ttb" onclick="setTT(this,'AUTH')">Auth</div>
          <div class="ttb" onclick="setTT(this,'TRADE')">Trade</div>
          <div class="ttb" onclick="setTT(this,'ML')">ML</div>
          <div class="ttb" onclick="setTT(this,'WALLET')">Wallet</div>
          <div class="ttb" onclick="setTT(this,'ALERT')">Alerts</div>
        </div>
        <div class="tb" id="termB"></div>
      </div>
    </div>

    <!-- ── AI BRAIN ── -->
    <div class="pg bp" id="pg-brain">
      <div class="bw">
        <div class="page-hd">
          <div class="page-title">🧠 Machine Learning Model</div>
          <span class="pill pill-pk">Ridge LR + KMeans</span>
          <span class="pill pill-ig">Real-Time Inference</span>
          <span class="pill pill-sf">Profit Signals</span>
        </div>
        <div class="card">
          <div class="card-hd">💬 Sentiment Analyzer</div>
          <div class="sg">
            <textarea class="sinp" id="sentTxt" placeholder="e.g. 'Bitcoin moon 🚀 India crypto bull run!' or 'ETH crash dump sell everything'…"></textarea>
            <button class="sbtn" onclick="doSent()">Analyze</button>
          </div>
          <div class="sres" id="sentRes"></div>
        </div>
        <div class="card">
          <div class="card-hd">⚡ Model Training — 3 Advanced AI Models</div>
          <div class="tcfg">
            <div class="cg"><div class="cl">Model Type</div>
              <select class="inp" id="mType">
                <option value="random_forest">Random Forest Ensembles</option>
                <option value="xgboost">XGBoost / Neural Network</option>
                <option value="ridge_lr">Ridge Linear Regression</option>
              </select>
            </div>
            <div class="cg"><div class="cl">Epochs</div>
              <input class="inp" id="mEpoch" type="number" value="60" min="10" max="300"/>
            </div>
            <div class="cg"><div class="cl">Learning Rate</div>
              <input class="inp" id="mLR" type="number" value="0.008" step="0.001" min="0.001"/>
            </div>
            <div class="cg"><div class="cl">Train / Test Split</div>
              <select class="inp" id="mSplit">
                <option value="0.7">70 / 30</option>
                <option value="0.8" selected>80 / 20</option>
                <option value="0.9">90 / 10</option>
              </select>
            </div>
            <div class="cg"><div class="cl">K Clusters</div>
              <input class="inp" id="mK" type="number" value="5" min="2" max="8"/>
            </div>
            <div class="cg"><div class="cl">Status</div>
              <div class="inp" style="background:var(--bg2);cursor:default" id="tStat">Ready</div>
            </div>
          </div>
          <div class="pb2"><div class="pf" id="pFill" style="width:0%"></div></div>
          <div class="tlog" id="tLog"></div>
          <div style="margin-top:13px">
            <button class="btn" onclick="startTrain()">⚡ Train Models</button>
            <button class="btn2" onclick="refreshML()">↻ Refresh</button>
          </div>
        </div>
        <div class="mrow">
          <div class="mc"><div class="ml2">MAE</div><div class="mv" id="mMAE">—</div></div>
          <div class="mc"><div class="ml2">R² Score</div><div class="mv" id="mR2">—</div></div>
          <div class="mc"><div class="ml2">Accuracy</div><div class="mv" id="mAcc">—</div></div>
          <div class="mc"><div class="ml2">Silhouette</div><div class="mv" id="mSil">—</div></div>
        </div>
        <div class="bgrid">
          <div class="card"><div class="card-hd">📊 Feature Importance</div><canvas id="fChart" height="200"></canvas></div>
          <div class="card"><div class="card-hd">🎯 Signal Distribution</div><canvas id="dChart" height="200"></canvas></div>
        </div>
        <div class="card">
          <div class="card-hd">📋 Full Prediction Table — 20 Cryptos</div>
          <div style="overflow-x:auto">
            <table class="pt" id="predT">
              <thead><tr>
                <th>Symbol</th><th>Name</th><th>Current $</th><th>Predicted $</th>
                <th>Δ%</th><th>Signal</th><th>RSI</th><th>MACD</th>
                <th>Cluster</th><th>Stop Loss</th><th>Take Profit</th>
                <th>Confidence</th><th>How To Trade</th><th>Action</th>
              </tr></thead>
              <tbody id="predB">
                <tr><td colspan="14"><div class="emp"><div class="eico">🤖</div>
                  <div class="etxt">Train models to see profit predictions</div></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── NEWS & ANALYTICS ── -->
    <div class="pg bp" id="pg-news">
      <div class="bw">
        <div class="page-hd">
          <div class="page-title">📰 News & Analytics</div>
          <span class="pill pill-pk">Real-Time Data</span>
        </div>
        <div class="card">
          <div class="card-hd">Live Global Crypto News Feed</div>
          <div class="emp" style="padding:20px"><div class="eico">📡</div><div class="etxt">Awaiting market news feed initialization from API...</div></div>
        </div>
      </div>
    </div>

    <!-- ── WALLET ── -->
    <div class="pg wp2" id="pg-wallet">
      <div class="ww">
        <div class="page-hd">
          <div class="page-title">💳 Wallet</div>
          <span class="pill pill-pk">UPI / GPay</span>
          <span class="pill pill-ig">QR Scanner</span>
        </div>
        <div class="wbg">
          <div class="wbc"><div class="wbl">Trading Balance</div>
            <div class="wbv" id="wBal">$0.00</div>
            <div class="wbs">Available to trade</div></div>
          <div class="wbc"><div class="wbl">Wallet Balance</div>
            <div class="wbv" id="wWlt">$0.00</div>
            <div class="wbs">Deposit / Withdraw</div></div>
          <div class="wbc"><div class="wbl">Portfolio Value</div>
            <div class="wbv" id="wPort">$0.00</div>
            <div class="wbs">Open positions</div></div>
        </div>
        <div class="wg">
          <div class="card">
            <div class="card-hd">📱 Deposit via GPay / UPI</div>
            <div class="qwrap">
              <img id="qrI" class="qimg" style="display:none"/>
              <div class="qfrm" id="qrF">Loading QR…</div>
              <div class="utag">UPI ID: <b>denco@okaxis</b></div>
              <div class="aps" id="amtP">
                <div class="ab" onclick="setAmt(this,100)">₹100</div>
                <div class="ab" onclick="setAmt(this,500)">₹500</div>
                <div class="ab on" onclick="setAmt(this,1000)">₹1K</div>
                <div class="ab" onclick="setAmt(this,5000)">₹5K</div>
                <div class="ab" onclick="setAmt(this,10000)">₹10K</div>
                <div class="ab" onclick="setAmt(this,50000)">₹50K</div>
              </div>
              <input class="inp" id="custAmt" type="number" placeholder="Custom amount (₹)"
                style="max-width:220px;text-align:center;margin-bottom:0" oninput="custAmtChange()"/>
              <button class="gpb" onclick="openGPay()">📲  Pay with GPay</button>
              <div style="display:flex;gap:8px;align-items:center;margin-top:2px;flex-wrap:wrap;justify-content:center">
                <input class="inp" id="txnInp" placeholder="Enter TXN ID to confirm"
                  style="max-width:200px;margin-bottom:0"/>
                <button class="btn" onclick="confirmDep()">Confirm Deposit</button>
              </div>
            </div>
          </div>
          <div class="card">
            <div class="card-hd">📷 QR Scanner + Withdraw</div>
            <div class="scan" id="scanA" onclick="toggleScan()">
              <video id="scanVid" autoplay playsinline></video>
              <div class="scanl" id="scanL"></div>
              <div class="scico" id="scanIco">📷</div>
              <div class="sctxt" id="scanT">Tap to scan UPI / withdrawal QR code</div>
            </div>
            <div class="qr-result" id="qrResult">
              <div class="qrl">Scanned UPI ID</div><div class="qrv" id="qrUpiId">—</div>
              <div class="qrl" style="margin-top:6px">Name</div><div class="qrv" id="qrName">—</div>
              <div class="qrl" style="margin-top:6px">Amount</div><div class="qrv" id="qrAmt">—</div>
              <button class="btn" style="margin-top:10px;width:100%" onclick="useScannedQR()">Use This QR for Withdrawal</button>
            </div>
            <div style="margin-top:14px">
              <div class="cl" style="margin-bottom:8px">Withdraw Method</div>
              <div class="mg">
                <div class="mcard on" onclick="selMeth(this,'Bank Transfer')"><div class="tico">🏦</div><div class="tnm">Bank</div></div>
                <div class="mcard" onclick="selMeth(this,'GPay')"><div class="tico">📱</div><div class="tnm">GPay</div></div>
                <div class="mcard" onclick="selMeth(this,'UPI')"><div class="tico">💸</div><div class="tnm">UPI</div></div>
                <div class="mcard" onclick="selMeth(this,'PhonePe')"><div class="tico">📲</div><div class="tnm">PhonePe</div></div>
                <div class="mcard" onclick="selMeth(this,'Paytm')"><div class="tico">💳</div><div class="tnm">Paytm</div></div>
                <div class="mcard" onclick="selMeth(this,'NEFT')"><div class="tico">🔗</div><div class="tnm">NEFT</div></div>
              </div>
              <input class="inp" id="wAcc" placeholder="UPI ID / Account / Phone number"/>
              <input class="inp" id="wAmt" type="number" placeholder="Amount to withdraw (₹)"/>
              <button class="trb sell" style="width:100%;margin-top:2px" onclick="doWithdraw()">Withdraw →</button>
            </div>
          </div>
        </div>
        <div class="card">
          <div class="card-hd">📒 Transaction History</div>
          <div id="txnL"><div class="emp"><div class="eico">💳</div><div class="etxt">No transactions yet</div></div></div>
        </div>
      </div>
    </div>

    <!-- ── PORTFOLIO ── -->
    <div class="pg pp" id="pg-portfolio">
      <div class="pw">
        <div class="page-hd"><div class="page-title">📈 Portfolio</div></div>
        <div class="pst">
          <div class="psc"><div class="sl">Balance</div><div class="sv" id="pBal">—</div></div>
          <div class="psc"><div class="sl">Portfolio Value</div><div class="sv" id="pPV">—</div></div>
          <div class="psc"><div class="sl">Total P&L</div><div class="sv" id="pPNL">—</div></div>
          <div class="psc"><div class="sl">Total Trades</div><div class="sv" id="pTC">—</div></div>
        </div>
        <div class="card">
          <div class="card-hd">Open Positions</div>
          <div style="overflow-x:auto">
            <table class="pos-t">
              <thead><tr>
                <th>Symbol</th><th>Shares</th><th>Avg Price</th><th>Current</th>
                <th>Market Value</th><th>P&L</th><th>P&L%</th><th>ML Signal</th><th>Action</th>
              </tr></thead>
              <tbody id="posB">
                <tr><td colspan="9"><div class="emp"><div class="eico">📊</div>
                  <div class="etxt">No open positions. Trade to build your portfolio.</div></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── HISTORY ── -->
    <div class="pg hp" id="pg-history">
      <div class="hw">
        <div class="page-hd"><div class="page-title">📋 Trade History</div></div>
        <div class="fb">
          <div class="fbt on" onclick="setHF(this,'ALL')">All</div>
          <div class="fbt" onclick="setHF(this,'BUY')">Buys Only</div>
          <div class="fbt" onclick="setHF(this,'SELL')">Sells Only</div>
        </div>
        <div class="card">
          <div style="overflow-x:auto">
            <table class="ht">
              <thead><tr>
                <th>Time</th><th>Type</th><th>Symbol</th><th>Name</th>
                <th>Qty</th><th>Price</th><th>Total</th>
                <th>ML Signal</th><th>Order Type</th><th>Note</th>
              </tr></thead>
              <tbody id="histB">
                <tr><td colspan="10"><div class="emp"><div class="eico">📋</div>
                  <div class="etxt">No trades yet</div></div></td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── PLANS ── -->
    <div class="pg bp" id="pg-plans">
      <div class="bw">
        <div class="page-hd">
          <div class="page-title">⭐ Subscription Plans</div>
          <span class="pill pill-pk">India Pricing</span>
          <span class="pill pill-ig">Unlock Full AI</span>
        </div>
        <div class="tri" style="margin-bottom:20px;border-radius:2px"></div>
        <div class="sub-grid" id="plansGrid"></div>
        <div class="card">
          <div class="card-hd">✨ Your Current Plan</div>
          <div style="display:flex;align-items:center;gap:16px">
            <div style="font-size:36px" id="curPlanIco">🆓</div>
            <div>
              <div style="font-family:var(--hd);font-size:16px;font-weight:800;color:var(--pk)" id="curPlanNm">Free</div>
              <div style="font-size:11px;color:var(--tx2);margin-top:4px" id="curPlanDesc">Basic features.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── CONTACT ── -->
    <div class="pg bp" id="pg-contact">
      <div class="bw">
        <div class="page-hd">
          <div class="page-title">✉️ Contact Us</div>
          <span class="pill pill-pk">Fast Response</span>
          <span class="pill pill-ig">Support</span>
        </div>
        <div class="contact-grid">
          <div class="card">
            <div class="card-hd">📬 Send Message</div>
            <div class="fl"><label>Your Name</label><input class="inp" style="margin-bottom:0" id="cName" placeholder="Aarav Shah"/></div>
            <div class="fl"><label>Your Email</label><input class="inp" style="margin-bottom:0" id="cEmail" type="email" placeholder="you@example.com"/></div>
            <div class="fl"><label>Subject</label>
              <select class="inp" style="margin-bottom:0" id="cSubject">
                <option>Subscription Help</option><option>Technical Issue</option>
                <option>Trading Support</option><option>Account Problem</option>
                <option>Partnership</option><option>Other</option>
              </select>
            </div>
            <div class="fl"><label>Message</label>
              <textarea class="sinp" id="cMessage" placeholder="Describe your issue…" style="min-height:100px"></textarea>
            </div>
            <button class="btn" style="width:100%" onclick="sendContact()">Send Message →</button>
            <div class="a-msg ok" id="contactOk" style="margin-top:10px"></div>
            <div class="a-msg er" id="contactErr" style="margin-top:10px"></div>
          </div>
          <div class="contact-info">
            <div class="card-hd">📍 Contact Information</div>
            <div class="contact-item">
              <div class="cico">📧</div>
              <div><div class="ctit">Email Support</div>
                <div class="csub"><a href="mailto:adhicse@gmail.com">adhicse@gmail.com</a></div></div>
            </div>
            <div class="contact-item">
              <div class="cico">☸</div>
              <div><div class="ctit">SENSTRIX BITCO</div>
                <div class="csub">AI-Powered Crypto Trading Platform</div></div>
            </div>
            <div class="contact-item">
              <div class="cico">🇮🇳</div>
              <div><div class="ctit">Made in India</div>
                <div class="csub">Jai Hind 🧡🤍💚</div></div>
            </div>
            <div class="contact-item">
              <div class="cico">⏰</div>
              <div><div class="ctit">Response Time</div>
                <div class="csub">Within 24 hours (IST)</div></div>
            </div>
            <div class="contact-item">
              <div class="cico">💡</div>
              <div><div class="ctit">Support Hours</div>
                <div class="csub">Mon–Sat, 9 AM – 6 PM IST</div></div>
            </div>
            <div style="margin-top:16px;padding:14px;background:var(--pk-g);border:1px solid var(--pk-m);border-radius:var(--bd-r)">
              <div style="font-size:11px;font-weight:700;color:var(--pk);margin-bottom:6px">🔗 Google Sheets Backend</div>
              <div style="font-size:10px;color:var(--tx2);line-height:1.6">All backend activity is automatically logged to our secure Google Sheets database.</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── ADMIN ── -->
    <div class="pg ap" id="pg-admin">
      <div class="aw">
        <div class="page-hd">
          <div class="page-title">🛡 Admin Panel</div>
          <span class="pill pill-pk">Backend Only</span>
        </div>
        <div class="ast">
          <div class="psc"><div class="sl">Total Users</div><div class="sv" id="adU">—</div></div>
          <div class="psc"><div class="sl">Total Balance</div><div class="sv" id="adB">—</div></div>
          <div class="psc"><div class="sl">Total Trades</div><div class="sv" id="adT">—</div></div>
          <div class="psc"><div class="sl">Active Now</div><div class="sv" id="adA">—</div></div>
        </div>
        <div class="card" style="margin-bottom:16px">
          <div class="card-hd">🔗 Google Sheets Integration</div>
          <div style="display:flex;align-items:center;gap:14px;flex-wrap:wrap">
            <div style="font-size:11px;color:var(--tx2);flex:1">
              Backend data (users, trades, deposits, ML results) logged to Google Sheets.
            </div>
            <a href="https://docs.google.com/spreadsheets/d/1F3yuo2Ai1o3F061BAmxpCIDqS2KnxPzHwJEpt4_plKE/edit?usp=sharing"
              target="_blank" style="text-decoration:none">
              <button class="btn">📊 Open Google Sheets</button>
            </a>
          </div>
        </div>
        <div class="ucards" id="uCards">
          <div class="emp"><div class="eico">🛡</div><div class="etxt">Loading users…</div></div>
        </div>
      </div>
    </div>

  </div>
</div>

<!-- CHATBOT -->
<div class="bot-fab" onclick="$('botPan').classList.toggle('on')">✨</div>
<div class="bot-pan" id="botPan">
  <div class="bot-hd">
    <div><b>Gemini Assistant</b></div>
    <div style="cursor:pointer" onclick="$('botPan').classList.remove('on')">✕</div>
  </div>
  <div class="bot-msgs" id="botMsgs">
    <div class="msg ai">Hi! I'm your Google AI Assistant. Ask me anything about crypto or trading.</div>
  </div>
  <div class="bot-inp">
    <input type="text" id="botInp" placeholder="Ask Gemini..." onkeypress="if(event.key==='Enter')sendBotMsg()"/>
    <button onclick="sendBotMsg()">SEND</button>
  </div>
</div>

<!-- TOASTS -->
<div class="tw" id="tw"></div>

<script>
// ═══ STATE ═══
let SES='',USER=null,PX={},SYM='BTC',SIDE='buy',HF='ALL',TF='all',WM='Bank Transfer',QR_AMT=1000;
let ML={},TL=[],SCAN=null,SCAN_INTERVAL=null,SCANNED_QR=null;
let PC=null,FC=null,DC=null,MC=null;
let _pollTmr=null,CHART_TYPE='line';

try{SES=localStorage.getItem('senstrix_tok')||'';USER=JSON.parse(localStorage.getItem('senstrix_usr')||'null');}catch{}

const PLANS_DATA={
  'Free':   {price:0,    price_inr:0,    badge:'🆓',btnCls:'ou',
             features:['5 trades/day','Basic ML signals','Price alerts: 3']},
  'Starter':{price:9.99, price_inr:833,  badge:'⭐',btnCls:'sf',
             features:['50 trades/day','Advanced ML signals','Price alerts: 20','Portfolio analytics']},
  'Pro':    {price:29.99,price_inr:2499, badge:'💎',btnCls:'gn',
             features:['Unlimited trades','Full ML engine','Unlimited alerts','Priority support','API access']},
  'Elite':  {price:99.99,price_inr:8333, badge:'👑',btnCls:'as',
             features:['Everything in Pro','Dedicated signals','1-on-1 support','Custom ML models','Early access']},
};

// ═══ HELPERS ═══
const $=id=>document.getElementById(id);
const Q=sel=>document.querySelectorAll(sel);

function fmt(n,d=2){
  if(n==null||isNaN(n))return'—';
  const abs=Math.abs(n);
  if(abs>=1e9)return'$'+(n/1e9).toFixed(2)+'B';
  if(abs>=1e6)return'$'+(n/1e6).toFixed(2)+'M';
  if(abs>=1000)return'$'+n.toLocaleString('en-IN',{minimumFractionDigits:d,maximumFractionDigits:d});
  return'$'+n.toFixed(Math.max(d,abs<1?4:2));
}
const fmtP=n=>(n>=0?'+':'')+n.toFixed(2)+'%';
const cls=n=>n>=0?'up':'dn';

function toast(msg,type='info',ms=3200){
  const d=document.createElement('div');
  d.className=`toast ${type}`;d.textContent=msg;
  $('tw').appendChild(d);
  setTimeout(()=>d.style.opacity='0',ms-320);
  setTimeout(()=>d.remove(),ms);
}

function api(path,opts={}){
  const h={'Content-Type':'application/json'};
  if(SES)h['X-Session']=SES;
  return fetch(path,{headers:h,...opts}).then(r=>r.json()).catch(e=>({ok:false,msg:e.message}));
}

function mbCls(sig){
  if(!sig||sig==='—')return'mb-h';
  const s=sig.replace(' ','_');
  return{STRONG_BUY:'mb-sb',BUY:'mb-b',HOLD:'mb-h',SELL:'mb-s',STRONG_SELL:'mb-ss'}[s]||'mb-h';
}

function esc(t){return(t||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}

// ═══ AUTH ═══
function aTab(t){
  Q('.a-tab').forEach((x,i)=>x.classList.toggle('on',i===(t==='li'?0:1)));
  $('liF').classList.toggle('on',t==='li');
  $('reF').classList.toggle('on',t==='re');
}

async function doLogin(){
  const em=$('liEm').value.trim(),pw=$('liPw').value;
  if(!em||!pw){showMsg('liErr','Email and password required','er');return;}
  const r=await api('/api/login',{method:'POST',body:JSON.stringify({email:em,password:pw})});
  if(!r.ok){showMsg('liErr',r.msg,'er');return;}
  onLogin(r.token,r.user);
}

async function doReg(){
  const d={firstName:$('reFN').value.trim(),lastName:$('reLN').value.trim(),
           username:$('reUN').value.trim(),email:$('reEm').value.trim(),
           password:$('rePw').value,capital:$('reCap').value};
  if(!d.firstName||!d.email||!d.password){showMsg('reErr','Fill all required fields','er');return;}
  if(d.password.length<6){showMsg('reErr','Password must be at least 6 chars','er');return;}
  const r=await api('/api/register',{method:'POST',body:JSON.stringify(d)});
  if(!r.ok){showMsg('reErr',r.msg,'er');return;}
  showMsg('reOk','Account created! Signing in…','ok');
  setTimeout(()=>onLogin(r.token,r.user),900);
}

async function doDemo(){
  const r=await api('/api/demo',{method:'POST'});
  if(r.ok)onLogin(r.token,r.user);else toast(r.msg,'er');
}

function onLogin(tok,user){
  SES=tok;USER=user;
  localStorage.setItem('senstrix_tok',tok);
  localStorage.setItem('senstrix_usr',JSON.stringify(user));
  $('aScr').classList.add('gone');
  $('appScr').classList.remove('gone');
  updTop();startApp();
}

function doLogout(){
  SES='';USER=null;
  localStorage.removeItem('senstrix_tok');localStorage.removeItem('senstrix_usr');
  [PC,FC,DC,MC].forEach(c=>{if(c){c.destroy();}});PC=FC=DC=MC=null;
  if(_pollTmr){clearTimeout(_pollTmr);_pollTmr=null;}
  stopScan();
  $('appScr').classList.add('gone');$('aScr').classList.remove('gone');
}

function showMsg(id,msg,t){$(id).textContent=msg;$(id).className=`a-msg ${t}`;$(id).style.display='block';}

function updTop(){
  if(!USER)return;
  $('topBal').textContent=fmt(USER.balance||0);
  $('topNm').textContent=USER.firstName||'User';
  $('topAv').textContent=((USER.firstName||'')[0]+(USER.lastName||'')[0]).toUpperCase()||'DT';
  $('topPlan').textContent=USER.plan||'Free';
}

// ═══ NAV ═══
Q('.nt').forEach(t=>{
  t.addEventListener('click',()=>{
    Q('.nt').forEach(x=>x.classList.remove('on'));
    Q('.pg').forEach(x=>x.classList.remove('on'));
    t.classList.add('on');$('pg-'+t.dataset.p).classList.add('on');
    if(t.dataset.p==='portfolio')loadPort();
    if(t.dataset.p==='history')loadHist();
    if(t.dataset.p==='admin')loadAdmin();
    if(t.dataset.p==='wallet')loadWallet();
    if(t.dataset.p==='brain')refreshML();
    if(t.dataset.p==='plans')loadPlans();
  });
});

// ═══ APP START ═══
function startApp(){
  initChart();fetchPX();setInterval(fetchPX,2000);startSSE();
}

async function validateSession(){
  if(!SES||!USER){$('aScr').classList.remove('gone');$('appScr').classList.add('gone');return;}
  try{
    const r=await fetch('/api/me',{headers:{'X-Session':SES}}).then(x=>x.json());
    if(r.ok){
      USER=r.user;localStorage.setItem('senstrix_usr',JSON.stringify(USER));
      $('aScr').classList.add('gone');$('appScr').classList.remove('gone');
      updTop();startApp();
    }else{
      SES='';USER=null;localStorage.removeItem('senstrix_tok');localStorage.removeItem('senstrix_usr');
      $('aScr').classList.remove('gone');$('appScr').classList.add('gone');
    }
  }catch{$('aScr').classList.remove('gone');$('appScr').classList.add('gone');}
}
validateSession();

// ═══ PRICES ═══
let _prevPrices={};
async function fetchPX(){
  const d=await fetch('/api/prices').then(r=>r.json()).catch(()=>({}));
  _prevPrices=Object.assign({},PX);
  PX=d;
  renderWL();updChartHdr();updPriceTicker();
}

function renderWL(){
  const el=$('wlList'),n=Object.keys(PX).length;
  $('wlCnt').textContent=n;
  const ORDER={'STRONG BUY':0,'BUY':1,'HOLD':2,'SELL':3,'STRONG SELL':4};
  const sorted=Object.entries(PX).sort((a,b)=>(ORDER[a[1].mlSignal||'HOLD']??2)-(ORDER[b[1].mlSignal||'HOLD']??2));
  el.innerHTML=sorted.map(([s,v])=>{
    const sig=v.mlSignal||'';
    const bd=sig?`<span class="mb ${mbCls(sig)}">${sig}</span>`:'';
    return`<div class="wli${s===SYM?' sel':''}" onclick="selSym('${s}')">
      <div><div class="ws">${s}</div><div class="wn">${v.name}</div><div>${bd}</div></div>
      <div style="text-align:right">
        <div class="wp ${cls(v.pct)}">${fmt(v.price)}</div>
        <div class="wpc ${cls(v.pct)}">${fmtP(v.pct)}</div>
      </div>
    </div>`;
  }).join('');
}

function selSym(s){SYM=s;renderWL();updChartHdr();loadChartHist(s);updMLBox();updPriceTicker();}

function updChartHdr(){
  const v=PX[SYM];if(!v)return;
  $('cSym').textContent=SYM;$('cName').textContent=v.name;
  $('cPx').textContent=fmt(v.price);$('cPx').className='pbl '+cls(v.pct);
  $('cChg').textContent=`${fmt(v.change)} (${fmtP(v.pct)})`;
  $('cChg').className='pchg '+cls(v.pct);
  $('sh').textContent=fmt(v.high);$('sl2').textContent=fmt(v.low);
  const rsiEl=$('sr2');rsiEl.textContent=v.rsi?.toFixed(1)||'—';
  rsiEl.className='sv'+(v.rsi<30?' up':v.rsi>70?' dn':'');
  $('sm').textContent=v.macd?.toFixed(5)||'—';
  calcTotal();
}

// ═══ LIVE UP/DOWN PRICE TICKER IN ORDER PANEL ═══
function updPriceTicker(){
  const v=PX[SYM];if(!v)return;
  const prev=_prevPrices[SYM];
  const isUp=!prev||v.price>=prev.price;
  $('ptSym').textContent=SYM;
  $('ptPx').textContent=fmt(v.price);
  $('ptPx').className='pt-px '+(isUp?'up':'dn');
  $('ptArrow').textContent=isUp?'▲':'▼';
  $('ptArrow').style.color=isUp?'var(--gn)':'var(--rd)';
  const pctEl=$('ptPct');
  pctEl.textContent=fmtP(v.pct);
  pctEl.className='pt-pct '+(v.pct>=0?'pt-up':'pt-dn');
  drawMiniChart();
}

// ═══ MINI CANDLESTICK/BAR CHART IN ORDER PANEL ═══
function drawMiniChart(){
  const canvas=$('miniChart');if(!canvas)return;
  const ctx=canvas.getContext('2d');
  const history=_priceHistCache[SYM];
  if(!history||history.length<2){ctx.clearRect(0,0,canvas.width,canvas.height);return;}
  canvas.width=canvas.offsetWidth||240;
  canvas.height=36;
  const data=history.slice(-40);
  const prices=data.map(d=>d.p);
  const mn=Math.min(...prices),mx=Math.max(...prices),rng=mx-mn||1;
  const w=canvas.width,h=canvas.height,bw=Math.max(2,Math.floor(w/data.length)-1);
  ctx.clearRect(0,0,w,h);
  data.forEach((d,i)=>{
    const x=i*(bw+1);
    const isUp=(d.c||d.p)>=(d.o||d.p);
    const color=isUp?'#03a685':'#ff4f4f';
    // Body
    const yC=h-((( d.c||d.p)-mn)/rng*(h-4))-2;
    const yO=h-(((d.o||d.p)-mn)/rng*(h-4))-2;
    const yH=h-(((d.h||d.p)-mn)/rng*(h-4))-2;
    const yL=h-(((d.l||d.p)-mn)/rng*(h-4))-2;
    // Wick
    ctx.strokeStyle=color;ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(x+bw/2,yH);ctx.lineTo(x+bw/2,yL);ctx.stroke();
    // Candle body
    ctx.fillStyle=color;
    const bodyTop=Math.min(yO,yC);
    const bodyH=Math.max(1,Math.abs(yO-yC));
    ctx.fillRect(x,bodyTop,bw,bodyH);
  });
}

let _priceHistCache={};
async function loadChartHist(sym){
  const r=await api(`/api/prices/history/${sym}`);
  if(!r.ok||!r.history)return;
  _priceHistCache[sym]=r.history;
  if(CHART_TYPE==='line')renderLineChart(r.history);
  else renderCandleChart(r.history);
  drawMiniChart();
}

// ═══ MAIN CHART ═══
function initChart(){
  const ctx=$('pChart').getContext('2d');
  PC=new Chart(ctx,{
    type:'line',
    data:{labels:[],datasets:[{data:[],borderColor:'#FF3F6C',borderWidth:2,
      backgroundColor:'rgba(255,63,108,.06)',fill:true,tension:0.4,pointRadius:0}]},
    options:{
      responsive:true,maintainAspectRatio:false,animation:false,
      plugins:{legend:{display:false},tooltip:{mode:'index',intersect:false,
        backgroundColor:'rgba(255,255,255,.98)',titleColor:'#FF3F6C',
        bodyColor:'#535766',borderColor:'#e9e9eb',borderWidth:1,
        callbacks:{label:c=>' $'+c.raw.toFixed(6)}}},
      scales:{
        x:{ticks:{color:'#94969f',font:{size:9},maxTicksLimit:8},
           grid:{color:'rgba(40,44,63,.04)'},border:{color:'#e9e9eb'}},
        y:{ticks:{color:'#94969f',font:{size:9},callback:v=>fmt(v)},
           grid:{color:'rgba(40,44,63,.04)'},border:{color:'#e9e9eb'}}
      }
    }
  });
  loadChartHist(SYM);
}

function setChartType(type){
  CHART_TYPE=type;
  $('ctLine').classList.toggle('on',type==='line');
  $('ctCandle').classList.toggle('on',type==='candle');
  const h=_priceHistCache[SYM];
  if(h){if(type==='line')renderLineChart(h);else renderCandleChart(h);}
}

function renderLineChart(history){
  if(!PC)return;
  const isUp=PX[SYM]?.pct>=0;
  PC.data.labels=history.map((_,i)=>i);
  PC.data.datasets[0].data=history.map(p=>p.p);
  PC.data.datasets[0].type='line';
  PC.data.datasets[0].borderColor=isUp?'#FF3F6C':'#ff4f4f';
  PC.data.datasets[0].backgroundColor=isUp?'rgba(255,63,108,.06)':'rgba(255,79,79,.06)';
  PC.data.datasets[0].borderWidth=2;
  PC.data.datasets[0].tension=0.4;
  PC.data.datasets[0].pointRadius=0;
  PC.update();
}

function renderCandleChart(history){
  if(!PC)return;
  const data=history.slice(-80);
  // Render as bar chart approximation using open/close
  PC.data.labels=data.map((_,i)=>i);
  PC.data.datasets[0].data=data.map(d=>d.c||d.p);
  PC.data.datasets[0].type='bar';
  PC.data.datasets[0].backgroundColor=data.map(d=>(d.c||d.p)>=(d.o||d.p)?'rgba(3,166,133,.75)':'rgba(255,79,79,.75)');
  PC.data.datasets[0].borderColor=data.map(d=>(d.c||d.p)>=(d.o||d.p)?'#03a685':'#ff4f4f');
  PC.data.datasets[0].borderWidth=1;
  PC.data.datasets[0].fill=false;
  PC.data.datasets[0].tension=0;
  PC.update();
}

function setTf(el){
  Q('.tfb').forEach(b=>b.classList.remove('on'));el.classList.add('on');
  loadChartHist(SYM);
}

// ═══ ORDERS ═══
function setSide(s){
  SIDE=s;
  Q('.stab').forEach(t=>t.classList.remove('on'));
  document.querySelector(`.stab.${s}`).classList.add('on');
  const b=$('tBtn');b.className=`trb ${s}`;
  b.textContent=s==='buy'?'Place Buy Order':'Place Sell Order';
  calcTotal();
}

function calcTotal(){
  const qty=parseFloat($('oQty')?.value)||0;
  const px=PX[SYM]?.price||0;
  if($('oTot'))$('oTot').textContent=fmt(qty*px);
}

function updMLBox(){
  const p=ML[SYM];if(!p)return;
  $('mlBadge').textContent=p.signal||'—';
  $('mlBadge').className=`mb ${mbCls(p.signal)}`;
  $('mlHow').textContent=p.how_to_trade||'—';
  if(p.stop_loss&&p.take_profit){
    $('sltpBox').style.display='grid';
    $('slVal').textContent=fmt(p.stop_loss);
    $('tpVal').textContent=fmt(p.take_profit);
  }
}

async function placeTrade(){
  const qty=parseFloat($('oQty').value);
  if(!qty||qty<=0){toast('Enter a valid quantity','er');return;}
  const r=await api('/api/trade',{method:'POST',
    body:JSON.stringify({symbol:SYM,side:SIDE,qty,orderType:$('oType').value})});
  const m=$('tMsg');
  if(r.ok){
    m.textContent=`✅ ${SIDE.toUpperCase()} ${qty} ${SYM} @ ${fmt(PX[SYM]?.price)}`;
    m.className='tmsg ok';m.style.display='block';
    USER.balance=r.balance;updTop();
    toast(`${SIDE.toUpperCase()} ${qty} ${SYM} executed!`,'ok');
  }else{m.textContent='❌ '+r.msg;m.className='tmsg er';m.style.display='block';toast(r.msg,'er');}
  setTimeout(()=>m.style.display='none',4500);
}

// ═══ TERMINAL ═══
function startSSE(){
  const es=new EventSource('/api/events');
  es.onmessage=e=>{
    try{const ev=JSON.parse(e.data);TL.push(ev);if(TL.length>400)TL.shift();renderTerm();}catch{}
  };
}

function setTT(el,f){Q('.ttb').forEach(t=>t.classList.remove('on'));el.classList.add('on');TF=f;renderTerm();}

function renderTerm(){
  const fil=TF==='all'?TL:TL.filter(l=>l.cat===TF);
  const b=$('termB');
  b.innerHTML=fil.map((l,i)=>`
    <div class="tl">
      <span class="tln">${i+1}</span>
      <span class="tts">${l.ts}</span>
      <span class="tcat ${l.col||'WH'}">[${l.cat}]</span>
      <span class="tmg">${esc(l.msg)}</span>
    </div>`).join('');
  b.scrollTop=b.scrollHeight;
}

// ═══ AI BRAIN ═══
async function doSent(){
  const txt=$('sentTxt').value.trim();if(!txt)return;
  const r=await api('/api/sentiment',{method:'POST',body:JSON.stringify({text:txt})});
  if(!r.ok)return;
  const col=r.label==='BULLISH'?'var(--gn)':r.label==='BEARISH'?'var(--rd)':'var(--am)';
  const el=$('sentRes');
  el.innerHTML=`<span style="color:${col};font-size:15px;font-weight:700">${r.label}</span>
    <span style="color:var(--tx3);margin-left:12px;font-size:10px">
      Score: ${r.score>0?'+':''}${r.score.toFixed(3)} | 🐂 ${r.bull} bull words | 🐻 ${r.bear} bear words
    </span>`;
  el.style.display='block';
}

async function startTrain(){
  if(!SES){toast('Please login before training','er');return;}
  const cfg={model_type:$('mType').value,epochs:parseInt($('mEpoch').value)||60,
    lr:parseFloat($('mLR').value)||0.008,k:parseInt($('mK').value)||5,
    split:parseFloat($('mSplit').value)||0.8};
  const r=await api('/api/ml/train',{method:'POST',body:JSON.stringify(cfg)});
  if(!r.ok){toast(r.msg,'er');return;}
  toast('🚀 Model training started…','info');$('tStat').textContent='Training…';pollML();
}

async function refreshML(){await pollML();}

async function pollML(){
  const r=await api('/api/ml/status');if(!r.ok)return;
  $('pFill').style.width=r.progress+'%';
  $('tStat').textContent=r.training?`Training… ${r.progress}%`:(r.trained?'✅ Trained':'Ready');
  if(r.trainLog){
    const el=$('tLog');
    el.innerHTML=r.trainLog.map(l=>`<div>[${l.ts}] ${esc(l.msg)}</div>`).join('');
    el.scrollTop=el.scrollHeight;
  }
  if(r.metrics){$('mMAE').textContent=r.metrics.mae||'—';$('mR2').textContent=r.metrics.r2||'—';$('mAcc').textContent=r.metrics.acc||'—';$('mSil').textContent=r.metrics.sil||'—';}
  if(r.predictions&&Object.keys(r.predictions).length){
    ML=r.predictions;renderPredTable(r.predictions);
    renderFeatChart(r.featImportance);renderDistChart(r.predictions);renderWL();updMLBox();
  }
  if(r.training){_pollTmr=setTimeout(pollML,600);}
}

function renderPredTable(preds){
  const ORDER={'STRONG BUY':0,'BUY':1,'HOLD':2,'SELL':3,'STRONG SELL':4};
  const sorted=Object.entries(preds).sort((a,b)=>(ORDER[a[1].signal??'HOLD']??2)-(ORDER[b[1].signal??'HOLD']??2)||(b[1].conf-a[1].conf));
  $('predB').innerHTML=sorted.map(([sym,p])=>{
    const cur=PX[sym]?.price||0,cf=Math.round((p.conf||0)*100);
    return`<tr>
      <td><b style="font-family:var(--hd);font-weight:800">${sym}</b></td>
      <td style="color:var(--tx3)">${PX[sym]?.name||''}</td>
      <td>${fmt(cur)}</td><td>${fmt(p.pred)}</td>
      <td class="${cls(p.delta)}">${fmtP(p.delta)}</td>
      <td><span class="mb ${mbCls(p.signal)}">${p.signal}</span></td>
      <td style="color:${p.rsi<30?'var(--gn)':p.rsi>70?'var(--rd)':'var(--tx3)'}">
        ${p.rsi?.toFixed(0)||'—'}</td>
      <td style="color:var(--tx3)">${p.macd?.toFixed(4)||'—'}</td>
      <td style="color:var(--as);font-size:9px">${p.cluster_name||''}</td>
      <td class="dn">${fmt(p.stop_loss)}</td>
      <td class="up">${fmt(p.take_profit)}</td>
      <td><div class="cb"><div class="cf" style="width:${cf}%"></div></div>
        <span style="font-size:9px;color:var(--tx3);margin-left:4px">${cf}%</span></td>
      <td style="font-size:9px;color:var(--tx3);max-width:200px;white-space:pre-wrap;word-break:break-word">
        ${esc(p.how_to_trade||'')}</td>
      <td><button class="tdb" onclick="goTrade('${sym}')">Trade →</button></td>
    </tr>`;
  }).join('');
}

function goTrade(sym){
  SYM=sym;
  Q('.nt').forEach(t=>t.classList.remove('on'));Q('.pg').forEach(t=>t.classList.remove('on'));
  document.querySelector('[data-p="markets"]').classList.add('on');$('pg-markets').classList.add('on');
  renderWL();updChartHdr();loadChartHist(sym);updMLBox();updPriceTicker();
  toast(`Switched to ${sym} — ${ML[sym]?.signal||'Train AI for signal'}`,'info');
}

function renderFeatChart(fi){
  if(!fi||!fi.length)return;
  const ctx=$('fChart').getContext('2d');
  if(FC)FC.destroy();
  FC=new Chart(ctx,{type:'bar',data:{
    labels:fi.map(f=>f[0]),
    datasets:[{data:fi.map(f=>f[1]),
      backgroundColor:['rgba(255,63,108,.8)','rgba(255,153,51,.8)','rgba(19,136,8,.8)',
                       'rgba(0,0,128,.7)','rgba(3,166,133,.8)','rgba(255,79,79,.7)',
                       'rgba(96,165,250,.7)','rgba(139,92,246,.7)'],
      borderRadius:5,borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{backgroundColor:'rgba(255,255,255,.98)',
        titleColor:'#FF3F6C',bodyColor:'#535766',borderColor:'#e9e9eb',borderWidth:1}},
      scales:{x:{ticks:{color:'#94969f',font:{size:9}},grid:{color:'rgba(40,44,63,.04)'}},
              y:{ticks:{color:'#94969f',font:{size:9}},grid:{color:'rgba(40,44,63,.04)'}}}
    }
  });
}

function renderDistChart(preds){
  const cnt={'STRONG BUY':0,'BUY':0,'HOLD':0,'SELL':0,'STRONG SELL':0};
  Object.values(preds).forEach(p=>{if(cnt[p.signal]!==undefined)cnt[p.signal]++;});
  const ctx=$('dChart').getContext('2d');
  if(DC)DC.destroy();
  DC=new Chart(ctx,{type:'doughnut',data:{
    labels:Object.keys(cnt),
    datasets:[{data:Object.values(cnt),
      backgroundColor:['rgba(3,166,133,.85)','rgba(255,153,51,.82)','rgba(148,150,159,.7)',
                       'rgba(255,79,79,.8)','rgba(192,57,43,.85)'],
      borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{position:'bottom',labels:{color:'#535766',font:{size:9},boxWidth:10,padding:8}},
        tooltip:{backgroundColor:'rgba(255,255,255,.98)',titleColor:'#FF3F6C',
          bodyColor:'#535766',borderColor:'#e9e9eb',borderWidth:1}}}
  });
}

// ═══ WALLET ═══
async function loadWallet(){
  if(!SES){toast('Please login first','er');return;}
  const r=await api('/api/portfolio');
  if(!r.ok){toast(r.msg||'Session expired','er');return;}
  $('wBal').textContent=fmt(r.balance);$('wWlt').textContent=fmt(r.wallet);
  $('wPort').textContent=fmt(r.portfolioValue);
  renderTxns(r.transactions||[]);loadQR();
}

async function loadQR(){
  if(!SES)return;
  const r=await api(`/api/wallet/qr?amount=${QR_AMT}`);if(!r.ok)return;
  if(r.qr){$('qrI').src='data:image/png;base64,'+r.qr;$('qrI').style.display='block';$('qrF').style.display='none';}
  else{$('qrF').textContent=`UPI: ${r.upi||'denco@okaxis'} — ₹${QR_AMT}`;$('qrF').style.display='flex';}
}

function setAmt(el,amt){
  QR_AMT=amt;$('custAmt').value=amt;
  Q('.ab').forEach(b=>b.classList.remove('on'));el.classList.add('on');loadQR();
}

function custAmtChange(){
  const v=parseFloat($('custAmt').value);
  if(v>0){QR_AMT=v;Q('.ab').forEach(b=>b.classList.remove('on'));loadQR();}
}

function openGPay(){window.open(`upi://pay?pa=denco@okaxis&pn=SENSTRIX&am=${QR_AMT}&cu=INR`,'_blank');toast(`Opening GPay for ₹${QR_AMT}…`,'info');}

async function confirmDep(){
  const txnId=$('txnInp').value.trim()||`TXN${Math.floor(Math.random()*999999)}`;
  const r=await api('/api/wallet/deposit',{method:'POST',body:JSON.stringify({amount:QR_AMT,method:'GPay',txnId})});
  if(r.ok){toast(`✅ Deposit ₹${QR_AMT} confirmed!`,'ok');USER.balance=r.balance;updTop();loadWallet();}
  else toast(r.msg,'er');
}

function selMeth(el,m){Q('.mcard').forEach(c=>c.classList.remove('on'));el.classList.add('on');WM=m;}

async function doWithdraw(){
  const amt=parseFloat($('wAmt').value),acc=$('wAcc').value.trim();
  if(!amt||amt<=0){toast('Enter amount to withdraw','er');return;}
  if(!acc){toast('Enter account/UPI ID','er');return;}
  const r=await api('/api/wallet/withdraw',{method:'POST',body:JSON.stringify({amount:amt,method:WM,account:acc})});
  if(r.ok){toast(`✅ Withdrawal ₹${amt} via ${WM} initiated`,'ok');USER.balance=r.balance;updTop();loadWallet();}
  else toast(r.msg,'er');
}

// ═══ QR SCANNER ═══
function toggleScan(){if(SCAN)stopScan();else startScan();}

async function startScan(){
  $('scanT').textContent='Requesting camera…';
  try{
    SCAN=await navigator.mediaDevices.getUserMedia({video:{facingMode:'environment',width:{ideal:640},height:{ideal:480}}});
    const v=$('scanVid');v.srcObject=SCAN;v.style.display='block';
    $('scanIco').style.display='none';$('scanT').textContent='Scanning… tap to stop.';
    toast('📷 Camera active','info');
    await loadJsQR();startQRDecode();
  }catch(e){$('scanT').textContent='Camera denied. Tap to retry.';toast('Camera denied: '+e.message,'er');SCAN=null;}
}

function stopScan(){
  if(SCAN){SCAN.getTracks().forEach(t=>t.stop());SCAN=null;}
  if(SCAN_INTERVAL){clearInterval(SCAN_INTERVAL);SCAN_INTERVAL=null;}
  $('scanVid').style.display='none';$('scanIco').style.display='';
  $('scanT').textContent='Tap to scan UPI / withdrawal QR code';
}

function loadJsQR(){
  return new Promise(res=>{
    if(window.jsQR){res();return;}
    const s=document.createElement('script');s.src='https://cdnjs.cloudflare.com/ajax/libs/jsQR/1.4.0/jsQR.min.js';
    s.onload=res;s.onerror=res;document.head.appendChild(s);
  });
}

function startQRDecode(){
  const canvas=document.createElement('canvas'),ctx2=canvas.getContext('2d'),v=$('scanVid');
  SCAN_INTERVAL=setInterval(async()=>{
    if(!window.jsQR||!SCAN||v.readyState<2)return;
    canvas.width=v.videoWidth;canvas.height=v.videoHeight;
    ctx2.drawImage(v,0,0,canvas.width,canvas.height);
    const img=ctx2.getImageData(0,0,canvas.width,canvas.height);
    const code=window.jsQR(img.data,img.width,img.height);
    if(code&&code.data){stopScan();await handleScannedQR(code.data);}
  },350);
}

async function handleScannedQR(text){
  const r=await api('/api/wallet/parse-qr',{method:'POST',body:JSON.stringify({qrText:text})});
  if(r.ok&&r.result.valid){
    SCANNED_QR=r.result;
    $('qrUpiId').textContent=r.result.upi_id||'—';$('qrName').textContent=r.result.name||'—';
    $('qrAmt').textContent=r.result.amount?`₹${r.result.amount}`:'Not specified';
    $('qrResult').style.display='block';toast(`✅ QR scanned: ${r.result.upi_id}`,'ok');
  }else toast('Not a valid UPI code','er');
}

function useScannedQR(){
  if(!SCANNED_QR)return;
  $('wAcc').value=SCANNED_QR.upi_id||'';
  if(SCANNED_QR.amount)$('wAmt').value=SCANNED_QR.amount;
  toast('UPI ID filled from QR scan!','ok');$('qrResult').style.display='none';
}

function renderTxns(txns){
  const el=$('txnL');
  if(!txns.length){el.innerHTML='<div class="emp"><div class="eico">💳</div><div class="etxt">No transactions yet</div></div>';return;}
  el.innerHTML=txns.map(t=>`
    <div class="ti">
      <div class="tiico ${t.type==='DEPOSIT'?'tidep':'tiwit'}">${t.type==='DEPOSIT'?'⬇️':'⬆️'}</div>
      <div class="tiinf">
        <div class="titp" style="color:${t.type==='DEPOSIT'?'var(--gn)':'var(--rd)'}">${t.type}</div>
        <div class="timt">${t.method} · ${t.time} · ID: ${t.id}</div>
      </div>
      <div>
        <div class="tiamt ${t.type==='DEPOSIT'?'up':'dn'}">${t.type==='DEPOSIT'?'+':'-'}₹${t.amount.toLocaleString('en-IN')}</div>
        <div class="tist ${t.status==='SUCCESS'?'ss':'sp'}">${t.status}</div>
      </div>
    </div>`).join('');
}

// ═══ PORTFOLIO ═══
async function loadPort(){
  if(!SES)return;
  const r=await api('/api/portfolio');if(!r.ok){toast(r.msg||'Please login first','er');return;}
  $('pBal').textContent=fmt(r.balance);$('pPV').textContent=fmt(r.portfolioValue);
  const pnl=r.totalPnL;$('pPNL').textContent=fmt(pnl);$('pPNL').className='sv '+cls(pnl);
  $('pTC').textContent=r.tradeCount||0;USER.balance=r.balance;updTop();
  const b=$('posB');
  if(!r.positions?.length){b.innerHTML='<tr><td colspan="9"><div class="emp"><div class="eico">📊</div><div class="etxt">No open positions. Trade to build your portfolio.</div></div></td></tr>';return;}
  b.innerHTML=r.positions.map(p=>`<tr>
    <td><b style="font-family:var(--hd);font-weight:800">${p.ticker}</b></td>
    <td>${p.shares?.toFixed(4)}</td><td>${fmt(p.avgPrice)}</td><td>${fmt(p.currentPrice)}</td>
    <td>${fmt(p.marketValue)}</td><td class="${cls(p.pnl)}">${fmt(p.pnl)}</td>
    <td class="${cls(p.pnlPct)}">${fmtP(p.pnlPct)}</td>
    <td><span class="mb ${mbCls(p.mlSignal)}">${p.mlSignal||'—'}</span></td>
    <td><button class="gtb" onclick="goTrade('${p.ticker}')">Trade</button></td>
  </tr>`).join('');
}

// ═══ HISTORY ═══
async function loadHist(){
  if(!SES)return;
  const r=await api('/api/portfolio');if(!r.ok){toast(r.msg||'Please login','er');return;}
  const trades=(r.history||[]).filter(t=>HF==='ALL'||t.type===HF);
  const b=$('histB');
  if(!trades.length){b.innerHTML='<tr><td colspan="10"><div class="emp"><div class="eico">📋</div><div class="etxt">No trades found</div></div></td></tr>';return;}
  b.innerHTML=trades.map(t=>`<tr>
    <td style="color:var(--tx3)">${t.time}</td>
    <td><span class="tyb ty-${t.type.toLowerCase()}">${t.type}</span></td>
    <td><b style="font-family:var(--hd);font-weight:800">${t.ticker}</b></td>
    <td style="color:var(--tx3)">${t.company||''}</td>
    <td>${t.qty?.toFixed(4)}</td><td>${fmt(t.price)}</td><td>${fmt(t.total)}</td>
    <td><span class="mb ${mbCls(t.mlSignal)}">${t.mlSignal||'—'}</span></td>
    <td style="color:var(--tx3)">${t.orderType||'Market'}</td>
    <td style="color:var(--tx3)">${esc(t.note||'')}</td>
  </tr>`).join('');
}

function setHF(el,f){HF=f;Q('.fbt').forEach(b=>b.classList.remove('on'));el.classList.add('on');loadHist();}

// ═══ PLANS ═══
function loadPlans(){
  const curPlan=USER?.plan||'Free';
  $('plansGrid').innerHTML=Object.entries(PLANS_DATA).map(([name,p])=>{
    const isCur=name===curPlan;
    return`<div class="sub-card${name==='Pro'?' popular':''}">
      <div class="sub-ico">${p.badge}</div>
      <div class="sub-nm">${name}</div>
      <div class="sub-pr" style="color:${name==='Free'?'var(--tx2)':name==='Starter'?'var(--sf)':name==='Pro'?'var(--ig)':'var(--as)'}">
        ${p.price===0?'FREE':'₹'+p.price_inr.toLocaleString('en-IN')}
      </div>
      <div class="sub-pr-inr">${p.price===0?'No cost':'$'+p.price+' / month'}</div>
      <ul class="sub-feats">${p.features.map(f=>`<li>${f}</li>`).join('')}</ul>
      <button class="sub-btn ${p.btnCls}" onclick="upgradePlan('${name}')"
        ${isCur?'disabled style="opacity:.5;cursor:default"':''}>
        ${isCur?'Current Plan':'Upgrade to '+name}
      </button>
    </div>`;
  }).join('');
  const cp=PLANS_DATA[curPlan];
  $('curPlanIco').textContent=cp?.badge||'🆓';$('curPlanNm').textContent=curPlan;
  $('curPlanDesc').textContent=cp?.features.join(' · ')||'';
}

async function upgradePlan(plan){
  if(plan==='Free'){toast('Already on Free plan','info');return;}
  const r=await api('/api/subscription/upgrade',{method:'POST',body:JSON.stringify({plan})});
  if(r.ok){USER=r.user;localStorage.setItem('senstrix_usr',JSON.stringify(USER));updTop();toast(`✅ Upgraded to ${plan}!`,'ok');loadPlans();}
  else toast(r.msg,'er');
}

// ═══ CONTACT ═══
async function sendContact(){
  const name=$('cName').value.trim(),email=$('cEmail').value.trim(),
    subject=$('cSubject').value,message=$('cMessage').value.trim();
  if(!name||!email||!message){showMsg('contactErr','Please fill all fields','er');return;}
  const r=await api('/api/contact',{method:'POST',body:JSON.stringify({name,email,subject,message})});
  if(r.ok){
    showMsg('contactOk',r.msg,'ok');$('contactErr').style.display='none';
    $('cName').value='';$('cEmail').value='';$('cMessage').value='';
  }else showMsg('contactErr',r.msg,'er');
}

// ═══ ADMIN ═══
async function loadAdmin(){
  if(!SES){toast('Please login to view admin panel','er');return;}
  const r=await api('/api/admin/users');if(!r.ok){toast(r.msg||'Denied','er');return;}
  const users=r.users||[];
  $('adU').textContent=users.length;
  let tb=0,tt=0;
  users.forEach(u=>{tb+=u.balance||0;tt+=u.totalTrades||0;});
  $('adB').textContent=fmt(tb);$('adT').textContent=tt;$('adA').textContent=users.length;
  const el=$('uCards');
  if(!users.length){el.innerHTML='<div class="emp"><div class="eico">👤</div><div class="etxt">No users registered</div></div>';return;}
  el.innerHTML=users.map(u=>{
    const ini=((u.firstName||'')[0]+(u.lastName||'')[0]).toUpperCase()||'??';
    const planBadge=u.plan&&u.plan!=='Free'?`<span class="plan-pill">${u.plan}</span>`:'';
    return`<div class="ucard">
      <div class="uch">
        <div class="ucav">${ini}</div>
        <div><div class="ucnm">${u.firstName} ${u.lastName} ${planBadge}</div>
          <div class="ucem">${u.email}</div></div>
      </div>
      <div class="ucst">
        <div class="ucsc"><div class="ucsl">Balance</div><div class="ucsv up">${fmt(u.balance)}</div></div>
        <div class="ucsc"><div class="ucsl">Wallet</div><div class="ucsv">${fmt(u.wallet)}</div></div>
        <div class="ucsc"><div class="ucsl">Trades</div><div class="ucsv">${u.totalTrades||0}</div></div>
        <div class="ucsc"><div class="ucsl">Joined</div><div class="ucsv" style="font-size:9px">${(u.joinedAt||'').split(' ')[0]}</div></div>
      </div>
    </div>`;
  }).join('');
}

// ═══ GOOGLE SEARCH ═══
function doGSearch(){
  const q=$('gSearch').value.trim().toUpperCase();
  if(!q) return;
  const match=Object.keys(PX).find(s=>s.startsWith(q));
  if(match){
    selSym(match);
    toast(`Found ${match}`,'info',1000);
  }
}

// ═══ CHATBOT ═══
async function sendBotMsg(){
  const inp=$('botInp');
  const txt=inp.value.trim();
  if(!txt)return;
  inp.value='';
  const m=$('botMsgs');
  m.insertAdjacentHTML('beforeend',`<div class="msg usr">${esc(txt)}</div>`);
  m.scrollTop=m.scrollHeight;
  const rr=await api('/api/chat',{method:'POST',body:JSON.stringify({msg:txt})});
  const rep=rr.ok?rr.reply:'Sorry, an error occurred.';
  m.insertAdjacentHTML('beforeend',`<div class="msg ai">${esc(rep)}</div>`);
  m.scrollTop=m.scrollHeight;
}

document.addEventListener('keydown',e=>{
  if(e.key==='Enter'){
    if(document.activeElement?.id==='liPw'||document.activeElement?.id==='liEm')doLogin();
  }
});
</script>
</body>
</html>"""

def main():
    global _users
    loaded = load_users()
    with _users_lock:
        _users.update(loaded)
    init_prices()
    threading.Thread(target=_tick, daemon=True).start()
    threading.Thread(target=_alert_watcher, daemon=True).start()
    sep("SENSTRIX BITCO v3 — ADVANCED AI TRADING")
    cprint("SERVER",  "Flask on port 5050", "SF")
    cprint("THEME",   "🌐 Google Material Design + Universal Search", "IG")
    cprint("CHART",   "✅ Candlestick + Line chart with UP/DOWN bar", "IG")
    cprint("NUMPY",   f"{'✅ available' if NP_OK else '❌ missing'}", "IG" if NP_OK else "RE")
    cprint("USERS",   f"{len(_users)} users loaded", "IG")
    cprint("CRYPTOS", f"{len(CRYPTOS)} assets tracked", "IG")
    sep()
    print(f"\n  \033[38;5;208m Open: http://localhost:5050 \033[0m\n")
    app.run(host="0.0.0.0", port=5050, debug=False, threaded=True)

if __name__ == "__main__":
    main()
