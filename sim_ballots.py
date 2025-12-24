import numpy as np
import string
import collections

# --- SIMULATION CONFIGURATION ---
SEED_VALUE = 99  # Controls Randomness (Groups & Scores)
TOTAL_CANDIDATES = 3  # Total candidates to distribute
NUM_GROUPS = 2  # How many factions to create
NOISE_LEVEL = 0.3        # Probability of score jitter

# Ballot counts per scenario
SCENARIO_COUNTS = {
    "Partisan": 2,
    "Traditional": 1,
    "Backup": 1,
    "Protest": 3,
    "Mixed Strategy": 3,
    "Anyone But": 4
}

def add_noise(score, noise_level):
    """Applies random jitter to a score."""
    if np.random.random() > noise_level:
        return score
    nudge = np.random.choice([0, 1, 2]) if score == 0 else np.random.choice([-1, 0, 1])
    return int(np.clip(score + nudge, 0, 5))

def run_simulation(seed, num_groups, total_cands, scenario_counts, noise_level):

    np.random.seed(seed)

    # --- 1. Randomly Partition Candidates ---
    if total_cands < num_groups:
        raise ValueError("Total candidates must be >= Number of groups")

    group_sizes = [1] * num_groups
    remaining = total_cands - num_groups
    for _ in range(remaining):
        group_sizes[np.random.randint(0, num_groups)] += 1

    # --- 2. Setup Candidates ---
    candidates = []
    group_info = collections.defaultdict(list)
    groups = []

    labels = [string.ascii_uppercase[i % 26] + (str(i//26) if i>=26 else "") for i in range(total_cands)]
    cand_idx = 0

    for g in range(num_groups):
        angle = (2 * np.pi * g) / num_groups
        center = np.array([0.6 * np.cos(angle), 0.6 * np.sin(angle)])
        g_id = f"Group {g+1}"
        g_indices = []

        for _ in range(group_sizes[g]):
            c_name = labels[cand_idx]
            c_pos = center + np.random.normal(0, 0.05, 2)

            candidates.append({
                "name": c_name,
                "group": g_id,
                "pos": c_pos,
                "index": cand_idx
            })
            group_info[g_id].append(c_name)
            g_indices.append(cand_idx)
            cand_idx += 1

        groups.append({"id": g_id, "center": center, "indices": g_indices})

    candidate_names = [c["name"] for c in candidates]
    output_ballots = collections.defaultdict(list)
    combined_ballots = [] # Master list for the final output

    # --- 3. Generate Ballots ---
    for scenario, count in scenario_counts.items():
        for _ in range(count):
            scores = [0] * total_cands
            home_group = np.random.choice(groups)
            my_indices = home_group["indices"]
            v_pos = home_group["center"] + np.random.normal(0, 0.4, 2)

            if scenario == "Partisan":
                for idx in my_indices: scores[idx] = add_noise(5, noise_level)

            elif scenario == "Traditional":
                best_idx = min(my_indices, key=lambda i: np.linalg.norm(v_pos - candidates[i]["pos"]))
                scores[best_idx] = add_noise(5, noise_level)
                for idx in my_indices:
                    if idx != best_idx: scores[idx] = add_noise(0, noise_level)

            elif scenario == "Backup":
                sorted_indices = sorted(my_indices, key=lambda i: np.linalg.norm(v_pos - candidates[i]["pos"]))
                if len(sorted_indices) > 0: scores[sorted_indices[0]] = add_noise(5, noise_level)
                if len(sorted_indices) > 1: scores[sorted_indices[1]] = add_noise(4, noise_level)

            elif scenario == "Protest":
                if my_indices:
                    target = np.random.choice(my_indices)
                    scores[target] = np.random.randint(1, 3)

            elif scenario == "Mixed Strategy":
                if np.random.random() > 0.5:
                    for idx in my_indices: scores[idx] = add_noise(5, noise_level)
                else:
                    pick = np.random.choice(my_indices)
                    scores[pick] = add_noise(5, noise_level)
                    for idx in my_indices:
                        if idx != pick: scores[idx] = add_noise(0, noise_level)

            elif scenario == "Anyone But":
                for i in range(total_cands):
                    if i in my_indices: scores[i] = 0
                    else: scores[i] = np.random.choice([3, 4, 5])

            output_ballots[scenario].append(scores)
            combined_ballots.append(scores)

    return candidate_names, output_ballots, group_info, combined_ballots

# --- EXECUTE ---
names, results, groups_map, all_ballots = run_simulation(
    seed=SEED_VALUE,
    num_groups=NUM_GROUPS,
    total_cands=TOTAL_CANDIDATES,
    scenario_counts=SCENARIO_COUNTS,
    noise_level=NOISE_LEVEL
)

# --- DISPLAY OUTPUT ---
print("--- Simulation Parameters ---")
print(f"Seed: {SEED_VALUE}")
print(f"Groups: {NUM_GROUPS} | Total Candidates: {TOTAL_CANDIDATES}")
print("\nGroups Structure:")
for g_name, c_list in groups_map.items():
    print(f"  {g_name}: {', '.join(c_list)}")
print("----------------------------")

# Print Individual Scenarios
for scenario, ballots in results.items():
    print(f"\n### {scenario}")
    print(f"{','.join(names)}")
    for b in ballots:
        print(f"{','.join(map(str, b))}")

# Print Combined Scenarios
print(f"\n### Combined ({len(all_ballots)} Ballots)")
print(f"{','.join(names)}")
for b in all_ballots:
    print(f"{','.join(map(str, b))}")