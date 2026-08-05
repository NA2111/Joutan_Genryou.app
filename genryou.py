import datetime
import json
import os
import smtplib
import mimetypes
from email.header import Header
from email.mime.text import MIMEText
import urllib.request
import pandas as pd
import streamlit as st

# ---------------------------------------------------------
# 1. ページ基本設定 ＆ タイムゾーン設定 (日本時間 JST: UTC+9)
# ---------------------------------------------------------
st.set_page_config(
    page_title="SDS・素材原料管理PRO",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="collapsed",
)

JST = datetime.timezone(datetime.timedelta(hours=9))

def get_jst_now(fmt="%Y-%m-%d %H:%M"):
    """常に日本時間（JST）で現在日時を返す関数"""
    return datetime.datetime.now(JST).strftime(fmt)

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


def send_email_notification(smtp_user, smtp_password, to_emails, subject, body):
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
        now = get_jst_now()
        cols = [
            "タブ名", "品名", "在庫数", "発注点", "単位", "更新日時",
            "保管場所", "安全区分", "SDSファイル", "ロット番号", "使用期限", "検索タグ", "備考", "メッセージ",
            "入荷予定日", "入荷予定数"
        ]
        df = pd.DataFrame(
            [
                ["樹脂・原料", "POM 白 φ30×1000", 2, 3, "本", now, "棚A-1", "指定なし 📦", "", "LOT-001", "2026-12-31", "汎用樹脂, 試作", "メイン使用材", "残わずか", "", 0],
                ["洗浄・化学品", "IPA (イソプロピルアルコール)", 1, 2, "缶", now, "危険物庫 B-1", "危険物 🔥", "", "CHM-992", "2024-05-01", "洗浄用, 溶剤", "火気厳禁", "要発注", "", 0],
            ],
            columns=cols,
        )
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    df = pd.read_csv(CSV_FILE, encoding="utf-8").fillna("")

    needs_save = False
    for col, default_val in [
        ("SDSファイル", ""), ("ロット番号", ""), ("使用期限", ""), ("検索タグ", ""),
        ("入荷予定日", ""), ("入荷予定数", 0)
    ]:
        if col not in df.columns:
            df[col] = default_val
            needs_save = True

    if needs_save:
        df.to_csv(CSV_FILE, index=False, encoding="utf-8")

    return df


def save_data(df):
    drop_cols = ["期限状態", "ステータス", "添付", "入荷予定"]
    df_to_save = df.drop(columns=[c for c in drop_cols if c in df.columns], errors='ignore')
    df_to_save.to_csv(CSV_FILE, index=False, encoding="utf-8")


def add_log(category, item_name, action, detail=""):
    now = get_jst_now("%Y-%m-%d %H:%M:%S")
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


def check_expiry(date_str):
    if not str(date_str).strip():
        return "✅ 登録なし"
    try:
        expiry_date = datetime.datetime.strptime(str(date_str).strip(), "%Y-%m-%d").date()
        today = datetime.datetime.now(JST).date()
        days_left = (expiry_date - today).days
        if days_left < 0:
            return "❌ 期限切れ"
        elif days_left <= 30:
            return f"⚠️ 間近({days_left}日)"
        else:
            return "✅ 有効"
    except ValueError:
        return "❓ 日付エラー"


def process_auto_arrival(df):
    today = datetime.datetime.now(JST).date()
    updated = False
    for idx, row in df.iterrows():
        arr_date_str = str(row.get("入荷予定日", "")).strip()
        if arr_date_str:
            try:
                arr_date = datetime.datetime.strptime(arr_date_str, "%Y-%m-%d").date()
                if today > arr_date:
                    add_qty = int(row.get("入荷予定数", 0))
                    item_name = row["品名"]
                    
                    df.at[idx, "在庫数"] += add_qty
                    df.at[idx, "入荷予定日"] = ""
                    df.at[idx, "入荷予定数"] = 0
                    df.at[idx, "更新日時"] = get_jst_now()
                    
                    add_log(row["タブ名"], item_name, "自動入庫", f"取り寄せ分 {add_qty}{row['単位']} を追加")
                    updated = True
            except ValueError:
                pass
    if updated:
        save_data(df)
    return df


