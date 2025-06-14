import datetime
import math
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from biz.service.review_service import ReviewService

load_dotenv("conf/.env")

# 从环境变量中读取用户名和密码
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "admin")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin")
USER_CREDENTIALS = {
    DASHBOARD_USER: DASHBOARD_PASSWORD
}


# 登录验证函数
def authenticate(username, password):
    return username in USER_CREDENTIALS and USER_CREDENTIALS[username] == password


# 获取数据函数
def get_data(service_func, authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None, columns=None):
    df = service_func(authors=authors, project_names=project_names, updated_at_gte=updated_at_gte,
                      updated_at_lte=updated_at_lte)

    if df.empty:
        return pd.DataFrame(columns=columns)

    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )

    def format_delta(row):
        if (row['additions'] and not math.isnan(row['additions'])
                and row['deletions'] and not math.isnan(row['deletions'])):
            return f"+{int(row['additions'])}  -{int(row['deletions'])}"
        else:
            return ""
    if "additions" in df.columns and "deletions" in df.columns:
        df["delta"] = df.apply(format_delta, axis=1)
    else:
        df["delta"] = ""
    data = df[columns]
    return data


# Streamlit 配置
st.set_page_config(layout="wide")


# 登录界面
def login_page():
    # 使用 st.columns 创建居中布局
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("登录")
        # 如果用户名和密码都为 'admin'，提示用户修改密码
        if DASHBOARD_USER == "admin" and DASHBOARD_PASSWORD == "admin":
            st.warning(
                "安全提示：检测到默认用户名和密码为 'admin'，存在安全风险！\n\n"
                "请立即修改：\n"
                "1. 打开 `.env` 文件\n"
                "2. 修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量\n"
                "3. 保存并重启应用"
            )
            st.write(f"当前用户名: `{DASHBOARD_USER}`, 当前密码: `{DASHBOARD_PASSWORD}`")

        username = st.text_input("用户名")
        password = st.text_input("密码", type="password")

        if st.button("登录"):
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()  # 重新运行应用以显示主要内容
            else:
                st.error("用户名或密码错误")


# 生成项目提交数量图表
def generate_project_count_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    # 计算每个项目的提交数量
    project_counts = df['project_name'].value_counts().reset_index()
    project_counts.columns = ['project_name', 'count']

    # 生成颜色列表，每个项目一个颜色
    colors = plt.colormaps['tab20'].resampled(len(project_counts))

    # 显示提交数量柱状图
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(
        project_counts['project_name'],
        project_counts['count'],
        color=[colors(i) for i in range(len(project_counts))]
    )
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig1)


# 生成项目平均分数图表
def generate_project_score_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    # 计算每个项目的平均分数
    project_scores = df.groupby('project_name')['score'].mean().reset_index()
    project_scores.columns = ['project_name', 'average_score']

    # 生成颜色列表，每个项目一个颜色
    # colors = plt.cm.get_cmap('Accent', len(project_scores))  # 使用'tab20'颜色映射，适合分类数据
    colors = plt.colormaps['Accent'].resampled(len(project_scores))
    # 显示平均分数柱状图
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.bar(
        project_scores['project_name'],
        project_scores['average_score'],
        color=[colors(i) for i in range(len(project_scores))]
    )
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig2)


# 生成人员提交数量图表
def generate_author_count_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    # 计算每个人员的提交数量
    author_counts = df['author'].value_counts().reset_index()
    author_counts.columns = ['author', 'count']

    # 生成颜色列表，每个项目一个颜色
    colors = plt.colormaps['Paired'].resampled(len(author_counts))
    # 显示提交数量柱状图
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(
        author_counts['author'],
        author_counts['count'],
        color=[colors(i) for i in range(len(author_counts))]
    )
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig1)


# 生成人员平均分数图表
def generate_author_score_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return

    # 计算每个人员的平均分数
    author_scores = df.groupby('author')['score'].mean().reset_index()
    author_scores.columns = ['author', 'average_score']

    # 显示平均分数柱状图
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    # 生成颜色列表，每个项目一个颜色
    colors = plt.colormaps['Pastel1'].resampled(len(author_scores))
    ax2.bar(
        author_scores['author'],
        author_scores['average_score'],
        color=[colors(i) for i in range(len(author_scores))]
    )
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig2)


