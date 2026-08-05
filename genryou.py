# ----------------------------------------------------
            # タブ1: 入出庫クイック操作 ＆ 取り寄せ
            # ----------------------------------------------------
            with op_tab1:
                unit_str = curr_row['単位'] if curr_row['単位'] else "個"
                st.markdown(f"**現在の在庫:** `{curr_row['在庫数']} {unit_str}` / **ロット:** `{curr_row['ロット番号']}`")
                
                # ★ 数量指定（キーボード入力・増減ボタン・スピン操作に対応）
                change_qty = st.number_input(
                    f"操作数量（単位: {unit_str}）",
                    min_value=1,
                    value=1,
                    step=1,
                    key=f"qty_num_{cat}_{selected_item}"
                )

                col_a, col_b, col_c = st.columns(3)
                # ★ 「➕ [指定数] [単位] 追加」ボタン
                if col_a.button(f"➕ {change_qty} {unit_str} 追加", key=f"add_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        df.loc[idx, "在庫数"] += change_qty
                        df.loc[idx, "更新日時"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_data(df)
                        st.toast(f"「{selected_item}」に {change_qty} {unit_str} 追加しました！")
                        st.rerun()

                # ★ 「➖ [指定数] [単位] 使用」ボタン
                if col_b.button(f"➖ {change_qty} {unit_str} 使用", key=f"use_{cat}", use_container_width=True):
                    idx = df[(df["タブ名"] == cat) & (df["品名"] == selected_item)].index
                    if not idx.empty:
                        current_qty = df.loc[idx[0], "在庫数"]
                        if current_qty >= change_qty:
                            df.loc[idx, "在庫数"] -= change_qty
                            df.loc[idx, "更新日時"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
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
