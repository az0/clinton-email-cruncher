#!/usr/bin/env python

"""
This script cleans up text in the JSON.

A major sources of errors is OCR, and classification metadata is a major source of junk,

The errors are extensive, and this script is far from perfect both in function and design.
"""

import re
import unittest
import os
import json
import sys
import re

from tqdm import tqdm
from fuzzywuzzy import fuzz

correct_addresses = [
    "Mills, Cheryl D <MillsCD@state.gov>",
    "Cheryl Mills",
    "Huma Abedin",
    "Abedin, Huma <AbedinH@state.gov>",
    "'huma@clintonemail.com' <huma@clintonemail.com>",
    "Huma Abedin <huma@clintonemail.com>",
    "H <HDR22@clintonemail.com>",
    "H <hrod17@clintonemail.com>",
    "Sullivan, Jacob J <SullivanJJ@state.gov>",
    "Jake Sullivan",
    "Hanley, Monica R <HanleyMR@state.gov>",
    "Jiloty, Lauren C <JilotyLC@state.gov>",
    "Verma, Richard R <VermaRR@state.gov>",
    "McHale, Judith A <McHaleJA@state.gov>",
    "sbwhoeop"  # Sidney Blumenthal
]

# For every email address like "Jiloty, Lauren C <JilotyLC@state.gov>"
# create another variation like "Jiloty, Lauren C [mailto:JilotyLC@state.gov]".
# Also, add one without the email address like "Jiloty, Lauren C".
#
correct_list_addition = []
for correct in correct_addresses:
    if correct.endswith('>'):
        # use the mailto: varaint
        correct_list_addition.append(
            correct.replace('<', '[mailto:').replace('>', ']'))
        # remove " <foo@example.com>" from end of string
        without_email_address = correct.split('<')[0].strip()
        correct_list_addition.append(without_email_address)

correct_addresses = sorted(correct_addresses+correct_list_addition)


def find_closest_match(entry: str, correct_spelling: list) -> str:
    """Find the closest match in the correct_spelling list"""
    best_match = max(correct_spelling, key=lambda x: fuzz.ratio(x, entry))
    score = fuzz.ratio(best_match, entry)
    # Return best match if similarity is high enough
    return best_match if score > 75 else None


def clean_email_envelope(text: str) -> str:
    """
    Given any single line of text, this cleans up email addresess in the envelope (i.e., from, to, cc, bcc)

    If not an envelope, return the same line.
    If an envelope, return cleaned-up version.

    This allows for OCR errors such as
        "HDR22" -> "HOR22"
        "CC: " -> "Ce: "
        "From: " -> "- From: "
    """
    assert not '\n' in text
    # Fix OCR error like 'rom: Robert Einhorn [mailto:'
    if re.match(r'(?i)^rom: .*(mailto|@(state|clint))', text):
        text = 'F' + text
    # Check if this is an envelope line.
    envelope_re = re.compile(r"(?i)[^a-zA-Z0-9]*(From|To|Cc|Ce|Bcc)[:;] ")
    if re.match(envelope_re, text):
        line_type = re.match(envelope_re, text).group(
            1)  # From, To, Cc, Ce, Bcc
        if line_type.lower() in ('cc', 'ce'):
            line_type = 'CC'  # Fix OCR.
        from_to_length = len(re.match(envelope_re, text).group(1))
        just_addresses = text[from_to_length+2:]
        addresses = []
        for address in just_addresses.split(';'):
            closest_address = find_closest_match(address, correct_addresses)
            if closest_address:
                address = closest_address
            else:
                pass
                # FIXME: Remove space by changing "[mailto:RussoRV @state.gov ]" to "[mailto:RussoRV@state.gov]" but only within mailto
            if address == 'sbwhoeop':
                address = 'Sidney Blumenthal <sbwhoeop>'
            if address in ('H', 'H oe'):
                address = 'Hillary Clinton'
            addresses.append(address.strip())
        return line_type + ': '+'; '.join(addresses)
    return text


