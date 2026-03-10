#!/usr/bin/env python3
# PolicyGen - Generate password masks according to a password policy (Python 3 port)
#
# Original: PACK 0.0.2 by Peter Kacherginsky
# Ported to Python 3 for Cracker's Toolkit.

import sys
import datetime
import itertools
from argparse import ArgumentParser

VERSION = "0.0.2-py3"


class PolicyGen:
    def __init__(self):
        self.output_file = None

        self.minlength = 8
        self.maxlength = 8
        self.mindigit = None
        self.minlower = None
        self.minupper = None
        self.minspecial = None
        self.maxdigit = None
        self.maxlower = None
        self.maxupper = None
        self.maxspecial = None

        self.pps = 1_000_000_000
        self.showmasks = False

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
            else:
                print("[!] Error, unknown mask ?%s in a mask %s" % (char, mask))
        return count

    def generate_masks(self, noncompliant):
        total_count = 0
        sample_count = 0
        total_complexity = 0
        sample_complexity = 0

        for length in range(self.minlength, self.maxlength + 1):
            print("[*] Generating %d character password masks." % length)
            total_length_count = 0
            sample_length_count = 0
            total_length_complexity = 0
            sample_length_complexity = 0

            for masklist in itertools.product(["?d", "?l", "?u", "?s"], repeat=length):
                mask = "".join(masklist)

                lowercount = uppercount = digitcount = specialcount = 0
                mask_complexity = self.getcomplexity(mask)
                total_length_count += 1
                total_length_complexity += mask_complexity

                for char in mask[1:].split("?"):
                    if char == "l":
                        lowercount += 1
                    elif char == "u":
                        uppercount += 1
                    elif char == "d":
                        digitcount += 1
                    elif char == "s":
                        specialcount += 1

                compliant = (
                    (self.minlower is None or lowercount >= self.minlower)
                    and (self.maxlower is None or lowercount <= self.maxlower)
                    and (self.minupper is None or uppercount >= self.minupper)
                    and (self.maxupper is None or uppercount <= self.maxupper)
                    and (self.mindigit is None or digitcount >= self.mindigit)
                    and (self.maxdigit is None or digitcount <= self.maxdigit)
                    and (self.minspecial is None or specialcount >= self.minspecial)
                    and (self.maxspecial is None or specialcount <= self.maxspecial)
                )

                if compliant ^ noncompliant:
                    sample_length_count += 1
                    sample_length_complexity += mask_complexity

                    if self.showmasks:
                        mask_time = mask_complexity / self.pps
                        time_human = (
                            ">1 year"
                            if mask_time > 60 * 60 * 24 * 365
                            else str(datetime.timedelta(seconds=int(mask_time)))
                        )
                        print(
                            "[{:>2}] {:<30} [l:{:>2} u:{:>2} d:{:>2} s:{:>2}] [{:>8}]  ".format(
                                length,
                                mask,
                                lowercount,
                                uppercount,
                                digitcount,
                                specialcount,
                                time_human,
                            )
                        )

                    if self.output_file:
                        self.output_file.write("%s\n" % mask)

            total_count += total_length_count
            sample_count += sample_length_count
            total_complexity += total_length_complexity
            sample_complexity += sample_length_complexity

        total_time = total_complexity / self.pps
        total_time_human = (
            ">1 year"
            if total_time > 60 * 60 * 24 * 365
            else str(datetime.timedelta(seconds=int(total_time)))
        )
        print("[*] Total Masks:  %d Time: %s" % (total_count, total_time_human))

        sample_time = sample_complexity / self.pps
        sample_time_human = (
            ">1 year"
            if sample_time > 60 * 60 * 24 * 365
            else str(datetime.timedelta(seconds=int(sample_time)))
        )
        print("[*] Policy Masks: %d Time: %s" % (sample_count, sample_time_human))


if __name__ == "__main__":
    parser = ArgumentParser(description="PolicyGen %s — Password Policy Mask Generator" % VERSION)
    parser.add_argument("-o", "--outputmasks", dest="output_masks", help="Save masks to file")
    parser.add_argument("--pps", type=int, default=1_000_000_000, help="Passwords per second")
    parser.add_argument("--showmasks", action="store_true", default=False)
    parser.add_argument("--noncompliant", action="store_true", default=False, help="Non-compliant masks")
    parser.add_argument("--minlength", type=int, default=8)
    parser.add_argument("--maxlength", type=int, default=8)
    parser.add_argument("--mindigit", type=int, default=None)
    parser.add_argument("--minlower", type=int, default=None)
    parser.add_argument("--minupper", type=int, default=None)
    parser.add_argument("--minspecial", type=int, default=None)
    parser.add_argument("--maxdigit", type=int, default=None)
    parser.add_argument("--maxlower", type=int, default=None)
    parser.add_argument("--maxupper", type=int, default=None)
    parser.add_argument("--maxspecial", type=int, default=None)
    parser.add_argument("-q", "--quiet", action="store_true", default=False)

    args = parser.parse_args()
    if not args.quiet:
        print("PolicyGen %s" % VERSION)

    policygen = PolicyGen()
    if args.output_masks:
        print("[*] Saving generated masks to [%s]" % args.output_masks)
        policygen.output_file = open(args.output_masks, "w")

    policygen.minlength = args.minlength
    policygen.maxlength = args.maxlength
    if args.mindigit is not None:
        policygen.mindigit = args.mindigit
    if args.minlower is not None:
        policygen.minlower = args.minlower
    if args.minupper is not None:
        policygen.minupper = args.minupper
    if args.minspecial is not None:
        policygen.minspecial = args.minspecial
    if args.maxdigit is not None:
        policygen.maxdigit = args.maxdigit
    if args.maxlower is not None:
        policygen.maxlower = args.maxlower
    if args.maxupper is not None:
        policygen.maxupper = args.maxupper
    if args.maxspecial is not None:
        policygen.maxspecial = args.maxspecial

    policygen.pps = args.pps
    policygen.showmasks = args.showmasks

    print("[*] Using {:,d} keys/sec for calculations.".format(policygen.pps))
    print("[*] Password policy:")
    print("    Pass Lengths: min:%d max:%d" % (policygen.minlength, policygen.maxlength))
    print(
        "    Min strength: l:%s u:%s d:%s s:%s"
        % (policygen.minlower, policygen.minupper, policygen.mindigit, policygen.minspecial)
    )
    print(
        "    Max strength: l:%s u:%s d:%s s:%s"
        % (policygen.maxlower, policygen.maxupper, policygen.maxdigit, policygen.maxspecial)
    )

    mode = "compliant" if not args.noncompliant else "non-compliant"
    print("[*] Generating [%s] masks." % mode)
    policygen.generate_masks(args.noncompliant)

    if policygen.output_file:
        policygen.output_file.close()
