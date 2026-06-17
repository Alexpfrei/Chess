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
    return None

def save_game(data):
    with open(GAME_FILE, "w") as f:
        json.dump(data, f)

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

# ── Setup screen ────────────────────────────────────────────────────────────────
if game is None:
    st.subheader("⏱️ Time Controls")
    use_clock = st.toggle("Use a clock", value=False)
    minutes, increment = 5, 0
    if use_clock:
        c1, c2 = st.columns(2)
        with c1:
            minutes = st.selectbox("Minutes per side", [1, 3, 5, 10, 15, 20, 30], index=2)
        with c2:
            increment = st.selectbox("Increment (seconds)", [0, 1, 2, 3, 5, 10], index=0)
    if st.button("▶ Start Game", use_container_width=True):
        save_game({
            "fen": chess.STARTING_FEN, "moves": [], "status": "ongoing",
            "use_clock": use_clock,
            "clocks": {"white": minutes * 60, "black": minutes * 60},
            "increment": increment,
            "last_move_time": None, "active_clock": None,
            "draw_offer": None, "result": None,
        })
        st.rerun()
    st.stop()

board = chess.Board(game["fen"])
use_clock = game.get("use_clock", False)
opponent = "black" if role == "white" else "white"

# ── Tick clock ──────────────────────────────────────────────────────────────────
if use_clock and game.get("active_clock") and game.get("last_move_time") and game["status"] == "ongoing":
    now = time.time()
    elapsed = now - game["last_move_time"]
    ac = game["active_clock"]
    game["clocks"][ac] = max(0, game["clocks"][ac] - elapsed)
    game["last_move_time"] = now
    if game["clocks"][ac] == 0:
        game["status"] = "finished"
        game["result"] = f"{'Black' if ac == 'white' else 'White'} wins on time"
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
            game["draw_offer"] = None
            just_moved = "white" if board.turn == chess.BLACK else "black"
            if use_clock:
                game["clocks"][just_moved] += game["increment"]
                game["active_clock"] = "white" if board.turn == chess.WHITE else "black"
                game["last_move_time"] = time.time()
            if board.is_game_over():
                game["status"] = "finished"
                game["result"] = board.result()
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

last_move_san = game["moves"][-1] if game["moves"] else None
last_from = chess.square_name(board.peek().from_square) if board.move_stack else None
last_to   = chess.square_name(board.peek().to_square)   if board.move_stack else None

# ── Layout ──────────────────────────────────────────────────────────────────────
board_col, side_col = st.columns([2, 1])

