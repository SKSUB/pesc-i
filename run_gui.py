import tkinter as tk
from tkinter import messagebox, StringVar, OptionMenu
import chess
from src.engine import StockfishEngine
from src import gui_tk

class ChessGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simple Chess - GUI")
        self.square_size = 64
        self.canvas_size = self.square_size * 8
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
        self.mode_menu = OptionMenu(ctrl_frame, self.mode_var, "Player vs Player", "Player vs Stockfish", "Stockfish vs Stockfish")
        self.mode_menu.pack(side=tk.LEFT)

        self.board = chess.Board()
        self.engine = StockfishEngine("/usr/local/bin/stockfish")

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

        self.selected_square = None

        self.draw_board()
        self.canvas.bind("<Button-1>", self.on_click)

        # ensure engine stops on close
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def coord_to_square(self, x: int, y: int) -> chess.Square:
        file = int(x // self.square_size)
        rank = 7 - int(y // self.square_size)
        return chess.square(file, rank)

    def draw_board(self) -> None:
        self.canvas.delete("all")
        colors = ["#F0D9B5", "#B58863"]
        for rank in range(8):
            for file in range(8):
                x0 = file * self.square_size
                y0 = (7 - rank) * self.square_size
                color = colors[(rank + file) % 2]
                self.canvas.create_rectangle(x0, y0, x0 + self.square_size, y0 + self.square_size, fill=color, outline="")

        # draw pieces
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                file = chess.square_file(square)
                rank = chess.square_rank(square)
                x = file * self.square_size + self.square_size / 2
                y = (7 - rank) * self.square_size + self.square_size / 2
                symbol = UNICODE_PIECES[piece.symbol()]
                self.canvas.create_text(x, y, text=symbol, font=("Arial", int(self.square_size / 1.8)))

    def on_click(self, event):
        sq = self.coord_to_square(event.x, event.y)
        if self.selected_square is None:
            # select if there's a piece of side to move
            piece = self.board.piece_at(sq)
            if piece and piece.color == self.board.turn:
                self.selected_square = sq
        else:
            move = chess.Move(self.selected_square, sq)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.move_list.insert(tk.END, self.board.peek().uci())
                self.selected_square = None
                self.draw_board()
                self.root.update()
                
                if self.mode_var.get() == "Player vs Stockfish":
                    self.request_engine_move()
                elif self.mode_var.get() == "Stockfish vs Stockfish":
                    self.engine_move()

            else:
                # click destination invalid; clear selection
                self.selected_square = None

    def new_game(self):
        self.board.reset()
        self.move_list.delete(0, tk.END)
        self.draw_board()

    def undo(self):
        if len(self.board.move_stack) >= 1:
            self.board.pop()
        if len(self.board.move_stack) >= 1:
            self.board.pop()
        self.move_list.delete(0, tk.END)
        # rebuild move list
        temp = chess.Board()
        for m in self.board.move_stack:
            temp.push(m)
            self.move_list.insert(tk.END, m.uci())
        self.draw_board()

    def on_close(self):
        try:
            self.engine.stop()
        except Exception:
            pass
        self.root.destroy()

    def request_engine_move(self):
        mv = self.engine.play(self.board, movetime_ms=self.time_scale.get())
        if mv:
            self.board.push(mv)
            self.move_list.insert(tk.END, mv.uci())
            self.draw_board()

    def engine_move(self):
        mv = self.engine.play(self.board, movetime_ms=self.time_scale.get())
        if mv:
            self.board.push(mv)
            self.move_list.insert(tk.END, mv.uci())
            self.draw_board()

    def analyze_position(self):
        depth = self.depth_scale.get()
        if depth == 0:
            depth = None
        res = self.engine.analyze(self.board, depth=depth, movetime_ms=self.time_scale.get())
        s = res["score"]
        st = res["score_type"]
        if st == "cp":
            text = f"{s} cp"
        else:
            text = f"mate {s}"
        self.eval_label.config(text=f"Eval: {text}  (depth {res.get('depth')})")
        self.pv_label.config(text="PV: " + " ".join(res.get("pv", [])))


def main():
    gui_tk.main()


if __name__ == "__main__":
    main()