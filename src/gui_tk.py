import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu
import chess
import chess.engine
import threading
import time
import os

STOCKFISH_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "stockfish", "stockfish"))

UNICODE_PIECES = {
    'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
    'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
}

class ChessGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("pesc-i Chess GUI")
        self.square_size = 64
        self.board_pixels = self.square_size * 8
        self.margin = 24  # space for coordinates labels
        self.canvas_size = self.board_pixels + 2 * self.margin
        self.canvas = tk.Canvas(root, width=self.canvas_size, height=self.canvas_size)
        self.canvas.pack(side=tk.LEFT)

        self.right_frame = tk.Frame(root)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.move_list = tk.Listbox(self.right_frame, width=30)
        self.move_list.pack(fill=tk.BOTH, expand=True)

        ctrl_frame = tk.Frame(self.right_frame)
        ctrl_frame.pack(fill=tk.X)
        tk.Button(ctrl_frame, text="New Game", command=self.new_game).pack(side=tk.LEFT)
        tk.Button(ctrl_frame, text="Undo", command=self.undo).pack(side=tk.LEFT)

        self.mode_var = StringVar(value="Player vs Player")
        self.mode_menu = OptionMenu(ctrl_frame, self.mode_var,
                                   "Player vs Player", "Player vs Stockfish", "Stockfish vs Stockfish",
                                   command=self.update_mode)
        self.mode_menu.pack(side=tk.LEFT)

        self.board = chess.Board()
        self.selected_square = None
        self.suggested_move = None

        # Engine (created on demand)
        self.engine = None
        self.engine_lock = threading.Lock()

        # Engine control frame
        ctrl = tk.Frame(root)
        ctrl.pack(side="right", fill="y", padx=6, pady=6)

        tk.Label(ctrl, text="Engine time (ms)").pack()
        self.time_scale = tk.Scale(ctrl, from_=50, to=5000, orient="horizontal")
        self.time_scale.set(200)
        self.time_scale.pack(fill="x")

        tk.Label(ctrl, text="Depth (0 = use time)").pack()
        self.depth_scale = tk.Scale(ctrl, from_=0, to=40, orient="horizontal")
        self.depth_scale.set(0)
        self.depth_scale.pack(fill="x")

        tk.Button(ctrl, text="Analyze", command=self.analyze_position).pack(fill="x", pady=4)

        self.eval_label = tk.Label(ctrl, text="Eval: -")
        self.eval_label.pack(pady=(10,0))
        self.pv_label = tk.Label(ctrl, text="PV: -", wraplength=200, justify="left")
        self.pv_label.pack()

        self.draw_board()
        self.canvas.bind("<Button-1>", self.on_click)

        # for engine vs engine loop
        self.engine_vs_engine_running = False

        # ensure engine stops on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def ensure_engine(self):
        with self.engine_lock:
            if self.engine is None:
                try:
                    self.engine = chess.engine.SimpleEngine.popen_uci(STOCKFISH_PATH)
                except Exception as e:
                    messagebox.showerror("Engine error", f"Could not start Stockfish: {e}")
                    self.engine = None

    def close_engine(self):
        with self.engine_lock:
            if self.engine is not None:
                try:
                    self.engine.quit()
                except Exception:
                    pass
                self.engine = None

    def update_mode(self, _=None):
        # stop any running self-play when switching modes
        self.engine_vs_engine_running = False
        self.new_game()

    def coord_to_square(self, x: int, y: int) -> chess.Square | None:
        # convert canvas x,y to square index; return None if outside board area
        bx0 = self.margin
        by0 = self.margin
        if x < bx0 or x >= bx0 + self.board_pixels or y < by0 or y >= by0 + self.board_pixels:
            return None
        file = int((x - bx0) // self.square_size)
        rank = 7 - int((y - by0) // self.square_size)
        return chess.square(file, rank)

    def draw_board(self) -> None:
        self.canvas.delete("all")
        colors = ["#F0D9B5", "#B58863"]

        # draw squares with margin offset
        for rank in range(8):
            for file in range(8):
                x0 = self.margin + file * self.square_size
                y0 = self.margin + (7 - rank) * self.square_size
                color = colors[(rank + file) % 2]
                self.canvas.create_rectangle(x0, y0, x0 + self.square_size, y0 + self.square_size, fill=color, outline="")

        # Highlight previous move (blue)
        if self.board.move_stack:
            last_move = self.board.peek()
            for sq in [last_move.from_square, last_move.to_square]:
                file = chess.square_file(sq)
                rank = chess.square_rank(sq)
                x0 = self.margin + file * self.square_size
                y0 = self.margin + (7 - rank) * self.square_size
                self.canvas.create_rectangle(x0, y0, x0 + self.square_size, y0 + self.square_size, fill="#89CFF0", outline="") # Light blue

        # Highlight suggested move (green)
        if self.suggested_move:
            for sq in [self.suggested_move.from_square, self.suggested_move.to_square]:
                file = chess.square_file(sq)
                rank = chess.square_rank(sq)
                x0 = self.margin + file * self.square_size
                y0 = self.margin + (7 - rank) * self.square_size
                self.canvas.create_rectangle(x0, y0, x0 + self.square_size, y0 + self.square_size, fill="#90EE90", outline="") # Light green

        # draw pieces (with margin offset)
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                x = self.margin + file * self.square_size + self.square_size / 2
                y = self.margin + (7 - rank) * self.square_size + self.square_size / 2
                symbol = UNICODE_PIECES[piece.symbol()]
                self.canvas.create_text(x, y, text=symbol, font=("Arial", int(self.square_size / 1.8)))

        # draw file labels (a-h) at top and bottom
        files = "abcdefgh"
        top_y = self.margin / 2
        bottom_y = self.margin + self.board_pixels + self.margin / 4
        for i, ch in enumerate(files):
            x = self.margin + i * self.square_size + self.square_size / 2
            self.canvas.create_text(x, top_y, text=ch, font=("Arial", 12))
            self.canvas.create_text(x, bottom_y, text=ch, font=("Arial", 12))

        # draw rank labels (1-8) at left and right
        for r in range(1, 9):
            y = self.margin + (8 - r) * self.square_size + self.square_size / 2
            left_x = self.margin / 4
            right_x = self.margin + self.board_pixels + self.margin / 4
            self.canvas.create_text(left_x, y, text=str(r), font=("Arial", 12))
            self.canvas.create_text(right_x, y, text=str(r), font=("Arial", 12))

    def on_click(self, event):
        if self.mode_var.get() == "Stockfish vs Stockfish":
            return  # ignore clicks in engine vs engine mode

        sq = self.coord_to_square(event.x, event.y)
        if sq is None:
            # clicked outside board (on coordinates margin) -> ignore
            return

        if self.selected_square is None:
            # select if there's a piece of side to move
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                self.selected_square = sq
        else:
            promotion = None
            if self.board.piece_type_at(self.selected_square) == chess.PAWN and chess.square_rank(sq) in (0, 7):
                promotion = chess.QUEEN
            move = chess.Move(self.selected_square, sq, promotion=promotion) if promotion else chess.Move(self.selected_square, sq)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.move_list.insert(tk.END, self.board.peek().uci())
                self.selected_square = None
                self.suggested_move = None # Clear suggestion after move
                self.draw_board()
                self.root.update()

                if self.mode_var.get() == "Player vs Stockfish":
                    # ask engine to move (in background)
                    threading.Thread(target=self.request_engine_move, daemon=True).start()
            else:
                # click destination invalid; clear selection
                self.selected_square = None

    def new_game(self):
        self.board.reset()
        self.move_list.delete(0, tk.END)
        self.selected_square = None
        self.suggested_move = None
        self.draw_board()

        mode = self.mode_var.get()
        if mode == "Stockfish vs Stockfish":
            # start engine vs engine loop
            self.engine_vs_engine_running = True
            self.ensure_engine()
            threading.Thread(target=self.engine_vs_engine_loop, daemon=True).start()
        else:
            # stop any running self-play
            self.engine_vs_engine_running = False

    def undo(self):
        # undo last two ply if possible (for human vs engine convenience)
        if len(self.board.move_stack) >= 1:
            self.board.pop()
        if len(self.board.move_stack) >= 1:
            self.board.pop()
        self.move_list.delete(0, tk.END)
        self.suggested_move = None
        # rebuild move list
        temp = chess.Board()
        for m in self.board.move_stack:
            temp.push(m)
            self.move_list.insert(tk.END, m.uci())
        self.draw_board()

    def on_close(self):
        self.engine_vs_engine_running = False
        try:
            self.close_engine()
        except Exception:
            pass
        self.root.destroy()

    def request_engine_move(self):
        self.ensure_engine()
        if self.engine is None:
            return
        try:
            limit = chess.engine.Limit()
            depth = self.depth_scale.get()
            if depth > 0:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=self.time_scale.get() / 1000.0)
            res = self.engine.play(self.board, limit)
            mv = res.move
            if mv:
                self.board.push(mv)
                self.move_list.insert(tk.END, mv.uci())
                self.draw_board()
        except Exception as e:
            print("Engine play error:", e)

    def engine_move_blocking(self):
        # helper for engine vs engine: play one move (blocking)
        self.ensure_engine()
        if self.engine is None:
            return None
        try:
            limit = chess.engine.Limit()
            depth = self.depth_scale.get()
            if depth > 0:
                limit = chess.engine.Limit(depth=depth)
            else:
                limit = chess.engine.Limit(time=self.time_scale.get() / 1000.0)
            res = self.engine.play(self.board, limit)
            return res.move
        except Exception as e:
            print("Engine play error:", e)
            return None

    def engine_vs_engine_loop(self):
        # run on background thread, alternating moves until game over or stopped
        while self.engine_vs_engine_running and not self.board.is_game_over():
            mv = self.engine_move_blocking()
            if mv:
                self.board.push(mv)
                self.move_list.insert(tk.END, mv.uci())
                # update GUI from main thread
                self.root.after(1, self.draw_board)
            else:
                break
            # small pause to keep UI responsive and let user see moves
            time.sleep(0.1)
        self.engine_vs_engine_running = False

    def analyze_position(self):
        self.ensure_engine()
        if self.engine is None:
            return
        depth = self.depth_scale.get()
        limit = chess.engine.Limit(depth=depth) if depth > 0 else chess.engine.Limit(time=self.time_scale.get() / 1000.0)
        try:
            info = self.engine.analyse(self.board, limit)
            score = info.get("score")
            pv = info.get("pv", [])
            if pv:
                self.suggested_move = pv[0]
            else:
                self.suggested_move = None
            self.draw_board() # Redraw to show suggestion
            # score can be mate or cp
            s_text = str(score) if score is not None else "-"
            self.eval_label.config(text=f"Eval: {s_text}")
            self.pv_label.config(text="PV: " + " ".join([m.uci() for m in pv]) if pv else "PV: -")
        except Exception as e:
            print("Engine analysis error:", e)

def main():
    """Main function to run the GUI."""
    root = tk.Tk()
    app = ChessGUI(root)
    root.mainloop()
