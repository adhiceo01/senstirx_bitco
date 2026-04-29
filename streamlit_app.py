import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time
import random
import json
import os
import hashlib
import uuid
import threading
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import qrcode
import io
import base64

# --- CONFIG ---
st.set_page_config(
    page_title="Senstrix Bitco v3 | AI Trading",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- CONSTANTS ---
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
}

PLANS = {
    'Free':    {'price': 0,     'badge': '🆓', 'color': '#FF3F6C'},
    'Starter': {'price': 9.99,  'badge': '⭐', 'color': '#FF9933'},
    'Pro':     {'price': 29.99, 'badge': '💎', 'color': '#138808'},
    'Elite':   {'price': 99.99, 'badge': '👑', 'color': '#000080'},
}

USERS_FILE = 'senstrix_users.json'

# --- STATE INITIALIZATION ---
if 'prices' not in st.session_state:
    st.session_state.prices = {sym: info['base'] for sym, info in CRYPTOS.items()}
    st.session_state.price_history = {sym: [info['base']] for sym, info in CRYPTOS.items()}
    st.session_state.user = None
    st.session_state.ml_trained = False
    st.session_state.ml_predictions = {}
    st.session_state.logs = []

def add_log(cat, msg, level="info"):
    ts = datetime.now().strftime("%H:%M:%S")
    st.session_state.logs.insert(0, f"[{ts}] [{cat.upper()}] {msg}")
    if len(st.session_state.logs) > 50:
        st.session_state.logs.pop()

# --- DATA PERSISTENCE ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_user_data(user):
    users = load_users()
    users[user['email']] = user
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# --- SIMULATION ---
def update_prices():
    for sym in st.session_state.prices:
        old_px = st.session_state.prices[sym]
        change = old_px * random.uniform(-0.005, 0.005)
        new_px = max(old_px + change, CRYPTOS[sym]['base'] * 0.5)
        st.session_state.prices[sym] = new_px
        st.session_state.price_history[sym].append(new_px)
        if len(st.session_state.price_history[sym]) > 100:
            st.session_state.price_history[sym].pop(0)

# --- ML ENGINE ---
def train_ml(model_type='ridge', epochs=50):
    add_log("ML", f"Training {model_type} model for {epochs} epochs...")
    syms = list(CRYPTOS.keys())
    data = []
    for s in syms:
        px = st.session_state.prices[s]
        rsi = random.uniform(30, 70)
        macd = random.uniform(-1, 1)
        data.append([px, rsi, macd])
    
    X = np.array(data)
    y = X[:, 0] * (1 + np.random.randn(len(syms)) * 0.02) # Synthetic targets
    
    if model_type == 'random_forest':
        model = RandomForestRegressor(n_estimators=epochs)
    else:
        model = Ridge()
    
    model.fit(X, y)
    preds = model.predict(X)
    
    results = {}
    for i, s in enumerate(syms):
        cur = st.session_state.prices[s]
        pred = float(preds[i])
        delta = (pred - cur) / cur * 100
        
        if delta > 2: sig, emoji = "STRONG BUY", "🚀"
        elif delta > 0.5: sig, emoji = "BUY", "📈"
        elif delta < -2: sig, emoji = "STRONG SELL", "🔻"
        elif delta < -0.5: sig, emoji = "SELL", "📉"
        else: sig, emoji = "HOLD", "⏸"
        
        results[s] = {
            'pred': round(pred, 2),
            'delta': round(delta, 2),
            'signal': sig,
            'emoji': emoji,
            'conf': round(random.uniform(0.6, 0.95), 2)
        }
    
    st.session_state.ml_predictions = results
    st.session_state.ml_trained = True
    add_log("ML", "Model training complete. Profit signals updated.")

