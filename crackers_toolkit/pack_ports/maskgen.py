#!/usr/bin/env python3
# MaskGen - Generate Password Masks  (Python 3 port)
#
# Original: PACK 0.0.3 by Peter Kacherginsky
# Ported to Python 3 for Cracker's Toolkit.

import sys
import csv
import datetime
from operator import itemgetter
from argparse import ArgumentParser

VERSION = "0.0.3-py3"


class MaskGen:
    def __init__(self):
        self.masks = {}
        self.target_time = None
        self.output_file = None

        self.minlength = None
        self.maxlength = None
        self.mintime = None
        self.maxtime = None
        self.mincomplexity = None
        self.maxcomplexity = None
        self.minoccurrence = None
        self.maxoccurrence = None

        self.customcharset1len = None
        self.customcharset2len = None
        self.customcharset3len = None
        self.customcharset4len = None

        self.pps = 1_000_000_000
        self.showmasks = False
        self.total_occurrence = 0

    def getcomplexity(self, mask):
        count = 1
        for char in mask[1:].split("?"):
            if char == "l":
                count *= 26
            elif char == "u":
                count *= 26
            elif char == "d":
                count *= 10
            elif char == "s":
                count *= 33
            elif char == "a":
                count *= 95
            elif char == "b":
                count *= 256
            elif char in ("h", "H"):
                count *= 16
            elif char == "1" and self.customcharset1len:
                count *= self.customcharset1len
            elif char == "2" and self.customcharset2len:
                count *= self.customcharset2len
            elif char == "3" and self.customcharset3len:
                count *= self.customcharset3len
            elif char == "4" and self.customcharset4len:
                count *= self.customcharset4len
            else:
                print("[!] Error, unknown mask ?%s in a mask %s" % (char, mask))
        return count

    def loadmasks(self, filename):
        with open(filename, "r") as f:
            reader = csv.reader(f, delimiter=",", quotechar='"')
            for row in reader:
                if len(row) < 2:
                    continue
                mask, occurrence = row[0], row[1]
                if mask == "":
                    continue

                mask_occurrence = int(occurrence)
                mask_length = len(mask) // 2
                mask_complexity = self.getcomplexity(mask)
                mask_time = mask_complexity / self.pps

                self.total_occurrence += mask_occurrence

                if (
                    (self.minoccurrence is None or mask_occurrence >= self.minoccurrence)
                    and (self.maxoccurrence is None or mask_occurrence <= self.maxoccurrence)
                    and (self.mincomplexity is None or mask_complexity >= self.mincomplexity)
                    and (self.maxcomplexity is None or mask_complexity <= self.maxcomplexity)
                    and (self.mintime is None or mask_time >= self.mintime)
                    and (self.maxtime is None or mask_time <= self.maxtime)
                    and (self.maxlength is None or mask_length <= self.maxlength)
                    and (self.minlength is None or mask_length >= self.minlength)
                ):
                    self.masks[mask] = {
                        "length": mask_length,
                        "occurrence": mask_occurrence,
                        "complexity": 1 - mask_complexity,
                        "time": mask_time,
                        "optindex": 1 - mask_complexity / mask_occurrence,
                    }

    def generate_masks(self, sorting_mode):
        sample_count = 0
        sample_time = 0
        sample_occurrence = 0

        if self.showmasks:
            print("[L:] Mask:                          [ Occ:  ] [ Time:  ]")

        for mask in sorted(
            self.masks.keys(),
            key=lambda m: self.masks[m][sorting_mode],
            reverse=True,
        ):
            if self.showmasks:
                time_human = (
                    ">1 year"
                    if self.masks[mask]["time"] > 60 * 60 * 24 * 365
                    else str(datetime.timedelta(seconds=int(self.masks[mask]["time"])))
                )
                print(
                    "[{:>2}] {:<30} [{:<7}] [{:>8}]  ".format(
                        self.masks[mask]["length"],
                        mask,
                        self.masks[mask]["occurrence"],
                        time_human,
                    )
                )

            if self.output_file:
                self.output_file.write("%s\n" % mask)

            sample_occurrence += self.masks[mask]["occurrence"]
            sample_time += self.masks[mask]["time"]
            sample_count += 1

            if self.target_time and sample_time > self.target_time:
                print("[!] Target time exceeded.")
                break

        if self.total_occurrence > 0:
            print("[*] Finished generating masks:")
            print("    Masks generated: %s" % sample_count)
            print(
                "    Masks coverage:  %d%% (%d/%d)"
                % (
                    sample_occurrence * 100 // self.total_occurrence,
                    sample_occurrence,
                    self.total_occurrence,
                )
            )
            time_human = (
                ">1 year"
                if sample_time > 60 * 60 * 24 * 365
                else str(datetime.timedelta(seconds=int(sample_time)))
            )
            print("    Masks runtime:   %s" % time_human)

    def getmaskscoverage(self, checkmasks):
        sample_count = 0
        sample_occurrence = 0
        total_complexity = 0

        if self.showmasks:
            print("[L:] Mask:                          [ Occ:  ] [ Time:  ]")

        for mask in checkmasks:
            mask = mask.strip()
            mask_complexity = self.getcomplexity(mask)
            total_complexity += mask_complexity

            if mask in self.masks:
                if self.showmasks:
                    time_human = (
                        ">1 year"
                        if self.masks[mask]["time"] > 60 * 60 * 24 * 365
                        else str(datetime.timedelta(seconds=int(self.masks[mask]["time"])))
                    )
                    print(
                        "[{:>2}] {:<30} [{:<7}] [{:>8}]  ".format(
                            self.masks[mask]["length"],
                            mask,
                            self.masks[mask]["occurrence"],
                            time_human,
                        )
                    )

                if self.output_file:
                    self.output_file.write("%s\n" % mask)

                sample_occurrence += self.masks[mask]["occurrence"]
                sample_count += 1

            if self.target_time and total_complexity / self.pps > self.target_time:
                print("[!] Target time exceeded.")
                break

        if self.total_occurrence > 0:
            total_time = total_complexity / self.pps
            time_human = (
                ">1 year"
                if total_time > 60 * 60 * 24 * 365
                else str(datetime.timedelta(seconds=int(total_time)))
            )
            print("[*] Finished matching masks:")
            print("    Masks matched: %s" % sample_count)
            print(
                "    Masks coverage:  %d%% (%d/%d)"
                % (
                    sample_occurrence * 100 // self.total_occurrence,
                    sample_occurrence,
                    self.total_occurrence,
                )
            )
            print("    Masks runtime:   %s" % time_human)


