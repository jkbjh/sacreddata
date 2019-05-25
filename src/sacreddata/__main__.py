import argparse
import os

from . import filereporter


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("directory")

    args = ap.parse_args()
