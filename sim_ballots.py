import numpy as np
import string
import collections

# --- SIMULATION CONFIGURATION ---
SEED_VALUE = 42
NUM_GROUPS = 5           # How many factions exist
CANDS_PER_GROUP = 2      # How many candidates in each faction
NOISE_LEVEL = 0.3        # Probability of score jitter

# Exact number of ballots to generate for each behavior
SCENARIO_COUNTS = {
    "Partisan": 5,       # Voters who love everyone in their group
    "Traditional": 5,    # Voters who pick only ONE candidate in their group
    "Backup": 5,         # Voters who rank their group (5, 4)
    "Protest": 5,        # Voters who give weak support (1, 2) to their group
    "Mixed Strategy": 5, # Voters who flip a coin between Partisan/Traditional
    "Anyone But": 5      # Voters who hate their assigned group, vote for others
}

def add_noise(score, noise_level):
    """Applies random jitter to a score."""
    if np.random.random() > noise_level:
        return score
    # Nudge score (clamped 0-5)
    nudge = np.random.choice([0, 1, 2]) if score == 0 else np.random.choice([-1, 0, 1])
    return int(np.clip(score + nudge, 0, 5))

def run_simulation(seed, num_groups, cands_per_group, scenario_counts, noise_level):

    np.random.seed(seed)

    # 1. Setup Groups & Candidates
    # Generate Group Centers (arranged in a rough circle for separation)
    group_data = {}
    candidates = []

    # Create Labels A, B, C...
    total_cands = num_groups * cands_per_group
    # Handle case if we run out of letters (use A1, A2 if needed, but simple for now)
    labels = [string.ascii_uppercase[i % 26] + (str(i//26) if i>=26 else "") for i in range(total_cands)]

    cand_idx = 0
    for g in range(num_groups):
        # Calculate angle for circular placement
        angle = (2 * np.pi * g) / num_groups
        radius = 0.6
        center = np.array([radius * np.cos(angle), radius * np.sin(angle)])

        g_id = f"Group {g+1}"
        group_cands = []

        # Create Candidates for this Group
        for _ in range(cands_per_group):
            c_name = labels[cand_idx]
            # Position is center + tiny jitter
            c_pos = center + np.random.normal(0, 0.05, 2)

            candidates.append({
                "name": c_name,
                "group": g_id,
                "pos": c_pos,
                "global_index": cand_idx
            })
            group_cands.append(cand_idx) # Store indices belonging to this group
            cand_idx += 1

        group_data[g_id] = {"center": center, "indices": group_cands}

    candidate_names = [c["name"] for c in candidates]
    output_ballots = collections.defaultdict(list)

    # 2. Generate Ballots per Scenario
    for scenario, count in scenario_counts.items():
        for _ in range(count):
            scores = [0] * total_cands

            # Pick a random "Home Group" for this voter
            # (For "Anyone But", this is the group they HATE. For others, it's the group they LOVE.)
            home_group_key = np.random.choice(list(group_data.keys()))
            home_data = group_data[home_group_key]
            my_indices = home_data["indices"]

            # Place voter near their home group (Standard deviation 0.4)
            v_pos = home_data["center"] + np.random.normal(0, 0.4, 2)

            # --- SCENARIO LOGIC ---

            if scenario == "Partisan":
                # Vote 5 for all candidates in home group
                for idx in my_indices:
                    scores[idx] = add_noise(5, noise_level)

            elif scenario == "Traditional":
                # Vote 5 for CLOSEST candidate in home group, 0 others
                best_idx = min(my_indices, key=lambda i: np.linalg.norm(v_pos - candidates[i]["pos"]))
                scores[best_idx] = add_noise(5, noise_level)
                # Noise for others in group
                for idx in my_indices:
                    if idx != best_idx: scores[idx] = add_noise(0, noise_level)

            elif scenario == "Backup":
                # Rank: 5, 4
                sorted_indices = sorted(my_indices, key=lambda i: np.linalg.norm(v_pos - candidates[i]["pos"]))
                if len(sorted_indices) > 0: scores[sorted_indices[0]] = add_noise(5, noise_level)
                if len(sorted_indices) > 1: scores[sorted_indices[1]] = add_noise(4, noise_level)

            elif scenario == "Protest":
                # Random 1s or 2s for home group
                if my_indices:
                    target = np.random.choice(my_indices)
                    scores[target] = np.random.randint(1, 3)

            elif scenario == "Mixed Strategy":
                # 50% Partisan, 50% Traditional
                if np.random.random() > 0.5:
                    for idx in my_indices: scores[idx] = add_noise(5, noise_level)
                else:
                    pick = np.random.choice(my_indices)
                    scores[pick] = add_noise(5, noise_level)
                    for idx in my_indices:
                        if idx != pick: scores[idx] = add_noise(0, noise_level)

            elif scenario == "Anyone But":
                # Assign 0 to Home Group (The "Hated" group)
                # Assign high random scores (3,4,5) to EVERYONE ELSE
                for i in range(total_cands):
                    if i in my_indices:
                        scores[i] = 0 # Strict 0 for hated group
                    else:
                        scores[i] = np.random.choice([3, 4, 5])

            output_ballots[scenario].append(scores)

    return candidate_names, output_ballots

# --- EXECUTE ---
names, results = run_simulation(
    seed=SEED_VALUE,
    num_groups=NUM_GROUPS,
    cands_per_group=CANDS_PER_GROUP,
    scenario_counts=SCENARIO_COUNTS,
    noise_level=NOISE_LEVEL
)

# --- DISPLAY OUTPUT ---
print("--- Simulation Parameters ---")
print(f"Seed: {SEED_VALUE}")
print(f"Candidates: {len(names)} ({NUM_GROUPS} groups of {CANDS_PER_GROUP})")
print(f"Noise Level: {NOISE_LEVEL}")
print("----------------------------")

for scenario, ballots in results.items():
    print(f"\n### {scenario}")
    # Print Headers for every block
    print(f"{','.join(names)}")
    for b in ballots:
        print(f"{','.join(map(str, b))}")