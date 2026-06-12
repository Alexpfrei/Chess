# -*- coding: utf-8 -*-
"""
Created on Fri Jun 12 14:08:25 2026

@author: Frei.Alexander.P
"""

import streamlit as st
import chess
import chess.svg
import time

st.set_page_config(page_title="Chess Challenge", layout="centered")

# ── Shared state via st.session_state (persisted across reruns for both players) ──
# We use a single shared game stored in a JSON-serialisable dict so both
# "players" (two browser tabs on the same machine, or two users hitting the
# same Streamlit Cloud app) always read the latest position.
#
# NOTE: Streamlit reruns the script for every user interaction, but
#       st.session_state is PER-SESSION (per browser tab).  To share state
#       between two sessions we persist the game into a tiny file (game.json).
#       This keeps the dependency list to just `streamlit` and `chess`.

import json, os

GAME_FILE = "game.json"

def load_game():
    if os.path.exists(GAME_FILE):
        with open(GAME_FILE) as f:
            data = json.load(f)
        return data
    return {"fen": chess.STARTING_FEN, "moves": [], "status": "ongoing", "last_updated": 0}

def save_game(data):
    with open(GAME_FILE, "w") as f:
        json.dump(data, f)

def reset_game():
    save_game({"fen": chess.STARTING_FEN, "moves": [], "status": "ongoing", "last_updated": time.time()})

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

# ── Load shared game ────────────────────────────────────────────────────────────
game = load_game()
board = chess.Board(game["fen"])

# ── Status banner ───────────────────────────────────────────────────────────────
def get_status(board):
    if board.is_checkmate():
        winner = "Black" if board.turn == chess.WHITE else "White"
        return f"🏆 Checkmate! **{winner}** wins!"
    if board.is_stalemate():
        return "🤝 Stalemate — it's a draw!"
    if board.is_insufficient_material():
        return "🤝 Draw — insufficient material."
    if board.is_check():
        return "⚠️ Check!"
    return None

status_msg = get_status(board)
if status_msg:
    st.success(status_msg)

# ── Board display ───────────────────────────────────────────────────────────────
flipped = (role == "black")
svg = chess.svg.board(board, flipped=flipped, size=420)
st.image(svg.encode(), use_container_width=False)

# ── Move input ──────────────────────────────────────────────────────────────────
my_turn = (board.turn == chess.WHITE and role == "white") or \
          (board.turn == chess.BLACK and role == "black")

if game["status"] == "ongoing" and not board.is_game_over():
    if my_turn:
        st.subheader("Your move")
        with st.form("move_form", clear_on_submit=True):
            move_input = st.text_input(
                "Enter move in UCI (e.g. e2e4) or SAN (e.g. e4, Nf3):",
                placeholder="e2e4"
            )
            submitted = st.form_submit_button("Make Move ▶")

        if submitted and move_input:
            move_input = move_input.strip()
            try:
                # Try UCI first, then SAN
                try:
                    move = chess.Move.from_uci(move_input)
                    if move not in board.legal_moves:
                        raise ValueError("illegal")
                except Exception:
                    move = board.parse_san(move_input)

                board.push(move)
                game["fen"] = board.fen()
                game["moves"].append(move_input)
                game["last_updated"] = time.time()
                if board.is_game_over():
                    game["status"] = "finished"
                save_game(game)
                st.rerun()

            except Exception:
                st.error(f"❌ Invalid or illegal move: `{move_input}`. Try again.")
    else:
        turn_name = "White" if board.turn == chess.WHITE else "Black"
        st.info(f"⏳ Waiting for **{turn_name}** to move…")
        time.sleep(2)
        st.rerun()

# ── Move history ────────────────────────────────────────────────────────────────
if game["moves"]:
    with st.expander("Move history"):
        pairs = []
        moves = game["moves"]
        for i in range(0, len(moves), 2):
            w = moves[i]
            b = moves[i+1] if i+1 < len(moves) else "…"
            pairs.append(f"{i//2+1}. {w}  {b}")
        st.text("\n".join(pairs))

# ── Admin controls ──────────────────────────────────────────────────────────────
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