def clean_original_message(text: str) -> str:
    """Standardizes variations of "---- Original Message ----"

    text: one string delimited by newlines
    return: one string with newlines and variations replaced
    """
    lines = []
    orig_msg = (r'---- Original Message ----',
                r'---------- Forwarded message ----------', '----- Message transféré ----')
    fwd_std = '---- Forwarded Message ----'
    line_like = r'[\-—_=~“”\'+\s]'  # "Like a line": OCR errors for hyphen
    for line in text.split('\n'):
        matched = find_closest_match(line, orig_msg)
        if matched:
            if 'Forward' in matched:
                lines.append(fwd_std)
                continue
            lines.append(matched)
            continue
        if re.match(r'(?i)^'+line_like+r'{3,5}\s*original\s*message\s*'+line_like+r'{3,5}$', line):
            lines.append('---- Original Message ----')
            continue
        if re.match(r'(?i)^[\-_=~“”srceno+]{1,10}\s*forwarded\s*message\s*'+line_like+r'{1,10}$', line):
            lines.append(fwd_std)
            continue
        lines.append(line)
    return '\n'.join(lines)


def remove_unclassified(text: str) -> str:
    """
    Removes variations of "unclassified"

    Text is one string delimited by newlines.

    This function removes variations as follows (short list) from the text:

(06134372 UNCLASSIFIED U.S. Department of State Case No. F-2016-07895 Doc No. 006134372 Date: 06/02/2017
C06130929 — UNCLASSIFIED U.S. Department of State Case No. F-2016-07895 Doc No. C06130929 Date: 05/31/2017
____UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05760075 Date: 06/30/2
UNCLASSIFIED STATE DEPT. - PRODUCED TO HOUSE SELECT BENGHAZI COMM.
    """
    unclassified_re1 = re.compile(
        r'([\(C]\d{8}[\s—]*)?(_+\s*)?(?:(?:UNCLASSIFIED|UNCLASSIFIED\s+U\.S\.)\s+U\.S\.\s+(?:Department|Deparmertf)\s+of\s+(State|Slate)\s+Case\s+No\.\s+F\-\d{4}\-\d{5}\s+Doc\s+No\.\s+C?\d{8}\s+Date\:\s+\d{2}\/\d{2}\/\d{4})(\s*_+)?',
        re.MULTILINE)
    text = re.sub(unclassified_re1, '', text, re.MULTILINE)
    unclassified_re2 = re.compile(
        r'(?:UNCLASSIFIED\s+U\.S\.\s+Department\s+of\s+(?:State|Slate)\s+Case\s+No\.\s+F\-\d{4}\-\d{5}\s+Doc\s+No\.\s+C?\d{8}\s+Date\:\s+\d{2}\/\d{2}\/\d{4})|(?:\(\d{8}\s+UNCLASSIFIED\s+U\.S\.\s+Department\s+of\s+State\s+Case\s+No\.\s+F\-\d{4}\-\d{5}\s+Doc\s+No\.\s+\d{8}\s+Date\:\s+\d{2}\/\d{2}\/\d{4}\))',
        re.MULTILINE)
    text = re.sub(unclassified_re2, '', text, re.MULTILINE)

    regex_as_strs = (
        r'UNCLASSIFIED.*(?:Date: \d{2}\/\d{2}\/\d{4}|Department.*Doc No)',
        r'Case No.? \w-\d{4}-\d{5}',  # Case No. F-2015-04841
        r'Date: \d{2}.*STATE-[\w\d]+',
        # Doc No. C05739665 STATE DEPT. - PRODUCED TO HOUSE SELECT BENGHAZI COMM.
        r'Doc No. C[\w]+.*COMM',
        r'Doc No.* C[\w]{5,10}',  # Doc No. C05739665 .
        r'UNCLASSIFIED STATE.*BENG.{2,6} COMM.?',
        # U.S. Department of State SUBJECT TO AGREEMENT ON SENSITIVE INFORMATION & REDACTIONS. NO FOIA WAIVER
        r'U.S. Depart.+FOIA WAIVER',
        r'UNCLASSIFIED',  # UNCLASSIFIED
        r'U.S. Department of State',  # U.S. Department of State
        r'SENSITIVE BUT UNCLASSIFIED',  # SENSITIVE BUT UNCLASSIFIED
        # ~ Reason: 1.4(D) ~ Declassify on: 08/14/2024
        r'Reason: \d.+Declassify.*\d{4}',
        r'This email is UNCLASSIFIED.',  # This email is UNCLASSIFIED.
        # UNCLASSIFIED US Deparmertf Slate Case No, F-20078 Duc No, COBYEE210 Date: 0430208
        r'UNCLASSIFIED.+Depar.+Date: \d+'
    )
    unclassified_regexes = []
    for regex_str in regex_as_strs:
        # OCR errors sometimes leave random puntucation, so remove non-alpanumeric from beginning and end like ".; CLASSIFIED |".
        unclassified_regexes.append(re.compile(
            r'^[^a-zA-Z0-9]*'+regex_str+r'[^a-zA-Z0-9]*$', re.MULTILINE))

    for regex in unclassified_regexes:
        text = re.sub(regex, '', text, re.MULTILINE)

    return text


