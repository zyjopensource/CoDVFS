# -*- coding: utf-8 -*-
import argparse
from codvfs.optim.search import bayes_search

def main():
    parser = argparse.ArgumentParser(description="CoDVFS: Coordinated DVFS with Bayesian Optimization")
    parser.add_argument("--app", choices=["hplai", "hpl"], default="hplai",
                        help="application: hplai or hpl")
    parser.add_argument("--iters", type=int, default=32, help="bayes optimization iterations")
    parser.add_argument("--quicktest", action="store_true", help="skip app execution")
    args = parser.parse_args()
    bayes_search(app=args.app, iterations=args.iters, quicktest=args.quicktest)

if __name__ == "__main__":
    main()