with board_col:
    st.caption(f"Playing as **{'White ♙' if role == 'white' else 'Black ♟'}**  |  Turn: **{'White' if board.turn == chess.WHITE else 'Black'}**")

    result = game.get("result")
    if result:
        st.success(f"🏁 {result}")
    elif board.is_checkmate():
        st.success(f"🏆 Checkmate! **{'Black' if board.turn == chess.WHITE else 'White'}** wins!")
    elif board.is_stalemate():
        st.success("🤝 Stalemate — draw!")
    elif board.is_check():
        st.warning("⚠️ Check!")
    elif game.get("draw_offer") == opponent:
        st.info(f"🤝 **{opponent.capitalize()}** offers a draw!")
    elif not my_turn and game["status"] == "ongoing":
        st.info("⏳ Waiting for opponent's move…")

    PIECES = {
        'K':'♔','Q':'♕','R':'♖','B':'♗','N':'♘','P':'♙',
        'k':'♚','q':'♛','r':'♜','b':'♝','n':'♞','p':'♟'
    }

    # Build clock HTML only if using clock
    if use_clock:
        wt = fmt_time(game["clocks"]["white"])
        bt = fmt_time(game["clocks"]["black"])
        top_color  = "Black" if role == "white" else "White"
        bot_color  = "White" if role == "white" else "Black"
        top_time   = bt     if role == "white" else wt
        bot_time   = wt     if role == "white" else bt
        top_active = game["active_clock"] == ("black" if role == "white" else "white")
        bot_active = game["active_clock"] == ("white" if role == "white" else "black")
        clock_top = f'<div class="clock {"clk-active" if top_active else "clk-idle"}"><span>{top_color}</span><span>{top_time}</span></div>'
        clock_bot = f'<div class="clock {"clk-active" if bot_active else "clk-idle"}"><span>{bot_color}</span><span>{bot_time}</span></div>'
        board_height = 700
    else:
        clock_top = clock_bot = ""
        board_height = 600

    board_html = f"""
<!DOCTYPE html><html><head><style>
* {{ box-sizing:border-box; margin:0; padding:0; }}
body {{ background:transparent; font-family:sans-serif; display:flex; flex-direction:column; align-items:flex-start; padding:8px; }}
.clock {{ display:flex; justify-content:space-between; align-items:center; width:516px; padding:6px 12px; border-radius:6px; margin:4px 0; font-size:22px; font-weight:bold; }}
.clock span:first-child {{ font-size:14px; font-weight:normal; }}
.clk-active {{ background:#2a7a2a; color:#fff; }}
.clk-idle   {{ background:#444;    color:#aaa; }}
#wrap {{ display:flex; flex-direction:row; align-items:flex-start; }}
#rank-labels {{ display:flex; flex-direction:column; width:20px; }}
#rank-labels span {{ height:62px; display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:bold; color:#888; }}
#grid {{ display:grid; grid-template-columns:repeat(8,62px); grid-template-rows:repeat(8,62px); border:3px solid #333; flex-shrink:0; }}
#file-labels {{ display:flex; margin-left:20px; }}
#file-labels span {{ width:62px; text-align:center; font-size:13px; font-weight:bold; color:#888; padding-top:4px; }}
.sq {{ width:62px; height:62px; display:flex; align-items:center; justify-content:center; font-size:44px; cursor:pointer; position:relative; user-select:none; }}
.light {{ background:#f0d9b5; }} .dark {{ background:#b58863; }}
.last-move {{ background:#cdd16e !important; }}
.selected  {{ outline:4px inset rgba(20,180,20,0.8); }}
.target .dot {{ width:22px; height:22px; border-radius:50%; background:rgba(20,160,20,0.5); position:absolute; }}
.target.has-piece .dot {{ width:58px; height:58px; border-radius:0; background:transparent; border:4px solid rgba(20,160,20,0.6); }}
.piece {{ line-height:1; position:relative; z-index:1; }}
.wp {{ color:#fff; text-shadow:0 0 3px #000,0 0 3px #000; }}
.bp {{ color:#000; text-shadow:0 0 2px #fff; }}
#status {{ margin-top:8px; font-size:14px; color:#888; }}
</style></head><body>
{clock_top}
<div id="wrap"><div id="rank-labels"></div><div id="grid"></div></div>
<div id="file-labels"></div>
{clock_bot}
<div id="status"></div>
<script>
var P={json.dumps(PIECES)};
var legalMap={json.dumps(legal_map)};
var myTurn={'true' if my_turn and game['status']=='ongoing' else 'false'};
var flipped={'true' if role=='black' else 'false'};
var lastFrom={json.dumps(last_from)};
var lastTo={json.dumps(last_to)};
var lastSAN={json.dumps(last_move_san)};
var selected=null;

function parseFen(fen){{
  return fen.split(' ')[0].split('/').map(function(r){{
    var a=[];for(var c of r){{if(isNaN(c))a.push(c);else for(var i=0;i<+c;i++)a.push('');}}return a;
  }});
}}
var bd=parseFen("{board.fen()}");
var files=['a','b','c','d','e','f','g','h'];
var ranks=['8','7','6','5','4','3','2','1'];
var rO=flipped?[7,6,5,4,3,2,1,0]:[0,1,2,3,4,5,6,7];
var fO=flipped?[7,6,5,4,3,2,1,0]:[0,1,2,3,4,5,6,7];

var rl=document.getElementById('rank-labels');
rO.forEach(function(ri){{var s=document.createElement('span');s.textContent=ranks[ri];rl.appendChild(s);}});
var fl=document.getElementById('file-labels');
fO.forEach(function(fi){{var s=document.createElement('span');s.textContent=files[fi];fl.appendChild(s);}});

function sq(ri,fi){{return files[fi]+ranks[ri];}}

function render(){{
  var g=document.getElementById('grid');g.innerHTML='';
  rO.forEach(function(ri){{fO.forEach(function(fi){{
    var s=sq(ri,fi),piece=bd[ri][fi];
    var light=(ri+fi)%2===0,isSel=s===selected;
    var tgts=legalMap[selected]||[],isTgt=tgts.includes(s);
    var d=document.createElement('div');
    d.className='sq '+(light?'light':'dark');
    if(s===lastFrom||s===lastTo)d.className+=' last-move';
    if(isSel)d.className+=' selected';
    if(isTgt){{d.className+=' target';if(piece)d.className+=' has-piece';var dot=document.createElement('div');dot.className='dot';d.appendChild(dot);}}
    if(piece){{var sp=document.createElement('span');sp.className='piece '+(piece===piece.toUpperCase()?'wp':'bp');sp.textContent=P[piece]||'';d.appendChild(sp);}}
    d.dataset.sq=s;d.addEventListener('click',onClick);g.appendChild(d);
  }});}});
  document.getElementById('status').textContent=lastSAN?'Last move: '+lastSAN+(myTurn?' — your turn!':''):(myTurn?'Your turn — click a piece.':'Waiting for opponent…');
}}

function onClick(){{
  if(!myTurn){{document.getElementById('status').textContent='Not your turn!';return;}}
  var s=this.dataset.sq;
  if(selected){{
    var tgts=legalMap[selected]||[];
    if(tgts.includes(s)){{send(selected+s);}}
    else if(legalMap[s]){{selected=s;render();}}
    else{{selected=null;render();}}
  }}else{{if(legalMap[s]){{selected=s;render();}}}}
}}

function send(uci){{
  document.getElementById('status').textContent='Sending…';
  var inputs=window.parent.document.querySelectorAll('input[type=text]');
  for(var inp of inputs){{
    if(inp.getAttribute('aria-label')==='move_input'){{
      var setter=Object.getOwnPropertyDescriptor(window.parent.HTMLInputElement.prototype,'value').set;
      setter.call(inp,uci);
      inp.dispatchEvent(new Event('input',{{bubbles:true}}));
      inp.dispatchEvent(new Event('change',{{bubbles:true}}));
      inp.dispatchEvent(new KeyboardEvent('keydown',{{bubbles:true,cancelable:true,key:'Enter',code:'Enter',keyCode:13}}));
      inp.dispatchEvent(new KeyboardEvent('keypress',{{bubbles:true,cancelable:true,key:'Enter',code:'Enter',keyCode:13}}));
      inp.dispatchEvent(new KeyboardEvent('keyup',{{bubbles:true,cancelable:true,key:'Enter',code:'Enter',keyCode:13}}));
      break;
    }}
  }}
}}
render();
</script></body></html>
"""

    components.html(board_html, height=board_height)

    move_val = st.text_input("move_input", label_visibility="collapsed", key="move_input_box")
    if move_val and move_val != st.session_state.get("last_move", ""):
        st.session_state["last_move"] = move_val
        st.session_state["pending_move"] = move_val
        st.rerun()

    if game["moves"]:
        with st.expander("Move history"):
            moves = game["moves"]
            pairs = [f"{i//2+1}. {moves[i]}  {moves[i+1] if i+1 < len(moves) else '…'}" for i in range(0, len(moves), 2)]
            st.text("\n".join(pairs))

    st.divider()
    if game["status"] == "ongoing":
        a1, a2, a3, a4 = st.columns(4)
        with a1:
            if st.button("🏳️ Resign", use_container_width=True):
                game["status"] = "finished"
                game["result"] = f"{'Black' if role == 'white' else 'White'} wins by resignation"
                save_game(game); st.rerun()
        with a2:
            if game.get("draw_offer") == opponent:
                if st.button("✅ Accept Draw", use_container_width=True):
                    game["status"] = "finished"
                    game["result"] = "Draw by agreement"
                    save_game(game); st.rerun()
            elif game.get("draw_offer") == role:
                st.button("🤝 Draw offered…", disabled=True, use_container_width=True)
            else:
                if st.button("🤝 Offer Draw", use_container_width=True):
                    game["draw_offer"] = role
                    save_game(game); st.rerun()
        with a3:
            if game.get("draw_offer") == opponent:
                if st.button("❌ Decline Draw", use_container_width=True):
                    game["draw_offer"] = None
                    save_game(game); st.rerun()
        with a4:
            if st.button("🔄 Switch sides", use_container_width=True):
                st.session_state.role = None; st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ New game", use_container_width=True):
                for f in [GAME_FILE, CHAT_FILE]:
                    if os.path.exists(f): os.remove(f)
                st.rerun()
        with c2:
            if st.button("🔄 Switch sides", use_container_width=True):
                st.session_state.role = None; st.rerun()

# ── Chat ────────────────────────────────────────────────────────────────────────
with side_col:
    st.subheader("💬 Chat")
    chat = load_chat()
    with st.container(height=500):
        if not chat:
            st.caption("No messages yet…")
        for msg in chat:
            who = msg["role"].capitalize()
            bg = "#dfeedd" if msg["role"] == "white" else "#e8eeff"
            st.markdown(
                f'<div style="background:{bg};border-radius:8px;padding:6px 10px;margin:4px 0;color:#000">'
                f'<b>{who}</b>: {msg["text"]}</div>', unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        chat_text = st.text_input("Message", placeholder="Say something…")
        if st.form_submit_button("Send") and chat_text.strip():
            chat.append({"role": role, "text": chat_text.strip()})
            save_chat(chat); st.rerun()

# ── Auto-refresh ────────────────────────────────────────────────────────────────
if game["status"] == "ongoing":
    time.sleep(2)
    st.rerun()
