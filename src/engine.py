class StockfishEngine:
    def __init__(self, path: str):
        self.path = path
        self.process = None

    def start_engine(self):
        import subprocess
        self.process = subprocess.Popen(self.path, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)

    def stop_engine(self):
        if self.process:
            self.process.terminate()
            self.process = None

    def send_command(self, command: str):
        if self.process:
            self.process.stdin.write(command + '\n')
            self.process.stdin.flush()

    def read_output(self):
        if self.process:
            return self.process.stdout.readline().strip()

    def get_best_move(self, board_fen: str, time_limit: int):
        self.send_command(f"position fen {board_fen}")
        self.send_command(f"go movetime {time_limit}")
        while True:
            output = self.read_output()
            if output.startswith("bestmove"):
                return output.split()[1]

    def analyze_position(self, board_fen: str, depth: int):
        self.send_command(f"position fen {board_fen}")
        self.send_command(f"go depth {depth}")
        analysis = {}
        while True:
            output = self.read_output()
            if output.startswith("info"):
                parts = output.split()
                score_index = parts.index("score") + 1
                score_type = parts[score_index]
                score_value = parts[score_index + 1]
                analysis["score"] = score_value
                analysis["score_type"] = score_type
            if output.startswith("bestmove"):
                break
        return analysis