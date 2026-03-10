#!/usr/bin/env python3
# RuleGen - Advanced automated password rule and wordlist generator (Python 3 port)
#
# Original: PACK 0.0.4 by Peter Kacherginsky
# Uses Levenshtein Reverse Path algorithm and Enchant spell checking.
# Ported to Python 3 for Cracker's Toolkit.

import sys
import re
import time
import operator
import subprocess
import multiprocessing
from argparse import ArgumentParser
from collections import Counter

VERSION = "0.0.4-py3"

# Try to import enchant; provide fallback message if missing
try:
    import enchant
    HAS_ENCHANT = True
except ImportError:
    HAS_ENCHANT = False

HASHCAT_PATH = "hashcat/"


class RuleGen:
    def __init__(self, language="en", providers="aspell,myspell", basename="analysis",
                 threads=None, wordlist=None):
        if threads is None:
            threads = multiprocessing.cpu_count()
        self.threads = threads

        self.enchant_dict = None
        if HAS_ENCHANT and wordlist is None:
            broker = enchant.Broker()
            broker.set_ordering("*", providers)
            try:
                self.enchant_dict = enchant.Dict(language, broker)
            except enchant.errors.DictNotFoundError:
                print("[!] Dictionary for language '%s' not found." % language)
                self.enchant_dict = None
        elif HAS_ENCHANT and wordlist is not None:
            self.enchant_dict = enchant.request_pwl_dict(wordlist)

        self.basename = basename

        # Finetuning word generation
        self.max_word_dist = 10
        self.max_words = 10
        self.more_words = False
        self.simple_words = False

        # Finetuning rule generation
        self.max_rule_len = 10
        self.max_rules = 10
        self.more_rules = False
        self.simple_rules = False
        self.brute_rules = False

        # Debugging options
        self.verbose = False
        self.debug = False
        self.word = None
        self.quiet = False
        self.hashcat = False

        # Statistics
        self.numeric_stats_total = 0
        self.special_stats_total = 0
        self.foreign_stats_total = 0

        # Preanalysis patterns
        self.password_pattern = {
            "insertion": re.compile(r'^[^a-z]*(?P<password>.+?)[^a-z]*$', re.IGNORECASE),
            "email": re.compile(r'^(?P<password>.+?)@[A-Z0-9.-]+\.[A-Z]{2,4}', re.IGNORECASE),
            "alldigits": re.compile(r'^(\d+)$', re.IGNORECASE),
            "allspecial": re.compile(r'^([^a-z0-9]+)$', re.IGNORECASE),
        }

        # Hashcat rules engine
        self.hashcat_rule = {}
        self.hashcat_rule[':'] = lambda x: x
        self.hashcat_rule["l"] = lambda x: x.lower()
        self.hashcat_rule["u"] = lambda x: x.upper()
        self.hashcat_rule["c"] = lambda x: x.capitalize()
        self.hashcat_rule["C"] = lambda x: x[0].lower() + x[1:].upper() if len(x) > 1 else x.lower()
        self.hashcat_rule["t"] = lambda x: x.swapcase()
        self.hashcat_rule["T"] = lambda x, y: x[:y] + x[y].swapcase() + x[y + 1:]
        self.hashcat_rule["E"] = lambda x: " ".join([i[0].upper() + i[1:] for i in x.split(" ")])
        self.hashcat_rule["r"] = lambda x: x[::-1]
        self.hashcat_rule["{"] = lambda x: x[1:] + x[0]
        self.hashcat_rule["}"] = lambda x: x[-1] + x[:-1]
        self.hashcat_rule["d"] = lambda x: x + x
        self.hashcat_rule["p"] = lambda x, y: x * y
        self.hashcat_rule["f"] = lambda x: x + x[::-1]
        self.hashcat_rule["z"] = lambda x, y: x[0] * y + x
        self.hashcat_rule["Z"] = lambda x, y: x + x[-1] * y
        self.hashcat_rule["q"] = lambda x: "".join([i + i for i in x])
        self.hashcat_rule["y"] = lambda x, y: x[:y] + x
        self.hashcat_rule["Y"] = lambda x, y: x + x[-y:]
        self.hashcat_rule["["] = lambda x: x[1:]
        self.hashcat_rule["]"] = lambda x: x[:-1]
        self.hashcat_rule["D"] = lambda x, y: x[:y] + x[y + 1:]
        self.hashcat_rule["'"] = lambda x, y: x[:y]
        self.hashcat_rule["x"] = lambda x, y, z: x[:y] + x[y + z:]
        self.hashcat_rule["@"] = lambda x, y: x.replace(y, '')
        self.hashcat_rule["$"] = lambda x, y: x + y
        self.hashcat_rule["^"] = lambda x, y: y + x
        self.hashcat_rule["i"] = lambda x, y, z: x[:y] + z + x[y:]
        self.hashcat_rule["o"] = lambda x, y, z: x[:y] + z + x[y + 1:]
        self.hashcat_rule["s"] = lambda x, y, z: x.replace(y, z)
        self.hashcat_rule["L"] = lambda x, y: x[:y] + chr(ord(x[y]) << 1) + x[y + 1:]
        self.hashcat_rule["R"] = lambda x, y: x[:y] + chr(ord(x[y]) >> 1) + x[y + 1:]
        self.hashcat_rule["+"] = lambda x, y: x[:y] + chr(ord(x[y]) + 1) + x[y + 1:]
        self.hashcat_rule["-"] = lambda x, y: x[:y] + chr(ord(x[y]) - 1) + x[y + 1:]
        self.hashcat_rule["."] = lambda x, y: x[:y] + x[y + 1] + x[y + 1:]
        self.hashcat_rule[","] = lambda x, y: x[:y] + x[y - 1] + x[y + 1:]
        self.hashcat_rule["k"] = lambda x: x[1] + x[0] + x[2:]
        self.hashcat_rule["K"] = lambda x: x[:-2] + x[-1] + x[-2]
        self.hashcat_rule["*"] = lambda x, y, z: (
            x[:y] + x[z] + x[y + 1:z] + x[y] + x[z + 1:]
            if z > y else
            x[:z] + x[y] + x[z + 1:y] + x[z] + x[y + 1:]
        )

        # Leet speak substitutions
        self.leet = {
            "1": "i", "2": "z", "3": "e", "4": "a", "5": "s",
            "6": "b", "7": "t", "8": "b", "9": "g", "0": "o",
            "!": "i", "|": "i", "@": "a", "$": "s", "+": "t",
        }

        # Preanalysis rules to try for each word
        self.preanalysis_rules = [
            ([], self.hashcat_rule[':']),
            (['r'], self.hashcat_rule['r']),
        ]

    # ── Levenshtein ──────────────────────────────────────────────
    def levenshtein(self, word, password):
        matrix = []
        for i in range(len(password) + 1):
            matrix.append([])
            for j in range(len(word) + 1):
                if i == 0:
                    matrix[i].append(j)
                elif j == 0:
                    matrix[i].append(i)
                else:
                    matrix[i].append(0)

        for i in range(1, len(password) + 1):
            for j in range(1, len(word) + 1):
                if password[i - 1] == word[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1]
                else:
                    insertion = matrix[i - 1][j] + 1
                    deletion = matrix[i][j - 1] + 1
                    substitution = matrix[i - 1][j - 1] + 1
                    matrix[i][j] = min(insertion, deletion, substitution)
        return matrix

    def levenshtein_distance(self, s1, s2):
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if not s1:
            return len(s2)
        previous_row = list(range(len(s2) + 1))
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]

    def generate_levenshtein_rules(self, word, password):
        matrix = self.levenshtein(word, password)
        paths = self.levenshtein_reverse_recursive(matrix, len(matrix) - 1, len(matrix[0]) - 1, 0)
        return [path for path in paths if len(path) <= matrix[-1][-1]]

    def levenshtein_reverse_recursive(self, matrix, i, j, path_len):
        if i == 0 and j == 0 or path_len > matrix[-1][-1]:
            return [[]]

        paths = []
        cost = matrix[i][j]
        cost_delete = cost_insert = cost_equal_or_replace = sys.maxsize

        if i > 0:
            cost_insert = matrix[i - 1][j]
        if j > 0:
            cost_delete = matrix[i][j - 1]
        if i > 0 and j > 0:
            cost_equal_or_replace = matrix[i - 1][j - 1]

        cost_min = min(cost_delete, cost_insert, cost_equal_or_replace)

        if cost_insert == cost_min:
            for p in self.levenshtein_reverse_recursive(matrix, i - 1, j, path_len + 1):
                paths.append(p + [('insert', i - 1, j)])
        if cost_delete == cost_min:
            for p in self.levenshtein_reverse_recursive(matrix, i, j - 1, path_len + 1):
                paths.append(p + [('delete', i, j - 1)])
        if cost_equal_or_replace == cost_min:
            if cost_equal_or_replace == cost:
                for p in self.levenshtein_reverse_recursive(matrix, i - 1, j - 1, path_len):
                    paths.append(p)
            else:
                for p in self.levenshtein_reverse_recursive(matrix, i - 1, j - 1, path_len + 1):
                    paths.append(p + [('replace', i - 1, j - 1)])
        return paths

    def load_custom_wordlist(self, wordlist_file):
        if HAS_ENCHANT:
            self.enchant_dict = enchant.request_pwl_dict(wordlist_file)

    # ── Word generation ──────────────────────────────────────────
    def generate_words(self, password):
        if self.debug:
            print("[*] Generating source words for %s" % password)

        words = []
        best_found_distance = 9999

        if not self.brute_rules:
            active_rules = self.preanalysis_rules[:1]
        else:
            active_rules = self.preanalysis_rules

        for pre_rule, pre_rule_lambda in active_rules:
            pre_password = pre_rule_lambda(password)

            if self.word:
                suggestions = [self.word]
            elif self.simple_words:
                suggestions = self.generate_simple_words(pre_password)
            else:
                suggestions = self.generate_advanced_words(pre_password)

            extra = []
            for s in suggestions[:self.max_words]:
                cleaned = s.replace(' ', '').replace('-', '')
                if cleaned not in suggestions:
                    extra.append(cleaned)
            suggestions.extend(extra)

            for suggestion in suggestions:
                distance = self.levenshtein_distance(suggestion, pre_password)
                words.append({
                    "suggestion": suggestion,
                    "distance": distance,
                    "password": pre_password,
                    "pre_rule": pre_rule,
                    "best_rule_length": 9999,
                })

        words_collection = []
        for word in sorted(words, key=lambda w: w["distance"]):
            if not self.more_words:
                if word["distance"] < best_found_distance:
                    best_found_distance = word["distance"]
                elif word["distance"] > best_found_distance:
                    break

            if word["distance"] <= self.max_word_dist:
                words_collection.append(word)

        if self.max_words:
            words_collection = words_collection[:self.max_words]
        return words_collection

    def generate_simple_words(self, password):
        if self.enchant_dict:
            return self.enchant_dict.suggest(password)
        return []

    def generate_advanced_words(self, password):
        m = self.password_pattern["insertion"].match(password)
        if m:
            password = m.group('password')
        m = self.password_pattern["email"].match(password)
        if m:
            password = m.group('password')
        cleaned = ''
        for c in password:
            cleaned += self.leet.get(c, c)
        password = cleaned

        if self.enchant_dict:
            return self.enchant_dict.suggest(password)
        return []

    # ── Hashcat offset helpers ───────────────────────────────────
    def int_to_hashcat(self, N):
        if N < 10:
            return str(N)
        return chr(65 + N - 10)

    def hashcat_to_int(self, N):
        if N.isdigit():
            return int(N)
        return ord(N) - 65 + 10

    # ── Hashcat rule generation ──────────────────────────────────
    def generate_hashcat_rules(self, suggestion, password):
        lev_rules = self.generate_levenshtein_rules(suggestion, password)
        hashcat_rules = []
        best_found_rule_length = 9999

        for lev_rule in lev_rules:
            if self.simple_rules:
                hr = self.generate_simple_hashcat_rules(suggestion, lev_rule, password)
            else:
                hr = self.generate_advanced_hashcat_rules(suggestion, lev_rule, password)
            if hr is not None:
                hashcat_rules.append(hr)

        result = []
        for hr in sorted(hashcat_rules, key=len):
            rl = len(hr)
            if not self.more_rules:
                if rl < best_found_rule_length:
                    best_found_rule_length = rl
                elif rl > best_found_rule_length:
                    break
            if rl <= self.max_rule_len:
                result.append(hr)
        return result

    def generate_simple_hashcat_rules(self, word, rules, password):
        hashcat_rules = []
        word_rules = word

        for (op, p, w) in rules:
            if op == 'insert':
                hashcat_rules.append("i%s%s" % (self.int_to_hashcat(p), password[p]))
                word_rules = self.hashcat_rule['i'](word_rules, p, password[p])
            elif op == 'delete':
                hashcat_rules.append("D%s" % self.int_to_hashcat(p))
                word_rules = self.hashcat_rule['D'](word_rules, p)
            elif op == 'replace':
                hashcat_rules.append("o%s%s" % (self.int_to_hashcat(p), password[p]))
                word_rules = self.hashcat_rule['o'](word_rules, p, password[p])

        return hashcat_rules if word_rules == password else None

    def generate_advanced_hashcat_rules(self, word, rules, password):
        hashcat_rules = []
        word_rules = word
        password_lower = sum(1 for c in password if c.islower())
        password_upper = sum(1 for c in password if c.isupper())

        for i, (op, p, w) in enumerate(rules):
            if op == 'insert':
                hashcat_rules.append("i%s%s" % (self.int_to_hashcat(p), password[p]))
                word_rules = self.hashcat_rule['i'](word_rules, p, password[p])
            elif op == 'delete':
                hashcat_rules.append("D%s" % self.int_to_hashcat(p))
                word_rules = self.hashcat_rule['D'](word_rules, p)
            elif op == 'replace':
                if word_rules[p] == password[p]:
                    pass  # obsolete
                elif (p < len(password) - 1 and p < len(word_rules) - 1
                      and word_rules[p] == password[p + 1]
                      and word_rules[p + 1] == password[p]):
                    if p == 0 and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['k'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("k")
                        word_rules = self.hashcat_rule['k'](word_rules)
                    elif p == len(word_rules) - 2 and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['K'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("K")
                        word_rules = self.hashcat_rule['K'](word_rules)
                    elif self.generate_simple_hashcat_rules(
                            self.hashcat_rule['*'](word_rules, p, p + 1), rules[i + 1:], password):
                        hashcat_rules.append("*%s%s" % (self.int_to_hashcat(p), self.int_to_hashcat(p + 1)))
                        word_rules = self.hashcat_rule['*'](word_rules, p, p + 1)
                    else:
                        hashcat_rules.append("o%s%s" % (self.int_to_hashcat(p), password[p]))
                        word_rules = self.hashcat_rule['o'](word_rules, p, password[p])
                elif word_rules[p].islower() and word_rules[p].upper() == password[p]:
                    if password_upper and password_lower and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['t'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("t")
                        word_rules = self.hashcat_rule['t'](word_rules)
                    elif self.generate_simple_hashcat_rules(
                            self.hashcat_rule['u'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("u")
                        word_rules = self.hashcat_rule['u'](word_rules)
                    elif p == 0 and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['c'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("c")
                        word_rules = self.hashcat_rule['c'](word_rules)
                    else:
                        hashcat_rules.append("T%s" % self.int_to_hashcat(p))
                        word_rules = self.hashcat_rule['T'](word_rules, p)
                elif word_rules[p].isupper() and word_rules[p].lower() == password[p]:
                    if password_upper and password_lower and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['t'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("t")
                        word_rules = self.hashcat_rule['t'](word_rules)
                    elif self.generate_simple_hashcat_rules(
                            self.hashcat_rule['l'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("l")
                        word_rules = self.hashcat_rule['l'](word_rules)
                    elif p == 0 and self.generate_simple_hashcat_rules(
                            self.hashcat_rule['C'](word_rules), rules[i + 1:], password):
                        hashcat_rules.append("C")
                        word_rules = self.hashcat_rule['C'](word_rules)
                    else:
                        hashcat_rules.append("T%s" % self.int_to_hashcat(p))
                        word_rules = self.hashcat_rule['T'](word_rules, p)
                elif (word_rules[p].isalpha() and not password[p].isalpha()
                      and self.generate_simple_hashcat_rules(
                          self.hashcat_rule['s'](word_rules, word_rules[p], password[p]),
                          rules[i + 1:], password)):
                    hashcat_rules.append("s%s%s" % (word_rules[p], password[p]))
                    word_rules = self.hashcat_rule['s'](word_rules, word_rules[p], password[p])
                elif (p < len(password) - 1 and p < len(word_rules) - 1
                      and password[p] == password[p + 1] and password[p] == word_rules[p + 1]):
                    hashcat_rules.append(".%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule['.'](word_rules, p)
                elif p > 0 and w > 0 and password[p] == password[p - 1] and password[p] == word_rules[p - 1]:
                    hashcat_rules.append(",%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule[','](word_rules, p)
                elif ord(word_rules[p]) + 1 == ord(password[p]):
                    hashcat_rules.append("+%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule['+'](word_rules, p)
                elif ord(word_rules[p]) - 1 == ord(password[p]):
                    hashcat_rules.append("-%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule['-'](word_rules, p)
                elif ord(word_rules[p]) << 1 == ord(password[p]):
                    hashcat_rules.append("L%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule['L'](word_rules, p)
                elif ord(word_rules[p]) >> 1 == ord(password[p]):
                    hashcat_rules.append("R%s" % self.int_to_hashcat(p))
                    word_rules = self.hashcat_rule['R'](word_rules, p)
                else:
                    hashcat_rules.append("o%s%s" % (self.int_to_hashcat(p), password[p]))
                    word_rules = self.hashcat_rule['o'](word_rules, p, password[p])

        # Optimize: prefix rules
        last_prefix = 0
        prefix_rules = []
        for hr in hashcat_rules:
            if hr[0] == "i" and self.hashcat_to_int(hr[1]) == last_prefix:
                prefix_rules.append("^%s" % hr[2])
                last_prefix += 1
            elif prefix_rules:
                hashcat_rules = prefix_rules[::-1] + hashcat_rules[len(prefix_rules):]
                break
            else:
                break
        else:
            if prefix_rules:
                hashcat_rules = prefix_rules[::-1] + hashcat_rules[len(prefix_rules):]

        # Optimize: appendix rules
        last_appendix = len(password) - 1
        appendix_rules = []
        for hr in reversed(hashcat_rules):
            if hr[0] == "i" and self.hashcat_to_int(hr[1]) == last_appendix:
                appendix_rules.append("$%s" % hr[2])
                last_appendix -= 1
            elif appendix_rules:
                hashcat_rules = hashcat_rules[:-len(appendix_rules)] + appendix_rules[::-1]
                break
            else:
                break
        else:
            if appendix_rules:
                hashcat_rules = hashcat_rules[:-len(appendix_rules)] + appendix_rules[::-1]

        # Optimize: truncate left
        last_precut = 0
        precut_rules = []
        for hr in hashcat_rules:
            if hr[0] == "D" and self.hashcat_to_int(hr[1]) == last_precut:
                precut_rules.append("[")
            elif precut_rules:
                hashcat_rules = precut_rules[::-1] + hashcat_rules[len(precut_rules):]
                break
            else:
                break
        else:
            if precut_rules:
                hashcat_rules = precut_rules[::-1] + hashcat_rules[len(precut_rules):]

        # Optimize: truncate right
        last_postcut = len(password)
        postcut_rules = []
        for hr in reversed(hashcat_rules):
            if hr[0] == "D" and self.hashcat_to_int(hr[1]) >= last_postcut:
                postcut_rules.append("]")
            elif postcut_rules:
                hashcat_rules = hashcat_rules[:-len(postcut_rules)] + postcut_rules[::-1]
                break
            else:
                break
        else:
            if postcut_rules:
                hashcat_rules = hashcat_rules[:-len(postcut_rules)] + postcut_rules[::-1]

        return hashcat_rules if word_rules == password else None

    # ── Password analysis ────────────────────────────────────────
    def check_reversible_password(self, password):
        if password.isdigit():
            self.numeric_stats_total += 1
            return False
        elif sum(1 for c in password if c.isalpha()) < len(password) // 4:
            self.special_stats_total += 1
            return False
        elif any(ord(c) < 32 or ord(c) > 126 for c in password):
            self.foreign_stats_total += 1
            return False
        return True

    def analyze_password(self, password, rules_queue=None, words_queue=None):
        if rules_queue is None:
            rules_queue = multiprocessing.Queue()
        if words_queue is None:
            words_queue = multiprocessing.Queue()

        words = []

        if self.enchant_dict and self.enchant_dict.check(password) and not self.word:
            words.append({
                "password": password,
                "suggestion": password,
                "hashcat_rules": [[]],
                "pre_rule": [],
                "best_rule_length": 9999,
            })
        else:
            words = self.generate_words(password)
            for word in words:
                word["hashcat_rules"] = self.generate_hashcat_rules(
                    word["suggestion"], word["password"]
                )

        self.print_hashcat_rules(words, password, rules_queue, words_queue)

    def print_hashcat_rules(self, words, password, rules_queue, words_queue):
        best_found_rule_length = 9999

        for word in sorted(words, key=lambda w: len(w.get("hashcat_rules", [[]])[-1]) if w.get("hashcat_rules") else 9999):
            words_queue.put(word["suggestion"])

            for hashcat_rule in word.get("hashcat_rules", []):
                rule_length = len(hashcat_rule)
                if not self.more_rules:
                    if rule_length < best_found_rule_length:
                        best_found_rule_length = rule_length
                    elif rule_length > best_found_rule_length:
                        break
                if rule_length <= self.max_rule_len:
                    rule_str = " ".join(hashcat_rule + word.get("pre_rule", []) or [':'])
                    if self.verbose:
                        print("[+] %s => %s => %s" % (word["suggestion"], rule_str, password))
                    rules_queue.put(rule_str)

    def password_worker(self, i, passwords_queue, rules_queue, words_queue):
        try:
            while True:
                password = passwords_queue.get()
                if password is None:
                    break
                self.analyze_password(password, rules_queue, words_queue)
        except (KeyboardInterrupt, SystemExit):
            pass

    def rule_worker(self, rules_queue, output_rules_filename):
        print("[*] Saving rules to %s" % output_rules_filename)
        with open(output_rules_filename, 'w') as f:
            try:
                while True:
                    rule = rules_queue.get()
                    if rule is None:
                        break
                    f.write("%s\n" % rule)
                    f.flush()
            except (KeyboardInterrupt, SystemExit):
                pass

    def word_worker(self, words_queue, output_words_filename):
        print("[*] Saving words to %s" % output_words_filename)
        with open(output_words_filename, 'w') as f:
            try:
                while True:
                    word = words_queue.get()
                    if word is None:
                        break
                    f.write("%s\n" % word)
                    f.flush()
            except (KeyboardInterrupt, SystemExit):
                pass

    def analyze_passwords_file(self, passwords_file):
        print("[*] Analyzing passwords file: %s" % passwords_file)
        print("[*] Press Ctrl-C to end execution and generate statistical analysis.")

        passwords_queue = multiprocessing.Queue(self.threads)
        rules_queue = multiprocessing.Queue()
        words_queue = multiprocessing.Queue()

        workers = []
        for i in range(self.threads):
            p = multiprocessing.Process(
                target=self.password_worker,
                args=(i, passwords_queue, rules_queue, words_queue),
            )
            p.start()
            workers.append(p)

        rule_proc = multiprocessing.Process(
            target=self.rule_worker,
            args=(rules_queue, "%s.rule" % self.basename),
        )
        rule_proc.start()

        word_proc = multiprocessing.Process(
            target=self.word_worker,
            args=(words_queue, "%s.word" % self.basename),
        )
        word_proc.start()

        password_count = 0
        analysis_start = time.time()
        segment_start = analysis_start

        try:
            with open(passwords_file, 'r', encoding='latin-1', errors='replace') as f:
                for password in f:
                    password = password.rstrip('\r\n')
                    if len(password) > 0:
                        if not self.quiet and password_count != 0 and password_count % 5000 == 0:
                            segment_time = time.time() - segment_start
                            rate = 5000 / segment_time if segment_time > 0 else 0
                            print(
                                "[*] Processed %d passwords in %.2f seconds at %.2f p/sec"
                                % (password_count, time.time() - analysis_start, rate)
                            )
                            segment_start = time.time()

                        password_count += 1
                        if self.check_reversible_password(password):
                            passwords_queue.put(password)

        except (KeyboardInterrupt, SystemExit):
            print("\n[!] Rulegen was interrupted.")
        else:
            for _ in range(self.threads):
                passwords_queue.put(None)
            while not passwords_queue.empty():
                time.sleep(1)
            rules_queue.put(None)
            words_queue.put(None)

        analysis_time = time.time() - analysis_start
        rate = password_count / analysis_time if analysis_time > 0 else 0
        print(
            "[*] Finished processing %d passwords in %.2f seconds at %.2f p/sec"
            % (password_count, analysis_time, rate)
        )

        if password_count > 0:
            print("[*] Generating statistics for [%s] rules and words." % self.basename)
            print(
                "[-] Skipped %d all numeric passwords (%.2f%%)"
                % (self.numeric_stats_total, self.numeric_stats_total * 100.0 / password_count)
            )
            print(
                "[-] Skipped %d passwords with <25%% alpha (%.2f%%)"
                % (self.special_stats_total, self.special_stats_total * 100.0 / password_count)
            )
            print(
                "[-] Skipped %d non-ASCII passwords (%.2f%%)"
                % (self.foreign_stats_total, self.foreign_stats_total * 100.0 / password_count)
            )

        # Generate sorted output files
        try:
            with open("%s.rule" % self.basename, 'r') as rf:
                rules_counter = Counter(rf)
            with open("%s-sorted.rule" % self.basename, 'w') as rsf:
                rule_total = sum(rules_counter.values())
                print("\n[*] Top 10 rules")
                for idx, (rule, count) in enumerate(rules_counter.most_common()):
                    rsf.write(rule)
                    if idx < 10 and rule_total > 0:
                        print("[+] %s - %d (%.2f%%)" % (rule.rstrip('\r\n'), count, count * 100 / rule_total))
        except FileNotFoundError:
            pass

        try:
            with open("%s.word" % self.basename, 'r') as wf:
                words_counter = Counter(wf)
            with open("%s-sorted.word" % self.basename, 'w') as wsf:
                word_total = sum(words_counter.values())
                print("\n[*] Top 10 words")
                for idx, (word, count) in enumerate(words_counter.most_common()):
                    wsf.write(word)
                    if idx < 10 and word_total > 0:
                        print("[+] %s - %d (%.2f%%)" % (word.rstrip('\r\n'), count, count * 100 / word_total))
        except FileNotFoundError:
            pass


if __name__ == "__main__":
    parser = ArgumentParser(description="RuleGen %s — Password Rule Generator" % VERSION)
    parser.add_argument("passwords", help="Passwords file or single password (with --password)")
    parser.add_argument("-b", "--basename", default="analysis", help="Output base name")
    parser.add_argument("-w", "--wordlist", help="Custom wordlist for rule analysis")
    parser.add_argument("-q", "--quiet", action="store_true", default=False)
    parser.add_argument("--threads", type=int, default=multiprocessing.cpu_count())

    wt = parser.add_argument_group("Word generation")
    wt.add_argument("--maxworddist", type=int, default=10)
    wt.add_argument("--maxwords", type=int, default=5)
    wt.add_argument("--morewords", action="store_true", default=False)
    wt.add_argument("--simplewords", action="store_true", default=False)

    rt = parser.add_argument_group("Rule generation")
    rt.add_argument("--maxrulelen", type=int, default=10)
    rt.add_argument("--maxrules", type=int, default=5)
    rt.add_argument("--morerules", action="store_true", default=False)
    rt.add_argument("--simplerules", action="store_true", default=False)
    rt.add_argument("--bruterules", action="store_true", default=False)

    sp = parser.add_argument_group("Spell checker")
    sp.add_argument("--providers", default="aspell,myspell")
    sp.add_argument("--language", default="en", help="Enchant dictionary language code")

    db = parser.add_argument_group("Debug")
    db.add_argument("-v", "--verbose", action="store_true", default=False)
    db.add_argument("-d", "--debug", action="store_true", default=False)
    db.add_argument("--password", action="store_true", default=False, help="Treat arg as password")
    db.add_argument("--word", help="Custom word for analysis")

    args = parser.parse_args()
    if not args.quiet:
        print("RuleGen %s" % VERSION)

    rulegen = RuleGen(
        language=args.language,
        providers=args.providers,
        basename=args.basename,
        threads=args.threads,
        wordlist=args.wordlist,
    )
    rulegen.max_word_dist = args.maxworddist
    rulegen.max_words = args.maxwords
    rulegen.more_words = args.morewords
    rulegen.simple_words = args.simplewords
    rulegen.max_rule_len = args.maxrulelen
    rulegen.max_rules = args.maxrules
    rulegen.more_rules = args.morerules
    rulegen.simple_rules = args.simplerules
    rulegen.brute_rules = args.bruterules
    rulegen.word = args.word
    rulegen.verbose = args.verbose
    rulegen.debug = args.debug
    rulegen.quiet = args.quiet

    if not args.word and not args.wordlist and HAS_ENCHANT and rulegen.enchant_dict:
        print("[*] Using Enchant '%s' module." % rulegen.enchant_dict.provider.name)

    if args.password:
        rulegen.analyze_password(args.passwords)
    else:
        rulegen.analyze_passwords_file(args.passwords)
