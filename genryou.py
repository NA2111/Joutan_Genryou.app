import datetime
import json
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText
import urllib.request
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 1. ページ基本設定 (スマホ＆PC最適化)
# ---------------------------------------------------------
st.set_page_config(
    page_title="SDS・素材原料管理PRO",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 保存用ファイル・フォルダ設定
CSV_FILE = "sds_inventory_tabs.csv"
LOG_FILE = "sds_inventory_log.csv"
MSG_FILE = "sds_global_message.txt"
WEBHOOK_FILE = "sds_webhook_url.txt"
SDS_DIR = "sds_files"  # 添付ファイルの保存フォルダ

# 添付ファイル用フォルダの自動生成
os.makedirs(SDS_DIR, exist_ok=True)

SAFETY_CATEGORIES = [
    "指定なし 📦",
    "危険物 🔥",
    "劇物・毒物 ⚠️",
    "高圧ガス 💥",
    "要冷蔵 ❄️",
]


# ---------------------------------------------------------
# 2. 設定・データ処理関数
# ---------------------------------------------------------
def save_sds_file(uploaded_file, item_name):
    """アップロードされた添付ファイルを保存してパスを返す"""
    if uploaded_file is None:
        return ""
    ext = os.path.splitext(uploaded_file.name)[1]
    safe_name = f"{item_name}_SDS{ext}"
    file_path = os.path.join(SDS_DIR, safe_name)

    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return file_path


def load_webhook_url():
    if os.path.exists(WEBHOOK_FILE):
        with open(WEBHOOK_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return ""


def save_webhook_url(url):
    with open(WEBHOOK_FILE, "w", encoding="utf-8") as f:
        f.write(url.strip())


def send_google_chat_notification(webhook_url, message_text):
    payload = {"text": message_text}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url, data=data, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req) as response:
            return True, "Google Chatへ通知を送信しました！"
    except Exception as e:
        return False, f"送信失敗: {e}"


def send_email_notification(
    smtp_user, smtp_password, to_emails, subject, body
):
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = smtp_user
        msg["To"] = ", ".join(to_emails)

        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, to_emails, msg.as_string())
        server.close()
        return True, "一括メールを送信しました！"
    except Exception as e:
        return False, f"メール送信失敗: {e}"


def load_data():
    cols = [
        "タブ名",
        "品名",
        "在庫数",
        "発注点",
        "単位",
        "更新日時",
        "保管場所",
        "安全区分",
        "SDSファイル",
        "備考",
        "メッセージ",
    ]
    if not os.path.exists(CSV_FILE):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        df = pd.DataFrame(
            [
                [
                    "樹脂・原料",
                    "POM 白 φ30×1000",
                    2,
                    3,
                    "本",
                    now,
                    "棚A-1",
                    "指定なし 📦",
                    "",
                    "メイン使用材",
                    "残わずか",
                ],
                [
                    "洗浄・化学品",
                    "IPA (イソプロピルアルコール)",
                    1,
                    2,
                    "缶",
                    now,
                    "危険物庫 B-1",
                    "危険物 🔥",
                    "",
                    "火気厳禁",
                    "要発注",
                ],
            ],
            columns=cols,
        )
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    df = pd.read_csv(CSV_FILE, encoding="utf-8").fillna("")

    if "SDSファイル" not in df.columns:
        df["SDSファイル"] = ""
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    return df


def save_data(df):
    df.to_csv(CSV_FILE, index=False, encoding="utf-8")


def add_log(category, item_name, action, detail=""):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = pd.DataFrame(
        [[now, category, item_name, action, detail]],
        columns=["日時", "カテゴリ", "品名", "操作内容", "詳細"],
    )
    if not os.path.exists(LOG_FILE):
        log_entry.to_csv(LOG_FILE, index=False, encoding="utf-8")
    else:
        log_entry.to_csv(
            LOG_FILE, mode="a", header=False, index=False, encoding="utf-8"
        )


