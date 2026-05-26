import os
import json
import streamlit as st
from google import genai

GOALS_FILE = "goals.json"
GEMINI_MODEL = "gemini-2.0-flash-lite"

st.set_page_config(
    page_title="MY LIFE OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""<style>
[data-testid="stAppViewContainer"],[data-testid="stMain"],.main{background:#000!important}
.block-container{max-width:860px!important;padding:2rem 2.5rem!important}
[data-testid="stSidebar"]{background:#070707!important;border-right:1px solid #141414!important}
[data-testid="stSidebar"] *{color:#fff!important}
[data-testid="stSidebar"] .stButton>button{
  background:transparent!important;border:1px solid #1c1c1c!important;
  color:#666!important;border-radius:0!important;font-size:.82rem!important;
  letter-spacing:1.5px!important;text-transform:uppercase!important;
  text-align:left!important;padding:.55rem 1rem!important
}
[data-testid="stSidebar"] .stButton>button:hover{background:#111!important;color:#fff!important;border-color:#3a3a3a!important}
[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:#fff!important;color:#000!important;border-color:#fff!important;font-weight:900!important}
h1{font-size:2.5rem!important;font-weight:900!important;letter-spacing:-2px!important;color:#fff!important;line-height:1.1!important}
h2{font-size:1.25rem!important;font-weight:800!important;color:#fff!important;text-transform:uppercase!important;letter-spacing:1px!important}
h3{font-size:.8rem!important;font-weight:700!important;color:#555!important;text-transform:uppercase!important;letter-spacing:2.5px!important}
p,li{color:#999!important}
.stTextArea textarea,.stTextInput input{
  background:#0a0a0a!important;color:#fff!important;
  border:1px solid #1e1e1e!important;border-radius:0!important;font-size:.94rem!important
}
.stTextArea textarea:focus,.stTextInput input:focus{border-color:#444!important;box-shadow:none!important}
.stButton>button{
  background:#0c0c0c!important;color:#fff!important;
  border:1px solid #1e1e1e!important;border-radius:0!important;
  font-weight:700!important;font-size:.84rem!important;
  text-transform:uppercase!important;letter-spacing:.8px!important;padding:.55rem 1.1rem!important
}
.stButton>button:hover{background:#161616!important;border-color:#444!important}
.stButton>button[kind="primary"]{background:#fff!important;color:#000!important;border-color:#fff!important;font-weight:900!important}
.stButton>button[kind="primary"]:hover{background:#d8d8d8!important;border-color:#d8d8d8!important}
[data-testid="stExpander"]{background:#080808!important;border:1px solid #161616!important;border-radius:0!important}
[data-testid="stExpander"] summary{color:#bbb!important;font-size:.92rem!important}
[data-testid="stMetricLabel"]{color:#444!important;font-size:.7rem!important;text-transform:uppercase!important;letter-spacing:2px!important}
[data-testid="stMetricValue"]{color:#fff!important;font-weight:900!important}
.stCheckbox label{color:#999!important;font-size:.9rem!important}
.stSelectbox>div>div{background:#0a0a0a!important;border:1px solid #1e1e1e!important;border-radius:0!important;color:#fff!important}
#MainMenu,footer{visibility:hidden}
[data-testid="stHeader"]{background:transparent!important}
</style>""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
for k, v in {
    "nav_page": "goals",
    "messages": [],
    "current_mode": None,
    "selected_goal_idx": 0,
    "editing_field": None,
    "waiting_response": False,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Gemini client ─────────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# ── Data ──────────────────────────────────────────────────────────────────────
def load_goals():
    if not os.path.exists(GOALS_FILE):
        return {"goals": []}
    with open(GOALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_goals(data):
    with open(GOALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def toggle_task(data, task_id):
    for g in data["goals"]:
        for m in g.get("children", []):
            for t in m.get("children", []):
                if t["id"] == task_id:
                    t["done"] = not t.get("done", False)
    save_goals(data)

def current_goal_name(data):
    idx = st.session_state.selected_goal_idx
    if data["goals"] and idx < len(data["goals"]):
        return data["goals"][idx]["title"]
    return "ゴール未設定"

# ── Fallback frameworks ───────────────────────────────────────────────────────
FRAMEWORKS = {
    "wallhit": {
        "title": "GOAL WALLHIT — 6 AXES",
        "axes": [
            ("定義", "このゴールを「〜することで〜になる」の形で言語化すると？"),
            ("現在地", "今どこにいますか？ 数値・状態・感覚で正直に。"),
            ("収益モデル", "誰が・何に・いくら払うのか。"),
            ("到達式", "ゴール = A × B × C の形に分解すると？"),
            ("ボトルネック", "今一番詰まっているのはどこですか？ 1つだけ。"),
            ("速度バランス", "質と量、どちらを今は優先すべきか。なぜ？"),
        ],
        "question": "6軸のうち、一番「答えにくい」と感じたのはどれですか？\nそこが今の本質的なボトルネックです。",
    },
    "criteria": {
        "title": "COMPLETION CRITERIA — 2 AXES",
        "axes": [
            ("達成タイプ", "単月突破（1度でもOK）か、安定達成（3ヶ月連続など継続）か？"),
            ("指標", "売上・粗利・手取り・入金 — どの数字で「達成」を判定しますか？"),
        ],
        "question": "「あなた個人として」完了条件を一文で書いてください。\n例: 「miku個人として、手取り月50万円を3ヶ月連続で達成した時点で完了とする」",
    },
    "breakdown": {
        "title": "TASK BREAKDOWN — 6 PRIORITY ACTIONS",
        "axes": [
            ("① 最速で結果が出る行動", "今すぐできる、最小インプット×最大インパクトな行動は？"),
            ("② 収益直結のアクション", "お金に直接つながる行動を具体化すると？"),
            ("③ 仕組み化の第一歩", "繰り返し作業を一つ選んで仕組みにするとしたら？"),
            ("④ ボトルネック解消", "最大の詰まりを解消する具体的な行動は？"),
            ("⑤ 学習・インプット", "今足りていない知識・スキルは何ですか？"),
            ("⑥ 環境・ネットワーク", "誰と繋がれば10倍速で進みますか？"),
        ],
        "question": "今日の「最初の1手」を決めてください。明日ではなく、今日です。",
    },
    "action": {
        "title": "ACTION PLAN — EXECUTION FRAMEWORK",
        "axes": [
            ("現在地確認", "目標名だけ決まっている状態をスタート地点とします。"),
            ("今週できること", "今週中に完了できる具体的な行動を3つ挙げてください。"),
            ("今日できること", "今日の残り時間でできることを1つだけ選んでください。"),
            ("邪魔になるもの", "この行動を妨げる可能性があるものを正直に。"),
            ("他者に任せられるもの", "自分がやらなくていいタスクはどれですか？"),
        ],
        "question": "今日の行動を「動詞 + 対象 + 期限」で一文に。\n例:「クライアントリスト20社を今日17時までに作成する」",
    },
}

# ── Mode config ───────────────────────────────────────────────────────────────
MODE_CONFIG = {
    "wallhit": {
        "label": "⭐  ゴールの壁打ちをする",
        "auto_msg": "ゴール『{g}』について壁打ちしたいです。論点を広げながら考えを整理してください。",
        "system": (
            "あなたは「みきゅん」、ユーザーの目標達成を本質的に支援するAIコーチです。"
            "ゴールが具体的な場合は6軸の論点（定義・現在地・収益モデル・到達式・ボトルネック・速度バランス）を提示し最も本質的な1問を投げかけてください。"
            "ゴールが曖昧な場合は「達成したい変化」「なぜ今やるのか」「達成した状態」を言語化させるコーチングを行ってください。"
            "余計なポジティブ演出は不要です。的確にシンプルに。"
        ),
    },
    "criteria": {
        "label": "⭐  完了条件を決める",
        "auto_msg": "ゴール『{g}』の完了条件を明確にしたいです。達成状態が分かる基準を一緒に整理してください。",
        "system": (
            "あなたは「みきゅん」です。「単月突破」か「安定達成」かの達成タイプと、"
            "「売上・粗利・手取り・入金」のどの指標で見るかの2軸を整理し、"
            "ユーザーに合わせた完了条件の文章案（例: miku個人として〜）を提案して問いかけてください。"
            "余計な前置き不要。"
        ),
    },
    "breakdown": {
        "label": "⭐  タスクを整理・分解する",
        "auto_msg": "ゴール『{g}』を具体的なタスクに分解したいです。優先順も含めて整理してください。",
        "system": (
            "あなたは「みきゅん」です。"
            "ビジネスや目標達成の流れに沿った優先順位付きの6本の子ゴール案をロジカルに提示し、"
            "「今日の最初の1手」を明確に指定してください。余計な前置き不要。"
        ),
    },
    "action": {
        "label": "⭐  みきゅんにやってもらう",
        "auto_msg": "ゴール『{g}』の実行を進めたいです。次にやることと進め方を一緒に整理してください。",
        "system": (
            "あなたは「みきゅん」です。現在地が「目標名だけ立っている状態」であることを前提に、"
            "実行単位まで落とし込むための具体的なアクションプランと、"
            "次に進むための本質的な質問を投げかけてください。余計な前置き不要。"
        ),
    },
}

# ── AI functions ──────────────────────────────────────────────────────────────
def call_mikyun(mode_key, messages, goal_name):
    """Returns (text, is_fallback)."""
    if not client:
        return "", True
    cfg = MODE_CONFIG[mode_key]
    history = "".join(
        f"{'ユーザー' if m['role']=='user' else 'みきゅん'}: {m['content']}\n\n"
        for m in messages[:-1]
    )
    last = messages[-1]["content"]
    prompt = (
        f"{cfg['system']}\n\n"
        f"現在のゴール:『{goal_name}』\n\n"
        f"{('会話履歴:\n' + history) if history else ''}"
        f"ユーザー: {last}\n\nみきゅんとして回答:"
    )
    try:
        res = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return res.text, False
    except Exception:
        return "", True


def call_brainstorm(raw_input, existing_data, merge):
    """Returns (new_data_dict, error_str)."""
    if not client:
        return None, "APIキー未設定"
    schema = (
        '{"goals":[{"id":"goal_xxxx","title":"大目標","description":"説明","status":"active",'
        '"deadline":"","current_state":"","completion_criteria":"",'
        '"children":[{"id":"mid_xxxx","title":"中目標","description":"説明","status":"active",'
        '"children":[{"id":"task_xxxx","title":"タスク","status":"pending","done":false}]}]}]}'
    )
    if merge:
        prompt = (
            f"目標設計の専門家として、ユーザーの思考テキストを既存ツリーに統合してください。\n"
            f"既存:{json.dumps(existing_data, ensure_ascii=False)}\n入力:{raw_input}\nJSONのみ返す:\n{schema}"
        )
    else:
        prompt = (
            f"目標設計の専門家として、ユーザーの思考テキストからゼロで目標ツリーを設計してください。\n"
            f"入力:{raw_input}\nJSONのみ返す:\n{schema}"
        )
    try:
        res = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        raw = res.text.strip()
        if "```" in raw:
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        s, e = raw.find("{"), raw.rfind("}") + 1
        if s != -1 and e > s:
            raw = raw[s:e]
        return json.loads(raw), None
    except Exception as ex:
        return None, str(ex)

# ── Framework renderer ────────────────────────────────────────────────────────
def render_framework(mode_key):
    fw = FRAMEWORKS[mode_key]
    items_html = ""
    for label, desc in fw["axes"]:
        items_html += (
            f'<div style="padding:11px 0;border-bottom:1px solid #111;">'
            f'<div style="font-size:.7rem;text-transform:uppercase;letter-spacing:1.5px;color:#444;margin-bottom:3px;">{label}</div>'
            f'<div style="color:#aaa;font-size:.9rem;line-height:1.5;">{desc}</div>'
            f'</div>'
        )
    question_html = fw["question"].replace("\n", "<br>")
    st.markdown(
        f'<div style="background:#060606;border:1px solid #1a1a1a;padding:20px 24px;margin:10px 0;">'
        f'<div style="font-size:.68rem;text-transform:uppercase;letter-spacing:3px;color:#444;margin-bottom:14px;">{fw["title"]}</div>'
        f'{items_html}'
        f'<div style="margin-top:14px;padding-top:12px;border-top:1px solid #111;color:#ccc;font-size:.9rem;line-height:1.65;">'
        f'💬 {question_html}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div style="font-size:1rem;font-weight:900;letter-spacing:2.5px;'
        'text-transform:uppercase;padding:20px 0 4px;color:#fff;">⚡ MY LIFE OS</div>',
        unsafe_allow_html=True,
    )
    st.markdown('<hr style="border:none;border-top:1px solid #141414;margin:6px 0 18px;">', unsafe_allow_html=True)

    for nav_key, nav_label in [
        ("goals", "🎯  GOAL"),
        ("brainstorm", "💬  AI壁打ち"),
        ("mikyun", "🤖  みきゅんとお話"),
    ]:
        is_active = st.session_state.nav_page == nav_key
        if st.button(nav_label, key=f"nav_{nav_key}", use_container_width=True,
                     type="primary" if is_active else "secondary"):
            st.session_state.nav_page = nav_key
            st.rerun()

    st.markdown('<hr style="border:none;border-top:1px solid #141414;margin:18px 0;">', unsafe_allow_html=True)
    data = load_goals()
    total = sum(len(m.get("children", [])) for g in data["goals"] for m in g.get("children", []))
    done = sum(
        1 for g in data["goals"]
        for m in g.get("children", [])
        for t in m.get("children", [])
        if t.get("done")
    )
    st.metric("TASKS", f"{done} / {total}")

# ── Page: GOAL ────────────────────────────────────────────────────────────────
if st.session_state.nav_page == "goals":
    data = load_goals()

    if not data["goals"]:
        st.markdown(
            '<div style="text-align:center;padding:80px 0;">'
            '<div style="font-size:.82rem;color:#333;text-transform:uppercase;letter-spacing:3px;">'
            'ここをタップしてゴールを設定しよう！</div></div>',
            unsafe_allow_html=True,
        )
        with st.form("new_goal_form"):
            t = st.text_input("大ゴールを入力", placeholder="例: 月収50万円を達成する")
            d = st.text_area("説明（任意）", height=80)
            if st.form_submit_button("設定する ▶", type="primary") and t:
                new_g = {
                    "id": f"goal_{os.urandom(4).hex()}",
                    "title": t, "description": d, "status": "active",
                    "deadline": "", "current_state": "", "completion_criteria": "",
                    "children": [],
                }
                data["goals"].append(new_g)
                save_goals(data)
                st.rerun()
    else:
        if len(data["goals"]) > 1:
            titles = [g["title"] for g in data["goals"]]
            sel = st.selectbox("ゴールを選択", titles,
                               index=min(st.session_state.selected_goal_idx, len(titles) - 1))
            st.session_state.selected_goal_idx = titles.index(sel)

        idx = min(st.session_state.selected_goal_idx, len(data["goals"]) - 1)
        goal = data["goals"][idx]

        # Big goal card
        st.markdown(
            f'<div style="border:2px solid #fff;padding:26px 30px;margin-bottom:18px;background:#040404;">'
            f'<div style="font-size:.68rem;text-transform:uppercase;letter-spacing:3px;color:#444;margin-bottom:6px;">BIG GOAL</div>'
            f'<div style="font-size:2.3rem;font-weight:900;line-height:1.15;color:#fff;">{goal["title"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Meta buttons
        deadline = goal.get("deadline", "")
        current_state = goal.get("current_state", "")
        completion_criteria = goal.get("completion_criteria", "")

        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            lbl = f"📅 {deadline}" if deadline else "📅 期日を設定"
            if st.button(lbl, use_container_width=True, key="btn_dl"):
                st.session_state.editing_field = None if st.session_state.editing_field == "deadline" else "deadline"
                st.rerun()
        with mc2:
            lbl = "📍 現状 ✓" if current_state else "📍 現状を入力"
            if st.button(lbl, use_container_width=True, key="btn_cs"):
                st.session_state.editing_field = None if st.session_state.editing_field == "current_state" else "current_state"
                st.rerun()
        with mc3:
            lbl = "✅ 完了基準 ✓" if completion_criteria else "✅ 完了の基準"
            if st.button(lbl, use_container_width=True, key="btn_cc"):
                st.session_state.editing_field = None if st.session_state.editing_field == "completion_criteria" else "completion_criteria"
                st.rerun()

        ef = st.session_state.editing_field
        if ef == "deadline":
            with st.form("f_dl"):
                v = st.text_input("期日", value=deadline, placeholder="例: 2026年12月31日")
                if st.form_submit_button("保存") and v is not None:
                    data["goals"][idx]["deadline"] = v
                    save_goals(data)
                    st.session_state.editing_field = None
                    st.rerun()
        elif ef == "current_state":
            with st.form("f_cs"):
                v = st.text_area("現状", value=current_state, height=100,
                                 placeholder="例: 月収15万円。副業未着手。")
                if st.form_submit_button("保存"):
                    data["goals"][idx]["current_state"] = v
                    save_goals(data)
                    st.session_state.editing_field = None
                    st.rerun()
        elif ef == "completion_criteria":
            with st.form("f_cc"):
                v = st.text_area("完了の基準", value=completion_criteria, height=100,
                                 placeholder="例: 手取り月50万円を3ヶ月連続で達成")
                if st.form_submit_button("保存"):
                    data["goals"][idx]["completion_criteria"] = v
                    save_goals(data)
                    st.session_state.editing_field = None
                    st.rerun()

        st.markdown('<hr style="border:none;border-top:1px solid #111;margin:18px 0;">', unsafe_allow_html=True)

        # Tasks
        if goal.get("children"):
            st.markdown("### TASKS")
            for mid in goal["children"]:
                with st.expander(f"  {mid['title']}", expanded=False):
                    if mid.get("description"):
                        st.caption(mid["description"])
                    for task in mid.get("children", []):
                        ca, cb = st.columns([0.06, 0.94])
                        with ca:
                            chk = st.checkbox("", value=task.get("done", False), key=f"t_{task['id']}")
                            if chk != task.get("done", False):
                                toggle_task(data, task["id"])
                                st.rerun()
                        with cb:
                            color = "#3a3a3a" if task.get("done") else "#ccc"
                            title_html = f"<s>{task['title']}</s>" if task.get("done") else task["title"]
                            st.markdown(
                                f'<div style="color:{color};font-size:.9rem;padding-top:5px;">{title_html}</div>',
                                unsafe_allow_html=True,
                            )
        else:
            st.markdown(
                '<div style="color:#2a2a2a;text-align:center;padding:22px;'
                'border:1px dashed #1a1a1a;font-size:.8rem;text-transform:uppercase;letter-spacing:1.5px;">'
                'タスクなし — AI壁打ちで生成する</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<hr style="border:none;border-top:1px solid #111;margin:18px 0;">', unsafe_allow_html=True)

        if st.button("🤖 みきゅんとお話 ▶", type="primary", use_container_width=True, key="goto_mik"):
            st.session_state.nav_page = "mikyun"
            st.rerun()

# ── Page: AI壁打ち ────────────────────────────────────────────────────────────
elif st.session_state.nav_page == "brainstorm":
    st.markdown("# AI壁打ち")
    st.markdown(
        '<div style="color:#3a3a3a;font-size:.78rem;text-transform:uppercase;'
        'letter-spacing:2px;margin-bottom:22px;">HEAD DUMP → GOAL TREE</div>',
        unsafe_allow_html=True,
    )

    raw = st.text_area(
        "思考の垂れ流し",
        height=200,
        placeholder="例: 最近体がなまってる。仕事もうまくいってないし収入増やしたい。英語も勉強しなきゃ...",
    )

    bc1, bc2 = st.columns(2)
    with bc1:
        do_merge = st.button("🔁 既存に追加・統合", use_container_width=True,
                             key="brs_merge", disabled=not raw.strip())
    with bc2:
        do_new = st.button("🆕 ゼロから生成", use_container_width=True, type="primary",
                           key="brs_new", disabled=not raw.strip())

    if do_merge or do_new:
        data = load_goals()
        with st.spinner("Gemini が構造化中..."):
            new_data, err = call_brainstorm(raw, data, merge=do_merge)
        if err:
            st.error(f"エラー: {err}")
        else:
            save_goals(new_data)
            st.success("✅ 目標ツリーを更新しました — GOALタブで確認できます")
            st.json(new_data)

# ── Page: みきゅんとお話 ──────────────────────────────────────────────────────
elif st.session_state.nav_page == "mikyun":
    data = load_goals()
    goal_name = current_goal_name(data)

    st.markdown("# みきゅんとお話")
    st.markdown(
        f'<div style="color:#3a3a3a;font-size:.72rem;text-transform:uppercase;letter-spacing:2px;margin-bottom:2px;">CURRENT GOAL</div>'
        f'<div style="color:#fff;font-size:1.05rem;font-weight:700;margin-bottom:20px;">{goal_name}</div>',
        unsafe_allow_html=True,
    )

    # Battle panel header
    st.markdown(
        '<div style="color:#3a3a3a;font-size:.75rem;text-transform:uppercase;'
        'letter-spacing:1.5px;margin-bottom:14px;">'
        '何かお手伝いできることはありますか？　選択されたゴールについて、AIがサポートします。</div>',
        unsafe_allow_html=True,
    )

    # 2×2 mode buttons (Pokemon layout)
    mode_order = [("wallhit", "criteria"), ("breakdown", "action")]
    for row_keys in mode_order:
        cols = st.columns(2)
        for col, mk in zip(cols, row_keys):
            with col:
                if st.button(MODE_CONFIG[mk]["label"], use_container_width=True, key=f"mode_{mk}"):
                    auto_msg = MODE_CONFIG[mk]["auto_msg"].format(g=goal_name)
                    st.session_state.messages = [{"role": "user", "content": auto_msg}]
                    st.session_state.current_mode = mk
                    st.session_state.waiting_response = True
                    st.rerun()

    # AI call (runs on the rerun after a mode button is pressed)
    if st.session_state.waiting_response and st.session_state.current_mode:
        with st.spinner("みきゅんが考えています..."):
            text, is_fb = call_mikyun(
                st.session_state.current_mode, st.session_state.messages, goal_name
            )
        st.session_state.messages.append({
            "role": "assistant",
            "content": text,
            "fallback": is_fb,
            "mode": st.session_state.current_mode,
        })
        st.session_state.waiting_response = False

    # Chat display
    if st.session_state.messages:
        st.markdown('<hr style="border:none;border-top:1px solid #111;margin:18px 0;">', unsafe_allow_html=True)

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(
                    f'<div style="background:#0a0a0a;border:1px solid #161616;padding:12px 16px;margin:8px 0;">'
                    f'<div style="font-size:.68rem;color:#333;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:5px;">YOU</div>'
                    f'<div style="color:#888;font-size:.9rem;">{msg["content"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            else:
                if msg.get("fallback"):
                    render_framework(msg["mode"])
                else:
                    content_html = msg["content"].replace("\n", "<br>")
                    st.markdown(
                        f'<div style="background:#050505;border-left:2px solid #fff;padding:16px 20px;margin:8px 0;">'
                        f'<div style="font-size:.68rem;color:#444;text-transform:uppercase;letter-spacing:1.5px;margin-bottom:8px;">みきゅん</div>'
                        f'<div style="color:#ddd;font-size:.92rem;line-height:1.8;">{content_html}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        # Follow-up input
        if st.session_state.current_mode and not st.session_state.waiting_response:
            with st.form("followup", clear_on_submit=True):
                user_in = st.text_area("続けて聞く", height=80,
                                       placeholder="質問や続きを入力...",
                                       label_visibility="collapsed")
                if st.form_submit_button("送信 →", type="primary") and user_in.strip():
                    st.session_state.messages.append({"role": "user", "content": user_in.strip()})
                    st.session_state.waiting_response = True
                    st.rerun()
