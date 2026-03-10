#!/usr/bin/env python3
# StatsGen - Password Statistical Analysis tool  (Python 3 port)
#
# Original: PACK 0.0.3 by Peter Kacherginsky
# Ported to Python 3 for Cracker's Toolkit.

import sys
import re
import operator
import string
from argparse import ArgumentParser
import time

VERSION = "0.0.3-py3"


class StatsGen:
    def __init__(self):
        self.output_file = None

        # Filters
        self.minlength = None
        self.maxlength = None
        self.simplemasks = None
        self.charsets = None
        self.quiet = False
        self.debug = True

        # Stats dictionaries
        self.stats_length = {}
        self.stats_simplemasks = {}
        self.stats_advancedmasks = {}
        self.stats_charactersets = {}

        self.hiderare = False

        self.filter_counter = 0
        self.total_counter = 0

        self.mindigit = None
        self.minupper = None
        self.minlower = None
        self.minspecial = None
        self.maxdigit = None
        self.maxupper = None
        self.maxlower = None
        self.maxspecial = None

    def analyze_password(self, password):
        pass_length = len(password)
        digit = lower = upper = special = 0
        simplemask = []
        advancedmask_string = ""

        for letter in password:
            if letter in string.digits:
                digit += 1
                advancedmask_string += "?d"
                if not simplemask or simplemask[-1] != "digit":
                    simplemask.append("digit")
            elif letter in string.ascii_lowercase:
                lower += 1
                advancedmask_string += "?l"
                if not simplemask or simplemask[-1] != "string":
                    simplemask.append("string")
            elif letter in string.ascii_uppercase:
                upper += 1
                advancedmask_string += "?u"
                if not simplemask or simplemask[-1] != "string":
                    simplemask.append("string")
            else:
                special += 1
                advancedmask_string += "?s"
                if not simplemask or simplemask[-1] != "special":
                    simplemask.append("special")

        simplemask_string = "".join(simplemask) if len(simplemask) <= 3 else "othermask"
        policy = (digit, lower, upper, special)

        if digit and not lower and not upper and not special:
            charset = "numeric"
        elif not digit and lower and not upper and not special:
            charset = "loweralpha"
        elif not digit and not lower and upper and not special:
            charset = "upperalpha"
        elif not digit and not lower and not upper and special:
            charset = "special"
        elif not digit and lower and upper and not special:
            charset = "mixedalpha"
        elif digit and lower and not upper and not special:
            charset = "loweralphanum"
        elif digit and not lower and upper and not special:
            charset = "upperalphanum"
        elif not digit and lower and not upper and special:
            charset = "loweralphaspecial"
        elif not digit and not lower and upper and special:
            charset = "upperalphaspecial"
        elif digit and not lower and not upper and special:
            charset = "specialnum"
        elif not digit and lower and upper and special:
            charset = "mixedalphaspecial"
        elif digit and not lower and upper and special:
            charset = "upperalphaspecialnum"
        elif digit and lower and not upper and special:
            charset = "loweralphaspecialnum"
        elif digit and lower and upper and not special:
            charset = "mixedalphanum"
        else:
            charset = "all"

        return (pass_length, charset, simplemask_string, advancedmask_string, policy)

    def generate_stats(self, filename):
        with open(filename, "r", encoding="latin-1", errors="replace") as f:
            for password in f:
                password = password.rstrip("\r\n")
                if len(password) == 0:
                    continue

                self.total_counter += 1
                (pass_length, characterset, simplemask, advancedmask, policy) = (
                    self.analyze_password(password)
                )
                (digit, lower, upper, special) = policy

                if (
                    (self.charsets is None or characterset in self.charsets)
                    and (self.simplemasks is None or simplemask in self.simplemasks)
                    and (self.maxlength is None or pass_length <= self.maxlength)
                    and (self.minlength is None or pass_length >= self.minlength)
                ):
                    self.filter_counter += 1

                    if self.mindigit is None or digit < self.mindigit:
                        self.mindigit = digit
                    if self.maxdigit is None or digit > self.maxdigit:
                        self.maxdigit = digit
                    if self.minupper is None or upper < self.minupper:
                        self.minupper = upper
                    if self.maxupper is None or upper > self.maxupper:
                        self.maxupper = upper
                    if self.minlower is None or lower < self.minlower:
                        self.minlower = lower
                    if self.maxlower is None or lower > self.maxlower:
                        self.maxlower = lower
                    if self.minspecial is None or special < self.minspecial:
                        self.minspecial = special
                    if self.maxspecial is None or special > self.maxspecial:
                        self.maxspecial = special

                    self.stats_length[pass_length] = self.stats_length.get(pass_length, 0) + 1
                    self.stats_charactersets[characterset] = self.stats_charactersets.get(characterset, 0) + 1
                    self.stats_simplemasks[simplemask] = self.stats_simplemasks.get(simplemask, 0) + 1
                    self.stats_advancedmasks[advancedmask] = self.stats_advancedmasks.get(advancedmask, 0) + 1

    def print_stats(self):
        if self.total_counter == 0:
            print("[!] No passwords to analyze.")
            return

        print(
            "[+] Analyzing %d%% (%d/%d) of passwords"
            % (
                self.filter_counter * 100 // self.total_counter,
                self.filter_counter,
                self.total_counter,
            )
        )
        print(
            "    NOTE: Statistics below is relative to the number of analyzed passwords, not total number of passwords"
        )

        print("\n[*] Length:")
        for length, count in sorted(
            self.stats_length.items(), key=operator.itemgetter(1), reverse=True
        ):
            pct = count * 100 // self.filter_counter
            if self.hiderare and pct == 0:
                continue
            print("[+] %25d: %02d%% (%d)" % (length, pct, count))

        print("\n[*] Character-set:")
        for char, count in sorted(
            self.stats_charactersets.items(), key=operator.itemgetter(1), reverse=True
        ):
            pct = count * 100 // self.filter_counter
            if self.hiderare and pct == 0:
                continue
            print("[+] %25s: %02d%% (%d)" % (char, pct, count))

        print("\n[*] Password complexity:")
        print(
            "[+]                     digit: min(%s) max(%s)"
            % (self.mindigit, self.maxdigit)
        )
        print(
            "[+]                     lower: min(%s) max(%s)"
            % (self.minlower, self.maxlower)
        )
        print(
            "[+]                     upper: min(%s) max(%s)"
            % (self.minupper, self.maxupper)
        )
        print(
            "[+]                   special: min(%s) max(%s)"
            % (self.minspecial, self.maxspecial)
        )

        print("\n[*] Simple Masks:")
        for simplemask, count in sorted(
            self.stats_simplemasks.items(), key=operator.itemgetter(1), reverse=True
        ):
            pct = count * 100 // self.filter_counter
            if self.hiderare and pct == 0:
                continue
            print("[+] %25s: %02d%% (%d)" % (simplemask, pct, count))

        print("\n[*] Advanced Masks:")
        for advancedmask, count in sorted(
            self.stats_advancedmasks.items(), key=operator.itemgetter(1), reverse=True
        ):
            pct = count * 100 // self.filter_counter
            if pct > 0:
                print("[+] %25s: %02d%% (%d)" % (advancedmask, pct, count))
            if self.output_file:
                self.output_file.write("%s,%d\n" % (advancedmask, count))


