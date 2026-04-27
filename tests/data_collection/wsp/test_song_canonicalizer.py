from src.jambandnerd.data_collection.wsp.song_canonicalizer import (
    build_canonical_lookup,
    canonicalize_song_name,
)


class TestCanonicalizeSongName:
    def test_canonical_period_variants_c_brown(self):
        assert canonicalize_song_name("C Brown") == "C. Brown"
        assert canonicalize_song_name("C.Brown") == "C. Brown"
        assert canonicalize_song_name("C. Brown") == "C. Brown"

    def test_canonical_period_variants_mr_soul(self):
        assert canonicalize_song_name("Mr Soul") == "Mr. Soul"
        assert canonicalize_song_name("Mr. Soul") == "Mr. Soul"

    def test_canonical_period_variants_mr_crowley(self):
        assert canonicalize_song_name("Mr Crowley") == "Mr. Crowley"
        assert canonicalize_song_name("Mr. Crowley") == "Mr. Crowley"

    def test_canonical_aka_walkin(self):
        assert canonicalize_song_name("Walkin'") == "Walkin' (For Your Love)"

    def test_canonical_aka_bowlegged_woman(self):
        assert (
            canonicalize_song_name("Bowlegged Woman Knock Kneed Man")
            == "Bowlegged Woman"
        )

    def test_canonical_aka_coconut_image(self):
        assert canonicalize_song_name("Coconut Image") == "Coconut"

    def test_canonical_aka_older_souls(self):
        assert canonicalize_song_name("Older Souls") == "Holden Oversoul"

    def test_canonical_aka_pilgrim_radio(self):
        assert canonicalize_song_name("Pilgrim Radio") == "Pilgrims"

    def test_canonical_aka_minglewood(self):
        assert canonicalize_song_name("Minglewood Blues") == "New Minglewood Blues"

    def test_canonical_aka_guilded_splinters(self):
        assert (
            canonicalize_song_name("Guilded Splinters") == "I Walk On Guilded Splinters"
        )
        assert (
            canonicalize_song_name("Walk On Guilded Splinters")
            == "I Walk On Guilded Splinters"
        )

    def test_canonical_aka_worry(self):
        assert canonicalize_song_name("Worried") == "Worry"
        assert canonicalize_song_name("Worryin'") == "Worry"

    def test_canonical_aka_sleepy_monkey(self):
        assert canonicalize_song_name("Monkey") == "Sleepy Monkey"
        assert canonicalize_song_name("Monkey Image") == "Sleepy Monkey"
        assert canonicalize_song_name("Sleepy Monkey") == "Sleepy Monkey"
        assert canonicalize_song_name("Brand New Song") == "Brand New Song"

    def test_exact_canonical_name_unchanged(self):
        assert canonicalize_song_name("C. Brown") == "C. Brown"
        assert canonicalize_song_name("Mr. Soul") == "Mr. Soul"
        assert canonicalize_song_name("Pigeons") == "Pigeons"

    def test_empty_string_passthrough(self):
        assert canonicalize_song_name("") == ""

    def test_whitespace_stripped(self):
        assert canonicalize_song_name("  C Brown  ") == "C. Brown"

    def test_case_insensitive(self):
        assert canonicalize_song_name("c brown") == "C. Brown"
        assert canonicalize_song_name("C BROWN") == "C. Brown"
        assert canonicalize_song_name("mr soul") == "Mr. Soul"

    def test_dynamic_lookup_used_when_no_static_match(self):
        lookup = {"some db alias": "Canonical DB Name"}
        result = canonicalize_song_name("Some DB Alias", lookup)
        assert result == "Canonical DB Name"

    def test_static_takes_precedence_over_dynamic(self):
        lookup = {"c brown": "Wrong DB Name"}
        result = canonicalize_song_name("C Brown", lookup)
        assert result == "C. Brown"

    def test_st_louis(self):
        assert canonicalize_song_name("St. Louis") == "St. Louis"
        assert canonicalize_song_name("St Louis") == "St. Louis"


class TestBuildCanonicalLookup:
    def test_builds_from_song_rows(self):
        rows = [
            {"song_name": "C. Brown", "aka": None},
            {"song_name": "Mr. Soul", "aka": None},
            {"song_name": "Coconut", "aka": "Coconut Image"},
        ]
        lookup = build_canonical_lookup(rows)
        assert "c. brown" in lookup
        assert lookup["c. brown"] == "C. Brown"
        assert "coconut image" in lookup
        assert lookup["coconut image"] == "Coconut"

    def test_aka_comma_separated(self):
        rows = [
            {"song_name": "Iko Iko", "aka": "Aiko Aiko, Aiko, Iko"},
        ]
        lookup = build_canonical_lookup(rows)
        assert lookup["aiko aiko"] == "Iko Iko"
        assert lookup["aiko"] == "Iko Iko"
        assert lookup["iko"] == "Iko Iko"

    def test_empty_rows(self):
        lookup = build_canonical_lookup([])
        assert lookup == {}

    def test_skips_rows_without_song_name(self):
        rows = [{"aka": "Some Alias"}]
        lookup = build_canonical_lookup(rows)
        assert lookup == {}
