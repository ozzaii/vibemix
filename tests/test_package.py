# SPDX-License-Identifier: Apache-2.0
"""Package import + version smoke tests."""


def test_import_succeeds():
    import vibemix

    assert vibemix is not None


def test_version():
    import vibemix

    assert vibemix.__version__ == "0.1.0-dev0"