# --- UI COMPONENTS ---
def login_page():
    st.title("🔐 Senstrix Bitco Login")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Sign In")
        email = st.text_input("Email", key="login_email")
        pw = st.text_input("Password", type="password", key="login_pw")
        if st.button("Login"):
            users = load_users()
            if email in users and users[email]['pwHash'] == hash_pw(pw):
                st.session_state.user = users[email]
                add_log("AUTH", f"User {email} logged in.")
                st.rerun()
            else:
                st.error("Invalid credentials")
                
    with col2:
        st.subheader("Register")
        new_email = st.text_input("Email", key="reg_email")
        new_name = st.text_input("Name", key="reg_name")
        new_pw = st.text_input("Password", type="password", key="reg_pw")
        if st.button("Create Account"):
            users = load_users()
            if new_email in users:
                st.error("User already exists")
            else:
                user = {
                    'name': new_name,
                    'email': new_email,
                    'pwHash': hash_pw(new_pw),
                    'balance': 50000.0,
                    'wallet': 50000.0,
                    'positions': {},
                    'history': [],
                    'plan': 'Free'
                }
                save_user_data(user)
                st.session_state.user = user
                add_log("AUTH", f"New user {new_email} registered.")
                st.rerun()

def dashboard():
    st.title(f"📊 Senstrix Terminal")
    
    # Live Ticker
    cols = st.columns(5)
    for i, sym in enumerate(list(CRYPTOS.keys())[:5]):
        px = st.session_state.prices[sym]
        hist = st.session_state.price_history[sym]
        change = (px - hist[0]) / hist[0] * 100
        cols[i].metric(sym, f"${px:,.2f}", f"{change:+.2f}%")
        
    st.divider()
    
    col_chart, col_order = st.columns([2, 1])
    
    with col_chart:
        selected_sym = st.selectbox("Select Asset", list(CRYPTOS.keys()))
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            y=st.session_state.price_history[selected_sym],
            mode='lines',
            line=dict(color='#FF3F6C', width=2),
            fill='tozeroy',
            fillcolor='rgba(255, 63, 108, 0.1)'
        ))
        fig.update_layout(
            title=f"{selected_sym} Real-Time Chart",
            template="plotly_dark",
            margin=dict(l=0, r=0, t=30, b=0),
            height=400,
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor='#222')
        )
        st.plotly_chart(fig, use_container_width=True)
        
    with col_order:
        st.subheader("Place Order")
        side = st.radio("Side", ["Buy", "Sell"], horizontal=True)
        qty = st.number_input("Quantity", min_value=0.0001, step=0.1, format="%.4f")
        px = st.session_state.prices[selected_sym]
        total = qty * px
        st.write(f"Estimated Total: **${total:,.2f}**")
        
        if st.button(f"Confirm {side}", use_container_width=True):
            user = st.session_state.user
            if side == "Buy":
                if user['balance'] >= total:
                    user['balance'] -= total
                    user['positions'][selected_sym] = user['positions'].get(selected_sym, 0) + qty
                    user['history'].insert(0, {'time': datetime.now().strftime("%Y-%m-%d %H:%M"), 'type': 'BUY', 'sym': selected_sym, 'qty': qty, 'px': px})
                    save_user_data(user)
                    st.success("Order Executed")
                    add_log("TRADE", f"BUY {qty} {selected_sym} @ ${px:,.2f}")
                else:
                    st.error("Insufficient Funds")
            else:
                if user['positions'].get(selected_sym, 0) >= qty:
                    user['balance'] += total
                    user['positions'][selected_sym] -= qty
                    user['history'].insert(0, {'time': datetime.now().strftime("%Y-%m-%d %H:%M"), 'type': 'SELL', 'sym': selected_sym, 'qty': qty, 'px': px})
                    save_user_data(user)
                    st.success("Order Executed")
                    add_log("TRADE", f"SELL {qty} {selected_sym} @ ${px:,.2f}")
                else:
                    st.error("Insufficient Position")

