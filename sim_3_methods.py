import starvote
import random
import string
from starvote import Tiebreaker

class SimpleTiebreaker(Tiebreaker):
    def __call__(self, options, tie, desired, exception):
        # Consistent tie-breaking by alphabetical order
        return sorted(tie)[:desired]

def generate_ballots(num_cands, num_ballots):
    candidates = list(string.ascii_uppercase[:num_cands])
    ballots = []
    for _ in range(num_ballots):
        ballots.append({c: random.randint(0, 5) for c in candidates})
    return candidates, ballots

def format_csv(candidates, ballots):
    header = ",".join(candidates)
    rows = [",".join(str(b[c]) for c in candidates) for b in ballots]
    return f"{header}\n" + "\n".join(rows)

def find_minimal_gold(num_cands=3, num_ballots=3, num_winners=2, seed=42):
    # Set the seed for reproducibility
    random.seed(seed)
    tiebreaker = SimpleTiebreaker()

    attempt = 0
    while True:
        attempt += 1
        candidates, ballots = generate_ballots(num_cands, num_ballots)

        # Execute methods on identical ballot set
        res_allocated = set(starvote.election(starvote.allocated, ballots, seats=num_winners, tiebreaker=tiebreaker))
        res_bloc = set(starvote.election(starvote.bloc, ballots, seats=num_winners, tiebreaker=tiebreaker))
        res_sss = set(starvote.election(starvote.sss, ballots, seats=num_winners, tiebreaker=tiebreaker))

        # Check for three distinct sets of winners
        unique_results = {
            tuple(sorted(list(res_allocated))),
            tuple(sorted(list(res_bloc))),
            tuple(sorted(list(res_sss)))
        }

        if len(unique_results) == 3:
            # Format results for alignment
            w_alloc = ",".join(sorted(list(res_allocated)))
            w_bloc  = ",".join(sorted(list(res_bloc)))
            w_sss   = ",".join(sorted(list(res_sss)))

            # Print Parameters and Results
            print("--- Election Summary ---")
            print(f"Parameters: candidates={num_cands}, ballots={num_ballots}, winners={num_winners}, seed={seed}")
            print(f"Attempt:    {attempt}")
            print(f"Allocated:  {w_alloc}")
            print(f"Bloc STAR:  {w_bloc}")
            print(f"SSS:        {w_sss}")
            print("\nBallots:")
            print("```text")
            print(format_csv(candidates, ballots))
            print("```")
            break

if __name__ == "__main__":
    # Parameters can be adjusted here
    find_minimal_gold(num_cands=3, num_ballots=3, num_winners=2, seed=42)