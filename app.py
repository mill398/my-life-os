import os
import json
import streamlit as st
from google import genai

# ── 設定 ──────────────────────────────────────────────────────────────────────
GOALS_FILE = "goals.json"
GEMINI_MODEL = "gemini-1.5-flash"

st.set_page_config(
    page_title="My Life OS — Addy",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Gemini クライアント ────────────────────────────────────────────────────────
@st.cache_resource
def get_gemini_client():
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        st.error("APIキーが設定されていません。Streamlit Cloud の Secrets か環境変数 `GEMINI_API_KEY` を設定してください。")
        st.stop()
    return genai.Client(api_key=api_key)

client = get_gemini_client()

# ── データ I/O ────────────────────────────────────────────────────────────────
def load_goals() -> dict:
    if not os.path.exists(GOALS_FILE):
        return {"goals": []}
    with open(GOALS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_goals(data: dict):
    with open(GOALS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def toggle_task_done(data: dict, task_id: str):
    def recurse(nodes):
        for node in nodes:
            if node.get("id") == task_id:
                node["done"] = not node.get("done", False)
                return True
            if recurse(node.get("children", [])):
                return True
        return False
    recurse(data["goals"])
    save_goals(data)

# ── スタイル ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
.goal-card  { background:#1e293b; border-radius:12px; padding:14px 18px; margin-bottom:8px; border-left:4px solid #6366f1; }
.mid-card   { background:#1e293b; border-radius:8px;  padding:10px 14px; margin:4px 0;      border-left:3px solid #06b6d4; }
.task-row   { padding:4px 0; }
.addy-bubble { background:#1e293b; border-radius:12px; padding:16px 20px; margin-top:12px; border-left:4px solid #10b981; }
h1, h2, h3 { color: #f1f5f9; }
</style>
""", unsafe_allow_html=True)

# ── サイドバー ────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧭 My Life OS")
    st.markdown("---")
    page = st.radio(
        "ナビゲーション",
        ["📊 目標ツリー", "💬 AI壁打ち", "🤖 Addyに相談"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    data = load_goals()
    total_tasks = sum(
        len(mid.get("children", []))
        for g in data["goals"]
        for mid in g.get("children", [])
    )
    done_tasks = sum(
        1
        for g in data["goals"]
        for mid in g.get("children", [])
        for t in mid.get("children", [])
        if t.get("done")
    )
    st.metric("完了タスク", f"{done_tasks} / {total_tasks}")

# ── ページ：目標ツリー ────────────────────────────────────────────────────────
if page == "📊 目標ツリー":
    st.title("📊 目標ツリー")
    st.caption("大目標 → 中期目標 → タスク の階層で管理します。")

    data = load_goals()
    if not data["goals"]:
        st.info("まだ目標がありません。「AI壁打ち」で目標を追加してみましょう！")
    else:
        for goal in data["goals"]:
            with st.expander(f"🎯  {goal['title']}", expanded=True):
                if goal.get("description"):
                    st.caption(goal["description"])
                for mid in goal.get("children", []):
                    st.markdown(f"<div class='mid-card'>", unsafe_allow_html=True)
                    st.markdown(f"**🔹 {mid['title']}**")
                    if mid.get("description"):
                        st.caption(mid["description"])
                    for task in mid.get("children", []):
                        col1, col2 = st.columns([0.05, 0.95])
                        with col1:
                            checked = st.checkbox(
                                "", value=task.get("done", False), key=task["id"]
                            )
                            if checked != task.get("done", False):
                                toggle_task_done(data, task["id"])
                                st.rerun()
                        with col2:
                            label = f"~~{task['title']}~~" if task.get("done") else task["title"]
                            st.markdown(label)
                    st.markdown("</div>", unsafe_allow_html=True)

# ── ページ：AI壁打ち ──────────────────────────────────────────────────────────
elif page == "💬 AI壁打ち":
    st.title("💬 AI壁打ち")
    st.caption("頭の中にあることを雑に書き出してください。Gemini が目標ツリーに整理します。")

    raw_input = st.text_area(
        "思考の垂れ流し・音声入力テキスト・やりたいこと など",
        height=200,
        placeholder="例：最近体がなまってる。仕事もうまくいってないし収入増やしたい。英語も勉強しなきゃ...",
    )

    mode = st.radio(
        "処理モード",
        ["🔁 既存ツリーに追加・統合", "🆕 ゼロからツリーを生成"],
        horizontal=True,
    )

    if st.button("✨ Gemini に整理してもらう", type="primary", disabled=not raw_input.strip()):
        data = load_goals()
        existing_json = json.dumps(data, ensure_ascii=False, indent=2)

        if "統合" in mode:
            prompt = f"""あなたは目標設計の専門家です。
ユーザーの雑な思考テキストを分析し、既存の目標ツリーに**追加・統合**してください。

## 既存の目標ツリー（JSON）
{existing_json}

## ユーザーの入力テキスト
{raw_input}

## 出力ルール
- 必ず以下の JSON スキーマに従った完全な goals.json を返してください。
- 既存のゴールと重複する場合はマージし、新しいものは追加してください。
- id は "goal_<uuid4前8文字>" "mid_<uuid4前8文字>" "task_<uuid4前8文字>" の形式で採番。
- done フィールドは必ず false で初期化。
- JSON のみを返し、説明文は一切含めないこと。

## スキーマ
{{
  "goals": [
    {{
      "id": "goal_xxxx",
      "title": "大目標のタイトル",
      "description": "大目標の説明（1〜2文）",
      "status": "active",
      "children": [
        {{
          "id": "mid_xxxx",
          "title": "中期目標のタイトル",
          "description": "中期目標の説明（1〜2文）",
          "status": "active",
          "children": [
            {{
              "id": "task_xxxx",
              "title": "具体的なタスク（行動ベース）",
              "status": "pending",
              "done": false
            }}
          ]
        }}
      ]
    }}
  ]
}}"""
        else:
            prompt = f"""あなたは目標設計の専門家です。
ユーザーの雑な思考テキストを分析し、**ゼロから**目標ツリーを設計してください。

## ユーザーの入力テキスト
{raw_input}

## 出力ルール
- 必ず以下の JSON スキーマに従った完全な goals.json を返してください。
- id は "goal_<uuid4前8文字>" "mid_<uuid4前8文字>" "task_<uuid4前8文字>" の形式で採番。
- done フィールドは必ず false で初期化。
- JSON のみを返し、説明文は一切含めないこと。

## スキーマ
{{
  "goals": [
    {{
      "id": "goal_xxxx",
      "title": "大目標のタイトル",
      "description": "大目標の説明（1〜2文）",
      "status": "active",
      "children": [
        {{
          "id": "mid_xxxx",
          "title": "中期目標のタイトル",
          "description": "中期目標の説明（1〜2文）",
          "status": "active",
          "children": [
            {{
              "id": "task_xxxx",
              "title": "具体的なタスク（行動ベース）",
              "status": "pending",
              "done": false
            }}
          ]
        }}
      ]
    }}
  ]
}}"""

        with st.spinner("Gemini が思考を整理中..."):
            try:
                response = client.models.generate_content(
                    model=GEMINI_MODEL,
                    contents=prompt,
                )
                raw_json = response.text.strip()
                # コードブロック除去
                if "```" in raw_json:
                    raw_json = raw_json.split("```")[1]
                    if raw_json.startswith("json"):
                        raw_json = raw_json[4:]
                # 先頭の { まで、末尾の } 以降を削ぎ落とす
                start = raw_json.find("{")
                end = raw_json.rfind("}") + 1
                if start != -1 and end > start:
                    raw_json = raw_json[start:end]
                new_data = json.loads(raw_json)
                save_goals(new_data)
                st.success("✅ 目標ツリーを更新しました！「目標ツリー」タブで確認できます。")
                st.json(new_data)
            except json.JSONDecodeError as e:
                st.error(f"JSONのパースに失敗しました: {e}")
                st.code(raw_json, language="json")
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")

# ── ページ：Addyに相談 ────────────────────────────────────────────────────────
elif page == "🤖 Addyに相談":
    st.title("🤖 Addyに相談")
    st.caption("Addy（AI）が今のあなたの状態から、今日やるべき3つを選んでくれます。")

    col1, col2 = st.columns([1, 1])
    with col1:
        context_input = st.text_area(
            "今日の状況・気分・制約（任意）",
            height=120,
            placeholder="例：今日は2時間しか時間がない。気分はまあまあ。集中できそう。",
        )

    with col2:
        st.markdown("#### 🎯 Addyからの提案")
        placeholder = st.empty()

    if st.button("📋 今日のToDoを選んでもらう", type="primary"):
        data = load_goals()
        tree_json = json.dumps(data, ensure_ascii=False, indent=2)

        prompt = f"""あなたは「Addy」という名の、ユーザーの行動を支援するAIコーチです。
温かみがあり、的確なアドバイスをするキャラクターです。

ユーザーの目標ツリーを分析し、**今日やるべき具体的なタスクを3つ**提案してください。

## 目標ツリー
{tree_json}

## 今日のユーザーの状況
{context_input if context_input.strip() else "（特に指定なし）"}

## 出力フォーマット（厳守）
以下のフォーマットで、Markdownで出力してください。

---
### 🌟 今日のAddy's Pick

**① [タスク名]**
> 選んだ理由：〇〇だから、今日これをやることで〇〇につながります。

**② [タスク名]**
> 選んだ理由：〇〇だから、今日これをやることで〇〇につながります。

**③ [タスク名]**
> 選んだ理由：〇〇だから、今日これをやることで〇〇につながります。

---
💬 **Addyより一言**：
[ユーザーへの励ましや今日のポイントを1〜2文で]
"""

        with placeholder:
            with st.spinner("Addy が考え中..."):
                try:
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt,
                    )
                    st.markdown(
                        f"<div class='addy-bubble'>{response.text}</div>",
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
