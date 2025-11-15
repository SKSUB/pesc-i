import tkinter as tk
from tkinter import messagebox
import chess


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

        self.board = chess.Board()

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

        tk.Button(ctrl, text="Engine move", command=self.request_engine_move).pack(fill="x", pady=4)
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
                # ask engine for reply
                reply = self.engine.get_best_move(self.board, time_limit=0.2)
                if reply:
                    try:
                        m = chess.Move.from_uci(reply)
                        if m in self.board.legal_moves:
                            self.board.push(m)
                            self.move_list.insert(tk.END, self.board.peek().uci())
                            self.draw_board()
                    except Exception:
                        pass
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
        # called after player move to get engine reply
        mv = self.engine.play(self.board, movetime_ms=self.time_scale.get())
        if mv:
            self.board.push(mv)
            self.update_board_ui()
            # optional: show a quick analysis after engine move
            self.analyze_position()

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
    board = chess.Board()

    unicode_pieces = {
        'P': '♙', 'N': '♘', 'B': '♗', 'R': '♖', 'Q': '♕', 'K': '♔',
        'p': '♟', 'n': '♞', 'b': '♝', 'r': '♜', 'q': '♛', 'k': '♚'
    }

    root = tk.Tk()
    root.title("Simple Chess - No Engine")

    selected_sq = {'sq': None}
    squares_btn = {}

    def square_bg(file_idx, rank_idx):
        return "#F0D9B5" if (file_idx + rank_idx) % 2 == 0 else "#B58863"

    def piece_unicode_at(sq):
        p = board.piece_at(sq)
        return unicode_pieces.get(p.symbol(), '') if p else ''

    def update_board():
        for rank in range(7, -1, -1):
            for file_idx in range(8):
                sq = chess.square(file_idx, rank)
                btn = squares_btn[sq]
                btn.config(text=piece_unicode_at(sq))
                # highlight selected
                if selected_sq['sq'] == sq:
                    btn.config(relief=tk.SUNKEN)
                else:
                    btn.config(relief=tk.RAISED)
                btn.config(bg=square_bg(file_idx, rank))

        status_var.set(f"{'White' if board.turn else 'Black'} to move. Moves: {board.fullmove_number}")

    def on_square_click(sq):
        # If nothing selected, try select a piece of current turn
        sel = selected_sq['sq']
        piece = board.piece_at(sq)
        if sel is None:
            if piece is None or piece.color != board.turn:
                return
            selected_sq['sq'] = sq
            update_board()
            return

        # If same square clicked again -> deselect
        if sel == sq:
            selected_sq['sq'] = None
            update_board()
            return

        # Attempt move (handle simple promotion to queen)
        promotion = None
        if board.piece_type_at(sel) == chess.PAWN and chess.square_rank(sq) in (0, 7):
            promotion = chess.QUEEN
        mv = chess.Move(sel, sq, promotion=promotion) if promotion else chess.Move(sel, sq)

        if mv in board.legal_moves:
            board.push(mv)
            selected_sq['sq'] = None
            update_board()
            if board.is_checkmate():
                messagebox.showinfo("Game over", f"Checkmate! {'White' if not board.turn else 'Black'} wins.")
            elif board.is_stalemate():
                messagebox.showinfo("Game over", "Stalemate.")
            return
        else:
            # If illegal, try to select new piece if it belongs to current turn
            if piece and piece.color == board.turn:
                selected_sq['sq'] = sq
            else:
                messagebox.showwarning("Illegal move", "That move is not legal.")
                selected_sq['sq'] = None
        update_board()

    board_frame = tk.Frame(root)
    board_frame.grid(row=0, column=0, padx=8, pady=8)

    # create 8x8 buttons
    for r_ui, rank in enumerate(range(7, -1, -1)):
        for file_idx in range(8):
            sq = chess.square(file_idx, rank)
            btn = tk.Button(board_frame, text=piece_unicode_at(sq),
                            font=("DejaVu Sans", 24), width=2, height=1,
                            command=lambda s=sq: on_square_click(s))
            btn.grid(row=r_ui, column=file_idx)
            squares_btn[sq] = btn

    control_frame = tk.Frame(root)
    control_frame.grid(row=1, column=0, pady=(0, 8))

    def new_game():
        board.reset()
        selected_sq['sq'] = None
        update_board()

    def undo():
        if board.move_stack:
            board.pop()
            selected_sq['sq'] = None
            update_board()

    tk.Button(control_frame, text="New Game", command=new_game).pack(side=tk.LEFT, padx=4)
    tk.Button(control_frame, text="Undo", command=undo).pack(side=tk.LEFT, padx=4)
    status_var = tk.StringVar()
    status_label = tk.Label(root, textvariable=status_var)
    status_label.grid(row=2, column=0, pady=(0,8))

    update_board()
    root.mainloop()


if __name__ == "__main__":
    main()