if __name__ == "__main__":
    parser = ArgumentParser(description="StatsGen %s — Password Statistical Analysis" % VERSION)
    parser.add_argument("passwords", help="Passwords file to analyze")
    parser.add_argument("-o", "--output", dest="output_file", help="Save masks to file")
    parser.add_argument("--minlength", type=int, help="Minimum password length")
    parser.add_argument("--maxlength", type=int, help="Maximum password length")
    parser.add_argument("--charset", dest="charsets", help="Charset filter (comma separated)")
    parser.add_argument("--simplemask", dest="simplemasks", help="Mask filter (comma separated)")
    parser.add_argument("--hiderare", action="store_true", default=False, help="Hide stats < 1%%")
    parser.add_argument("-q", "--quiet", action="store_true", default=False)

    args = parser.parse_args()

    if not args.quiet:
        print("StatsGen %s" % VERSION)

    print("[*] Analyzing passwords in [%s]" % args.passwords)

    statsgen = StatsGen()
    if args.minlength is not None:
        statsgen.minlength = args.minlength
    if args.maxlength is not None:
        statsgen.maxlength = args.maxlength
    if args.charsets is not None:
        statsgen.charsets = [x.strip() for x in args.charsets.split(",")]
    if args.simplemasks is not None:
        statsgen.simplemasks = [x.strip() for x in args.simplemasks.split(",")]
    if args.hiderare:
        statsgen.hiderare = True
    if args.output_file:
        print("[*] Saving advanced masks and occurrences to [%s]" % args.output_file)
        statsgen.output_file = open(args.output_file, "w")

    statsgen.generate_stats(args.passwords)
    statsgen.print_stats()

    if statsgen.output_file:
        statsgen.output_file.close()
