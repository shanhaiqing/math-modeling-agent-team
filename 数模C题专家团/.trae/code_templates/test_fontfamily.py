# -*- coding: utf-8 -*-
import matplotlib
matplotlib.use("Agg")
import sys
sys.path.insert(0, ".trae/code_templates")
import visualization_style as vs
vs.setup_style()
print("font.family =", vs.plt.rcParams["font.family"])
print("mathtext.fontset =", vs.plt.rcParams.get("mathtext.fontset"))
print("font.sans-serif =", vs.plt.rcParams["font.sans-serif"])