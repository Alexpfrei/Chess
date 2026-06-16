import streamlit as st
import chess
import json
import os
import time
import streamlit.components.v1 as components

st.set_page_config(page_title="Chess Challenge", layout="wide")

GAME_FILE = "game.json"
CHAT_FILE = "chat.json"

def load_game():
    if os.path.exists(GAME_FILE):
        with open(GAME_FILE) as f:
            return json.load(f)
    return {"fen": chess.STARTING_FEN, "moves": [], "status": "ongoing",
            "clocks": {"white": 0, "black": 0}, "increment": 0,
            "last_move_time": None, "active_clock": None, "time_set": False}

def save_game(data):
    with open(GAME_FILE, "w") as f:
        json.dump(data, f)

def reset_game(white_secs, black_secs, increment):
    save_game({
        "fen": chess.STARTING_FEN, "moves": [], "status": "ongoing",
        "clocks": {"white": white_secs, "black": black_secs},
        "increment": increment,
        "last_move_time": None, "active_clock": None, "time_set": True
    })

def load_chat():
    if os.path.exists(CHAT_FILE):
        with open(CHAT_FILE) as f:
            return json.load(f)
    return []

def save_chat(msgs):
    with open(CHAT_FILE, "w") as f:
        json.dump(msgs, f)

def fmt_time(secs):
    secs = max(0, int(secs))
    return f"{secs//60}:{secs%60:02d}"

