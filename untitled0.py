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

# ── Role selection ──────────────────────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = None

st.title("♟️ Chess Challenge")

if st.session_state.role is None:
    st.subheader("Who are you?")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("♙ I am White", use_container_width=True):
            st.session_state.role = "white"
            st.rerun()
    with col2:
        if st.button("♟ I am Black", use_container_width=True):
            st.session_state.role = "black"
            st.rerun()
    st.stop()

role = st.session_state.role
st.caption(f"You are playing as **{'White ♙' if role == 'white' else 'Black ♟'}**")

game = load_game()
board = chess.Board(game["fen"])

# ── Handle move submitted via query param ───────────────────────────────────────
params = st.query_params
if "move" in params:
    uci = params["move"]
    try:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            # try promotion to queen
            move = chess.Move.from_uci(uci + "q")
        if move in board.legal_moves:
            board.push(move)
            game["fen"] = board.fen()
            game["moves"].append(move.uci())
            if board.is_game_over():
                game["status"] = "finished"
            save_game(game)
    except Exception:
        pass
    st.query_params.clear()
    st.rerun()

# ── Status ──────────────────────────────────────────────────────────────────────
if board.is_checkmate():
    winner = "Black" if board.turn == chess.WHITE else "White"
    st.success(f"🏆 Checkmate! **{winner}** wins!")
elif board.is_stalemate():
    st.success("🤝 Stalemate — draw!")
elif board.is_check():
    st.warning("⚠️ Check!")

my_turn = (board.turn == chess.WHITE and role == "white") or \
          (board.turn == chess.BLACK and role == "black")

if not my_turn and not board.is_game_over():
    st.info(f"⏳ Waiting for **{'White' if board.turn == chess.WHITE else 'Black'}** to move…")

# ── Build legal moves map ───────────────────────────────────────────────────────
legal_map = {}
for m in board.legal_moves:
    f = chess.square_name(m.from_square)
    t = chess.square_name(m.to_square)
    legal_map.setdefault(f, []).append(t)

legal_map_json = json.dumps(legal_map)
fen = board.fen()
flipped = "true" if role == "black" else "false"
my_turn_js = "true" if my_turn and not board.is_game_over() else "false"