def generate_author_code_line_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return
    
    # 检查必要的列是否存在
    if 'additions' not in df.columns or 'deletions' not in df.columns:
        st.warning("无法生成代码行数图表：缺少必要的数据列")
        return
        
    # 计算每个人员的代码行数（additions + deletions）
    df['total_lines'] = df['additions'] + df['deletions']
    author_code_lines = df.groupby('author')['total_lines'].sum().reset_index()
    author_code_lines.columns = ['author', 'code_lines']

    # 显示代码行数柱状图
    fig3, ax3 = plt.subplots(figsize=(10, 6))
    colors = plt.colormaps['Set3'].resampled(len(author_code_lines))
    ax3.bar(
        author_code_lines['author'],
        author_code_lines['code_lines'],
        color=[colors(i) for i in range(len(author_code_lines))]
    )
    plt.xticks(rotation=45, ha='right', fontsize=26)
    plt.tight_layout()
    st.pyplot(fig3)


# 主要内容
def main_page():
    st.markdown("#### 审查日志")

    current_date = datetime.date.today()
    start_date_default = current_date - datetime.timedelta(days=7)

    # 根据环境变量决定是否显示 push_tab
    show_push_tab = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

    if show_push_tab:
        mr_tab, push_tab = st.tabs(["Merge Request", "Push"])
    else:
        mr_tab = st.container()

    def display_data(tab, service_func, columns, column_config):
        with tab:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                start_date = st.date_input("开始日期", start_date_default, key=f"{tab}_start_date")
            with col2:
                end_date = st.date_input("结束日期", current_date, key=f"{tab}_end_date")

            start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
            end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

            data = get_data(service_func, updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            unique_authors = sorted(df["author"].dropna().unique().tolist()) if not df.empty else []
            unique_projects = sorted(df["project_name"].dropna().unique().tolist()) if not df.empty else []
            with col3:
                authors = st.multiselect("用户名", unique_authors, default=[], key=f"{tab}_authors")
            with col4:
                project_names = st.multiselect("项目名", unique_projects, default=[], key=f"{tab}_projects")

            data = get_data(service_func, authors=authors, project_names=project_names,
                            updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            st.data_editor(
                df,
                use_container_width=True,
                column_config=column_config
            )

            total_records = len(df)
            average_score = df["score"].mean() if not df.empty else 0
            st.markdown(f"**总记录数:** {total_records}，**平均分:** {average_score:.2f}")


            # 创建2x2网格布局展示四个图表
            row1, row2, row3, row4 = st.columns(4)
            with row1:
                st.markdown("<div style='text-align: center;'><b>项目提交次数</b></div>", unsafe_allow_html=True)
                generate_project_count_chart(df)
            with row2:
                st.markdown("<div style='text-align: center;'><b>项目平均分数</b></div>", unsafe_allow_html=True)
                generate_project_score_chart(df)
            with row3:
                st.markdown("<div style='text-align: center;'><b>人员提交次数</b></div>", unsafe_allow_html=True)
                generate_author_count_chart(df)
            with row4:
                st.markdown("<div style='text-align: center;'><b>人员平均分数</b></div>", unsafe_allow_html=True)
                generate_author_score_chart(df)

            row5, row6, row7, row8 = st.columns(4)
            with row5:
                st.markdown("<div style='text-align: center;'><b>人员代码变更总行数(增加+删除)</b></div>", unsafe_allow_html=True)
                # 只有当 additions 和 deletions 列都存在时才显示代码行数图表
                if 'additions' in df.columns and 'deletions' in df.columns:
                    generate_author_code_line_chart(df)
                else:
                    st.info("无法显示代码行数图表：缺少必要的数据列")

    # Merge Request 数据展示
    mr_columns = ["project_name", "author", "source_branch", "target_branch", "updated_at", "commit_messages", "delta",
                  "score", "url", "additions", "deletions"]

    mr_column_config = {
        "score": st.column_config.ProgressColumn(
            format="%f",
            min_value=0,
            max_value=100,
        ),
        "url": st.column_config.LinkColumn(
            max_chars=100,
            display_text=r"查看"
        ),
        "additions": None,
        "deletions": None,
    }

    display_data(mr_tab, ReviewService().get_mr_review_logs, mr_columns, mr_column_config)

    # Push 数据展示
    if show_push_tab:
        push_columns = ["project_name", "author", "branch", "updated_at", "commit_messages", "delta", "score", "additions", "deletions"]

        push_column_config = {
            "score": st.column_config.ProgressColumn(
                format="%f",
                min_value=0,
                max_value=100,
            ),
            "additions": None,
            "deletions": None,
        }

        display_data(push_tab, ReviewService().get_push_review_logs, push_columns, push_column_config)


# 应用入口
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    main_page()
else:
    login_page()
