import starvote
import re
import sys
import random
import string
from collections import defaultdict
from starvote import Tiebreaker

# --- CONFIGURATION ---
NUM_SIMULATIONS = 10      # Total elections to test
NUM_CANDIDATES = 5        # Candidates per election
NUM_BALLOTS = 3           # Ballots per election
MAX_SCORE = 5             # STAR voting standard is 0-5
MAX_EXAMPLES_TO_PRINT = 3 # How many divergence examples to show in detail
RANDOM_SEED = 42          # Seed for reproducibility
SHOW_MATRIX = False       # <--- Set to True to see the Runoff Matrix

# --- ANSI Color Codes ---
COLOR_GREEN = '\033[92m'
COLOR_RED = '\033[91m'
COLOR_RESET = '\033[0m'

# ---
# 1. HELPER FUNCTIONS
# ---

def generate_random_election_data(num_candidates, num_ballots):
    """
    Generates a random list of ballots (dicts) and a corresponding CSV string.
    Returns: (ballots_list, csv_string)
    """
    candidates = [string.ascii_uppercase[i] for i in range(num_candidates)]
    ballots = []
    csv_rows = [", ".join(candidates)] # Header

    for _ in range(num_ballots):
        scores = [random.randint(0, MAX_SCORE) for _ in range(num_candidates)]
        ballot_dict = {cand: score for cand, score in zip(candidates, scores)}
        ballots.append(ballot_dict)
        csv_rows.append(", ".join(map(str, scores)))

    return ballots, "\n".join(csv_rows)

def parse_ballots_from_string(ballot_string):
    """Parses CSV string into a list of dictionaries for starvote."""
    lines = [line.split('#')[0].strip() for line in ballot_string.strip().split('\n') if line.strip()]
    if not lines: return []

    headers = [name.strip() for name in re.split(r'[,\t]+', lines[0]) if name.strip()]
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

        ballot = {headers[i]: scores[i] for i in range(len(headers))}
        for _ in range(weight):
            ballots.append(ballot)

    return ballots

def calculate_preference_matrix(ballot_data_text):
    """Parses CSV string into a Preference Matrix."""
    candidates = []
    ballots = []

    lines = [l.strip() for l in ballot_data_text.strip().split('\n') if l.strip()]
    if not lines: return None, None

    headers = [h.strip() for h in lines[0].split(',')]
    candidates = headers

    for line in lines[1:]:
        parts = line.split(',')
        try:
            scores = [int(p.strip()) for p in parts]
            ballots.append(scores)
        except: continue

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
    """Prints the preference matrix with Finalists highlighted."""
    if not candidates or not matrix: return
    if finalists is None: finalists = []

    print("\n--- Runoff (Preference) Matrix ---")
    print(f"Legend: {COLOR_GREEN}For{COLOR_RESET} - {COLOR_RED}Against{COLOR_RESET} - No Preference")
    print("        * indicates Top 2 Finalist")

    col_width = 12
    header = " " * (col_width + 4) + " | "
    for cand in candidates:
        display = f"* {cand}" if cand in finalists else f"  {cand}"
        header += f"{display:^{col_width}} |"
    print(header)
    print("-" * len(header))

    for cand_i in candidates:
        prefix = "* " if cand_i in finalists else "  "
        row_str = f"{prefix}{cand_i} >".rjust(col_width + 4) + " | "
        for cand_j in candidates:
            if cand_i == cand_j:
                row_str += f"{'---':^{col_width}} |"
            else:
                vals = matrix[cand_i][cand_j]
                f_str = f"{COLOR_GREEN}{vals[0]}{COLOR_RESET}-{COLOR_RED}{vals[1]}{COLOR_RESET}-{vals[2]}"
                # simple padding calc
                plain_len = len(f"{vals[0]}-{vals[1]}-{vals[2]}")
                pad = col_width - plain_len
                l_pad = pad // 2
                r_pad = pad - l_pad
                row_str += " " * l_pad + f_str + " " * r_pad + " |"
        print(row_str)

