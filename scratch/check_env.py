import os
for k, v in os.environ.items():
    if "KEY" in k.upper() or "BASE" in k.upper():
        print(f"{k}: {'***' if v else 'empty'}")
