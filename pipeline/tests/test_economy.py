"""Reproduce Table A-2 of the supplementary appendix: California 2024, delta = 0.55."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from economy import weighted_change  # noqa: E402

CA = [("2020-12", 139.31), ("2021-01", 140.16), ("2021-02", 141.24), ("2021-03", 142.27),
      ("2021-04", 143.14), ("2021-05", 144.58), ("2021-06", 145.25), ("2021-07", 146.91),
      ("2021-08", 148.39), ("2021-09", 149.97), ("2021-10", 151.9), ("2021-11", 153.37),
      ("2021-12", 154.37), ("2022-01", 155.56), ("2022-02", 157.25), ("2022-03", 158.8),
      ("2022-04", 159.86), ("2022-05", 160.54), ("2022-06", 161.23), ("2022-07", 162.0),
      ("2022-08", 162.71), ("2022-09", 162.61), ("2022-10", 162.38), ("2022-11", 162.46),
      ("2022-12", 162.54), ("2023-01", 162.62), ("2023-02", 163.02), ("2023-03", 163.37),
      ("2023-04", 163.79), ("2023-05", 164.28), ("2023-06", 164.4), ("2023-07", 164.4),
      ("2023-08", 164.54), ("2023-09", 164.44), ("2023-10", 164.6), ("2023-11", 165.01),
      ("2023-12", 165.47), ("2024-01", 165.62), ("2024-02", 165.67), ("2024-03", 166.05),
      ("2024-04", 166.45), ("2024-05", 167.21), ("2024-06", 167.68)]


def test_table_a2():
    v, last = weighted_change(CA, "2021-01", "2024-06", 0.55, nowcast=False)
    assert last == "2024-06"
    # Paper: 0.224461996. The table's index values are rounded to 2 decimals,
    # so allow a small tolerance.
    assert abs(v - 0.224461996) < 0.002, v


def test_nowcast_shift_full_data_is_identity():
    a, _ = weighted_change(CA, "2021-01", "2024-06", 0.55, nowcast=True)
    b, _ = weighted_change(CA, "2021-01", "2024-06", 0.55, nowcast=False)
    assert a == b


if __name__ == "__main__":
    v, _ = weighted_change(CA, "2021-01", "2024-06", 0.55, nowcast=False)
    print(f"California 2024: {v:.9f} (paper 0.224461996)")
    test_table_a2(); test_nowcast_shift_full_data_is_identity(); print("ok")
