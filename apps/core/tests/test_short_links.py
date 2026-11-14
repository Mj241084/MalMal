import pytest

from apps.core import shortlinks


@pytest.mark.parametrize("pk", [1, 35, 36, 4279, 10**9, 10**15])
def test_roundtrip_and_length(pk):
    assert shortlinks.decode(shortlinks.encode("p", pk)) == ("p", pk)
    assert len(shortlinks.short_link_param("p", pk)) <= 25


@pytest.mark.parametrize("bad", ["", "p", "3a7", "p!", "x12", "p" + "z" * 11])
def test_decode_rejects_junk(bad):
    with pytest.raises(ValueError):
        shortlinks.decode(bad)
