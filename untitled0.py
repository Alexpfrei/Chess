import streamlit as st
import chess
import json
import os
import time

st.set_page_config(page_title="Chess Challenge", layout="wide")

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

PIECE_UNICODE = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟',
    '.': ''
}

# ── Role selection ──────────────────────────────────────────────────────────────
if "role" not in st.session_state:
    st.session_state.role = None
if "selected" not in st.session_state:
    st.session_state.selected = None

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
game = load_game()
board = chess.Board(game["fen"])

my_turn = (board.turn == chess.WHITE and role == "white") or \
          (board.turn == chess.BLACK and role == "black")

# ── Legal moves for current position ───────────────────────────────────────────
legal_map = {}
for m in board.legal_moves:
    f = chess.square_name(m.from_square)
    t = chess.square_name(m.to_square)
    legal_map.setdefault(f, []).append(t)

selected = st.session_state.selected

# ── Header ──────────────────────────────────────────────────────────────────────
st.caption(f"Playing as **{'White ♙' if role == 'white' else 'Black ♟'}**  |  "
           f"Turn: **{'White' if board.turn == chess.WHITE else 'Black'}**")

if board.is_checkmate():
    winner = "Black" if board.turn == chess.WHITE else "White"
    st.success(f"🏆 Checkmate! **{winner}** wins!")
elif board.is_stalemate():
    st.success("🤝 Stalemate — draw!")
elif board.is_check():
    st.warning("⚠️ Check!")
elif not my_turn:
    st.info("⏳ Waiting for opponent's move…")

# ── Build board grid ────────────────────────────────────────────────────────────
# ranks/files ordered by perspective
ranks = range(7, -1, -1) if role == "white" else range(0, 8)
files = range(0, 8)       if role == "white" else range(7, -1, -1)

FILE_NAMES = "abcdefgh"
RANK_NAMES = "12345678"

targets = legal_map.get(selected, []) if selected else []

# Square size via CSS
st.markdown("""
<style>
div[data-testid="column"] > div > div > div > div > div > button {
    padding: 0 !important;
    min-height: 60px !important;
    height: 60px !important;
    width: 60px !important;
    font-size: 36px !important;
    line-height: 1 !important;
    border-radius: 0 !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

for rank_idx in ranks:
    cols = st.columns([0.3] + [1]*8, gap="small")
    cols[0].markdown(f"<div style='text-align:right;padding-top:18px;font-weight:bold'>{RANK_NAMES[rank_idx]}</div>", unsafe_allow_html=True)
    for col_i, file_idx in enumerate(files):
        sq = chess.square(file_idx, rank_idx)
        sq_name = chess.square_name(sq)
        piece = board.piece_at(sq)
        symbol = PIECE_UNICODE.get(piece.symbol(), '') if piece else ''

        is_light = (rank_idx + file_idx) % 2 == 1
        is_selected = (sq_name == selected)
        is_target = (sq_name in targets)

        # Background colour
        if is_selected:
            bg = "#7fc97f"
        elif is_target:
            bg = "#a0d8a0"
        elif is_light:
            bg = "#f0d9b5"
        else:
            bg = "#b58863"

        # Piece colour
        if piece:
            piece_color = "#ffffff" if piece.color == chess.WHITE else "#000000"
            text_shadow = "0 0 2px #000" if piece.color == chess.WHITE else "0 0 2px #fff"
            label = f'<span style="color:{piece_color};text-shadow:{text_shadow};font-size:36px;line-height:60px">{symbol}</span>'
        elif is_target:
            label = '<span style="font-size:18px;color:rgba(0,120,0,0.6)">●</span>'
        else:
            label = '<span> </span>'

        btn_html = f"""
        <form action="" method="get">
          <button name="sq" value="{sq_name}" style="
            width:60px;height:60px;background:{bg};border:none;cursor:pointer;
            display:flex;align-items:center;justify-content:center;
            font-size:36px;padding:0;margin:0;
          ">{label if piece else (label)}</button>
        </form>
        """

        with cols[col_i + 1]:
            st.markdown(f"""
            <style>
            div[data-testid="stButton"]:has(button[title="{sq_name}"]) button {{
                background-color: {bg} !important;
                color: {'white' if piece and piece.color == chess.WHITE else 'black'} !important;
                text-shadow: {'0 0 3px #000' if piece and piece.color == chess.WHITE else '0 0 3px #fff'} !important;
            }}
            </style>
            """, unsafe_allow_html=True)
            clicked = st.button(
                symbol if symbol else ("●" if is_target else " "),
                key=f"sq_{sq_name}",
                help=sq_name,
                use_container_width=False,
            )

        if clicked and my_turn:
            if selected is None:
                # Select this square if it has a moveable piece
                if sq_name in legal_map:
                    st.session_state.selected = sq_name
                    st.rerun()
            else:
                if sq_name in targets:
                    # Make the move
                    uci = selected + sq_name
                    move = chess.Move.from_uci(uci)
                    # Auto-promote to queen
                    if move not in board.legal_moves:
                        move = chess.Move.from_uci(uci + "q")
                    if move in board.legal_moves:
                        board.push(move)
                        game["fen"] = board.fen()
                        game["moves"].append(move.uci())
                        if board.is_game_over():
                            game["status"] = "finished"
                        save_game(game)
                    st.session_state.selected = None
                    st.rerun()
                elif sq_name in legal_map:
                    st.session_state.selected = sq_name
                    st.rerun()
                else:
                    st.session_state.selected = None
                    st.rerun()

# File labels
cols = st.columns([0.3] + [1]*8, gap="small")
for col_i, file_idx in enumerate(files):
    cols[col_i + 1].markdown(
        f"<div style='text-align:center;font-weight:bold'>{FILE_NAMES[file_idx]}</div>",
        unsafe_allow_html=True
    )

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
        st.session_state.selected = None
        st.rerun()
with col_b:
    if st.button("🗑️ Reset game"):
        reset_game()
        st.session_state.selected = None
        st.rerun()

# ── Auto-refresh when waiting for opponent ──────────────────────────────────────
if not my_turn and not board.is_game_over():
    time.sleep(3)
    st.rerun()
