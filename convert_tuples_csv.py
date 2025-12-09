import re
import string

def convert_ballots_to_csv(input_str):
    # 1. Extract content inside parentheses using Regex
    # This captures "0,0,0" from "(0,0,0)"
    matches = re.findall(r'\(([^)]+)\)', input_str)

    if not matches:
        print("No ballot data found.")
        return

    # 2. Determine the number of candidates from the first entry
    # to generate the dynamic header (A, B, C, etc.)
    first_ballot_parts = matches[0].split(',')
    num_candidates = len(first_ballot_parts)

    # Generate header letters: A,B,C...
    header = ",".join(string.ascii_uppercase[:num_candidates])

    # 3. Print Output
    print(header)
    for match in matches:
        # Strip whitespace from individual numbers just in case
        cleaned_row = ",".join(num.strip() for num in match.split(','))
        print(cleaned_row)

# --- Usage ---
input_data = '''
(0,0,0) (0,0,1) (0,0,1) (0,3,0)
'''

convert_ballots_to_csv(input_data)