class ReverseSequenceTiebreaker(Tiebreaker):
    def initialize(self, options, ballots):
        if ballots:
            cands = sorted(list(ballots[0].keys()), reverse=True)
            self.order_map = {c: i for i, c in enumerate(cands)}
        else:
            self.order_map = {}

    def __call__(self, options, tie, desired, exception):
        return sorted(tie, key=lambda c: self.order_map.get(c, 999))[:desired]

def analyze_case(csv_string, index, total_cases, show_matrix=False):
    """Helper to print a single case analysis."""
    print("\n" + "#"*60)
    print(f" ANALYSIS OF DIVERGENCE CASE #{index + 1:,} (of {total_cases:,} found) ")
    print("#"*60)

    # Parse and Recalculate
    cands, matrix = calculate_preference_matrix(csv_string)
    ballots = parse_ballots_from_string(csv_string)

    print("\n--- Input Ballot Data ---")
    print(csv_string)

    print("\n--- STARVOTE Re-Run ---")
    winners = starvote.election(
        method=starvote.star,
        ballots=ballots,
        seats=1,
        tiebreaker=ReverseSequenceTiebreaker(),
        verbosity=1
    )

    if show_matrix:
        finalists = get_top_two_finalists(ballots)
        print_matrix(cands, matrix, finalists)

# ---
# 2. MAIN SIMULATION
# ---

def run_simulation():
    # SET SEED FOR REPRODUCIBILITY
    random.seed(RANDOM_SEED)

    count_divergence = 0
    count_normal = 0
    divergence_cases = []

    print("Starting Simulation...")
    print(f"Config:   {NUM_SIMULATIONS:,} elections, {NUM_CANDIDATES} candidates, {NUM_BALLOTS} ballots each.")
    print(f"Show Mat: {SHOW_MATRIX}")
    print(f"Max Ex:   {MAX_EXAMPLES_TO_PRINT}")
    print(f"Seed:     {RANDOM_SEED}")
    print("-" * 60)

    for i in range(NUM_SIMULATIONS):
        ballots, csv_string = generate_random_election_data(NUM_CANDIDATES, NUM_BALLOTS)

        # Calc Score Winner
        scores = defaultdict(int)
        for b in ballots:
            for c, s in b.items():
                scores[c] += s
        ranked_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        score_winner = ranked_scores[0][0]

        # Run STAR Election
        tiebreaker = ReverseSequenceTiebreaker()
        winners = starvote.election(
            method=starvote.star,
            ballots=ballots,
            seats=1,
            tiebreaker=tiebreaker,
            verbosity=0
        )
        star_winner = list(winners)[0]

        if star_winner != score_winner:
            count_divergence += 1
            divergence_cases.append(csv_string)
        else:
            count_normal += 1

        # One-line Progress Indicator
        # FIX: Ensure we never mod by 0 if num_simulations < 100
        progress_step = max(1, NUM_SIMULATIONS // 100)

        if (i + 1) % progress_step == 0 or (i + 1) == NUM_SIMULATIONS:
            sys.stdout.write(f"\r... Completed {i + 1:,} elections")
            sys.stdout.flush()

    print() # Newline after progress bar completes

    # --- REPORTING ---
    print("\n" + "="*30)
    print("      SIMULATION RESULTS      ")
    print("="*30)
    print(f"Total Elections:      {NUM_SIMULATIONS:,}")
    print(f"Divergences Detected: {count_divergence:,} ({(count_divergence/NUM_SIMULATIONS)*100:.1f}%)")
    print(f"No Divergence:        {count_normal:,}")
    print("="*30)

    if divergence_cases:
        to_print = min(len(divergence_cases), MAX_EXAMPLES_TO_PRINT)

        for idx in range(to_print):
            analyze_case(divergence_cases[idx], idx, len(divergence_cases), show_matrix=SHOW_MATRIX)

        remaining = len(divergence_cases) - to_print
        if remaining > 0:
            print(f"\n... and {remaining:,} more divergence cases not shown.")
    else:
        print("\nNo divergences found in this batch.")

if __name__ == "__main__":
    run_simulation()