# ── Session state ───────────────────────────────────────────────────────────────
for k, v in [("role", None), ("pending_move", ""), ("chat_input", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

st.title("♟️ Chess Challenge")

# ── Role selection ──────────────────────────────────────────────────────────────
if st.session_state.role is None:
    st.subheader("Who are you?")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("♙ I am White", use_container_width=True):
            st.session_state.role = "white"; st.rerun()
    with c2:
        if st.button("♟ I am Black", use_container_width=True):
            st.session_state.role = "black"; st.rerun()
    st.stop()

role = st.session_state.role
game = load_game()
board = chess.Board(game["fen"])

# ── Time setup screen ───────────────────────────────────────────────────────────
if not game.get("time_set"):
    st.subheader("⏱️ Set Time Controls")
    col1, col2, col3 = st.columns(3)
    with col1:
        minutes = st.selectbox("Minutes per side", [1, 3, 5, 10, 15, 20, 30], index=2)
    with col2:
        increment = st.selectbox("Increment (seconds)", [0, 1, 2, 3, 5, 10], index=0)
    with col3:
        st.write("")
        st.write("")
        if st.button("▶ Start Game", use_container_width=True):
            reset_game(minutes * 60, minutes * 60, increment)
            st.rerun()
    st.caption("Both players will see this screen. Once White clicks Start, the game begins.")
    st.stop()

# ── Deduct time from previous move ─────────────────────────────────────────────
now = time.time()
if game.get("active_clock") and game.get("last_move_time"):
    elapsed = now - game["last_move_time"]
    ac = game["active_clock"]
    game["clocks"][ac] = max(0, game["clocks"][ac] - elapsed)
    if game["clocks"][ac] == 0 and game["status"] == "ongoing":
        game["status"] = "finished"
        game["winner"] = "black" if ac == "white" else "white"
        save_game(game)

# ── Process pending move ────────────────────────────────────────────────────────
if st.session_state.pending_move:
    uci = st.session_state.pending_move
    st.session_state.pending_move = ""
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            move = chess.Move.from_uci(uci + "q")
        if move in board.legal_moves:
            san = board.san(move)
            board.push(move)
            game["fen"] = board.fen()
            game["moves"].append(san)
            # Clock: add increment to the side that just moved, switch active clock
            just_moved = "white" if board.turn == chess.BLACK else "black"
            game["clocks"][just_moved] = game["clocks"][just_moved] + game["increment"]
            game["active_clock"] = "white" if board.turn == chess.WHITE else "black"
            game["last_move_time"] = time.time()
            if board.is_game_over():
                game["status"] = "finished"
            save_game(game)
    except Exception:
        pass
    st.rerun()

my_turn = (board.turn == chess.WHITE and role == "white") or \
          (board.turn == chess.BLACK and role == "black")

legal_map = {}
for m in board.legal_moves:
    f = chess.square_name(m.from_square)
    t = chess.square_name(m.to_square)
    legal_map.setdefault(f, []).append(t)

# Get last move in SAN
last_move_san = game["moves"][-1] if game["moves"] else None

# ── Layout: board left, sidebar right ──────────────────────────────────────────
board_col, side_col = st.columns([2, 1])

with board_col:
    st.caption(f"Playing as **{'White ♙' if role == 'white' else 'Black ♟'}**  |  Turn: **{'White' if board.turn == chess.WHITE else 'Black'}**")

    if game.get("winner"):
        st.success(f"🏆 **{game['winner'].capitalize()}** wins on time!")
    elif board.is_checkmate():
        st.success(f"🏆 Checkmate! **{'Black' if board.turn == chess.WHITE else 'White'}** wins!")
    elif board.is_stalemate():
        st.success("🤝 Stalemate — draw!")
    elif board.is_check():
        st.warning("⚠️ Check!")
    elif not my_turn and not board.is_game_over():
        st.info("⏳ Waiting for opponent's move…")

    PIECES = {
        'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙',
        'k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟'
    }

    # Clocks (live display)
    wt = fmt_time(game["clocks"]["white"])
    bt = fmt_time(game["clocks"]["black"])
    # Show opponent clock on top, own clock on bottom
    top_color = "Black" if role == "white" else "White"
    bot_color = "White" if role == "white" else "Black"
    top_time  = bt if role == "white" else wt
    bot_time  = wt if role == "white" else bt

    board_html = f"""
<!DOCTYPE html><html><head><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: transparent; font-family: sans-serif; display: flex; flex-direction: column; align-items: flex-start; padding: 8px; }}
.clock-bar {{ display:flex; align-items:center; justify-content:space-between; width: 516px; padding: 6px 10px; border-radius: 6px; margin: 4px 0; font-size: 22px; font-weight: bold; }}
.clock-bar.active {{ background: #2a5; color: #fff; }}
.clock-bar.inactive {{ background: #444; color: #ccc; }}
.clock-name {{ font-size: 14px; font-weight: normal; }}
#wrap {{ display: flex; flex-direction: row; align-items: flex-start; }}
#rank-labels {{ display: flex; flex-direction: column; width: 20px; }}
#rank-labels span {{ height: 62px; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: bold; color: #888; }}
#grid {{ display: grid; grid-template-columns: repeat(8, 62px); grid-template-rows: repeat(8, 62px); border: 3px solid #333; flex-shrink: 0; }}
#file-labels {{ display: flex; flex-direction: row; margin-left: 20px; }}
#file-labels span {{ width: 62px; text-align: center; font-size: 13px; font-weight: bold; color: #888; padding-top: 4px; }}
.sq {{ width: 62px; height: 62px; display: flex; align-items: center; justify-content: center; font-size: 44px; cursor: pointer; position: relative; user-select: none; }}
.light {{ background: #f0d9b5; }}
.dark  {{ background: #b58863; }}
.sq.selected {{ outline: 4px inset rgba(20,180,20,0.8); }}
.sq.last-from, .sq.last-to {{ background: #cdd16e !important; }}
.sq.target .dot {{ width: 22px; height: 22px; border-radius: 50%; background: rgba(20,160,20,0.5); position: absolute; }}
.sq.target.has-piece .dot {{ width: 58px; height: 58px; border-radius: 0; background: transparent; border: 4px solid rgba(20,160,20,0.6); }}
.piece {{ line-height: 1; position: relative; z-index: 1; }}
.white-piece {{ color: #fff; text-shadow: 0 0 3px #000, 0 0 3px #000; }}
.black-piece {{ color: #000; text-shadow: 0 0 2px #fff; }}
#status {{ margin-top: 8px; font-size: 14px; color: #888; }}
</style></head><body>

<div class="clock-bar {'active' if game['active_clock'] == ('black' if role == 'white' else 'white') else 'inactive'}">
  <span class="clock-name">{top_color}</span>
  <span>{top_time}</span>
</div>

<div id="wrap">
  <div id="rank-labels"></div>
  <div id="grid"></div>
</div>
<div id="file-labels"></div>

<div class="clock-bar {'active' if game['active_clock'] == ('white' if role == 'white' else 'black') else 'inactive'}">
  <span class="clock-name">{bot_color}</span>
  <span>{bot_time}</span>
</div>

<div id="status"></div>

<script>
var PIECES = {json.dumps(PIECES)};
var legalMap = {json.dumps(legal_map)};
var myTurn = {'true' if my_turn and not board.is_game_over() and game['status'] == 'ongoing' else 'false'};
var flipped = {'true' if role == 'black' else 'false'};
var selected = null;
var lastMoveSAN = {json.dumps(last_move_san)};

// Highlight last move squares from SAN (we pass uci squares from Python)
var lastFrom = {json.dumps(chess.square_name(board.peek().from_square) if board.move_stack else None)};
var lastTo   = {json.dumps(chess.square_name(board.peek().to_square)   if board.move_stack else None)};

function parseFen(fen) {{
    return fen.split(' ')[0].split('/').map(function(row) {{
        var arr = [];
        for (var ch of row) {{
            if (isNaN(ch)) arr.push(ch);
            else for (var i = 0; i < +ch; i++) arr.push('');
        }}
        return arr;
    }});
}}

var boardArr = parseFen("{board.fen()}");
var files = ['a','b','c','d','e','f','g','h'];
var ranks = ['8','7','6','5','4','3','2','1'];
var rankOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
var fileOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];

var rl = document.getElementById('rank-labels');
rankOrder.forEach(function(ri) {{
    var s = document.createElement('span'); s.textContent = ranks[ri]; rl.appendChild(s);
}});
var fl = document.getElementById('file-labels');
fileOrder.forEach(function(fi) {{
    var s = document.createElement('span'); s.textContent = files[fi]; fl.appendChild(s);
}});

function sqName(ri, fi) {{ return files[fi] + ranks[ri]; }}

function render() {{
    var grid = document.getElementById('grid');
    grid.innerHTML = '';
    rankOrder.forEach(function(ri) {{
        fileOrder.forEach(function(fi) {{
            var sq = sqName(ri, fi);
            var piece = boardArr[ri][fi];
            var isLight = (ri + fi) % 2 === 0;
            var isSelected = sq === selected;
            var targets = legalMap[selected] || [];
            var isTarget = targets.includes(sq);

            var div = document.createElement('div');
            div.className = 'sq ' + (isLight ? 'light' : 'dark');
            if (sq === lastFrom || sq === lastTo) div.className += ' last-from';
            if (isSelected) div.className += ' selected';
            if (isTarget) {{
                div.className += ' target';
                if (piece) div.className += ' has-piece';
                var dot = document.createElement('div'); dot.className = 'dot';
                div.appendChild(dot);
            }}
            if (piece) {{
                var span = document.createElement('span');
                span.className = 'piece ' + (piece === piece.toUpperCase() ? 'white-piece' : 'black-piece');
                span.textContent = PIECES[piece] || '';
                div.appendChild(span);
            }}
            div.dataset.sq = sq;
            div.addEventListener('click', onClick);
            grid.appendChild(div);
        }});
    }});

    // Update status with last move in SAN
    var statusEl = document.getElementById('status');
    if (lastMoveSAN) {{
        statusEl.textContent = 'Last move: ' + lastMoveSAN + (myTurn ? ' — your turn!' : '');
    }} else {{
        statusEl.textContent = myTurn ? 'Your turn — click a piece.' : 'Waiting for opponent…';
    }}
}}

function onClick() {{
    if (!myTurn) {{ document.getElementById('status').textContent = "Not your turn!"; return; }}
    var sq = this.dataset.sq;
    if (selected) {{
        var targets = legalMap[selected] || [];
        if (targets.includes(sq)) {{
            sendMove(selected + sq);
        }} else if (legalMap[sq]) {{
            selected = sq; render();
        }} else {{
            selected = null; render();
        }}
    }} else {{
        if (legalMap[sq]) {{ selected = sq; render(); }}
    }}
}}

function sendMove(uci) {{
    document.getElementById('status').textContent = 'Sending move…';
    var inputs = window.parent.document.querySelectorAll('input[type=text]');
    for (var inp of inputs) {{
        if (inp.getAttribute('aria-label') === 'move_input') {{
            var setter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
            setter.call(inp, uci);
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
            inp.dispatchEvent(new KeyboardEvent('keydown', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 }}));
            inp.dispatchEvent(new KeyboardEvent('keypress', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 }}));
            inp.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true, cancelable: true, key: 'Enter', code: 'Enter', keyCode: 13 }}));
            break;
        }}
    }}
}}

render();
</script>
</body></html>
"""

    components.html(board_html, height=660)

    move_val = st.text_input("move_input", label_visibility="collapsed", key="move_input_box")
    if move_val and move_val != st.session_state.get("last_move", ""):
        st.session_state["last_move"] = move_val
        st.session_state["pending_move"] = move_val
        st.rerun()

    # Move history
    if game["moves"]:
        with st.expander("Move history"):
            moves = game["moves"]
            pairs = [f"{i//2+1}. {moves[i]}  {moves[i+1] if i+1 < len(moves) else '…'}" for i in range(0, len(moves), 2)]
            st.text("\n".join(pairs))

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🔄 Switch sides"):
            st.session_state.role = None; st.rerun()
    with c2:
        if st.button("🗑️ New game"):
            if os.path.exists(GAME_FILE): os.remove(GAME_FILE)
            if os.path.exists(CHAT_FILE): os.remove(CHAT_FILE)
            st.rerun()

# ── Chat sidebar ────────────────────────────────────────────────────────────────
with side_col:
    st.subheader("💬 Chat")
    chat = load_chat()

    chat_box = st.container(height=500)
    with chat_box:
        if not chat:
            st.caption("No messages yet…")
        for msg in chat:
            who = msg["role"].capitalize()
            color = "#dfe" if msg["role"] == "white" else "#eef"
            st.markdown(
                f'<div style="background:{color};border-radius:8px;padding:6px 10px;margin:4px 0">'
                f'<b>{who}</b>: {msg["text"]}</div>',
                unsafe_allow_html=True
            )

    with st.form("chat_form", clear_on_submit=True):
        chat_text = st.text_input("Message", placeholder="Say something…")
        if st.form_submit_button("Send") and chat_text.strip():
            chat.append({"role": role, "text": chat_text.strip()})
            save_chat(chat)
            st.rerun()

# ── Auto-refresh ────────────────────────────────────────────────────────────────
if not board.is_game_over() and game["status"] == "ongoing":
    time.sleep(2)
    st.rerun()
