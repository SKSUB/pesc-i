class StockfishWrapper:
    def __init__(self, path: str):
        self.path = path
        self.process = None

    def start_engine(self):
        import subprocess
        self.process = subprocess.Popen(self.path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, universal_newlines=True)

    def stop_engine(self):
        if self.process:
            self.process.stdin.write("quit\n")
            self.process.stdin.flush()
            self.process.terminate()
            self.process = None

    def send_command(self, command: str):
        if self.process:
            self.process.stdin.write(command + "\n")
            self.process.stdin.flush()
            return self.get_response()

    def get_response(self):
        response = ""
        while True:
            line = self.process.stdout.readline()
            if line.startswith("bestmove") or line.startswith("info"):
                response += line
                break
            if line == "":
                break
        return response.strip()

    def get_best_move(self, board_fen: str, time_limit: int):
        self.send_command(f"position fen {board_fen}")
        self.send_command(f"go movetime {time_limit}")
        response = self.get_response()
        best_move = response.split()[1] if "bestmove" in response else None
        return best_move

    def analyze(self, board_fen: str, depth: int):
        self.send_command(f"position fen {board_fen}")
        self.send_command(f"go depth {depth}")
        response = self.get_response()
        return response