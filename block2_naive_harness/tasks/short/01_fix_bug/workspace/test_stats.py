import pytest

from stats import moving_average, median


def test_moving_average_covers_every_window():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_moving_average_window_equals_length():
    assert moving_average([2, 4, 6], 3) == [4.0]


def test_moving_average_rejects_bad_window():
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


def test_median_odd_and_even():
    assert median([3, 1, 2]) == 2
    assert median([4, 1, 3, 2]) == 2.5
