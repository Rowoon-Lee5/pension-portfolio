# -*- coding: utf-8 -*-
"""두 실행 폴더(포트폴리오판)의 CSV를 칸 단위로 비교(동결 규칙 12 대용, 감사 r3 R3-L8).
쓰기: python notebooks/candidate5/_diff_runs_cand5p.py <옛 run 폴더> <새 run 폴더>
출력(새 폴더): diff_vs_<옛 폴더 이름>_cells.csv(바뀐 칸) · _summary.csv(파일별 대조 행·한쪽에만 있는 행·바뀐 칸 수·바뀐 열).
키 = 아래 KEYS 중 그 파일에 있는 열. 숫자 = 상대차 > 1e-12면 바뀜. 경로 수가 다른 부트스트랩 파일(빠른 시험)은 건너뜀.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

KEYS = ["path", "asset", "m", "person", "b", "K1", "K2", "region", "cell", "D", "후보", "비교", "쌍", "블록", "기준", "차이",
        "폭락달", "H", "파일", "항목", "사람", "세금 그릇", "키", "구간", "단계"]
BOOT = ("boot_stats.csv", "defer_boot_stats.csv", "boot_p70_m30_gap.csv")


def diff(old: Path, new: Path):
    cells, summ = [], []
    nb = lambda r: __import__("json").load(open(r / "N" / "boot_meta.json", encoding="utf-8"))["n_boot"] if (r / "N" / "boot_meta.json").exists() else None
    same_boot = nb(old) == nb(new)
    for f in sorted(p.relative_to(new) for p in new.rglob("*.csv") if not p.name.startswith("diff_vs_")):
        if not (old / f).exists():
            summ.append({"파일": str(f), "비고": "새 파일"}); continue
        if f.name in BOOT and not same_boot:
            summ.append({"파일": str(f), "비고": f"부트스트랩 경로 수 다름({nb(old)} vs {nb(new)}) → 건너뜀"}); continue
        a, b = pd.read_csv(old / f), pd.read_csv(new / f)
        key = [k for k in KEYS if k in a.columns and k in b.columns]
        a, b = (x.assign(_i=x.groupby(key, dropna=False).cumcount() if key else np.arange(len(x))) for x in (a, b))   # 키가 겹치는 행은 순번으로 구분
        j = a.merge(b, on=key + ["_i"], how="outer", suffixes=("_old", "_new"), indicator=True)
        both = j[j._merge == "both"]; changed = []
        for c in [c for c in a.columns if c in b.columns and c not in key + ["_i"]]:
            x, y = both[c + "_old"], both[c + "_new"]
            if pd.api.types.is_numeric_dtype(x) and pd.api.types.is_numeric_dtype(y) and not pd.api.types.is_bool_dtype(x):
                d = ~((x.isna() & y.isna()) | ((x - y).abs() <= 1e-12 * np.maximum(x.abs(), 1)))
            else:
                d = x.astype(str) != y.astype(str)
            if d.any():
                changed.append(f"{c}({int(d.sum())})")
                cells.append(both.loc[d, key].assign(파일=str(f), 열=c, 옛값=x[d].values, 새값=y[d].values))
        summ.append({"파일": str(f), "대조 행": len(both), "옛 폴더에만": int((j._merge == "left_only").sum()),
                     "새 폴더에만": int((j._merge == "right_only").sum()), "바뀐 칸": sum(int(s.split("(")[1][:-1]) for s in changed),
                     "바뀐 열": ", ".join(changed), "비고": "키 " + "·".join(key)})
    cells = pd.concat(cells, ignore_index=True) if cells else pd.DataFrame(columns=["파일", "열", "옛값", "새값"])
    return cells, pd.DataFrame(summ)


if __name__ == "__main__":
    old, new = Path(sys.argv[1]), Path(sys.argv[2])
    cells, summ = diff(old, new)
    stem = new / f"diff_vs_{old.name}"
    cells.to_csv(f"{stem}_cells.csv", index=False, encoding="utf-8-sig"); summ.to_csv(f"{stem}_summary.csv", index=False, encoding="utf-8-sig")
    print(summ.to_string(index=False))
    print(f"바뀐 칸 {len(cells)}개 → {stem}_cells.csv")
