import starvote
import io
import csv
import re
from collections import defaultdict
from starvote import Tiebreaker

# ---
# 1. SHARED INPUT DATA
# ---
csv_input = """
A,B,C,D,E
1,2,5,4,3
1,1,4,4,3
4,4,3,3,0
0,0,4,4,4
0,0,2,2,3
3,3,3,3,3
"""

reverse_tiebreaking_order_manual = []

# --- ANSI Color Codes ---
COLOR_GREEN = '\033[92m'  # Green for 'For'
COLOR_RED = '\033[91m'    # Red for 'Against'
COLOR_RESET = '\033[0m'   # Reset to default color

# ---
# 2. HELPER FUNCTIONS
# ---

def parse_ballots_from_string(ballot_string):
    """
    Parses CSV string into a list of dictionaries for starvote.
    Supports weighted rows: '2:3,4,5' -> creates two ballots of 3,4,5.
    """
    lines = []
    # Pre-process lines to handle comments and empty lines
    for line in ballot_string.strip().split('\n'):
        clean_line = line.split('#')[0].strip()
        if clean_line:
            lines.append(clean_line)

    if not lines: return []

    # Parse headers
    headers = [name.strip() for name in re.split(r'[,\t]+', lines[0]) if name.strip()]

    ballots = []
    for line in lines[1:]:
        parts = re.split(r'[,\t]+', line)

        # Check for weight in the first element (e.g., "2:3")
        weight = 1
        if ':' in parts[0]:
            w_str, s_str = parts[0].split(':', 1)
            try:
                weight = int(w_str)
                parts[0] = s_str # Replace "2:3" with "3" for scoring
            except ValueError:
                pass # If parsing fails, treat as normal score

        try:
            scores = [int(p.strip()) for p in parts if p.strip()]
        except ValueError: continue

        if len(scores) != len(headers): continue

        # Create the ballot object
        ballot = {}
        for i, header in enumerate(headers):
            ballot[header] = scores[i]

        # Append it 'weight' times
        for _ in range(weight):
            ballots.append(ballot)

    return ballots

def calculate_preference_matrix(ballot_data_text):
    """
    Parses CSV string into a Preference Matrix.
    Supports weighted rows: '2:3,4,5'.
    """
    candidates = []
    ballots = []

    # Normalize lines (tabs to commas, remove comments)
    normalized_lines = []
    for line in ballot_data_text.strip().split('\n'):
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
        except StopIteration: return None, None

        for row in reader:
            clean_row = [f.strip() for f in row if f.strip()]
            if not clean_row: continue

            # Check for weight
            weight = 1
            if ':' in clean_row[0]:
                w_str, s_str = clean_row[0].split(':', 1)
                try:
                    weight = int(w_str)
                    clean_row[0] = s_str
                except ValueError:
                    pass

            try:
                scores = [int(s) for s in clean_row]
                # Expand the weight into the list immediately
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
            for_i = 0
            against_i = 0
            no_pref = 0
            for ballot in ballots:
                if i < len(ballot) and j < len(ballot):
                    if ballot[i] > ballot[j]: for_i += 1
                    elif ballot[j] > ballot[i]: against_i += 1
                    else: no_pref += 1
            matrix[c_i][c_j] = (for_i, against_i, no_pref)

    return candidates, matrix

def get_top_two_finalists(ballots):
    """Calculates scores to find the two finalists."""
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
    """
    Prints the preference matrix with Finalists highlighted by *.
    """
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
            key=len,
            default=max_data_str
        )
    data_width = len(max_data_str)
    col_width = max(col_width, data_width, 10)

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
                vis_len = len(raw_str)
                padding = col_width - vis_len
                l_pad = padding // 2
                r_pad = padding - l_pad

                colored_tuple = (
                    f"{COLOR_GREEN}{for_val}{COLOR_RESET} - "
                    f"{COLOR_RED}{against_val}{COLOR_RESET} - "
                    f"{no_pref_val}"
                )

                row_str += f"{' '*l_pad}{colored_tuple}{' '*r_pad} |"
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

    if condorcet_winner:
        print(f"  {condorcet_winner}")
    else:
        print("  No Condorcet Winner (cycle detected)")

# ---
# 3. TIEBREAKER CLASS
# ---
class ReverseSequenceTiebreaker(Tiebreaker):
    def __init__(self, manual_order=None):
        self.manual_order = manual_order or []
        self.order_map = {}
        self.info_printed = False

    def initialize(self, options, ballots):
        first = next(iter(ballots))
        cands = list(first.keys())
        if self.manual_order:
            self.preferred_order = self.manual_order
        else:
            self.preferred_order = list(reversed(cands))
        self.order_map = {c: i for i, c in enumerate(self.preferred_order)}

    def __call__(self, options, tie, desired, exception):
        if not self.info_printed and not self.manual_order:
            pass
            self.info_printed = True
        return sorted(tie, key=lambda c: self.order_map.get(c, 999))[:desired]

# ---
# 4. EXTENDED ANALYSIS
# ---
def print_extended_analysis(ballots, winners, matrix):
    """
    Checks for Score vs Runoff inversion and prints detailed analysis.
    """
    if not ballots: return

    # 1. Calculate Score Winner
    scores = defaultdict(int)
    for b in ballots:
        for c, s in b.items():
            scores[c] += s

    ranked_by_score = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    score_winner_name = ranked_by_score[0][0]
    score_winner_points = ranked_by_score[0][1]

    # 2. Get Runoff Winner
    if not winners: return
    runoff_winner_name = list(winners)[0]

    # 3. Check for Divergence
    if score_winner_name != runoff_winner_name:
        votes_winner = 0
        votes_loser = 0
        for b in ballots:
            s_win = b[runoff_winner_name]
            s_lose = b[score_winner_name]
            if s_win > s_lose: votes_winner += 1
            if s_lose > s_win: votes_loser += 1

        print(f"{'  NOTE: SCORING / RUNOFF DIVERGENCE DETECTED  ':^60}")
        print(f"\nWhy did {score_winner_name} lose despite having the highest score?")
        print("-" * 50)
        print(f"1. {score_winner_name} was the 'Consensus Candidate' (Score Winner).")
        print(f"   They received {score_winner_points} points.")
        print(f"\n2. {runoff_winner_name} was the 'Majority Favorite' (Runoff Winner).")
        print(f"   In the head-to-head runoff, the majority preferred {runoff_winner_name}.")
        print("-" * 50)

# ---
# 5. EXECUTION
# ---

def run_election(csv_input, manual_tiebreaker_list):
    # A. Matrix Calculation
    candidates, matrix = calculate_preference_matrix(csv_input)
    if candidates and matrix:
        print("--- Input Ballot Data ---")
        print(csv_input.strip())

    # B. Starvote Execution
    ballots = parse_ballots_from_string(csv_input)
    sequence_tiebreaker = ReverseSequenceTiebreaker(manual_order=manual_tiebreaker_list)

    print("\n--- STARVOTE results: https://github.com/larryhastings/starvote ---")
    winners = starvote.election(
        method=starvote.star,
        ballots=ballots,
        seats=1,
        tiebreaker=sequence_tiebreaker,
        verbosity=1
    )

    # C. Identify Finalists for Visuals
    finalists = get_top_two_finalists(ballots)

    # D. Print Matrix with Finalists highlighted
    if winners:
        print_matrix(candidates, matrix, finalists)

        # E. Print Analysis
        print_extended_analysis(ballots, winners, matrix)

if __name__ == "__main__":
    run_election(csv_input, reverse_tiebreaking_order_manual)