import streamlit as st
import chess
import json
import os
import time
import streamlit.components.v1 as components

st.set_page_config(page_title="Chess Challenge", layout="centered")

GAME_FILE = "game.json"

def load_game():
    if os.path.exists(GAME_FILE):
        with open(GAME_FILE) as f:
            return json.load(f)
    return {"fen": chess.STARTING_FEN, "moves": [], "status": "ongoing"}

def save_game(data):
    with open(GAME_FILE, "w") as f:
        json.dump(data, f)

def reset_game():
    save_game({"fen": chess.STARTING_FEN, "moves": [], "status": "ongoing"})

# ── Session state ───────────────────────────────────────────────────────────────
for k, v in [("role", None), ("pending_move", "")]:
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

# ── Process any pending move ────────────────────────────────────────────────────
if st.session_state.pending_move:
    uci = st.session_state.pending_move
    st.session_state.pending_move = ""
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            move = chess.Move.from_uci(uci + "q")  # auto-promote to queen
        if move in board.legal_moves:
            board.push(move)
            game["fen"] = board.fen()
            game["moves"].append(move.uci())
            if board.is_game_over():
                game["status"] = "finished"
            save_game(game)
    except Exception:
        pass
    st.rerun()

my_turn = (board.turn == chess.WHITE and role == "white") or \
          (board.turn == chess.BLACK and role == "black")

# ── Legal moves map ─────────────────────────────────────────────────────────────
legal_map = {}
for m in board.legal_moves:
    f = chess.square_name(m.from_square)
    t = chess.square_name(m.to_square)
    legal_map.setdefault(f, []).append(t)

# ── Status ──────────────────────────────────────────────────────────────────────
st.caption(f"Playing as **{'White ♙' if role == 'white' else 'Black ♟'}**  |  Turn: **{'White' if board.turn == chess.WHITE else 'Black'}**")
if board.is_checkmate():
    st.success(f"🏆 Checkmate! **{'Black' if board.turn == chess.WHITE else 'White'}** wins!")
elif board.is_stalemate():
    st.success("🤝 Stalemate — draw!")
elif board.is_check():
    st.warning("⚠️ Check!")
elif not my_turn and not board.is_game_over():
    st.info("⏳ Waiting for opponent's move…")

# ── Board HTML ──────────────────────────────────────────────────────────────────
PIECES = {
    'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙',
    'k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟'
}

board_html = f"""
<!DOCTYPE html><html><head><style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: transparent; font-family: sans-serif; display: flex; flex-direction: column; align-items: center; }}
#wrap {{ display: flex; align-items: center; gap: 6px; }}
#grid {{ display: grid; grid-template-columns: repeat(8, 62px); grid-template-rows: repeat(8, 62px); border: 3px solid #333; }}
.sq {{
    width: 62px; height: 62px; display: flex; align-items: center; justify-content: center;
    font-size: 44px; cursor: pointer; position: relative; user-select: none;
}}
.light {{ background: #f0d9b5; }}
.dark  {{ background: #b58863; }}
.sq.selected {{ outline: 4px inset rgba(20,180,20,0.8); }}
.sq.target .dot {{
    width: 22px; height: 22px; border-radius: 50%;
    background: rgba(20,160,20,0.5); position: absolute;
}}
.sq.target.has-piece .dot {{
    width: 58px; height: 58px; border-radius: 0;
    background: transparent; border: 4px solid rgba(20,160,20,0.6);
}}
.piece {{ line-height: 1; position: relative; z-index: 1; }}
.white-piece {{ color: #fff; text-shadow: 0 0 3px #000, 0 0 3px #000; }}
.black-piece {{ color: #000; text-shadow: 0 0 2px #fff; }}
.rank-label {{ writing-mode: vertical-lr; font-size: 13px; font-weight: bold; color: #555; padding: 0 4px; display:flex; flex-direction:column; justify-content:space-around; height:496px; }}
.file-label {{ display:flex; justify-content:space-around; width:496px; font-size:13px; font-weight:bold; color:#555; margin-top:4px; }}
.file-label span, .rank-label span {{ width:62px; text-align:center; display:flex; align-items:center; justify-content:center; }}
#status {{ margin-top: 10px; font-size: 14px; color: #444; min-height: 20px; }}
</style></head><body>

<div id="wrap">
  <div class="rank-label" id="rankLabels"></div>
  <div id="grid"></div>
</div>
<div class="file-label" id="fileLabels"></div>
<div id="status"></div>

<script>
var PIECES = {json.dumps(PIECES)};
var legalMap = {json.dumps(legal_map)};
var myTurn = {'true' if my_turn and not board.is_game_over() else 'false'};
var flipped = {'true' if role == 'black' else 'false'};
var selected = null;

// Parse FEN into 8x8: boardArr[rank0=rank8][file0=a]
function parseFen(fen) {{
    var rows = fen.split(' ')[0].split('/');
    return rows.map(function(row) {{
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

// Rank/file order based on perspective
var rankOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
var fileOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];

// Labels
var rl = document.getElementById('rankLabels');
rankOrder.forEach(function(ri) {{
    var s = document.createElement('span'); s.textContent = ranks[ri]; rl.appendChild(s);
}});
var fl = document.getElementById('fileLabels');
// spacer for rank label column
var spacer = document.createElement('span'); spacer.style.width='30px'; fl.appendChild(spacer);
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
}}

function onClick(e) {{
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
    document.getElementById('status').textContent = 'Sending move: ' + uci + '…';
    // Write into the hidden Streamlit text input and trigger change
    var inputs = window.parent.document.querySelectorAll('input[type=text]');
    for (var inp of inputs) {{
        if (inp.getAttribute('aria-label') === 'move_input') {{
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(inp, uci);
            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
            break;
        }}
    }}
}}

render();
document.getElementById('status').textContent = myTurn ? 'Your turn — click a piece.' : 'Waiting for opponent…';
</script>
</body></html>
"""

components.html(board_html, height=580)

# Hidden text input that JS writes into
move_val = st.text_input("move_input", label_visibility="collapsed", key="move_input_box")
if move_val and move_val != st.session_state.get("last_move", ""):
    st.session_state["last_move"] = move_val
    st.session_state["pending_move"] = move_val
    st.rerun()

# ── Move history ────────────────────────────────────────────────────────────────
if game["moves"]:
    with st.expander("Move history"):
        moves = game["moves"]
        pairs = [f"{i//2+1}. {moves[i]}  {moves[i+1] if i+1 < len(moves) else '…'}" for i in range(0, len(moves), 2)]
        st.text("\n".join(pairs))

# ── Controls ───────────────────────────────────────────────────────────────────
st.divider()
c1, c2 = st.columns(2)
with c1:
    if st.button("🔄 Switch sides"):
        st.session_state.role = None; st.rerun()
with c2:
    if st.button("🗑️ Reset game"):
        reset_game(); st.rerun()

# ── Auto-refresh when waiting ──────────────────────────────────────────────────
if not my_turn and not board.is_game_over():
    time.sleep(3)
    st.rerun()