df = load_data()
df = process_auto_arrival(df)
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

expired_items = len(df[df["期限状態"] == "❌ 期限切れ"])
near_expiry_items = len(df[df["期限状態"].str.contains("⚠️", na=False)])

c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 登録品目数", f"{total_items} 件")
c2.metric("⚠️ 要発注・補充", f"{low_stock + out_of_stock} 件")
c3.metric("❌ 在庫切れ", f"{out_of_stock} 件")
c4.metric("📅 期限切れ/間近", f"{expired_items + near_expiry_items} 件")

st.markdown("---")

# ---------------------------------------------------------
# 4. サイドバー (要発注アラート・検索・通知・ログ)
# ---------------------------------------------------------
st.sidebar.header("🛒 要発注状況")
if len(low_stock_df) > 0:
    st.sidebar.warning(f"現在 **{len(low_stock_df)} 件** が発注点以下です！")
else:
    st.sidebar.success("現在、発注が必要な品目はありません。")

st.sidebar.markdown("---")
st.sidebar.header("🔍 検索 & フィルター")
search_query = st.sidebar.text_input(
    "検索キーワード", placeholder="品名・タグ・ロット番号・場所..."
)
status_filter = st.sidebar.radio(
    "状態絞り込み", ["すべて", "⚠️ 要発注のみ", "🚚 取り寄せ中", "📅 期限切れ/間近", "📄 添付ファイルあり"]
)

