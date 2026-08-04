import datetime
import json
import os
import smtplib
from email.header import Header
from email.mime.text import MIMEText
import urllib.request
import urllib.parse
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 1. ページ基本設定 (スマホ＆PC最適化・モダンUI)
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
SDS_DIR = "sds_files"

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
    if not os.path.exists(CSV_FILE):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        cols = [
            "タブ名", "品名", "在庫数", "発注点", "単位", "更新日時",
            "保管場所", "安全区分", "SDSファイル", "ロット番号", "使用期限", "備考", "メッセージ"
        ]
        df = pd.DataFrame(
            [
                ["樹脂・原料", "POM 白 φ30×1000", 2, 3, "本", now, "棚A-1", "指定なし 📦", "", "LOT-001", "2026-12-31", "メイン使用材", "残わずか"],
                ["洗浄・化学品", "IPA (イソプロピルアルコール)", 1, 2, "缶", now, "危険物庫 B-1", "危険物 🔥", "", "CHM-992", "2024-05-01", "火気厳禁", "要発注"],
            ],
            columns=cols,
        )
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    df = pd.read_csv(CSV_FILE, encoding="utf-8").fillna("")

    # ★ 旧データから新データへの自動互換・列追加処理
    needs_save = False
    if "SDSファイル" not in df.columns:
        df["SDSファイル"] = ""
        needs_save = True
    if "ロット番号" not in df.columns:
        df["ロット番号"] = ""
        needs_save = True
    if "使用期限" not in df.columns:
        df["使用期限"] = ""
        needs_save = True

    if needs_save:
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


# 使用期限の判定ロジック
def check_expiry(date_str):
    if not str(date_str).strip():
        return "✅ 登録なし"
    try:
        expiry_date = datetime.datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        today = datetime.date.today()
        days_left = (expiry_date - today).days
        if days_left < 0:
            return "❌ 期限切れ"
        elif days_left <= 30:
            return f"⚠️ 間近({days_left}日)"
        else:
            return "✅ 有効"
    except ValueError:
        return "❓ 日付エラー"


df = load_data()

# 各行に期限ステータスを計算
df["期限状態"] = df["使用期限"].apply(check_expiry)

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

# 期限切れ・期限間近の集計
expired_items = len(df[df["期限状態"] == "❌ 期限切れ"])
near_expiry_items = len(df[df["期限状態"].str.contains("⚠️", na=False)])

# サマリーカードのデザイン
c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 登録品目数", f"{total_items} 件")
c2.metric("⚠️ 要発注・補充", f"{low_stock + out_of_stock} 件")
c3.metric("❌ 在庫切れ", f"{out_of_stock} 件")
c4.metric("📅 期限切れ/間近", f"{expired_items + near_expiry_items} 件")

st.markdown("---")

# ---------------------------------------------------------
# 4. サイドバー (発注リスト・検索・通知・ログ)
# ---------------------------------------------------------
st.sidebar.header("🛒 発注用リスト自動抽出")
if len(low_stock_df) > 0:
    st.sidebar.warning(f"現在 **{len(low_stock_df)} 件** が発注点以下です！")
    order_csv = low_stock_df[
        ["タブ名", "品名", "ロット番号", "在庫数", "発注点", "単位", "保管場所", "備考"]
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
    "検索キーワード", placeholder="品名・ロット番号・場所..."
)
status_filter = st.sidebar.radio(
    "状態絞り込み", ["すべて", "⚠️ 要発注のみ", "📅 期限切れ/間近", "📄 添付ファイルあり"]
)

st.sidebar.markdown("---")
st.sidebar.header("📢 アラート一括通知")