# ── HTML board with Unicode pieces ─────────────────────────────────────────────
html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: transparent; display: flex; flex-direction: column; align-items: center; font-family: sans-serif; }}
  #board {{ border: 3px solid #555; display: inline-block; }}
  .row {{ display: flex; }}
  .sq {{
    width: 56px; height: 56px;
    display: flex; align-items: center; justify-content: center;
    font-size: 40px;
    cursor: pointer;
    user-select: none;
    position: relative;
  }}
  .light {{ background: #f0d9b5; }}
  .dark  {{ background: #b58863; }}
  .sq.selected  {{ background: #7fc97f !important; }}
  .sq.target    {{ background: #7fc97f99 !important; }}
  .sq.target::after {{
    content: '';
    width: 22px; height: 22px;
    border-radius: 50%;
    background: rgba(0,140,0,0.45);
    position: absolute;
  }}
  .sq.target.occupied::after {{
    width: 52px; height: 52px;
    border-radius: 0;
    background: transparent;
    border: 4px solid rgba(0,140,0,0.6);
    border-radius: 4px;
  }}
  .label-file {{ font-size: 11px; position: absolute; bottom: 2px; right: 3px; color: #888; font-weight: bold; }}
  .label-rank {{ font-size: 11px; position: absolute; top: 2px; left: 3px; color: #888; font-weight: bold; }}
  #status {{ margin-top: 10px; font-size: 14px; color: #444; }}
</style>
</head>
<body>
<div id="board"></div>
<div id="status"></div>

<script>
var PIECES = {{
  'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
  'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
}};

var legalMap = {legal_map_json};
var myTurn   = {my_turn_js};
var flipped  = {flipped};
var selected = null;

// Parse FEN board part into 8x8 array [rank8..rank1][file a..h]
function parseFen(fen) {{
  var rows = fen.split(' ')[0].split('/');
  var board = [];
  for (var r = 0; r < 8; r++) {{
    var row = [];
    for (var ch of rows[r]) {{
      if (isNaN(ch)) {{ row.push(ch); }}
      else {{ for (var i = 0; i < parseInt(ch); i++) row.push(''); }}
    }}
    board.push(row);
  }}
  return board; // board[0] = rank 8, board[7] = rank 1
}}

var boardData = parseFen("{fen}");
var files = ['a','b','c','d','e','f','g','h'];
var ranks = ['8','7','6','5','4','3','2','1']; // rank index 0=rank8

function sqName(ri, fi) {{
  return files[fi] + ranks[ri]; // e.g. ri=6,fi=4 -> e2
}}

function renderBoard() {{
  var container = document.getElementById('board');
  container.innerHTML = '';

  var rankOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];
  var fileOrder = flipped ? [7,6,5,4,3,2,1,0] : [0,1,2,3,4,5,6,7];

  rankOrder.forEach(function(ri) {{
    var rowDiv = document.createElement('div');
    rowDiv.className = 'row';
    fileOrder.forEach(function(fi) {{
      var sq = sqName(ri, fi);
      var piece = boardData[ri][fi];
      var isLight = (ri + fi) % 2 === 0;
      var div = document.createElement('div');
      div.className = 'sq ' + (isLight ? 'light' : 'dark');
      div.dataset.sq = sq;
      if (piece) {{ div.className += ' occupied'; }}

      // Highlight
      if (sq === selected) div.className += ' selected';
      if (selected && legalMap[selected] && legalMap[selected].includes(sq)) {{
        div.className += ' target';
        if (piece) div.className += ' occupied';
      }}

      // Piece
      if (piece) {{
        var span = document.createElement('span');
        span.textContent = PIECES[piece] || '';
        // White pieces white fill, black pieces dark fill via CSS filter trick
        span.style.filter = piece === piece.toUpperCase()
          ? 'drop-shadow(0 0 1px #333)'   // white piece
          : 'drop-shadow(0 0 1px #eee)';  // black piece — glow helps distinguish
        span.style.color = piece === piece.toUpperCase() ? '#fff' : '#000';
        div.appendChild(span);
      }}

      // Labels
      if (fi === (flipped ? 7 : 0)) {{
        var rl = document.createElement('span');
        rl.className = 'label-rank';
        rl.textContent = ranks[ri];
        div.appendChild(rl);
      }}
      if (ri === (flipped ? 0 : 7)) {{
        var fl = document.createElement('span');
        fl.className = 'label-file';
        fl.textContent = files[fi];
        div.appendChild(fl);
      }}

      div.addEventListener('click', function() {{ onClickSq(this.dataset.sq); }});
      rowDiv.appendChild(div);
    }});
    container.appendChild(rowDiv);
  }});
}}

function onClickSq(sq) {{
  if (!myTurn) return;
  if (selected) {{
    var targets = legalMap[selected] || [];
    if (targets.includes(sq) && sq !== selected) {{
      submitMove(selected + sq);
      selected = null;
    }} else if (legalMap[sq] && legalMap[sq].length > 0) {{
      selected = sq;
      renderBoard();
    }} else {{
      selected = null;
      renderBoard();
    }}
  }} else {{
    if (legalMap[sq] && legalMap[sq].length > 0) {{
      selected = sq;
      renderBoard();
    }}
  }}
}}

function submitMove(uci) {{
  document.getElementById('status').textContent = 'Moving… (' + uci + ')';
  var url = window.location.href.split('?')[0] + '?move=' + uci;
  window.parent.location.href = url;
}}

renderBoard();
document.getElementById('status').textContent = myTurn ? 'Your turn — click a piece.' : "Waiting for opponent…";
</script>
</body>
</html>
"""

components.html(html, height=490, scrolling=False)

# ── Move history ────────────────────────────────────────────────────────────────
if game["moves"]:
    with st.expander("Move history"):
        moves = game["moves"]
        pairs = []
        for i in range(0, len(moves), 2):
            w = moves[i]
            b = moves[i+1] if i+1 < len(moves) else "…"
            pairs.append(f"{i//2+1}. {w}  {b}")
        st.text("\n".join(pairs))

# ── Controls ───────────────────────────────────────────────────────────────────
st.divider()
col_a, col_b = st.columns(2)
with col_a:
    if st.button("🔄 Switch sides"):
        st.session_state.role = None
        st.rerun()
with col_b:
    if st.button("🗑️ Reset game"):
        reset_game()
        st.rerun()

# ── Auto-refresh when waiting ──────────────────────────────────────────────────
if not my_turn and not board.is_game_over():
    time.sleep(3)
    st.rerun()