def ai_brain():
    st.title("🧠 AI Intelligence Engine")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Model Training")
        m_type = st.selectbox("Algorithm", ["Ridge Regression", "Random Forest", "Neural Network"])
        epochs = st.slider("Epochs", 10, 200, 60)
        if st.button("⚡ Start Training"):
            train_ml(m_type.lower().replace(" ", "_"), epochs)
            
    with col2:
        if st.session_state.ml_trained:
            st.subheader("Profit Signals")
            df_preds = pd.DataFrame([
                {'Symbol': s, 'Signal': p['emoji'] + " " + p['signal'], 'Predicted Price': f"${p['pred']:,.2f}", 'Confidence': f"{p['conf']*100:.0f}%"}
                for s, p in st.session_state.ml_predictions.items()
            ])
            st.table(df_preds)
        else:
            st.info("Train the model to see AI profit signals.")

def portfolio():
    st.title("📈 My Portfolio")
    user = st.session_state.user
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Available Balance", f"${user['balance']:,.2f}")
    col2.metric("Wallet Value", f"${user['wallet']:,.2f}")
    
    # Positions Table
    st.subheader("Active Positions")
    if user['positions']:
        pos_data = []
        total_mv = 0
        for sym, qty in user['positions'].items():
            if qty > 0:
                cur_px = st.session_state.prices[sym]
                mv = qty * cur_px
                total_mv += mv
                pos_data.append({'Asset': sym, 'Quantity': f"{qty:.4f}", 'Current Price': f"${cur_px:,.2f}", 'Market Value': f"${mv:,.2f}"})
        
        if pos_data:
            st.table(pd.DataFrame(pos_data))
            col3.metric("Total Equity", f"${(user['balance'] + total_mv):,.2f}")
        else:
            st.write("No active positions.")
    else:
        st.write("No active positions.")
        
    st.subheader("Trade History")
    if user['history']:
        st.table(pd.DataFrame(user['history'][:10]))

def wallet():
    st.title("💳 Wallet & Deposits")
    user = st.session_state.user
    
    tab1, tab2 = st.tabs(["Deposit", "Withdraw"])
    
    with tab1:
        st.subheader("Instant Deposit via UPI")
        amt = st.number_input("Amount (INR)", min_value=100, value=5000)
        upi_id = "denco@okaxis"
        upi_url = f"upi://pay?pa={upi_id}&pn=SENSTRIX&am={amt}&cu=INR&tn=SENSTRIX+Deposit"
        
        # QR Code
        qr = qrcode.QRCode(box_size=10, border=2)
        qr.add_data(upi_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="#FF3F6C", back_color="white")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        st.image(buf.getvalue(), width=250)
        st.write(f"UPI ID: `{upi_id}`")
        
        if st.button("Confirm Payment"):
            user['balance'] += (amt / 83.0) # Convert INR to USD approx
            user['wallet'] += (amt / 83.0)
            save_user_data(user)
            st.success(f"Deposited ${amt/83.0:.2f} successfully!")
            add_log("WALLET", f"DEPOSIT ₹{amt}")

# --- MAIN APP FLOW ---
if st.session_state.user is None:
    login_page()
else:
    # Sidebar Navigation
    with st.sidebar:
        st.image("https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_92x30dp.png", width=100) # Placeholder for logo
        st.title("Senstrix Finance")
        page = st.radio("Navigation", ["Terminal", "AI Brain", "Portfolio", "Wallet"])
        st.divider()
        st.write(f"Logged in as: **{st.session_state.user['name']}**")
        if st.button("Logout"):
            st.session_state.user = None
            st.rerun()
            
        # Live Terminal Logs
        st.divider()
        st.write("🛰 Live Terminal")
        for log in st.session_state.logs[:5]:
            st.caption(log)

    # Simulation Tick
    update_prices()
    
    if page == "Terminal":
        dashboard()
    elif page == "AI Brain":
        ai_brain()
    elif page == "Portfolio":
        portfolio()
    elif page == "Wallet":
        wallet()

    # Auto-refresh simulation
    time.sleep(1)
    st.rerun()
