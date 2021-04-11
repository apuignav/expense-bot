#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# @file   config.py
# @author Albert Puig (albert.puig@cern.ch)
# @date   16.07.2019
# =============================================================================
"""Config management."""

import yaml


CONFIG_FILE = "config.yaml"


def load_config(config_file=CONFIG_FILE):
    """Load configuration."""
    with open(config_file, "r") as config_stream:
        config = yaml.safe_load(config_stream)
    return config


# EOF