if __name__ == "__main__":
    parser = ArgumentParser(description="MaskGen %s — Generate Password Masks" % VERSION)
    parser.add_argument("masks_file", nargs="+", help="StatsGen output CSV file(s)")
    parser.add_argument("-t", "--targettime", dest="target_time", type=int, help="Target time (seconds)")
    parser.add_argument("-o", "--outputmasks", dest="output_masks", help="Save masks to file")
    parser.add_argument("--minlength", type=int)
    parser.add_argument("--maxlength", type=int)
    parser.add_argument("--mintime", type=int)
    parser.add_argument("--maxtime", type=int)
    parser.add_argument("--mincomplexity", type=int)
    parser.add_argument("--maxcomplexity", type=int)
    parser.add_argument("--minoccurrence", type=int)
    parser.add_argument("--maxoccurrence", type=int)
    parser.add_argument("--optindex", action="store_true", default=False)
    parser.add_argument("--occurrence", action="store_true", default=False)
    parser.add_argument("--complexity", action="store_true", default=False)
    parser.add_argument("--showmasks", action="store_true", default=False)
    parser.add_argument("--pps", type=int, default=1_000_000_000)
    parser.add_argument("--checkmasks", help="Comma-separated masks to check coverage")
    parser.add_argument("--checkmasksfile", help="File of masks to check coverage")
    parser.add_argument("-q", "--quiet", action="store_true", default=False)

    args = parser.parse_args()

    if not args.quiet:
        print("MaskGen %s" % VERSION)

    maskgen = MaskGen()
    if args.target_time:
        maskgen.target_time = args.target_time
    if args.output_masks:
        print("[*] Saving generated masks to [%s]" % args.output_masks)
        maskgen.output_file = open(args.output_masks, "w")
    if args.minlength:
        maskgen.minlength = args.minlength
    if args.maxlength:
        maskgen.maxlength = args.maxlength
    if args.mintime:
        maskgen.mintime = args.mintime
    if args.maxtime:
        maskgen.maxtime = args.maxtime
    if args.mincomplexity:
        maskgen.mincomplexity = args.mincomplexity
    if args.maxcomplexity:
        maskgen.maxcomplexity = args.maxcomplexity
    if args.minoccurrence:
        maskgen.minoccurrence = args.minoccurrence
    if args.maxoccurrence:
        maskgen.maxoccurrence = args.maxoccurrence

    maskgen.pps = args.pps
    maskgen.showmasks = args.showmasks

    print("[*] Using {:,d} keys/sec for calculations.".format(maskgen.pps))

    for f in args.masks_file:
        print("[*] Analyzing masks in [%s]" % f)
        maskgen.loadmasks(f)

    if args.checkmasks:
        checkmasks = [m.strip() for m in args.checkmasks.split(",")]
        print("[*] Checking coverage of these masks [%s]" % ", ".join(checkmasks))
        maskgen.getmaskscoverage(checkmasks)
    elif args.checkmasksfile:
        with open(args.checkmasksfile, "r") as mf:
            print("[*] Checking coverage of masks in [%s]" % args.checkmasksfile)
            maskgen.getmaskscoverage(mf)
    else:
        if args.occurrence:
            sorting_mode = "occurrence"
        elif args.complexity:
            sorting_mode = "complexity"
        else:
            sorting_mode = "optindex"
        print("[*] Sorting masks by their [%s]." % sorting_mode)
        maskgen.generate_masks(sorting_mode)

    if maskgen.output_file:
        maskgen.output_file.close()
