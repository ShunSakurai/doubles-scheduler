# app.py  ―  Streamlit GUI with running history
from doubles_cli import DoublesScheduler
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="ダブルス組み合わせ生成", page_icon="🏸", layout="centered"
)

st_autorefresh(interval=9 * 60 * 1000, limit=None, key="keep_alive")

st.markdown(
    """
    <style>
      .court-line{font-size:1.5rem;font-weight:600;margin-bottom:0.2rem;}
      .rest-line{font-size:1.2rem;margin-top:0.3rem;}
      .round-block.current{border:4px solid var(--primary-color, #1f77b4);border-radius:8px;}
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────
# サイドバー：設定とリセット
# ──────────────────────────────────
players = st.sidebar.number_input("プレーヤー", 9, 20, 10, step=1)
courts = st.sidebar.number_input("コート", 1, 4, 2, step=1)
if st.sidebar.button("🔄 組み合わせをリセット"):
    st.session_state.clear()

# ──────────────────────────────────
# セッション状態の初期化
# ──────────────────────────────────
if "scheduler" not in st.session_state:
    st.session_state.scheduler = DoublesScheduler(players, courts)
    st.session_state.P, st.session_state.C = players, courts
    st.session_state.round_no = 0
    st.session_state.rest_df = pd.DataFrame(
        {"プレーヤー": range(1, players + 1), "Rest": 0}
    )
    st.session_state.history = []            # (round_no, schedule) のリスト

# 人数・コート数が変わったら自動リセット
if players != st.session_state.P or courts != st.session_state.C:
    st.session_state.clear()
    st.rerun()

sch: DoublesScheduler = st.session_state.scheduler

# ----- 休み回数の一覧 -----

st.sidebar.subheader("休み回数")
st.sidebar.dataframe(
    st.session_state.rest_df.sort_values("プレーヤー"),
    hide_index=True,
    use_container_width=True,
)
# ──────────────────────────────────
# メイン UI
# ──────────────────────────────────
st.title("🏸 ダブルス組み合わせ生成")

gen = st.button("➕ 次の組み合わせを生成", use_container_width=True)

# ----- 新ラウンド生成 -----
if gen:
    sched = sch.next_round()
    st.session_state.round_no += 1

    # 休み回数更新
    for p in sched["Rest"]:
        st.session_state.rest_df.loc[
            st.session_state.rest_df["プレーヤー"] == p, "Rest"
        ] += 1

    # 履歴の先頭に追加（新しい順）
    st.session_state.history.insert(
        0, (st.session_state.round_no, sched)
    )

# ──────────────────────────────────
# ラウンド履歴（最新が上）
# ──────────────────────────────────
for idx, (rnd, sched) in enumerate(st.session_state.history):
    is_current = idx == 0                      # 先頭 ＝ 現在ラウンド
    cls = "round-block current" if is_current else "round-block"

    block_html = [f'<div class="{cls}">']
    block_html.append(f"<h3>ラウンド {rnd}</h3>")

    # 各コートのペア表示
    for court in sorted(k for k in sched if k != "Rest"):
        (a1, a2), (b1, b2) = sched[court]
        block_html.append(
            f'<div class="court-line">コート {court} : '
            f'{a1}-{a2} &nbsp;vs&nbsp; {b1}-{b2}</div>'
        )

    # 休みプレイヤー
    if sched["Rest"]:
        rest = ", ".join(map(str, sched["Rest"]))
        block_html.append(
            f'<div class="rest-line">休憩: {rest}</div>'
        )

    block_html.append("</div>")
    st.markdown("\n".join(block_html), unsafe_allow_html=True)
