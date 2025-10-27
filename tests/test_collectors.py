"""Tests for all band data collectors."""
import pytest
from datetime import date

# Import all collectors
from jambandnerd.data_collection.goose.collector import GooseCollector
from jambandnerd.data_collection.phish.collector import PhishCollector
from jambandnerd.data_collection.wsp.collector import WSPCollector
from jambandnerd.data_collection.billy.collector import BillyCollector
from jambandnerd.data_collection.um.collector import UmCollector

# Mock data will be loaded here
