#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   messages.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   19.07.2019
# =============================================================================
"""Message parsing."""

import re
import logging
from pathlib import Path
import yaml

import importlib_resources as resources
from fuzzywuzzy import fuzz, process
import datefinder


class ParseError(Exception):
    """Parsing error."""


class MessageParser:
    """Message parser."""

    def __init__(self, categories, matcher_classes):
        self.set_categories(categories)
        self._category_matchers = [matcher_class(self.categories)
                                   for matcher_class in matcher_classes]

    def set_categories(self, categories):
        """Set internal category list."""
        self.categories = {cat.lower(): cat for cat in categories}

    def get_category(self, concept, category):
        matched_cat = None
        for matcher in self._category_matchers:
            matched_cat = matcher.match(concept, category)
            if matched_cat:
                logging.debug("Matched category by %s -> %s", matcher, matched_cat)
                break
        return self.categories.get(matched_cat, None)

    def parse(self, message):
        """Parse the message.

        Return:
            tuple: Concept, value, currency, category.

        """
        raise NotImplementedError


class RegexParser(MessageParser):
    """Parser based on regexes."""

    CURRENCY_REGEX = re.compile(r'(-?\d+(?:[.,]\d{1,2})?)\s?(CHF|EUR)?', re.IGNORECASE)

    def parse(self, message):
        match = self.CURRENCY_REGEX.search(message)
        if not match:
            raise ParseError("Cannot find expense value/currency")
        value, currency = match.groups()
        concept = message[:match.start()].strip()
        cat = message[match.end():].strip()
        # First let's check dates
        found_dates = list(datefinder.find_dates(concept + cat, source=True))
        if len(found_dates) > 1:
            logging.error("Found too many dates in text, setting as None -> %s", found_dates)
            date = None
        elif len(found_dates) == 1:
            date, source_date = found_dates[0]
            cat = cat.replace(source_date, '')
            concept = concept.replace(source_date, '')
            logging.debug("Found date -> %s", date)
        else:
            date = None
        # Now match categories
        logging.debug("Found category -> %s", cat)
        category = self.get_category(concept, cat)
        return concept, value, currency, category, date


class FuzzyMatcherMixin:
    """Add fuzzy category matching."""

    def __init__(self, categories):
        self.categories = categories

    def match(self, _, category):
        if not category:
            return None
        matched_cat, score = process.extractOne(category.lower(), list(self.categories.keys()), scorer=fuzz.partial_ratio)
        logging.debug("Fuzzywuzzy match -> %s with score %s", matched_cat, score)
        if score < 75:
            matched_cat = None
            logging.debug("Cannot determine category -> %s was matched to %s with score %s",
                          category, matched_cat, score)
        return matched_cat


class RepetitionMatcherMixin:
    """Add category matching through repetition."""

    THRESHOLD_APPEARENCES = 10

    def __init__(self, categories):
        pass


class FixedMatcherMixin:
    """Add fixed category mixin."""

    INPUT_CATEGORIES = resources.files("expensebot") / "data" / "fixed_cats.yaml"

    def __init__(self, categories):
        with open(self.INPUT_CATEGORIES, 'rt', encoding='utf8') as input_file:
            self.fixed_categories = yaml.safe_load(input_file)
        self.categories = categories

    def match(self, concept, _):
        return self.fixed_categories.get(concept.lower(), None)


class ExpenseParser(RegexParser):
    """Full expense parser."""

    def __init__(self, categories):
        super().__init__(categories, [FuzzyMatcherMixin, FixedMatcherMixin])

# EOF