def load_global_message():
    if os.path.exists(MSG_FILE):
        with open(MSG_FILE, "r", encoding="utf-8") as f:
            return f.read()
    return "SDS・安全管理：取扱時は保護具を着用してください。"


def save_global_message(msg):
    with open(MSG_FILE, "w", encoding="utf-8") as f:
        f.write(msg)


df = load_data()

# ---------------------------------------------------------
# 3. メインヘッダー ＆ サマリーダッシュボード
# ---------------------------------------------------------
st.title("🧪 SDS・素材原料管理PRO")

global_msg = load_global_message()
if global_msg.strip():
    st.info(f"📢 **全体連絡メモ**: {global_msg}")

total_items = len(df[df["品名"] != ""])
low_stock_df = df[(df["在庫数"] <= df["発注点"]) & (df["品名"] != "")]
low_stock = len(low_stock_df[low_stock_df["在庫数"] > 0])
out_of_stock = len(df[df["在庫数"] == 0])

c1, c2, c3 = st.columns(3)
c1.metric("📦 全品目数", f"{total_items} 件")
c2.metric("⚠️ 要発注・補充", f"{low_stock + out_of_stock} 件")
c3.metric("❌ 在庫切れ", f"{out_of_stock} 件")

st.markdown("---")

# ---------------------------------------------------------
# 4. サイドバー (発注リスト・検索・通知・ログ)
# ---------------------------------------------------------
st.sidebar.header("🛒 発注用リスト自動抽出")
if len(low_stock_df) > 0:
    st.sidebar.warning(f"現在 **{len(low_stock_df)} 件** が発注点以下です！")
    order_csv = low_stock_df[
        [
            "タブ名",
            "品名",
            "在庫数",
            "発注点",
            "単位",
            "保管場所",
            "備考",
            "メッセージ",
        ]
    ].to_csv(index=False, encoding="shift-jis", errors="replace")
    st.sidebar.download_button(
        label="📄 発注依頼用CSVを出力",
        data=order_csv,
        file_name=f"発注依頼書_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )
else:
    st.sidebar.success("現在、発注が必要な品目はありません。")

st.sidebar.markdown("---")
st.sidebar.header("🔍 検索 & フィルター")
search_query = st.sidebar.text_input(
    "検索キーワード", placeholder="品名・保管場所・安全区分・メモ..."
)
status_filter = st.sidebar.radio(
    "状態絞り込み", ["すべて", "⚠️ 要発注のみ", "📄 添付ファイルあり"]
)

st.sidebar.markdown("---")
st.sidebar.header("📢 補充・発注リクエスト一括通知")

if len(low_stock_df) > 0:
    notify_method = st.sidebar.radio(
        "通知方法を選択", ["Google Chatスペースへ通知", "Gmail一括送信"]
    )

    if notify_method == "Google Chatスペースへ通知":
        saved_url = load_webhook_url()
        webhook_url = st.sidebar.text_input(
            "Google Chat Webhook URL",
            value=saved_url,
            type="password",
            help="一度入力すると自動保存されます",
        )
        if webhook_url.strip() != saved_url:
            save_webhook_url(webhook_url.strip())

        if st.sidebar.button("🔔 Google Chatへ一括通知"):
            if webhook_url.strip():
                save_webhook_url(webhook_url.strip())
                msg_lines = ["⚠️ **【素材・原料 補充リクエスト】**", ""]
                for _, r in low_stock_df.iterrows():
                    msg_lines.append(
                        f"・[{r['タブ名']}] {r['品名']} ({r['安全区分']}): 在庫"
                        f" {r['在庫数']} {r['単位']} (発注点: {r['発注点']})"
                    )
                msg_lines.append("\n発注または補充の対応をお願いします！")
                full_msg = "\n".join(msg_lines)

                ok, res_msg = send_google_chat_notification(
                    webhook_url.strip(), full_msg
                )
                if ok:
                    st.sidebar.success(res_msg)
                    add_log(
                        "システム",
                        "一括通知",
                        "GoogleChat送信",
                        f"{len(low_stock_df)}件",
                    )
                else:
                    st.sidebar.error(res_msg)
            else:
                st.sidebar.error("Webhook URLを入力してください。")

    elif notify_method == "Gmail一括送信":
        sender_email = st.sidebar.text_input("送信元Gmailアドレス")
        app_password = st.sidebar.text_input("アプリパスワード", type="password")
        target_emails = st.sidebar.text_area(
            "宛先アドレス (カンマ区切り)",
            placeholder="a@gmail.com, b@gmail.com",
        )

        if st.sidebar.button("📧 メールを一括送信"):
            if sender_email and app_password and target_emails:
                emails_list = [
                    e.strip() for e in target_emails.split(",") if e.strip()
                ]
                body_lines = [
                    "【素材・原料 補充リクエストアラート】",
                    "以下の品目が発注点以下になっています。",
                    "",
                ]
                for _, r in low_stock_df.iterrows():
                    body_lines.append(
                        f"・[{r['タブ名']}] {r['品名']}: 残り {r['在庫数']} {r['単位']} (発注点:"
                        f" {r['発注点']})"
                    )
                body_lines.append("\n至急対応をお願いします。")
                full_body = "\n".join(body_lines)

                ok, res_msg = send_email_notification(
                    sender_email,
                    app_password,
                    emails_list,
                    "【要対応】素材・SDS管理 補充発注リクエスト",
                    full_body,
                )
                if ok:
                    st.sidebar.success(res_msg)
                    add_log(
                        "システム",
                        "一括通知",
                        "メール送信",
                        f"{len(low_stock_df)}件",
                    )
                else:
                    st.sidebar.error(res_msg)
            else:
                st.sidebar.error("すべての項目を入力してください。")

st.sidebar.markdown("---")
st.sidebar.header("📝 全体連絡メモ編集")
new_g_msg = st.sidebar.text_area("掲示板メモ", value=global_msg, height=80)
if st.sidebar.button("掲示板メモを更新"):
    save_global_message(new_g_msg)
    st.sidebar.success("全体メモを更新しました！")
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🏷️ カテゴリ管理")
new_cat = st.sidebar.text_input("新しいカテゴリ名")
if st.sidebar.button("＋ カテゴリ追加"):
    if new_cat and new_cat not in df["タブ名"].unique():
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        new_row = pd.DataFrame(
            [
                [
                    new_cat,
                    "サンプル素材",
                    1,
                    1,
                    "個",
                    now,
                    "",
                    "指定なし 📦",
                    "",
                    "",
                    "初期アイテム",
                ]
            ],
            columns=df.columns,
        )
        df = pd.concat([df, new_row], ignore_index=True)
        save_data(df)
        add_log(new_cat, "サンプル素材", "カテゴリ作成")
        st.sidebar.success(f"「{new_cat}」を追加しました！")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📋 操作ログ & 全データ出力")
if st.sidebar.checkbox("操作ログを表示"):
    if os.path.exists(LOG_FILE):
        log_df = pd.read_csv(LOG_FILE, encoding="utf-8")
        st.sidebar.dataframe(log_df.tail(20), use_container_width=True)

csv_data = df.to_csv(index=False, encoding="shift-jis", errors="replace")
st.sidebar.download_button(
    label="📊 全データCSV出力 (Excel用)",
    data=csv_data,
    file_name=f"sds_inventory_{datetime.datetime.now().strftime('%Y%m%d')}.csv",
    mime="text/csv",
)

# ---------------------------------------------------------
# 5. メインコンテンツ (カテゴリ別タブ表示)
# ---------------------------------------------------------
categories = list(df["タブ名"].unique())
if not categories:
    categories = ["基本カテゴリ"]

tabs = st.tabs([f"📁 {cat}" for cat in categories])

for i, cat in enumerate(categories):
    with tabs[i]:
        cat_df = df[df["タブ名"] == cat].copy()

        def get_status(row):
            if row["在庫数"] == 0:
                return "❌ 在庫切れ"
            elif row["在庫数"] <= row["発注点"]:
                return "⚠️ 要発注"
            else:
                return "✅ 良好"

        def get_has_file(row):
            path = str(row["SDSファイル"]).strip()
            return "📄 あり" if path and os.path.exists(path) else "-"

        if not cat_df.empty:
            cat_df["ステータス"] = cat_df.apply(get_status, axis=1)
            cat_df["添付ファイル"] = cat_df.apply(get_has_file, axis=1)

        filtered_df = cat_df.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["品名"]
                .astype(str)
                .str.contains(search_query, case=False)
                | filtered_df["保管場所"]
                .astype(str)
                .str.contains(search_query, case=False)
                | filtered_df["安全区分"]
                .astype(str)
                .str.contains(search_query, case=False)
                | filtered_df["備考"]
                .astype(str)
                .str.contains(search_query, case=False)
                | filtered_df["メッセージ"]
                .astype(str)
                .str.contains(search_query, case=False)
            ]

        if status_filter == "⚠️ 要発注のみ":
            filtered_df = filtered_df[filtered_df["ステータス"] == "⚠️ 要発注"]
        elif status_filter == "📄 添付ファイルあり":
            filtered_df = filtered_df[filtered_df["添付ファイル"] == "📄 あり"]

        st.subheader(f"「{cat}」の一覧")
        st.caption("👇 表のチェックボックスまたは行を選択すると、下の操作対象が自動変更されます")

        display_df = (
            filtered_df if not filtered_df.empty else cat_df
        ).reset_index(drop=True)

        show_cols = [
            "品名",
            "在庫数",
            "発注点",
            "単位",
            "添付ファイル",
            "安全区分",
            "保管場所",
            "備考",
            "メッセージ",
            "ステータス",
            "更新日時",
        ]

        item_list = list(cat_df["品名"].unique())
        select_key = f"select_box_{cat}"

        # 初期値セット
        if select_key not in st.session_state and item_list:
            st.session_state[select_key] = item_list[0]

        # 行選択機能つきテーブル描画
        event = st.dataframe(
            display_df[show_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"df_table_{cat}",
        )

        # ★ テーブルの選択状態を直接下のセレクトボックスキーに連動反映させる処理
        selected_rows = (
            event.selection.rows
            if event and hasattr(event, "selection")
            else []
        )
        if selected_rows:
            clicked_idx = selected_rows[0]
            if clicked_idx < len(display_df):
                clicked_item = display_df.iloc[clicked_idx]["品名"]
                if clicked_item in item_list:
                    st.session_state[select_key] = clicked_item

        st.markdown("---")
        st.markdown("### ⚡ 現場クイック操作・SDS閲覧・編集")

        if item_list:
            # 万が一現在の選択状態が一覧にない場合の補正
            if st.session_state[select_key] not in item_list:
                st.session_state[select_key] = item_list[0]

            # 選択メニュー（表のクリックと完全同期）
            selected_item = st.selectbox(
                "操作または編集する品目（表の選択で即自動切り替え）",
                item_list,
                key=select_key,
            )

            curr_row = cat_df[cat_df["品名"] == selected_item].iloc[0]
            sds_path = str(curr_row["SDSファイル"]).strip()

            # 添付ファイル（SDS）開く・ダウンロードボタン
            if sds_path and os.path.exists(sds_path):
                with open(sds_path, "rb") as file:
                    st.download_button(
                        label=(
                            f"📄 「{selected_item}」の 添付ファイル（SDS）を開く・ダウンロード"
                        ),
                        data=file,
                        file_name=os.path.basename(sds_path),
                        mime="application/octet-stream",
                        use_container_width=True,
                    )
            else:
                st.caption(
                    "※この品目にはSDS等の添付ファイルがまだ登録されていません。下の編集フォームから添付できます。"
                )

            st.write("")

            col_a, col_b, col_c = st.columns(3)

            if col_a.button(
                "➕ 1つ補充", key=f"add_{cat}", use_container_width=True
            ):
                idx = df[
                    (df["タブ名"] == cat) & (df["品名"] == selected_item)
                ].index
                if not idx.empty:
                    df.loc[idx, "在庫数"] += 1
                    df.loc[idx, "更新日時"] = datetime.datetime.now().strftime(
                        "%Y-%m-%d %H:%M"
                    )
                    save_data(df)
                    add_log(
                        cat,
                        selected_item,
                        "補充(+1)",
                        f"変更後: {df.loc[idx[0], '在庫数']}",
                    )
                    st.toast(f"「{selected_item}」を1つ補充しました！")
                    st.rerun()

            if col_b.button(
                "➖ 1つ使用", key=f"use_{cat}", use_container_width=True
            ):
                idx = df[
                    (df["タブ名"] == cat) & (df["品名"] == selected_item)
                ].index
                if not idx.empty:
                    if df.loc[idx[0], "在庫数"] > 0:
                        df.loc[idx, "在庫数"] -= 1
                        df.loc[idx, "更新日時"] = (
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        )
                        save_data(df)
                        add_log(
                            cat,
                            selected_item,
                            "使用(-1)",
                            f"変更後: {df.loc[idx[0], '在庫数']}",
                        )
                        st.toast(f"「{selected_item}」を1つ使用しました！")
                        st.rerun()
                    else:
                        st.error("在庫数が0のため減らせません。")

            if col_c.button(
                "🗑️ 削除", key=f"del_{cat}", use_container_width=True
            ):
                df = df[~((df["タブ名"] == cat) & (df["品名"] == selected_item))]
                save_data(df)
                add_log(cat, selected_item, "品目削除")
                st.warning(f"「{selected_item}」を削除しました。")
                st.rerun()

            # ✏️ 編集フォーム
            with st.expander(
                f"✏️ 「{selected_item}」の品名・SDS添付ファイル・情報を編集"
            ):
                with st.form(f"edit_form_{cat}_{selected_item}"):
                    e_name = st.text_input("品名", value=curr_row["品名"])

                    ec1, ec2, ec3 = st.columns(3)
                    e_qty = ec1.number_input(
                        "在庫数",
                        min_value=0,
                        value=int(curr_row["在庫数"]),
                        step=1,
                    )
                    e_min = ec2.number_input(
                        "発注点 (最小在庫数)",
                        min_value=0,
                        value=int(
                            curr_row["発注点"] if curr_row["発注点"] != "" else 2
                        ),
                        step=1,
                    )
                    e_unit = ec3.text_input("単位", value=curr_row["単位"])

                    e_safe = st.selectbox(
                        "安全区分タグ",
                        SAFETY_CATEGORIES,
                        index=(
                            SAFETY_CATEGORIES.index(curr_row["安全区分"])
                            if curr_row["安全区分"] in SAFETY_CATEGORIES
                            else 0
                        ),
                    )

                    st.markdown("**📄 SDS・添付ファイルの登録**")
                    if sds_path and os.path.exists(sds_path):
                        st.caption(
                            f"現在の添付ファイル:"
                            f" `{os.path.basename(sds_path)}`"
                        )
                    uploaded_sds = st.file_uploader(
                        "新しい添付ファイル(PDF, 画像等)を選択",
                        type=["pdf", "png", "jpg", "jpeg", "xlsx", "docx"],
                        key=f"file_edit_{selected_item}",
                    )

                    e_loc = st.text_input("保管場所", value=curr_row["保管場所"])
                    e_rem = st.text_input("備考", value=curr_row["備考"])
                    e_msg = st.text_input(
                        "💬 メッセージ（連絡事項）",
                        value=curr_row["メッセージ"],
                        placeholder="例: ◯◯さん発注対応中など",
                    )

                    edit_submitted = st.form_submit_button(
                        "更新内容を確定・保存"
                    )
                    if edit_submitted:
                        idx = df[
                            (df["タブ名"] == cat) & (df["品名"] == selected_item)
                        ].index
                        if not idx.empty:
                            new_name_clean = e_name.strip()
                            other_items = df[
                                (df["タブ名"] == cat) & (df.index != idx[0])
                            ]["品名"].values
                            if new_name_clean in other_items:
                                st.error("同名の品目がすでに存在します。")
                            else:
                                now = datetime.datetime.now().strftime(
                                    "%Y-%m-%d %H:%M"
                                )

                                final_sds_path = sds_path
                                if uploaded_sds is not None:
                                    final_sds_path = save_sds_file(
                                        uploaded_sds, new_name_clean
                                    )

                                df.loc[idx[0], "品名"] = new_name_clean
                                df.loc[idx[0], "在庫数"] = int(e_qty)
                                df.loc[idx[0], "発注点"] = int(e_min)
                                df.loc[idx[0], "単位"] = e_unit.strip()
                                df.loc[idx[0], "安全区分"] = e_safe
                                df.loc[idx[0], "SDSファイル"] = final_sds_path
                                df.loc[idx[0], "保管場所"] = e_loc.strip()
                                df.loc[idx[0], "備考"] = e_rem.strip()
                                df.loc[idx[0], "メッセージ"] = e_msg.strip()
                                df.loc[idx[0], "更新日時"] = now

                                save_data(df)
                                add_log(
                                    cat,
                                    new_name_clean,
                                    "詳細編集",
                                    f"旧名:{selected_item} | 添付ファイル更新",
                                )
                                st.session_state[select_key] = new_name_clean
                                st.success(
                                    f"「{new_name_clean}」の情報を更新しました！"
                                )
                                st.rerun()

        # ➕ 新規品目追加フォーム
        with st.expander(f"➕ 「{cat}」に新しい品目を追加"):
            with st.form(f"add_item_form_{cat}"):
                f_name = st.text_input("品名 (例: イソプロピルアルコール)")
                fc1, fc2, fc3 = st.columns(3)
                f_qty = fc1.number_input(
                    "初期数量", min_value=0, value=1, step=1
                )
                f_min = fc2.number_input(
                    "発注点 (最小在庫)", min_value=0, value=2, step=1
                )
                f_unit = fc3.selectbox(
                    "単位",
                    [
                        "缶",
                        "本",
                        "枚",
                        "個",
                        "箱",
                        "セット",
                        "台",
                        "kg",
                        "L",
                        "パック",
                    ],
                )
                f_safe = st.selectbox("安全区分タグ", SAFETY_CATEGORIES)

                f_sds_file = st.file_uploader(
                    "📄 SDS・添付ファイル(PDF等)をアップロード",
                    type=["pdf", "png", "jpg", "jpeg", "xlsx", "docx"],
                    key=f"file_add_{cat}",
                )

                f_loc = st.text_input("保管場所 (例: 危険物倉庫 棚A-1)")
                f_rem = st.text_input("備考 (例: 火気厳禁)")
                f_msg = st.text_input("メッセージ", value="")

                submitted = st.form_submit_button("新しく品目を登録")
                if submitted:
                    if f_name.strip():
                        if (
                            f_name.strip()
                            in df[df["タブ名"] == cat]["品名"].values
                        ):
                            st.error("同名の品目がすでに存在します。")
                        else:
                            now = datetime.datetime.now().strftime(
                                "%Y-%m-%d %H:%M"
                            )
                            saved_path = ""
                            if f_sds_file is not None:
                                saved_path = save_sds_file(
                                    f_sds_file, f_name.strip()
                                )

                            new_row = pd.DataFrame(
                                [
                                    [
                                        cat,
                                        f_name.strip(),
                                        int(f_qty),
                                        int(f_min),
                                        f_unit,
                                        now,
                                        f_loc.strip(),
                                        f_safe,
                                        saved_path,
                                        f_rem.strip(),
                                        f_msg.strip(),
                                    ]
                                ],
                                columns=df.columns,
                            )
                            df = pd.concat([df, new_row], ignore_index=True)
                            save_data(df)
                            add_log(
                                cat,
                                f_name.strip(),
                                "新規追加",
                                f"初期在庫: {f_qty}{f_unit}",
                            )
                            st.success(f"「{f_name.strip()}」を登録しました！")
                            st.rerun()
                    else:
                        st.error("品名を入力してください。")
