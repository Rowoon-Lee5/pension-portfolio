"""12. 급락장 AI 연금 상담 감사 — 응답별 채점표(results/F_scores_by_response.csv)만 읽어 집계 표·그림을 만든다(새 호출·채점 없음).
채점은 LLM 보조 채점자(claude-haiku-5-5) 기준이라 잠정. 사람 2명 채점(Cohen's κ)이 끝나면 바뀔 수 있다.
실행: 저장소 루트에서 python 12_ai_advice_audit/notebooks/aggregate_F.py
  → 12_ai_advice_audit/results/F_model_summary.csv, F_taxerr_by_question.csv, F_wrong_fact_ids.csv, figures/fig_F_AI상담.*
"""
import hashlib
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "12_ai_advice_audit"
SRC = D / "results" / "F_scores_by_response.csv"
MAIN = ["claude-opus-5-5", "gemini-3.8-flash", "모델X"]
REF = "gpt-5.5(참고)"
COL = {"claude-opus-5-5": "#2a78d6", "gemini-3.8-flash": "#eb6834", "모델X": "#1baf7a", REF: "#9AA3AD"}   # 범주 색 1~3번(색각 검증 통과)
QL = {"Q1": "Q1 해지할까", "Q2": "Q2 다 팔까", "Q3": "Q3 언제 넣을까", "Q4": "Q4 계좌 이전", "Q5": "Q5 TDF로 바꿀까"}
names = {f.name for f in fm.fontManager.ttflist}
plt.rcParams.update({"font.family": ["Malgun Gothic" if "Malgun Gothic" in names else "NanumGothic", "DejaVu Sans"],
                     "axes.unicode_minus": False, "figure.dpi": 100, "savefig.dpi": 200,
                     "axes.spines.top": False, "axes.spines.right": False, "svg.hashsalt": "pension"})


def load():
    d = pd.read_csv(SRC, encoding="utf-8-sig")
    d["sell"] = d.S1.eq("명시권유") | d.S2.eq("명시권유")                                          # 주 지표(채점기준 '집계 규칙')
    d["sell_cond"] = d.S1.isin(["명시권유", "조건부권유"]) | d.S2.isin(["명시권유", "조건부권유"])  # 보조 지표
    d["wrong_any"] = d.T_wrong > 0
    for c in ("O_add", "O_rebal", "O_dca", "D"):
        d[c + "_y"] = d[c].eq("있음")
    d["S1_dissuade"] = d.S1.eq("만류")
    return d


def summary(d):
    per = d.groupby(["model", "prompt_id"]).agg(n=("sell", "size"), k=("sell", "sum")).reset_index()
    # 5번 중 3번 이상 = 다수 '팔라'. 5번을 다 못 받아 남은 횟수로 결론이 안 나면 미정(None)
    per["maj"] = [True if k >= 3 else (False if k + 5 - n < 3 else None) for k, n in zip(per.k, per.n)]
    m = d.groupby("model").agg(role=("role", "first"), 응답=("sell", "size"), 프롬프트=("prompt_id", "nunique"),
                               팔라_명시=("sell", "sum"), 팔라_조건부포함=("sell_cond", "sum"),
                               해지_만류_비율=("S1_dissuade", "mean"), 세법틀림1개이상_비율=("wrong_any", "mean"),
                               맞은진술=("T_correct", "sum"), 틀린진술=("T_wrong", "sum"), 불완전진술=("T_incomplete", "sum"),
                               숫자오류=("N_errors", "sum"), 추가납입언급=("O_add_y", "mean"), 리밸런싱언급=("O_rebal_y", "mean"),
                               분할매수언급=("O_dca_y", "mean"), 상담면책문구=("D_y", "mean")).reset_index()
    g = per.groupby("model")
    m["5번다받은프롬프트"] = m.model.map(g.n.apply(lambda n: int((n == 5).sum())))
    m["다수팔라_판정된프롬프트"] = m.model.map(g.maj.apply(lambda x: int(x.notna().sum())))
    m["다수팔라_프롬프트"] = m.model.map(g.maj.apply(lambda x: int((x == True).sum())))  # noqa: E712
    m["팔라_조건부포함_비율"] = m.팔라_조건부포함 / m.응답
    return m.set_index("model").loc[MAIN + [REF]].reset_index()


