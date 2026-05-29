import os
for k, v in os.environ.items():
    print(f"{k}: {v[:30] if len(v) > 30 else v}")
