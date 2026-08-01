# -*- coding: utf-8 -*-
from PIL import Image
import os
shots = r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\outputs\demo\screenshots"
names = ["00_home", "01_normal_auto_send", "02_promo_human", "03_negation_fixed", "04_oversize_error", "05_badconf_error", "06_refund_faq", "07_double_negation"]
out = r"C:\Users\admin\Documents\Codex\2026-08-01\new-chat\outputs\demo\Demo录屏_风险人工介入评估器.gif"
frames = []
for n in names:
    im = Image.open(os.path.join(shots, n + ".png")).convert("RGB")
    frames.append(im)
durations = [2600] + [2200] * (len(frames) - 1)
frames[0].save(out, save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=False)
print("gif saved:", out, os.path.getsize(out) // 1024, "KB", len(frames), "frames")