def remove_release_in(text: str) -> str:
    """
    Removes variations of "release in part" or "full" which may be one to three lines.

    Small list of variations
    RELEASE IN FULL
    RELEASE IN\n\nFULL
    RELEASE IN\nPART B6

    This does not catch codes like B5 and B6 when appended to another line like "From:".
    """
    release_in_part_re = re.compile(
        r'[^a-zA-Z0-9\n]*(Date:\s*\d{2}\/\d{2}\/\d{4}\s*)?(RELEASE|pecease)[\s\n]{1,2}IN[\n\s\|]{1,3}(FULL|PART?([\s\n|]{1,3}B[\deSBD,\.()]+)?)[^a-zA-Z0-9\n]*',
        re.MULTILINE)
    text = re.sub(release_in_part_re, '', text)
    # These all match a line that is one word exactly.
    # 1. A rule (i.e., line) is OCR'd many ways including SS and SSeS.
    # 2. Classification codes B5,B6 and OCR variations (e.g., B6 -> BG)
    text = re.sub(r'([\^\n])(B[56GS]|SS|SSeS|Es)([\^\n])',
                  r'\1\3', text, re.MULTILINE)
    if text == '|':
        text = ''
    return text


def process_json(fn: str) -> None:
    """Process one JSON file"""
    with open('json/'+fn, encoding='utf-8') as f:
        ret = json.load(f)
        text = ret['text']
        text = remove_unclassified(text)
        text = '\n'.join([clean_email_envelope(x) for x in text.split('\n')])
        text = remove_release_in(text)
        text = clean_original_message(text)
        # remove consecutive \n
        text = re.sub(r'[\n]{3,}', '\n\n', text)
        ret['clean_text'] = text
        with open('json/'+fn, 'w', encoding='utf-8') as f:
            # Save the changes.
            json.dump(ret, f)


def main() -> None:
    """Loop through JSON files"""
    import random
    filenames = os.listdir('json')
    random.shuffle(filenames)
    for fn in tqdm(filenames):
        process_json(fn)


