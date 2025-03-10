import datetime
import streamlit as st
import pandas as pd

from biz.service.review_service import ReviewService


# 获取数据函数
def get_data_by_date(authors=None, updated_at_gte=None, updated_at_lte=None):
    df = ReviewService().get_mr_review_logs(authors=authors, updated_at_gte=updated_at_gte,
                                            updated_at_lte=updated_at_lte)

    if df.empty:
        return pd.DataFrame(columns=["project_name", "author", "source_branch", "target_branch",
                                     "updated_at", "commit_messages", "score", "url"])

    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )

    data = df[
        ["project_name", "author", "source_branch", "target_branch", "updated_at", "commit_messages", "score", "url"]]
    # 将列名替换为中文
    data.rename(columns={
        "project_name": "项目名称",
        "author": "作者",
        "source_branch": "源分支",
        "target_branch": "目标分支",
        "updated_at": "更新时间",
        "commit_messages": "提交信息",
        "score": "评分",
        "url": "链接"
    }, inplace=True)
    return data


# Streamlit 配置
st.set_page_config(layout="wide")
st.markdown("### 审查日志")

current_date = datetime.date.today()
start_date_default = current_date - datetime.timedelta(days=7)

col1, col2, col3 = st.columns(3)
with col1:
    startdate = st.date_input("开始日期", start_date_default)

with col2:
    enddate = st.date_input("结束日期", current_date)

start_datetime = datetime.datetime.combine(startdate, datetime.time.min)
end_datetime = datetime.datetime.combine(enddate, datetime.time.max)

# 先获取数据
data = get_data_by_date(updated_at_gte=int(start_datetime.timestamp()), updated_at_lte=int(end_datetime.timestamp()))
df = pd.DataFrame(data)

# 动态获取 `authors` 选项
unique_authors = sorted(df["作者"].dropna().unique().tolist()) if not df.empty else []

with col3:
    authors = st.multiselect("用户名", unique_authors, default=[])

# 重新获取数据（带 `authors` 过滤）
data = get_data_by_date(authors=authors, updated_at_gte=int(start_datetime.timestamp()),
                        updated_at_lte=int(end_datetime.timestamp()))
df = pd.DataFrame(data)

st.data_editor(
    df,
    use_container_width=True,
    column_config={
        "评分": st.column_config.ProgressColumn(
            format="%f",
            min_value=0,
            max_value=100,
        ),
        "链接": st.column_config.LinkColumn(
            max_chars=100,
            display_text=r"查看"
        ),
    }
)

# 计算统计信息
total_records = len(df)
average_score = df["评分"].mean() if not df.empty else 0

# 显示统计信息
st.markdown(f"**总记录数:** {total_records}，**平均分:** {average_score:.2f}")
