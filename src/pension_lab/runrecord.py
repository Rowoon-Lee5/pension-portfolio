"""실행 기록 공통 함수 — 생성기 run_meta·실행본 사본·매니페스트가 같은 해시 방식을 쓰게 한다(감사 3c A-7).

해시 방식(하나로 통일): 텍스트 파일(.py·.ipynb·.md·.html·.csv)은 CRLF→LF로 바꾼 바이트의 sha256(`lf_sha256`).
git blob(LF)과 같은 바이트라 깨끗한 클론에서도 다시 계산된다. 원본 바이트 해시(`raw_sha256`)는 참고로 함께 적는다.
"""
from __future__ import annotations
import datetime, hashlib, json, subprocess
from pathlib import Path

from . import paths

ROOT = Path(__file__).resolve().parents[2]


def raw_sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def lf_sha256(p) -> str:
    return hashlib.sha256(Path(p).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def git(*a) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *a], capture_output=True, text=True, encoding="utf-8").stdout.strip()


def outputs_sha256(nb) -> tuple[int, str]:
    """코드셀 outputs 전체를 JSON(sort_keys, ensure_ascii=False)으로 직렬화한 해시와 출력 개수."""
    outs = [c.get("outputs", []) for c in nb.cells if c.cell_type == "code"]
    return sum(len(o) for o in outs), hashlib.sha256(json.dumps(outs, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def write_run_meta(out_dir, generator: Path, deps=(), extra: str = "") -> None:
    """run_meta.txt: 생성기·의존 모듈 LF sha256, git HEAD, 해당 파일의 작업트리 변경 여부, 실행 끝 시각."""
    rel = [str(Path(generator).resolve().relative_to(ROOT)).replace("\\", "/")] + list(deps)
    dirty = git("status", "--porcelain", "--", *rel)
    # git_head = 실행 끝 시각의 브랜치 HEAD(공유 브랜치라 다른 주제 커밋일 수 있음). code_commit = 생성기·의존 모듈을 마지막으로 바꾼 커밋.
    txt = (f"hash_method=sha256 of LF-normalized bytes (CRLF->LF)\ngenerator={Path(generator).name}\nsha256_lf={lf_sha256(generator)}\n"
           f"git_head={git('rev-parse', 'HEAD')}\ncode_commit={git('log', '-1', '--format=%H', '--', *rel)}\ncode_dirty={dirty.replace(chr(10), '; ') or 'clean'}\n"
           f"run_end={datetime.datetime.now().isoformat(timespec='seconds')}\n"
           + "".join(f"dep {m} sha256_lf={lf_sha256(ROOT / m)}\n" for m in deps) + extra)
    (Path(out_dir) / "run_meta.txt").write_text(txt, encoding="utf-8")


EXEC_DIR = paths.RESULTS / "executed_notebooks"


def save_executed(nb, nb_path: Path, exec_dir: Path = EXEC_DIR) -> Path:
    """실행본을 저장소 노트북과 git 밖 사본 둘 다에 쓴다. 저장소 노트북은 출력이 찍히므로 커밋 전에 nbstripout으로 지운다
    (README 재현 방법 5, .gitattributes). git 밖 사본은 출력이 남는다."""
    import nbformat as nbf
    n, _ = outputs_sha256(nb)
    assert n > 0, f"실행본 출력 0개(파일을 쓰지 않고 멈춤): {nb_path}"   # 감사 3d D-4: 검사 먼저, 쓰기 나중
    nbf.write(nb, nb_path)
    exec_dir.mkdir(parents=True, exist_ok=True)
    dst = exec_dir / Path(nb_path).name
    nbf.write(nb, dst)
    return dst