class TestCleanText(unittest.TestCase):

    def test_clean_email_envelope(self):
        """
        Test for clean_email_envelope()

        """

        equal_tests = (
            ('From: Chery! Mills', 'From: Cheryl Mills'),
            ('From: Mills, Chery! D [MillsCcD@state.gov]',
             "From: Mills, Cheryl D <MillsCD@state.gov>"),
            ('rom: Robert Einhorn [mailto:', "From: Robert Einhorn [mailto:"),
            ('From: H [mailto:HDR22@clintonemail.com]',
             'From: H [mailto:HDR22@clintonemail.com]'),
        )
        for equal_test in equal_tests:
            self.assertEqual(clean_email_envelope(
                equal_test[0]), equal_test[1])

        tests = """From: C - Cheryl Mills
From: C — Chery] Mills
From: : cherylmillg | B6
From: Cheryl Mills [mailto: B6
From: Cheryl Mills milsed@state.gov
From: Cheryl Mills < | on behalf of Cheryl Mills
From: "Chery! Mills"
From: Chery! Mills B6
From: Chery! Mills [maitto: _ J
To: Chery! Millst
To: Mills, Chery! D
From: Mills, Chery! D [mailto:MillsCcD@state.gov]
From: Mills, Chery! D' <MilsCD@state.gov>
From: Mills, Cheryl D <!
From: Mills, Cheryl D [mailto:
From: Mills, Cheryl D [mailto:IvillsCD @state.gov}
From: Mills, Cheryl D [mailto: MillsCcD@state.gov]
From: Mills, Cheryl D [mailto:MillsCD@state.gov) _
From: Mills, Cheryl D <MiisCD@state.gov>
From: "Mills, Cheryl D" <MillsCD@state.gov>
From: "Mills, Cheryl D" [MillsCD @state.gov]
From: . Mills, Cheryl D <MillsCD@state.gov>
From: : Mills, Cheryl D <MillsCD@state.gov>
From: Mills, Cheryl D <MillsCD@state.gov> |
From: Mils, Cheryl D [mailto:MilscD@state.gov)
From: Mills, Cheryl D [mailto:MillsCcD@state.gov]
From: Mills, Cheryl D <Mills;CD@state.gov>
From: Mills, Cheryl D [mailto:MillscD@state.gov]
From: Mills, Cheryl D <MillsCD @state.gov>
From: Mills, Chery! D [mailto:MillsCD@state.gov]
From: Mills, Cheryl D [mailto:MillsCD @state.gov]
From: Mills, Chery! D
From: Mills, Chery! D <MillsCD@state.gov>
From: Mills, Cheryl D <MillsCcD@state.gov>
From: Mills, Cheryl D [mailto:MillsCD@state.gov]
From: "Abedin, Huma" <AbedinH@state.gov>
From: "Abedin, Huma’ <AbedinH@state.gov>
From: ‘ Abedin, Huma <AbedinH@state.gov>
From: Abedin, Huma <AbedinH@state, gov>
From: Abedin, Huma <AbedinH@state.gov> .
From: Abedin, Huma [mailto:AbedinH @state.gov] ~
From: Abedin, Huma [mailtorAbedinH@stategov]
From: Abedin, Huma [mailtto:AbedinH @state.gov]
From: Huma Abedin ——
From: Huma Abedin abedinh@state.gov ee
From: Huma Abedin < B6
From: Huma Abedin [mailto:Huma@clintonemail.com]
From: Huma Abedin (mailto: Huma@clintonemail.com]
From: Huma Abedin [mailto:Huma@clintonemail.com
Cc: Huma Abedin <Huma@@clintonemail.com >
Ce: ‘huma@clintonemail.com' <huma@clintonemail.com>
From: * Huma Abedin <Huma@clintonemail.com>
From: Huma Abedit
From: Abedin, Huma [mailto:AbedinH @state.gov]
From: Abedin, Huma <AbedinH @state.gov>
From: Huma Abedin <Huma@clintonemail.com>
From: Abedin, Huma [mailto:AbedinH@state.gov]
From: Abedin, Huma <AbedinH@state.gov>
To; Huma Abedin <Huma@clintonemail.com>
From: HDR22@clintonemail.com
From: H <hdr22@clinton
From: H <HDR22@ciintcnemail.com>
From: H <HDR22@clintonemail. com>
From: H <HDR22@clintonemail.com> i
From: H <HDR22@clintonemall.com>
From: H <HOR22@clintonemail.com>
From: H <hrod17@clintonemail.com> .
From: H <hrod17@clintonemail.com> . |
From: H <hrod17@clintonemail.com> |
-From: H <hrod17@clintonemail.com>
From: H <hrod17@ctintonemail.com>
From: H <hrod17@dintonemail.com>
From: H {maifto:HDR22@clintonemail.com}
From: H [mailte:HDR22@clintonemail.com}
From: H [mailto:hdr22@clintonemail.com ]
From: H [mailto: HDR22@clintonemail. com}
From: H [mailto: HDR22@clintonemail.com)
From: H [mailto: HDR22@clintonemail.com] !
From: H [mailto: HDR22@clintonemail.com}
From: H [mailto:HDR22@clintonemail.co m]
From: H {mailto: HDR22@clintonemail.com]
From: H {mailto:HDR22@clintonemall.com)
From: H [mailto:HOR22@clintonemail.com]
From: H [mailto:HOR22@clintonemail.com}
From: H [maitto: HDR22@clintonemail.com]
From: H [maitto:HDR22@clintonemail.com]
From: H [maitto:HDR22@clintonemall.com]
From: H [mallto:HDR22@clintonemail.com]
From: H [mallto: HOR22@clintonemail.com]
From: H<HDR22@clintonemail.com>
From: H <hrod17 @clintonemail.com>
From: H (mailto: HDR22@clintonemail.com]
From: H [mailto:HDR22@clintonemail.com ]
From: H [mailto: HDR22 @clintonemail.com]
From: H [mailto:HDR22 @clintonemail.com)
From: H [mailto:HDR22 @clintonemail.com]
From: H [mailto:HDR22@clintonemail.com}
From: . H <hrod17@clintonemail.com>
From: H <HDR22 @clintonemail.com>
From: H [mailto:HDR22@clintonemail.com)
From: H [mailto: HDR22@clintonemail.com]
From: H [mailto:HDR22@clintonemail.com]
From: H <hrod17@clintonemail.com>
From: Sullivan, Jacob J [mailto:Sullivan]J@state.gov]
From: Sullivan, Jacob ) <Sullivan))@state.gov>
From: Jiloty, Lauren C [mailto:JilotyLC@state.gov}"""
        test_list = tests.split('\n')
        test_list = set(test_list) - \
            set(['From: ' + x for x in correct_addresses])
        unchanged_list = []
        changed_list = []
        for test in test_list:
            ret = clean_email_envelope(test)
            test_str = test.ljust(50)  # Improve readability.
            if test != ret:
                changed_list.append(f'{test_str} -> {ret}')
            else:
                unchanged_list.append(f'UNCHANGED: {test_str}')
        for changed_list_item in changed_list:
            print(changed_list_item)
        # Keep the unchanged items at the end, so that it is easier to spot errors.
        for unchanged_list_item in unchanged_list:
            print(unchanged_list_item)
        self.assertLess(len(unchanged_list), 14)

        tests_unchanged = [
            'To: Person One; Person Two',
            'To: Mills, Cheryl D; Sullivan, Jacob J'
        ]
        tests_unchanged += ['From: ' + x for x in correct_addresses]
        tests_unchanged = list(set(tests_unchanged))
        tests_unchanged.remove('From: H')  # This is expanded to her full name.
        # This is expanded to include his name.
        tests_unchanged.remove('From: sbwhoeop')
        for correct in tests_unchanged:
            self.assertEqual(clean_email_envelope(correct), correct)

    def test_remove_release_in(self):
        """Test for remove_release_in()"""
        do_not_change_list = (
            'release in full',
            'FOR IMMEDIATE RELEASE',
            'This\nhas\nmultiple lines.'
        )
        for do_not_change in do_not_change_list:
            self.assertEqual(remove_release_in(do_not_change), do_not_change)
        # Verify it is case sensitive: it should not match other cases.
        self.assertEqual(remove_release_in(
            'release in full'), 'release in full')
        tests = (
            'RELEASE IN PART',
            'RELEASE IN PART\nB6',
            'RELEASE IN PART\nBe'
            'RELEASE IN PART B6',
            'RELEASE IN PART B6)',
            'RELEASE IN PART B6|',
            'RELEASE IN PART\n\nB6',
            'RELEASE IN PART |\nBS',
            'RELEASE IN PAR\n\nB5',
            'RELEASE IN\nFULL',
            'RELEASE IN \nFULL',
            'RELEASE IN\n\nFULL',
            'RELEASE IN\nPART B5,B6',
            'RELEASE IN PART B5,B6',
            'RELEASE IN PART\nB5,B6',
            'RELEASE IN FULL,',
            'RELEASE IN FULL!',
            'RELEASE IN FULL}',
            '(RELEASE IN FULL',
            'RELEASE IN PART\nB1,1.4(B),1.4(D)',
            'Date: 05/13/2015 RELEASE IN |\nFULL',
            'pecease\n\nIN FULL',
            'BS',  # OCR error
            'B5',
            'B6',
            'BG',  # OCR error for 'B6'
            'Es',  # maybe a rule (rule=line; not "release in part")
        )

        error_count = 0
        for test in tests:
            ret = remove_release_in('foo\n'+test+'\nbar')
            self.assertIsInstance(ret, str)
            if not ret == 'foo\n\nbar':
                print(f'{test.replace('\n', '\\n')
                         } -> "{ret.replace('\n', '\\n')}"')
                error_count += 1
        self.assertLess(error_count, 1)

    def test_remove_unclassified(self):
        """Test for remove_unclassified()"""
        # "all" means remove the whole line
        all_tests = (
            "UNCLASSIFIED U.S. Department of State Case No. F-2016-07895 Doc No. C06134372 Date: 06/02/2017",
            "UNCLASSIFIED US Deparmertf Slate Case No, F-20078 Duc No, COBYEE210 Date: 0430208",
            "UNCLASSIFIED U.S. Department of Slate Case No. F-2016-07895 Doc No, CO6131108 Date: 10/20/2016",
            "UNCLASSIFIED U.S. Department of State Case No. 22014-20439 Doc No. C05763231 Date: 07/31/2015",
            "UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No",
            "UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. 05771423 Date: 08/31/2015",
            "UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05758461 Date: 10/30/2015 _",
            "UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05759596 Date: 06/30/2015 __",
            "____UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05760075 Date: 06/30/2015",
            "_ UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05760135 Date: 06/30/2015",
            "_ UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05760157 Date: 06/30/2015",
            "___ UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05760483 Date: 06/30/2015",
            "_UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05766850 Date: 10/30/2015",
            "____UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05767831 Date: 11/30/2015",
            "UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05770432 Date: 08/31/2015",
            "___UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05770469 Date: 08/31/2015",
            "___UNCLASSIFIED U.S. Department of State Case No. F-2014-20439 Doc No. C05771271 Date: 08/31/2015",
            'UNCLASSIFIED STATE DEPT. - PRODUCED TO HOUSE SELECT BENGHAZI COMM.',
            'Case No. F-2015-04845',
            'Doc No. C05739665 .',
            'Doc No. C05739665 STATE DEPT. - PRODUCED TO HOUSE SELECT BENGHAZI COMM.',
            'Date: 05/13/2015. SUBJECT TO AGREEMENT ON SENSITIVE INFORMATION & REDACTIONS. NO FOIA WAIVER. STATE-SCB0045629',
            'U.S. Department of State SUBJECT TO AGREEMENT ON SENSITIVE INFORMATION & REDACTIONS. NO FOIA WAIVER',
            'UNCLASSIFIED',
            'U.S. Department of State',
            '~ Reason: 1.4(D) ~ Declassify on: 08/14/2024',
            'SENSITIVE BUT UNCLASSIFIED',
            'This email is UNCLASSIFIED.',
        )
        num_tests = len(all_tests)
        for this_test in all_tests:
            with self.subTest(input=input):
                actual = remove_unclassified('foo\n'+this_test+'\nbar')
                self.assertIsInstance(actual, str)
                self.assertEqual(actual, 'foo\n\nbar')
        # FIXME: test with line to be partially changed like
        # '_ Original Message —- Classified by DAS, A/GIS, DoS on 07/30/2015 ~ Class: CONFIDENTIAL'

    def test_clean_original_message(self):
        """Test for clean_original_message()"""
        orig_tests = """—_ Original Message -----
----- Original Message ---—
ee Original Message -----
oo Original Message -----
Original Message -----
od Original Message -----
----- Original Message —---
see Original Message -----
—— Original Message -----
----- Original Message —-—
cd Original Message -----
oe Original Message -----
-----Original Message-----
— Original Message -----
----- Originai Message -----
----- Original Messege -----
----- Original Messaae -----
—_ Original Message — '
----- Original Message -----"""
        for test in orig_tests.split('\n'):
            with self.subTest(input=test):
                actual = clean_original_message(test)
                self.assertIsInstance(actual, str)
                self.assertEqual(actual, '---- Original Message ----')
        fwd_tests = """- Forwarded message -
srooseceee Forwarded message -----+----
---------= Forwarded message ----~—-—
---------- Forwarded message ----------"""
        for test in fwd_tests.split('\n'):
            with self.subTest(input=test):
                actual = clean_original_message(test)
                self.assertIsInstance(actual, str)
                self.assertEqual(actual, '---- Forwarded Message ----')

        # Test multiline.
        ret = clean_original_message("foo\n_____ Original Message -----\nbar")
        self.assertEqual(ret, "foo\n---- Original Message ----\nbar")
        ret = clean_original_message("foo\n- Original Message -----\nbar")
        self.assertEqual(ret, "foo\n---- Original Message ----\nbar")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--test', action='store_true')
    args = parser.parse_args()
    if args.test:
        sys.argv = [x for x in sys.argv if x != '--test']
        unittest.main()
    else:
        main()
