import starvote
import io
import csv
import re
import random
from collections import defaultdict
from starvote import Tiebreaker

# ---
# 1. CONFIGURATION & INPUT
# ---
csv_input = """
#,A,B,C,D,E
5:5,3,4,1,2
5:5,1,2,4,3
8:2,5,1,3,4
3:4,3,5,1,2
7:4,2,5,1,3
2:3,4,5,2,1
7:1,2,4,5,3
8:3,4,1,2,5
"""

# TIEBREAKER SETTINGS
TIEBREAKER_MODE = 'manual'
MANUAL_ORDER = ['B', 'A', 'C']
RANDOM_SEED = 42

# --- ANSI Color Codes ---
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_RESET = '\033[0m'

# ---
# 2. TIEBREAKER CLASS
# ---
class SequenceTiebreaker(Tiebreaker):
    def __init__(self, mode='last', manual_order=None, silent=False):
        self.mode = mode.lower()
        self.manual_order = manual_order or []
        self.silent = silent
        self.order_map = {}
        self.info_printed = False

    def initialize(self, options, ballots):
        first_ballot = next(iter(ballots))
        cands_in_csv_order = list(first_ballot.keys())

        if self.mode == 'manual' and self.manual_order:
            self.preferred_order = self.manual_order
        elif self.mode == 'first':
            self.preferred_order = cands_in_csv_order
        else:
            self.preferred_order = list(reversed(cands_in_csv_order))

        self.order_map = {c: i for i, c in enumerate(self.preferred_order)}

        if not self.info_printed and not self.silent:
            print(f"Tiebreaker: \"{self.mode.upper()}\" Candidate first - priority order:  {self.preferred_order}")
            self.info_printed = True

    def __call__(self, options, tie, desired, exception):
        ranked = sorted(tie, key=lambda c: self.order_map.get(c, 999))
        winners = ranked[:desired]

        if not self.silent:
            print("\n[Tiebreaker: Sequence Priority]")
            print(f"  Tie detected among: {tie}")
            print(f"  Priority order: {self.preferred_order}")
            print(f"  Result: {winners} selected based on sequence priority.")

        return winners

# ---
# 3. HELPER FUNCTIONS
# ---
def parse_ballots_from_string(ballot_string):
    lines = []
    for line in ballot_string.strip().split('\n'):
        line = line.strip()
        # FIX 1: Allow line to start with "#," (header case)
        if line.startswith("#,"):
            clean_line = line
        else:
            clean_line = line.split('#')[0].strip()

        if clean_line:
            lines.append(clean_line)

    if not lines: return []

    headers = [name.strip() for name in re.split(r'[,\t]+', lines[0]) if name.strip()]

    # FIX 2: If first header is '#', remove it to align with data columns
    if headers and headers[0] == '#':
        headers.pop(0)

    ballots = []
    for line in lines[1:]:
        parts = re.split(r'[,\t]+', line)
        weight = 1
        if ':' in parts[0]:
            w_str, s_str = parts[0].split(':', 1)
            try:
                weight = int(w_str)
                parts[0] = s_str
            except ValueError: pass

        try:
            scores = [int(p.strip()) for p in parts if p.strip()]
        except ValueError: continue

        if len(scores) != len(headers): continue

        ballot = {}
        for i, header in enumerate(headers):
            ballot[header] = scores[i]
        for _ in range(weight):
            ballots.append(ballot)
    return ballots

def calculate_preference_matrix(ballot_data_text):
    candidates = []
    ballots = []
    normalized_lines = []
    for line in ballot_data_text.strip().split('\n'):
        line = line.strip()
        # FIX 1 (Matrix): Allow line to start with "#,"
        if line.startswith("#,"):
            clean = line
        else:
            clean = line.split('#')[0].strip()

        if clean:
            normalized_lines.append(clean.replace('\t', ','))
    normalized_text = "\n".join(normalized_lines)

    try:
        f = io.StringIO(normalized_text)
        reader = csv.reader(f)
        try:
            headers = next(reader)
            if any(h.strip() for h in headers):
                candidates = [h.strip() for h in headers if h.strip()]
                # FIX 2 (Matrix): Remove '#' from candidates list
                if candidates and candidates[0] == '#':
                    candidates.pop(0)
        except StopIteration: return None, None

        for row in reader:
            clean_row = [f.strip() for f in row if f.strip()]
            if not clean_row: continue
            weight = 1
            if ':' in clean_row[0]:
                w_str, s_str = clean_row[0].split(':', 1)
                try:
                    weight = int(w_str)
                    clean_row[0] = s_str
                except ValueError: pass
            try:
                scores = [int(s) for s in clean_row]
                for _ in range(weight):
                    ballots.append(scores)
            except: continue
    except: return None, None

    if not ballots: return None, None
    num_ballots = len(ballots)
    matrix = defaultdict(lambda: defaultdict(tuple))
    for i, c_i in enumerate(candidates):
        for j, c_j in enumerate(candidates):
            if i == j:
                matrix[c_i][c_j] = (0, 0, num_ballots)
                continue
            for_i = 0; against_i = 0; no_pref = 0
            for ballot in ballots:
                if i < len(ballot) and j < len(ballot):
                    if ballot[i] > ballot[j]: for_i += 1
                    elif ballot[j] > ballot[i]: against_i += 1
                    else: no_pref += 1
            matrix[c_i][c_j] = (for_i, against_i, no_pref)
    return candidates, matrix