# 在庫不足 または 期限警告がある場合
alert_df = df[(df["在庫数"] <= df["発注点"]) | (df["期限状態"].str.contains("❌|⚠️", regex=True))]
if len(alert_df) > 0:
    notify_method = st.sidebar.radio(
        "通知方法を選択", ["Google Chatスペースへ通知", "Gmail一括送信"]
    )

    if notify_method == "Google Chatスペースへ通知":
        saved_url = load_webhook_url()
        webhook_url = st.sidebar.text_input(
            "Google Chat Webhook URL",
            value=saved_url,
            type="password",
        )
        if webhook_url.strip() != saved_url:
            save_webhook_url(webhook_url.strip())

        if st.sidebar.button("🔔 アラートを一括通知"):
            if webhook_url.strip():
                save_webhook_url(webhook_url.strip())
                msg_lines = ["⚠️ **【原料・薬品アラート通知】**", ""]
                for _, r in alert_df.iterrows():
                    msg_lines.append(
                        f"・[{r['タブ名']}] {r['品名']} | 在庫:{r['在庫数']}{r['単位']} | 期限:{r['期限状態']}"
                    )
                msg_lines.append("\n状況の確認および対応をお願いします！")
                full_msg = "\n".join(msg_lines)

                ok, res_msg = send_google_chat_notification(webhook_url.strip(), full_msg)
                if ok:
                    st.sidebar.success(res_msg)
                    add_log("システム", "一括通知", "GoogleChat送信")
                else:
                    st.sidebar.error(res_msg)
            else:
                st.sidebar.error("Webhook URLを入力してください。")

    elif notify_method == "Gmail一括送信":
        sender_email = st.sidebar.text_input("送信元Gmailアドレス")
        app_password = st.sidebar.text_input("アプリパスワード", type="password")
        target_emails = st.sidebar.text_area("宛先アドレス (カンマ区切り)")

        if st.sidebar.button("📧 メールを一括送信"):
            if sender_email and app_password and target_emails:
                emails_list = [e.strip() for e in target_emails.split(",") if e.strip()]
                body_lines = ["【原料・薬品アラート通知】", "以下の品目に在庫不足または期限警告があります。", ""]
                for _, r in alert_df.iterrows():
                    body_lines.append(f"・[{r['タブ名']}] {r['品名']} | 在庫:{r['在庫数']}{r['単位']} | 期限:{r['期限状態']}")
                body_lines.append("\n至急対応をお願いします。")
                
                ok, res_msg = send_email_notification(
                    sender_email, app_password, emails_list, "【要対応】原料・薬品アラート", "\n".join(body_lines)
                )
                if ok:
                    st.sidebar.success(res_msg)
                    add_log("システム", "一括通知", "メール送信")
                else:
                    st.sidebar.error(res_msg)

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
            [[new_cat, "サンプル原料", 1, 1, "個", now, "", "指定なし 📦", "", "LOT-000", "", "", "初期アイテム"]],
            columns=df.columns[:-1], # 期限状態列を除外して追加
        )
        df = pd.concat([df.drop(columns=["期限状態"]), new_row], ignore_index=True)
        save_data(df)
        st.sidebar.success(f"「{new_cat}」を追加しました！")
        st.rerun()

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
            cat_df["添付"] = cat_df.apply(get_has_file, axis=1)

        filtered_df = cat_df.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["品名"].astype(str).str.contains(search_query, case=False)
                | filtered_df["ロット番号"].astype(str).str.contains(search_query, case=False)
                | filtered_df["保管場所"].astype(str).str.contains(search_query, case=False)
            ]

        if status_filter == "⚠️ 要発注のみ":
            filtered_df = filtered_df[filtered_df["ステータス"] == "⚠️ 要発注"]
        elif status_filter == "📅 期限切れ/間近":
            filtered_df = filtered_df[filtered_df["期限状態"].str.contains("❌|⚠️", regex=True)]
        elif status_filter == "📄 添付ファイルあり":
            filtered_df = filtered_df[filtered_df["添付"] == "📄 あり"]

        st.subheader(f"「{cat}」の一覧")
        st.caption("👇 表のチェックボックスまたは行を選択すると、下の操作対象が自動変更されます")

        display_df = (filtered_df if not filtered_df.empty else cat_df).reset_index(drop=True)

        show_cols = [
            "品名", "ロット番号", "在庫数", "単位", "期限状態", 
            "ステータス", "添付", "安全区分", "保管場所", "備考", "更新日時"
        ]

        item_list = list(cat_df["品名"].unique())
        select_key = f"select_box_{cat}"

        if select_key not in st.session_state and item_list:
            st.session_state[select_key] = item_list[0]

        # ★ Streamlitの最新UIを使ったモダンなテーブル描画 (在庫数をプログレスバー化)
        event = st.dataframe(
            display_df[show_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key=f"df_table_{cat}",
            column_config={
                "在庫数": st.column_config.ProgressColumn(
                    "在庫数", format="%d", min_value=0, max_value=20
                ),
                "期限状態": st.column_config.TextColumn("期限状態"),
            }
        )

        selected_rows = event.selection.rows if event and hasattr(event, "selection") else []
        if selected_rows:
            clicked_idx = selected_rows[0]
            if clicked_idx < len(display_df):
                clicked_item = display_df.iloc[clicked_idx]["品名"]
                if clicked_item in item_list:
                    st.session_state[select_key] = clicked_item

        st.markdown("---")

        if item_list:
            if st.session_state[select_key] not in item_list:
                st.session_state[select_key] = item_list[0]

            selected_item = st.selectbox(
                "🎯 操作対象の品目（表の選択で即自動切り替え）",
                item_list,
                key=select_key,
            )

            curr_row = cat_df[cat_df["品名"] == selected_item].iloc[0]
            sds_path = str(curr_row["SDSファイル"]).strip()

            # ★ 操作パネルを3つの「タブ」に分割してスッキリ整理！
            op_tab1, op_tab2, op_tab3 = st.tabs(["⚡ 入出庫クイック操作", "✏️ 情報・ファイル編集", "📱 QRコード表示・詳細"])

            # ----------------------------------------------------
            # タブ1: 入出庫操作
            # ----------------------------------------------------
            with op_tab1:
                st.markdown(f"**現在の在庫:** `{curr_row['在庫数']} {curr_row['単位']}` / **ロット:** `{curr_row['ロット番号']}`")
                
                col_a, col_b, col_c = st.columns(3)
                if col_a.button("➕ 1つ補充", key=f"add_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        df.loc[idx, "在庫数"] += 1
                        df.loc[idx, "更新日時"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_data(df.drop(columns=["期限状態"], errors='ignore'))
                        st.toast(f"「{selected_item}」を1つ補充しました！")
                        st.rerun()

                if col_b.button("➖ 1つ使用", key=f"use_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        if df.loc[idx[0], "在庫数"] > 0:
                            df.loc[idx, "在庫数"] -= 1
                            df.loc[idx, "更新日時"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            save_data(df.drop(columns=["期限状態"], errors='ignore'))
                            st.toast(f"「{selected_item}」を1つ使用しました！")
                            st.rerun()
                        else:
                            st.error("在庫数が0のため減らせません。")

                if col_c.button("🗑️ 品目を削除", key=f"del_{cat}", use_container_width=True):
                    df = df[~((df["タブ名"] == cat) & (df["品名"] == selected_item))]
                    save_data(df.drop(columns=["期限状態"], errors='ignore'))
                    st.warning(f"「{selected_item}」を削除しました。")
                    st.rerun()

            # ----------------------------------------------------
            # タブ2: 情報編集・添付ファイル
            # ----------------------------------------------------
            with op_tab2:
                with st.form(f"edit_form_{cat}_{selected_item}"):
                    e_name = st.text_input("品名", value=curr_row["品名"])

                    ec1, ec2, ec3 = st.columns(3)
                    e_qty = ec1.number_input("在庫数", min_value=0, value=int(curr_row["在庫数"]), step=1)
                    e_min = ec2.number_input("発注点", min_value=0, value=int(curr_row["発注点"] if curr_row["発注点"] != "" else 2), step=1)
                    e_unit = ec3.text_input("単位", value=curr_row["単位"])

                    ec4, ec5 = st.columns(2)
                    e_lot = ec4.text_input("ロット番号", value=curr_row["ロット番号"], placeholder="LOT-XXXX")
                    e_exp = ec5.date_input(
                        "使用期限 (空欄可)", 
                        value=datetime.datetime.strptime(curr_row["使用期限"], "%Y-%m-%d").date() if curr_row["使用期限"] else None,
                    )

                    e_safe = st.selectbox("安全区分タグ", SAFETY_CATEGORIES, index=(SAFETY_CATEGORIES.index(curr_row["安全区分"]) if curr_row["安全区分"] in SAFETY_CATEGORIES else 0))

                    st.markdown("**📄 SDS・添付ファイルの更新**")
                    if sds_path and os.path.exists(sds_path):
                        st.caption(f"現在の添付ファイル: `{os.path.basename(sds_path)}`")
                    uploaded_sds = st.file_uploader(
                        "新しい添付ファイルを選択 (上書きされます)", type=["pdf", "png", "jpg", "jpeg", "xlsx"], key=f"file_edit_{selected_item}"
                    )

                    e_loc = st.text_input("保管場所", value=curr_row["保管場所"])
                    e_rem = st.text_input("備考", value=curr_row["備考"])

                    if st.form_submit_button("更新内容を確定・保存"):
                        idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                        if not idx.empty:
                            new_name_clean = e_name.strip()
                            other_items = df[(df["タブ名"] == cat) & (df.index != idx[0])]["品名"].values
                            if new_name_clean in other_items:
                                st.error("同名の品目がすでに存在します。")
                            else:
                                final_sds_path = sds_path
                                if uploaded_sds is not None:
                                    final_sds_path = save_sds_file(uploaded_sds, new_name_clean)

                                df.loc[idx[0], "品名"] = new_name_clean
                                df.loc[idx[0], "在庫数"] = int(e_qty)
                                df.loc[idx[0], "発注点"] = int(e_min)
                                df.loc[idx[0], "単位"] = e_unit.strip()
                                df.loc[idx[0], "ロット番号"] = e_lot.strip()
                                df.loc[idx[0], "使用期限"] = e_exp.strftime("%Y-%m-%d") if e_exp else ""
                                df.loc[idx[0], "安全区分"] = e_safe
                                df.loc[idx[0], "SDSファイル"] = final_sds_path
                                df.loc[idx[0], "保管場所"] = e_loc.strip()
                                df.loc[idx[0], "備考"] = e_rem.strip()
                                df.loc[idx[0], "更新日時"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

                                save_data(df.drop(columns=["期限状態"], errors='ignore'))
                                st.session_state[select_key] = new_name_clean
                                st.success(f"「{new_name_clean}」の情報を更新しました！")
                                st.rerun()

            # ----------------------------------------------------
            # タブ3: QRコード & 詳細確認
            # ----------------------------------------------------
            with op_tab3:
                sc1, sc2 = st.columns([1, 2])
                with sc1:
                    # 品名とロット番号を埋め込んだQRコードの自動生成
                    qr_data = f"品名:{selected_item}\nロット:{curr_row['ロット番号']}\n期限:{curr_row['使用期限']}"
                    qr_url = f"https://chart.googleapis.com/chart?chs=150x150&cht=qr&chl={urllib.parse.quote(qr_data)}"
                    st.image(qr_url, caption="棚ラベル用QRコード")
                
                with sc2:
                    st.markdown(f"**安全区分:** {curr_row['安全区分']}")
                    st.markdown(f"**使用期限:** {curr_row['期限状態']} ({curr_row['使用期限']})")
                    if sds_path and os.path.exists(sds_path):
                        with open(sds_path, "rb") as file:
                            st.download_button(
                                label=f"📄 添付ファイル（SDS）をダウンロード",
                                data=file, file_name=os.path.basename(sds_path), mime="application/octet-stream"
                            )
                    else:
                        st.info("※ 添付ファイルはありません。")


        # ➕ 新規品目追加フォーム
        st.markdown("---")
        with st.expander(f"➕ 「{cat}」に新しい原料・薬品を登録"):
            with st.form(f"add_item_form_{cat}"):
                f_name = st.text_input("品名 (例: イソプロピルアルコール)")
                fc1, fc2, fc3 = st.columns(3)
                f_qty = fc1.number_input("初期数量", min_value=0, value=1, step=1)
                f_min = fc2.number_input("発注点 (最小在庫)", min_value=0, value=2, step=1)
                f_unit = fc3.text_input("単位", value="個")
                
                fc4, fc5 = st.columns(2)
                f_lot = fc4.text_input("ロット番号", placeholder="LOT-XXXX")
                f_exp = fc5.date_input("使用期限 (空欄の場合は × ボタンで消去)", value=None)

                f_safe = st.selectbox("安全区分タグ", SAFETY_CATEGORIES)
                f_sds_file = st.file_uploader("📄 SDS・添付ファイル(PDF等)をアップロード", type=["pdf", "png", "jpg", "jpeg", "xlsx"])
                f_loc = st.text_input("保管場所 (例: 危険物倉庫 棚A-1)")
                f_rem = st.text_input("備考 (例: 火気厳禁)")

                if st.form_submit_button("新しく品目を登録"):
                    if f_name.strip():
                        if f_name.strip() in df[df["タブ名"] == cat]["品名"].values:
                            st.error("同名の品目がすでに存在します。")
                        else:
                            saved_path = ""
                            if f_sds_file is not None:
                                saved_path = save_sds_file(f_sds_file, f_name.strip())

                            new_row = pd.DataFrame(
                                [[
                                    cat, f_name.strip(), int(f_qty), int(f_min), f_unit, 
                                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), 
                                    f_loc.strip(), f_safe, saved_path, f_lot.strip(), 
                                    f_exp.strftime("%Y-%m-%d") if f_exp else "", f_rem.strip(), ""
                                ]],
                                columns=df.columns[:-1], # 期限状態列を除く
                            )
                            df = pd.concat([df.drop(columns=["期限状態"]), new_row], ignore_index=True)
                            save_data(df)
                            st.success(f"「{f_name.strip()}」を登録しました！")
                            st.rerun()
                    else:
                        st.error("品名を入力してください。")