st.sidebar.markdown("---")
st.sidebar.header("📢 アラート一括通知")

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
                    msg_lines.append(f"・[{r['タブ名']}] {r['品名']} | 在庫:{r['在庫数']}{r['単位']} | 期限:{r['期限状態']}")
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
        now = get_jst_now()
        new_row = pd.DataFrame(
            [[new_cat, "サンプル原料", 1, 1, "個", now, "", "指定なし 📦", "", "LOT-000", "", "", "初期アイテム", "", "", 0]],
            columns=[c for c in df.columns if c != "期限状態"],
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
            if str(row.get("入荷予定日", "")).strip():
                return "🚚 取り寄せ中"
            if row["在庫数"] == 0:
                return "❌ 在庫切れ"
            elif row["在庫数"] <= row["発注点"]:
                return "⚠️ 要発注"
            else:
                return "✅ 良好"

        def get_has_file(row):
            path = str(row["SDSファイル"]).strip()
            return "📄 選択して開く" if path and os.path.exists(path) else "-"

        def get_arrival_info(row):
            d = str(row.get("入荷予定日", "")).strip()
            if d:
                try:
                    dt = datetime.datetime.strptime(d, "%Y-%m-%d")
                    return f"{dt.month}/{dt.day} ({row['入荷予定数']})"
                except:
                    return d
            return "-"

        if not cat_df.empty:
            cat_df["ステータス"] = cat_df.apply(get_status, axis=1)
            cat_df["添付"] = cat_df.apply(get_has_file, axis=1)
            cat_df["入荷予定"] = cat_df.apply(get_arrival_info, axis=1)

        filtered_df = cat_df.copy()
        if search_query:
            filtered_df = filtered_df[
                filtered_df["品名"].astype(str).str.contains(search_query, case=False)
                | filtered_df["ロット番号"].astype(str).str.contains(search_query, case=False)
                | filtered_df["保管場所"].astype(str).str.contains(search_query, case=False)
                | filtered_df["検索タグ"].astype(str).str.contains(search_query, case=False)
            ]

        if status_filter == "⚠️ 要発注のみ":
            filtered_df = filtered_df[filtered_df["ステータス"] == "⚠️ 要発注"]
        elif status_filter == "🚚 取り寄せ中":
            filtered_df = filtered_df[filtered_df["ステータス"] == "🚚 取り寄せ中"]
        elif status_filter == "📅 期限切れ/間近":
            filtered_df = filtered_df[filtered_df["期限状態"].str.contains("❌|⚠️", regex=True)]
        elif status_filter == "📄 添付ファイルあり":
            filtered_df = filtered_df[filtered_df["添付"] != "-"]

        st.subheader(f"「{cat}」の一覧")
        st.caption("✏️ **セル（品名・在庫数・単位など）をダブルクリックするとその場で直接編集できます！**")

        display_df = (filtered_df if not filtered_df.empty else cat_df).reset_index(drop=True)

        show_cols = [
            "品名", "検索タグ", "ロット番号", "在庫数", "単位", "期限状態", 
            "ステータス", "入荷予定", "添付", "安全区分", "保管場所", "備考", "更新日時"
        ]

        item_list = list(cat_df["品名"].unique())
        select_key = f"select_box_{cat}"
        next_key = f"next_select_{cat}"

        if next_key in st.session_state:
            st.session_state[select_key] = st.session_state.pop(next_key)

        if select_key not in st.session_state and item_list:
            st.session_state[select_key] = item_list[0]

        # オンライン直接編集対応
        edited_display_df = st.data_editor(
            display_df[show_cols],
            use_container_width=True,
            hide_index=True,
            key=f"df_editor_{cat}",
            disabled=["ステータス", "期限状態", "入荷予定", "添付", "更新日時"],
            column_config={
                "在庫数": st.column_config.NumberColumn("在庫数", min_value=0, step=1, format="%d"),
                "品名": st.column_config.TextColumn("品名", required=True),
                "単位": st.column_config.TextColumn("単位"),
            }
        )

        # 表のインライン編集の変更検知＆自動保存（日本時間）
        if not edited_display_df.equals(display_df[show_cols]):
            for row_i, edited_row in edited_display_df.iterrows():
                orig_row = display_df.iloc[row_i]
                if not edited_row.equals(orig_row[show_cols]):
                    orig_name = orig_row["品名"]
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == orig_name)].index
                    if not idx.empty:
                        df.loc[idx[0], "品名"] = str(edited_row["品名"]).strip()
                        df.loc[idx[0], "在庫数"] = int(edited_row["在庫数"])
                        df.loc[idx[0], "単位"] = str(edited_row["単位"]).strip()
                        df.loc[idx[0], "ロット番号"] = str(edited_row["ロット番号"]).strip()
                        df.loc[idx[0], "検索タグ"] = str(edited_row["検索タグ"]).strip()
                        df.loc[idx[0], "保管場所"] = str(edited_row["保管場所"]).strip()
                        df.loc[idx[0], "備考"] = str(edited_row["備考"]).strip()
                        df.loc[idx[0], "安全区分"] = str(edited_row["安全区分"])
                        df.loc[idx[0], "更新日時"] = get_jst_now()
                        
                        save_data(df)
                        st.toast(f"「{edited_row['品名']}」の変更を保存しました！")
                        st.rerun()

        st.markdown("---")

        if item_list:
            if st.session_state[select_key] not in item_list:
                st.session_state[select_key] = item_list[0]

            selected_item = st.selectbox(
                "🎯 操作対象の品目",
                item_list,
                key=select_key,
            )

            curr_row = cat_df[cat_df["品名"] == selected_item].iloc[0]
            sds_path = str(curr_row["SDSファイル"]).strip()

            if sds_path and os.path.exists(sds_path):
                st.success(f"📂 **{selected_item}** には添付ファイル（SDS）があります")
                
                mime_type, _ = mimetypes.guess_type(sds_path)
                if not mime_type:
                    mime_type = "application/octet-stream"

                with open(sds_path, "rb") as file:
                    st.download_button(
                        label=f"📄 {selected_item} の添付ファイルを開く・ダウンロード",
                        data=file, 
                        file_name=os.path.basename(sds_path), 
                        mime=mime_type, 
                        use_container_width=True,
                        type="primary"
                    )
                st.write("")

            op_tab1, op_tab2 = st.tabs(["⚡ 入出庫・取り寄せ操作", "✏️ 詳細情報・編集"])

            # ----------------------------------------------------
            # タブ1: 入出庫クイック操作 ＆ 取り寄せ
            # ----------------------------------------------------
            with op_tab1:
                unit_str = curr_row['単位'] if curr_row['単位'] else "個"
                st.markdown(f"**現在の在庫:** `{curr_row['在庫数']} {unit_str}` / **ロット:** `{curr_row['ロット番号']}`")
                
                change_qty = st.number_input(
                    f"操作数量（単位: {unit_str}）",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"qty_num_{cat}_{selected_item}"
                )

                col_a, col_b, col_c = st.columns(3)
                if col_a.button(f"➕ {change_qty} {unit_str} 追加", key=f"add_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        df.loc[idx, "在庫数"] += change_qty
                        df.loc[idx, "更新日時"] = get_jst_now()
                        save_data(df)
                        st.toast(f"「{selected_item}」に {change_qty} {unit_str} 追加しました！")
                        st.rerun()

                if col_b.button(f"➖ {change_qty} {unit_str} 使用", key=f"use_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        current_qty = df.loc[idx[0], "在庫数"]
                        if current_qty >= change_qty:
                            df.loc[idx, "在庫数"] -= change_qty
                            df.loc[idx, "更新日時"] = get_jst_now()
                            save_data(df)
                            st.toast(f"「{selected_item}」を {change_qty} {unit_str} 使用しました！")
                            st.rerun()
                        else:
                            st.error(f"在庫不足です。（現在在庫: {current_qty} {unit_str} / 使用指定: {change_qty} {unit_str}）")

                if col_c.button("🗑️ 品目を削除", key=f"del_{cat}", use_container_width=True):
                    df = df[~((df["タブ名"] == cat) & (df["品名"] == selected_item))]
                    save_data(df)
                    st.warning(f"「{selected_item}」を削除しました。")
                    st.rerun()

                # 取り寄せ・発注の手配セクション
                st.markdown("---")
                st.markdown("### 🚚 取り寄せ・発注の手配")
                arr_date = str(curr_row.get("入荷予定日", "")).strip()
                
                if arr_date:
                    st.info(f"🚚 現在 **{curr_row['入荷予定数']} {curr_row['単位']}** を取り寄せ中です。（到着予定日: {arr_date}）\n\n※予定日の翌日に自動で在庫へ加算されます。")
                    
                    ac1, ac2 = st.columns(2)
                    if ac1.button("✅ 今すぐ入荷を確定する (手動入庫)", key=f"force_arr_{cat}", use_container_width=True):
                        idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                        add_qty = int(curr_row["入荷予定数"])
                        df.loc[idx, "在庫数"] += add_qty
                        df.loc[idx, "入荷予定日"] = ""
                        df.loc[idx, "入荷予定数"] = 0
                        df.loc[idx, "更新日時"] = get_jst_now()
                        save_data(df)
                        add_log(cat, selected_item, "手動入荷", f"{add_qty}{curr_row['単位']} を追加")
                        st.success(f"{add_qty}{curr_row['単位']} を在庫に手動で追加しました！")
                        st.rerun()

                    if ac2.button("❌ 手配をキャンセル", key=f"cancel_arr_{cat}", use_container_width=True):
                        idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                        df.loc[idx, "入荷予定日"] = ""
                        df.loc[idx, "入荷予定数"] = 0
                        save_data(df)
                        add_log(cat, selected_item, "取り寄せ取消", "")
                        st.toast("取り寄せ手配をキャンセルしました。")
                        st.rerun()
                else:
                    with st.form(key=f"arrange_form_{cat}_{selected_item}"):
                        ac1, ac2 = st.columns(2)
                        arr_qty = ac1.number_input("取り寄せ予定数", min_value=1, value=int(curr_row["発注点"]) if curr_row["発注点"]>0 else 1)
                        default_date = datetime.datetime.now(JST).date() + datetime.timedelta(days=3)
                        arr_dt = ac2.date_input("入荷予定日", value=default_date)
                        
                        if st.form_submit_button("取り寄せ手配を登録する"):
                            idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                            df.loc[idx, "入荷予定日"] = arr_dt.strftime("%Y-%m-%d")
                            df.loc[idx, "入荷予定数"] = int(arr_qty)
                            save_data(df)
                            add_log(cat, selected_item, "取り寄せ登録", f"{arr_qty}{curr_row['単位']} 予定日:{arr_dt}")
                            st.toast("取り寄せ手配を登録しました！")
                            st.rerun()

            # ----------------------------------------------------
            # タブ2: 情報編集・添付ファイル
            # ----------------------------------------------------
            with op_tab2:
                with st.form(f"edit_form_{cat}_{selected_item}"):
                    e_name = st.text_input("品名", value=curr_row["品名"])
                    e_tags = st.text_input("🏷️ 検索用タグ (複数ある場合はカンマ区切り)", value=curr_row["検索タグ"], placeholder="例: 汎用樹脂, 試作, 洗浄用")

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

                    st.markdown("**📄 SDS・新しい添付ファイルの更新**")
                    uploaded_sds = st.file_uploader(
                        "新しくファイルを添付する (※現在のファイルは上書きされます)", type=["pdf", "png", "jpg", "jpeg", "xlsx"], key=f"file_edit_{selected_item}"
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
                                df.loc[idx[0], "検索タグ"] = e_tags.strip()
                                df.loc[idx[0], "在庫数"] = int(e_qty)
                                df.loc[idx[0], "発注点"] = int(e_min)
                                df.loc[idx[0], "単位"] = e_unit.strip()
                                df.loc[idx[0], "ロット番号"] = e_lot.strip()
                                df.loc[idx[0], "使用期限"] = e_exp.strftime("%Y-%m-%d") if e_exp else ""
                                df.loc[idx[0], "安全区分"] = e_safe
                                df.loc[idx[0], "SDSファイル"] = final_sds_path
                                df.loc[idx[0], "保管場所"] = e_loc.strip()
                                df.loc[idx[0], "備考"] = e_rem.strip()
                                df.loc[idx[0], "更新日時"] = get_jst_now()

                                save_data(df)
                                st.session_state[f"next_select_{cat}"] = new_name_clean
                                st.success(f"「{new_name_clean}」の情報を更新しました！")
                                st.rerun()

        # ➕ 新規品目追加フォーム
        st.markdown("---")
        with st.expander(f"➕ 「{cat}」に新しい原料・薬品を登録"):
            with st.form(f"add_item_form_{cat}"):
                f_name = st.text_input("品名 (例: イソプロピルアルコール)")
                f_tags = st.text_input("🏷️ 検索タグ (複数ある場合はカンマ区切り)", placeholder="例: 洗浄用, 劇物, Aライン用")
                
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
                                    get_jst_now(), 
                                    f_loc.strip(), f_safe, saved_path, f_lot.strip(), 
                                    f_exp.strftime("%Y-%m-%d") if f_exp else "", f_tags.strip(), f_rem.strip(), "", "", 0
                                ]],
                                columns=[c for c in df.columns if c not in ["期限状態", "ステータス", "添付", "入荷予定"]]
                            )
                            df = pd.concat([df.drop(columns=["期限状態", "ステータス", "添付", "入荷予定"], errors='ignore'), new_row], ignore_index=True)
                            save_data(df)
                            st.success(f"「{f_name.strip()}」を登録しました！")
                            st.rerun()
                    else:
                        st.error("品名を入力してください。")