def get_top_two_finalists(ballots):
    scores = defaultdict(int)
    for b in ballots:
        for c, s in b.items():
            scores[c] += s
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    finalists = []
    if len(ranked) >= 1: finalists.append(ranked[0][0])
    if len(ranked) >= 2: finalists.append(ranked[1][0])
    return finalists

def print_matrix(candidates, matrix, finalists=None):
    if not candidates or not matrix: return
    if finalists is None: finalists = []
    print("\n--- Runoff (Preference) Matrix ---")
    print(f"Legend: {COLOR_GREEN}For{COLOR_RESET} - {COLOR_RED}Against{COLOR_RESET} - No Preference")
    print("        * indicates Top 2 Finalist")

    col_width = max((len(c) + 2 for c in candidates), default=10)
    max_data_str = "0 - 0 - 0"
    if matrix:
        max_data_str = max(
            (f"{matrix[c1][c2][0]} - {matrix[c1][c2][1]} - {matrix[c1][c2][2]}"
             for c1 in candidates for c2 in candidates if c1 != c2),
            key=len, default=max_data_str
        )
    col_width = max(col_width, len(max_data_str), 10)
    row_label_width = col_width + 4
    header = " " * row_label_width + " | "

    for cand in candidates:
        display_name = f"* {cand}" if cand in finalists else f"  {cand}"
        header += f"{display_name:^{col_width}} |"
    print(header)
    print("-" * len(header))

    for cand_i in candidates:
        prefix = "* " if cand_i in finalists else "  "
        row_label = f"{prefix}{cand_i} >"
        row_str = f"{row_label:>{row_label_width}} | "
        for cand_j in candidates:
            if cand_i == cand_j:
                row_str += f"{'---':^{col_width}} |"
            else:
                for_val, against_val, no_pref_val = matrix[cand_i][cand_j]
                raw_str = f"{for_val} - {against_val} - {no_pref_val}"
                padding = col_width - len(raw_str)
                l_pad = padding // 2
                colored_tuple = (
                    f"{COLOR_GREEN}{for_val}{COLOR_RESET} - "
                    f"{COLOR_RED}{against_val}{COLOR_RESET} - "
                    f"{no_pref_val}"
                )
                row_str += f"{' '*l_pad}{colored_tuple}{' '*(padding-l_pad)} |"
        print(row_str)

    print("\n[Condorcet Winner]")
    condorcet_winner = None
    for c1 in candidates:
        is_winner = True
        for c2 in candidates:
            if c1 == c2: continue
            for_c1, against_c1, _ = matrix[c1][c2]
            if for_c1 <= against_c1:
                is_winner = False
                break
        if is_winner:
            condorcet_winner = c1
            break
    print(f"  {condorcet_winner if condorcet_winner else 'No Condorcet Winner (cycle detected)'}")

def print_extended_analysis(ballots, winners):
    if not winners: return
    runoff_winner_name = list(winners)[0]
    scores = defaultdict(int)
    for b in ballots:
        for c, s in b.items():
            scores[c] += s
    max_score = max(scores.values()) if scores else 0
    top_scorers = [c for c, s in scores.items() if s == max_score]

    if runoff_winner_name not in top_scorers:
        ranked_by_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        score_winner_name = ranked_by_score[0][0]
        print(f"\n{'  NOTE: SCORING / RUNOFF DIVERGENCE DETECTED  ':^60}")
        print(f"Score Winner ({score_winner_name}) != Runoff Winner ({runoff_winner_name})")
    else:
        print(f"\n[Analysis] Winner '{runoff_winner_name}' had the highest score ({max_score}). No divergence.")

# ---
# 4. EXECUTION
# ---
def run_election(csv_input, mode, manual_list, seed):
    candidates, matrix = calculate_preference_matrix(csv_input)
    ballots = parse_ballots_from_string(csv_input)
    finalists = get_top_two_finalists(ballots)

    if mode.lower() == 'random':
        tiebreaker_obj = lambda options, tie, desired, exception: random.sample(list(tie), desired)
        tiebreaker_silent = tiebreaker_obj
        random.seed(seed)
    else:
        tiebreaker_obj = SequenceTiebreaker(mode=mode, manual_order=manual_list, silent=False)
        tiebreaker_silent = SequenceTiebreaker(mode=mode, manual_order=manual_list, silent=True)

    if winners_silent := starvote.election(
            method=starvote.star,
            ballots=ballots,
            seats=1,
            tiebreaker=tiebreaker_silent,
            verbosity=0
    ):
        if candidates and matrix:
            print("--- Input Ballot Data ---")
            print(csv_input.strip())
            print_matrix(candidates, matrix, finalists)
            print_extended_analysis(ballots, winners_silent)

    print("\n--- STARVOTE results ---")
    if mode.lower() == 'random':
        random.seed(seed)
        print(f"Tiebreaker: RANDOM Mode (Seed: {seed})")

    winners = starvote.election(
        method=starvote.star,
        ballots=ballots,
        seats=1,
        tiebreaker=tiebreaker_obj,
        verbosity=1
    )

if __name__ == "__main__":
    run_election(csv_input, TIEBREAKER_MODE, MANUAL_ORDER, RANDOM_SEED)