def main():
    d = load()
    R = D / "results"
    src = f"12_ai_advice_audit/results/F_scores_by_response.csv\tsha256={hashlib.sha256(SRC.read_bytes()).hexdigest()}\trows={len(d)}"
    m = summary(d)
    m.to_csv(R / "F_model_summary.csv", index=False, encoding="utf-8-sig")
    q = d.groupby(["question", "model"]).agg(응답=("wrong_any", "size"), 세법틀림1개이상=("wrong_any", "sum"),
                                             세법틀림1개이상_비율=("wrong_any", "mean"), 틀린진술=("T_wrong", "sum"),
                                             불완전진술=("T_incomplete", "sum")).reset_index()
    q.to_csv(R / "F_taxerr_by_question.csv", index=False, encoding="utf-8-sig")
    ids = d[d.role == "본비교"].T_wrong_ids.fillna("").str.split(";").explode().str.strip()
    ids = ids[ids != ""]
    f = ids.groupby(ids.map(lambda x: int(x[1:]))).size()
    f = pd.DataFrame({"fact_id": [f"F{i}" for i in f.index], "틀림_진술수": f.values}).sort_values(["틀림_진술수", "fact_id"], ascending=[False, True])
    f.to_csv(R / "F_wrong_fact_ids.csv", index=False, encoding="utf-8-sig")
    for name in ("F_model_summary", "F_taxerr_by_question", "F_wrong_fact_ids"):
        (R / f"{name}_source.txt").write_text(src + "\n생성: 12_ai_advice_audit/notebooks/aggregate_F.py\n", encoding="utf-8")

    fig = plt.figure(figsize=(10, 5.6))
    ax = fig.add_axes([0.07, 0.22, 0.50, 0.55]); bx = fig.add_axes([0.73, 0.22, 0.25, 0.55])
    w = 0.26
    for i, mdl in enumerate(MAIN):
        z = q[q.model == mdl].set_index("question").reindex(list(QL))
        x = np.arange(5) + (i - 1) * w
        ax.bar(x, z.세법틀림1개이상_비율 * 100, w - 0.03, color=COL[mdl], label=f"{mdl} (응답 {int(z.응답.sum())})")
        for xi, v in zip(x, z.세법틀림1개이상_비율):
            ax.text(xi, v * 100 + 1.2, f"{v * 100:.0f}", ha="center", fontsize=7, color="#333")
    ax.set_xticks(range(5), list(QL.values()), fontsize=8)
    ax.set_ylim(0, 90); ax.set_ylabel("세법 진술이 1개 이상 틀린 응답 (%)", fontsize=8.5)
    ax.grid(axis="y", color="#E5E5E5", lw=0.6); ax.set_axisbelow(True)
    ax.legend(fontsize=7.5, frameon=False, loc="upper left", ncol=3)
    ax.set_title("질문별 세법 틀림 (질문당 응답: Claude·모델X 15, Gemini 4~5)", loc="left", fontsize=8.5, color="#222")
    ind = [("팔라_조건부포함_비율", "해지·전량매도 권유\n(조건부 포함)"), ("추가납입언급", "한도 안\n추가납입 언급"),
           ("상담면책문구", "전문가 상담·\n면책 문구")]
    ms = m.set_index("model")
    for j, (c, _) in enumerate(ind):
        for i, mdl in enumerate(MAIN):
            y = j + (i - 1) * 0.26
            bx.barh(y, ms.loc[mdl, c] * 100, 0.23, color=COL[mdl])
            bx.text(ms.loc[mdl, c] * 100 + 1.5, y, f"{ms.loc[mdl, c] * 100:.0f}", va="center", fontsize=7, color="#333")
    bx.set_yticks(range(3), [b for _, b in ind], fontsize=8); bx.invert_yaxis(); bx.set_xlim(0, 100)
    bx.set_xlabel("응답 중 비율 (%)", fontsize=8); bx.grid(axis="x", color="#E5E5E5", lw=0.6); bx.set_axisbelow(True)
    bx.set_title("'해지하라·다 팔라'고 직접 권한 응답:\n세 모델 모두 0건", loc="left", fontsize=8.5, color="#222")
    fig.suptitle("급락장 연금저축 AI 상담: '해지·다 팔라'는 없었고, 세법 오류는 한 모델에 몰렸다(잠정)", x=0.02, ha="left", fontsize=14, fontweight="bold", y=0.975)
    fig.text(0.02, 0.905, "가상 인물 3명 × 질문 5개 = 프롬프트 15개, 프롬프트마다 5번(Gemini는 무료 할당량 초과로 23건). 시스템 프롬프트·웹 검색 없음, 각 사 기본 설정.\n"
             "채점 = 정답표(소득세법·시행령 원문, F1~F15)와 대조. LLM 보조 채점자 claude-haiku-5-5 기준이라 잠정이고, 채점자가 Claude와 같은 회사 모델이다.",
             fontsize=8.5, color="#444", va="top", linespacing=1.4)
    fig.text(0.02, 0.015, "모델X = 제공사 약관상 결과 공개에 사전 서면 동의가 필요해 이름을 가린 모델. GPT-5.5(참고, 31건)는 크레딧 소진으로 본 비교에서 뺐고 그림에 넣지 않음(results 표에는 있음).\n"
             "출처: 12_ai_advice_audit/results/F_scores_by_response.csv. 투자 권유가 아님.", fontsize=7.2, color="#666", linespacing=1.4)
    F = D / "figures"; F.mkdir(exist_ok=True)
    fig.savefig(F / "fig_F_AI상담.png"); fig.savefig(F / "fig_F_AI상담.svg", metadata={"Date": None}); plt.close(fig)
    pd.concat([q[q.model.isin(MAIN)].assign(구분="질문별"), m[m.model.isin(MAIN)][["model"] + [c for c, _ in ind]].assign(구분="지표")]).to_csv(
        F / "fig_F_AI상담_data.csv", index=False, encoding="utf-8-sig")
    (F / "fig_F_AI상담_source.txt").write_text(src + "\n생성: 12_ai_advice_audit/notebooks/aggregate_F.py\n", encoding="utf-8")
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(m.T.to_string()); print(q.to_string()); print(f.to_string())


if __name__ == "__main__":
    main()
