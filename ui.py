import datetime
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from biz.service.review_service import ReviewService

load_dotenv()

from biz.utils.i18n import get_translator

_ = get_translator()

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
def get_data(service_func, authors=None, updated_at_gte=None, updated_at_lte=None, columns=None):
    df = service_func(authors=authors, updated_at_gte=updated_at_gte, updated_at_lte=updated_at_lte)

    if df.empty:
        return pd.DataFrame(columns=columns)

    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )

    data = df[columns]
    return data


# Streamlit 配置
st.set_page_config(layout="wide")


# 登录界面
def login_page():
    # 使用 st.columns 创建居中布局
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title(_("登录"))
        # 如果用户名和密码都为 'admin'，提示用户修改密码
        if DASHBOARD_USER == "admin" and DASHBOARD_PASSWORD == "admin":
            st.warning(_(
                "安全提示：检测到默认用户名和密码为 'admin'，存在安全风险！\n\n"
                "请立即修改：\n"
                "1. 打开 `.env` 文件\n"
                "2. 修改 `DASHBOARD_USER` 和 `DASHBOARD_PASSWORD` 变量\n"
                "3. 保存并重启应用"
            ))
            st.write(_("当前用户名: `{}`, 当前密码: `{}`").format(DASHBOARD_USER, DASHBOARD_PASSWORD))

        username = st.text_input(_("用户名"))
        password = st.text_input(_("密码"), type="password")

        if st.button(_("登录")):
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()  # 重新运行应用以显示主要内容
            else:
                st.error(_("用户名或密码错误"))


# 主要内容
def main_page():
    st.markdown(_("#### 审查日志"))

    current_date = datetime.date.today()
    start_date_default = current_date - datetime.timedelta(days=7)

    # 根据环境变量决定是否显示 push_tab
    show_push_tab = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

    if show_push_tab:
        mr_tab, push_tab = st.tabs([_("Merge Request"), _("Push")])
    else:
        mr_tab = st.container()

    def display_data(tab, service_func, columns, column_config):
        with tab:
            col1, col2, col3 = st.columns(3)
            with col1:
                start_date = st.date_input(_("开始日期"), start_date_default, key=f"{tab}_start_date")
            with col2:
                end_date = st.date_input(_("结束日期"), current_date, key=f"{tab}_end_date")

            start_datetime = datetime.datetime.combine(start_date, datetime.time.min)
            end_datetime = datetime.datetime.combine(end_date, datetime.time.max)

            data = get_data(service_func, updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            unique_authors = sorted(df["author"].dropna().unique().tolist()) if not df.empty else []
            with col3:
                authors = st.multiselect(_("用户名"), unique_authors, default=[], key=f"{tab}_authors")

            data = get_data(service_func, authors=authors, updated_at_gte=int(start_datetime.timestamp()),
                            updated_at_lte=int(end_datetime.timestamp()), columns=columns)
            df = pd.DataFrame(data)

            st.data_editor(
                df,
                use_container_width=True,
                column_config=column_config
            )

            total_records = len(df)
            average_score = df["score"].mean() if not df.empty else 0
            st.markdown(_("**总记录数:** {}，**平均分:** {}").format(total_records, f'{average_score:.2f}'))

    # Merge Request 数据展示
    mr_columns = ["project_name", "author", "source_branch", "target_branch", "updated_at", "commit_messages", "score",
                  "url"]

    mr_column_config = {
        "score": st.column_config.ProgressColumn(
            format="%f",
            min_value=0,
            max_value=100,
        ),
        "url": st.column_config.LinkColumn(
            max_chars=100,
            display_text=_(r"查看")
        ),
    }

    display_data(mr_tab, ReviewService().get_mr_review_logs, mr_columns, mr_column_config)

    # Push 数据展示
    if show_push_tab:
        push_columns = ["project_name", "author", "branch", "updated_at", "commit_messages", "score"]

        push_column_config = {
            "score": st.column_config.ProgressColumn(
                format="%f",
                min_value=0,
                max_value=100,
            ),
        }

        display_data(push_tab, ReviewService().get_push_review_logs, push_columns, push_column_config)


# 应用入口
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if st.session_state["authenticated"]:
    main_page()
else:
    login_page()
