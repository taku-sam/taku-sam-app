import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_plotly_events import plotly_events
import base64
import numpy as np

# ページ全体 (body) とサイドバー (フィルター) の背景を設定する CSS を出力
st.markdown(
    """
    <style>
    /* アプリのメインコンテナの背景 */
    [data-testid="stAppViewContainer"] {
        background-image: url("https://images.unsplash.com/photo-1623197532650-bacb8a68914e?q=80&w=1170&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
        background-size: cover;
        background-attachment: fixed;
    }

    /* サイドバー (フィルター) の背景 */
    [data-testid="stSidebar"] {
         background-image: url("https://images.unsplash.com/photo-1594052010777-a1edafaa6e84?q=80&w=627&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D");
         background-size: cover;
         background-attachment: fixed;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ────── データの読み込み（キャッシュ付き） ──────
@st.cache_data
def load_data():
    df = pd.read_csv("dfZ.csv")
    return df

df = load_data()

# ────── タイトルの設定 ──────
st.markdown(
    '<h1 style="color: #4D91AE; font-weight: bold;">Python Web App Dashboard</h1>',
    unsafe_allow_html=True,
)

# ────── サイドバーによるフィルター設定 ──────
st.sidebar.markdown(
    '<h1 style="color: black; font-weight: bold;">フィルター</h1>',
    unsafe_allow_html=True,
)

# target_flg のフィルター（"All", 0, 1）
target_options = ["All", "0", "1"]
target_selection = st.sidebar.selectbox("target_flg", target_options)

# 顧客クラスタのフィルター
clusters = sorted(df["顧客クラスタ"].unique())
clusters_options = ["All"] + [str(c) for c in clusters]
cluster_selection = st.sidebar.selectbox("顧客クラスタ", clusters_options)

# 性別フィルター
gender_options = ["All", "男性", "女性"]
gender_selection = st.sidebar.selectbox("性別", gender_options)

# 店舗IDフィルター（df に "店舗ID" カラムがある場合）
if "店舗ID" in df.columns:
    store_options = ["All"] + sorted(df["店舗ID"].unique().tolist())
    store_selection = st.sidebar.selectbox("店舗ID", store_options)
else:
    store_selection = "All"

# 連動フィルタリングのチェックボックス
linked_filter = st.sidebar.checkbox("連動フィルタリングを適用", value=False, key="linked_filter")

# フィルター適用
filtered_df = df.copy()
if target_selection != "All":
    filtered_df = filtered_df[filtered_df["target_flg"] == int(target_selection)]
if cluster_selection != "All":
    filtered_df = filtered_df[filtered_df["顧客クラスタ"] == int(cluster_selection)]
if gender_selection != "All":
    filtered_df = filtered_df[filtered_df["性別"] == gender_selection]
if store_selection != "All":
    filtered_df = filtered_df[filtered_df["店舗ID"] == store_selection]
if linked_filter and st.session_state.get("selected_ids"):
    sel_ids = st.session_state.selected_ids
    st.write("連動フィルタリング適用中 (顧客ID):", sel_ids)
    filtered_df = filtered_df[filtered_df["顧客ID"].isin(sel_ids)]

# ────── カラーマップ定義 ──────
target_color_map = {0: "#E6E1E1", 1: "#37BBCD"}
gender_color_map = {"女性": "#37BBCD", "男性": "#E6E1E1"}

# ────── 数値データ候補カラム ──────
numeric_cols = [
    "年齢", "入会後年数", "配信回数", "利用率",
    "失効ポイント合計", "失効ポイント回数",
    "店舗従業員数", "店舗従業員_中央値給与",
    "店舗従業員_中央値勤続期間_年", "店舗従業員_中央値満足度",
    "購買金額変化率"
]

# ────── グラフ種別の選択 (3種類のみ) ──────
graph_type = st.sidebar.radio("表示するグラフ", (
    "レインクラウドプロット", 
    "箱ひげ図＋スウォームプロット", 
    "バブルチャート"
))

# ────── 各種グラフの表示 ──────

if graph_type == "レインクラウドプロット":
    st.subheader("レインクラウドプロット")
    # 数値変数とグループ変数の選択
    raincloud_numeric = st.sidebar.selectbox("雨雲プロット用の数値変数", numeric_cols, key="raincloud_numeric")
    raincloud_group = st.sidebar.selectbox("グループ化変数 (雨雲)", ["target_flg", "性別", "顧客クラスタ", "店舗ID"], key="raincloud_group")
    
    # グループ変数ごとの色設定（指定の場合のみ）
    if raincloud_group == "target_flg":
        mapping = {0: "#37BBCD", 1: "#DA6272"}
    elif raincloud_group == "性別":
        mapping = {"男性": "#37BBCD", "女性": "#DA6272"}
    elif raincloud_group == "顧客クラスタ":
        mapping = {3: "#37BBCD", 2: "#DA6272", 1: "#87C143"}
    else:
        mapping = {}  # それ以外はデフォルト（例：#37BBCD を採用）
    
    # 各カテゴリごとに、y位置を決定
    group_categories = sorted(filtered_df[raincloud_group].unique())
    y_positions = {cat: i for i, cat in enumerate(group_categories)}
    np.random.seed(42)
    fig = go.Figure()
    
    # 各要素の垂直オフセット（グループ中心からのシフト値）
    offset_violin = 0.15   # half violinplot（Cloud）は上にシフト
    offset_box = 0.00      # 箱ひげ図（Umbrella）は中心
    offset_rain = -0.15    # ストリッププロット（Rain）は下にシフト
    
    for cat in group_categories:
        d = filtered_df[filtered_df[raincloud_group] == cat]
        pos = y_positions[cat]
        # 各カテゴリの色（mappingに無ければデフォルト）
        fill_color = mapping.get(cat, "#37BBCD")
        
        # Cloud: 半側体ヴァイオリンプロット（Kernel Density Estimate）
        fig.add_trace(go.Violin(
            x=d[raincloud_numeric],
            y=[pos + offset_violin] * len(d),  # オフセットを追加
            name=str(cat),
            side='positive',
            orientation='h',
            line=dict(color=fill_color),
            fillcolor=fill_color,
            width=0.8,
            spanmode='hard',
            showlegend=False,
            points=False  # 個別点は別途追加
        ))
        
        # Umbrella: 箱ひげ図（常にグレー）
        fig.add_trace(go.Box(
            x=d[raincloud_numeric],
            y=[pos + offset_box] * len(d),  # 中心位置
            name=str(cat),
            marker_color="gray",
            width=0.2,
            boxpoints=False,
            orientation='h',
            showlegend=False
        ))
        
        # Rain: ストリッププロット（ジッターを付けた散布図、色はfill_color）
        jitter = np.random.uniform(-0.05, 0.05, size=len(d))
        y_jitter = [pos + offset_rain + j for j in jitter]  # オフセット＋ジッターを追加
        fig.add_trace(go.Scatter(
            x=d[raincloud_numeric],
            y=y_jitter,
            mode='markers',
            marker=dict(color=fill_color, size=6),
            name=str(cat) + " Rain",
            showlegend=False
        ))
    
    # レイアウト調整：y軸にカテゴリ名を表示
    fig.update_layout(
        title=f"{raincloud_group} 別の {raincloud_numeric} Raincloud Plot",
        yaxis=dict(
            tickmode='array',
            tickvals=[pos for pos in y_positions.values()],
            ticktext=list(y_positions.keys())
        ),
        xaxis_title=raincloud_numeric,
        violingap=0.2,
        violinmode='overlay'
    )
    st.plotly_chart(fig, use_container_width=True)
    
elif graph_type == "箱ひげ図＋スウォームプロット":
    st.subheader("箱ひげ図＋スウォームプロット")
    box_numeric = st.sidebar.selectbox("数値変数 (箱ひげ図＋スウォームプロット)", numeric_cols, key="box_numeric")
    box_group = st.sidebar.selectbox("グループ化変数 (箱ひげ図＋スウォームプロット)", ["target_flg", "性別", "顧客クラスタ", "店舗ID"], key="box_group")
    
    # グループ変数ごとの色設定
    if box_group == "target_flg":
        mapping_box = {0: "#37BBCD", 1: "#DA6272"}
    elif box_group == "性別":
        mapping_box = {"男性": "#37BBCD", "女性": "#DA6272"}
    elif box_group == "顧客クラスタ":
        mapping_box = {3: "#DA6272", 2: "#DA6272", 1: "#DA6272"}
    else:
        mapping_box = {}
    
    # Plotly Express の箱ひげ図では、colorとcolor_discrete_mapを指定することで各カテゴリの色を設定
    fig = px.box(filtered_df, x=box_group, y=box_numeric, points="all",
                 title=f"{box_group} 別の {box_numeric} 箱ひげ図＋スウォームプロット",
                 color=box_group,
                 color_discrete_map=mapping_box)
    st.plotly_chart(fig, use_container_width=True)

elif graph_type == "バブルチャート":
    st.subheader("バブルチャート")
    x_var = st.sidebar.selectbox("X軸の変数 (Bubble)", numeric_cols, key="bubble_x")
    y_var = st.sidebar.selectbox("Y軸の変数 (Bubble)", numeric_cols, key="bubble_y")
    size_var = st.sidebar.selectbox("バブルサイズの変数", numeric_cols, key="bubble_size")
    # 購買金額変化率を選んだ場合、サイズがマイナスにならないように調整
    if size_var == "購買金額変化率":
        temp_df = filtered_df.copy()
        temp_df["adjusted_size"] = temp_df[size_var] - temp_df[size_var].min() + 1
        use_size = "adjusted_size"
    else:
        temp_df = filtered_df.copy()
        use_size = size_var
    
    fig = px.scatter(
        temp_df, x=x_var, y=y_var, size=use_size,
        color="target_flg", color_discrete_map=target_color_map,
        hover_data=["顧客ID", "顧客クラスタ", "店舗ID", "性別"],
        title=f"バブルチャート: {x_var} vs {y_var} (サイズ: {size_var})"
    )
    st.plotly_chart(fig, use_container_width=True)
