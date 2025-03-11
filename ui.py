import datetime
import os

from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib
import markdown
from dotenv import load_dotenv

from biz.service.review_service import ReviewService

load_dotenv()

# 设置matplotlib中文字体，解决中文显示乱码问题
matplotlib.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'Microsoft YaHei', 'WenQuanYi Micro Hei']
matplotlib.rcParams['axes.unicode_minus'] = False


# Markdown转HTML并创建tooltip的函数
def convert_markdown_to_html_tooltip(md_text):
    if not md_text:
        return ""
    # # 将Markdown转换为HTML
    # full_text_html = markdown.markdown(md_text)

    # # 将 Markdown 转换为 HTML
    # html = markdown.markdown(md_text)
    # # 使用 BeautifulSoup 解析 HTML 并提取纯文本
    # soup = BeautifulSoup(html, 'html.parser')
    # plain_text = soup.get_text(separator=' ')
    
    # # 清理多余的换行和空格
    # # plain_text = ' '.join(plain_text.split())
    # return plain_text
    
    return md_text

# 获取数据函数
def get_data(service_func, authors=None, project_names=None, updated_at_gte=None, updated_at_lte=None, columns=None):
    df = service_func(authors=authors, project_names=project_names, updated_at_gte=updated_at_gte, updated_at_lte=updated_at_lte)

    if df.empty:
        return pd.DataFrame(columns=columns)

    if "updated_at" in df.columns:
        df["updated_at"] = df["updated_at"].apply(
            lambda ts: datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(ts, (int, float)) else ts
        )
    
    # 处理review_result列，将Markdown内容转换为带有tooltip的HTML
    if "review_result" in df.columns:
        df["review_result"] = df["review_result"].apply(
            lambda text: convert_markdown_to_html_tooltip(text) if text else ""
        )

    data = df[columns]
    return data


# 生成项目提交数量图表
def generate_project_count_chart(df):
    if df.empty:
        st.info("没有数据可供展示")
        return
    
    # 计算每个项目的提交数量
    project_counts = df['project_name'].value_counts().reset_index()
    project_counts.columns = ['project_name', 'count']
    
    # 显示提交数量柱状图
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(project_counts['project_name'], project_counts['count'])
    ax1.set_xlabel('项目名称')
    ax1.set_ylabel('提交数量')
    plt.xticks(rotation=45, ha='right')
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
    
    # 显示平均分数柱状图
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    ax2.bar(project_scores['project_name'], project_scores['average_score'])
    ax2.set_xlabel('项目名称')
    ax2.set_ylabel('平均分数')
    plt.xticks(rotation=45, ha='right')
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
    
    # 显示提交数量柱状图
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    ax1.bar(author_counts['author'], author_counts['count'])
    ax1.set_xlabel('人员')
    ax1.set_ylabel('提交数量')
    plt.xticks(rotation=45, ha='right')
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
    ax2.bar(author_scores['author'], author_scores['average_score'])
    ax2.set_xlabel('人员')
    ax2.set_ylabel('平均分数')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    st.pyplot(fig2)


# Streamlit 配置
st.set_page_config(layout="wide")
st.markdown("#### 审查日志😊")

current_date = datetime.date.today()
start_date_default = current_date - datetime.timedelta(days=7)

# 根据环境变量决定是否显示 push_tab
show_push_tab = os.environ.get('PUSH_REVIEW_ENABLED', '0') == '1'

if show_push_tab:
    push_tab, mr_tab = st.tabs(["Push", "Merge Request"])
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
        
        # 添加统计图表
        st.markdown("### 统计图表")
        
        # 创建2x2网格布局展示四个图表
        row1_col1, row1_col2 = st.columns(2)
        row2_col1, row2_col2 = st.columns(2)
        
        with row1_col1:
            st.markdown("#### 项目提交数量")
            generate_project_count_chart(df)
        
        with row1_col2:
            st.markdown("#### 项目平均分数")
            generate_project_score_chart(df)
        
        with row2_col1:
            st.markdown("#### 人员提交数量")
            generate_author_count_chart(df)
        
        with row2_col2:
            st.markdown("#### 人员平均分数")
            generate_author_score_chart(df)
        



# 注意：人员统计图表已在display_data函数中生成，不需要在全局作用域调用


# Push 数据展示
if show_push_tab:
    push_columns = ["project_name", "author", "branch", "updated_at", "commit_messages", "score","review_result"]

    push_column_config = {
        "score": st.column_config.ProgressColumn(
            format="%f",
            min_value=0,
            max_value=100,
        ),
       
        "review_result": st.column_config.TextColumn(
            label="Review Result",
            help="双击查看完整内容",
            width="medium"
        )
    }

    display_data(push_tab, ReviewService().get_push_review_logs, push_columns, push_column_config)

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
        display_text=r"查看"
    ),
}

display_data(mr_tab, ReviewService().get_mr_review_logs, mr_columns, mr_column_config)