from scripts.check_version_sync import load_version_surfaces


def test_version_surfaces_are_in_sync() -> None:
    versions = load_version_surfaces()
    assert len(set(versions.values())) == 1
    assert set(versions) == {
        "pyproject",
        "web_package",
        "python_package",
        "site_version",
    }
