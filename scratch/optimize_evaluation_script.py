import os
import re

orig_path = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\edc-main\evaluate\evaluation_script.py"
dest_path = r"E:\HK2(2025-2026)\Đồ Án 2\MainFolder\MyProject\evaluate\evaluation_script_optimized.py"

with open(orig_path, "r", encoding="utf-8") as f:
    code = f.read()

# Define the replacement function
optimized_function = """def calculateSystemScore(totalsemevallist, totalsemevallistpertag, newreflist, newcandlist):
    import numpy as np
    from scipy.optimize import linear_sum_assignment

    selectedsemevallist = []
    selectedsemevallistpertag = []
    selectedalignment = []
    selectedscores = []
    alldicts = []

    for idx, candidate in enumerate(newcandlist):
        num_cands = len(newcandlist[idx])
        num_refs = len(newreflist[idx])
        
        # Build profit matrix
        profit_matrix = np.zeros((num_cands, num_refs))
        for c in range(num_cands):
            for r in range(num_refs):
                collectedscores = totalsemevallist[idx][c][r]
                if not isinstance(collectedscores, dict):
                    # In case of padded empty strings
                    profit_matrix[c, r] = 0.0
                    continue
                f1score = statistics.mean(
                    [
                        collectedscores.get("ent_type", {}).get("f1", 0.0),
                        collectedscores.get("partial", {}).get("f1", 0.0),
                        collectedscores.get("strict", {}).get("f1", 0.0),
                        collectedscores.get("exact", {}).get("f1", 0.0),
                    ]
                )
                profit_matrix[c, r] = f1score
                
        # Solve maximum weight bipartite matching (minimize -profit)
        row_ind, col_ind = linear_sum_assignment(-profit_matrix)
        
        collectedsemeval = []
        collectedsemevalpertag = []
        total_f1_sum = 0
        
        for c_idx, r_idx in zip(row_ind, col_ind):
            collectedscores = totalsemevallist[idx][c_idx][r_idx]
            total_f1_sum += profit_matrix[c_idx, r_idx]
            collectedsemeval.append(collectedscores)
            collectedsemevalpertag.append(totalsemevallistpertag[idx][c_idx][r_idx])
            
        selectedsemevallist.extend(collectedsemeval)
        selectedsemevallistpertag.extend(collectedsemevalpertag)
        selectedalignment.append((list(row_ind), list(col_ind)))
        div = len(candidate) if len(candidate) > 0 else 1
        selectedscores.append(total_f1_sum / div)"""

# Locate the function and replace it
# The original function starts with: def calculateSystemScore(totalsemevallist, totalsemevallistpertag, newreflist, newcandlist):
# and ends right before: print("-----------------------------------------------------------------")
# We will use regex to find and replace this block.

pattern = r"def calculateSystemScore\(totalsemevallist, totalsemevallistpertag, newreflist, newcandlist\):.*?print\(\"-----------------------------------------------------------------\"\)"
match = re.search(pattern, code, re.DOTALL)
if match:
    # Replace the matched region, but keep the trailing print
    replacement = optimized_function + "\n\n    print(\"-----------------------------------------------------------------\")"
    new_code = re.sub(pattern, replacement, code, flags=re.DOTALL)
    
    # Ensure the parent directory exists and write
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        f.write(new_code)
    print("Successfully created optimized evaluation script!")
else:
    print("Error: Could not locate calculateSystemScore function block.")
