import os
import re
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from datetime import datetime

# --- 配置 ---
# 从环境变量中获取 API 密钥
KIMI_API_KEY = os.environ.get("KIMI_API_KEY")
NBER_API_URL = 'https://www.nber.org/api/v1/working_page_listing/contentType/working_paper/_/_/search'
README_PATH = "README.md"
START_COMMENT = "<!-- NBER_PAPERS_START -->"
END_COMMENT = "<!-- NBER_PAPERS_END -->"

# --- Kimi API 客户端 ---
if KIMI_API_KEY:
    kimi_client = OpenAI(api_key=KIMI_API_KEY, base_url="https://api.moonshot.cn/v1")
else:
    # 如果在 GitHub Actions 中没有设置密钥，这将导致脚本失败，这是预期的行为
    print("错误：未找到 KIMI_API_KEY 环境变量。请在 GitHub Secrets 中设置它。")
    kimi_client = None

def translate_with_kimi(text):
    """使用 Kimi API 翻译文本"""
    if not kimi_client or not text:
        return "翻译失败（API未配置或文本为空）"
    
    # 对于简短或格式化的文本，直接返回，避免不必要的API调用
    if "暂无摘要" in text or "摘要未找到" in text:
        return text

    try:
        print(f"  正在翻译: '{text[:30]}...'")
        response = kimi_client.chat.completions.create(
            model="moonshot-v1-8k",
            messages=[
                {"role": "system", "content": "你是一个专业的经济学领域翻译助手。请将以下英文内容准确、流畅地翻译成中文。"},
                {"role": "user", "content": text}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"  Kimi 翻译 API 调用失败: {e}")
        return "翻译失败"

def process_authors(authors_html_list):
    """从 HTML 列表中解析作者姓名"""
    authors = []
    for html in authors_html_list:
        soup = BeautifulSoup(html, 'html.parser')
        if author_tag := soup.find('a'):
            authors.append(author_tag.get_text(strip=True))
    return authors or ['未知作者']

def fetch_and_process_papers():
    """获取并处理 NBER 的新论文"""
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    })

    print("正在从 NBER API 获取论文列表...")
    params = {'page': 1, 'perPage': 50, 'sortBy': 'public_date'}
    response = session.get(NBER_API_URL, params=params)
    response.raise_for_status()
    
    # 筛选本周新论文
    all_papers = response.json().get('results', [])
    new_papers = [p for p in all_papers if p.get('newthisweek')]
    
    if not new_papers:
        print("本周没有发现新的 NBER 论文。")
        return None

    print(f"发现了 {len(new_papers)} 篇新论文。开始处理...")
    
    processed_results = []
    for i, paper in enumerate(new_papers):
        print(f"正在处理第 {i+1}/{len(new_papers)} 篇: {paper.get('title')}")
        
        paper_url = f"https://www.nber.org{paper.get('url', '')}"
        
        try:
            # 获取单篇论文页面以提取摘要
            detail_response = session.get(paper_url, timeout=15)
            detail_soup = BeautifulSoup(detail_response.text, 'html.parser')
            
            abstract_div = detail_soup.find('div', class_='page-header__intro-inner')
            abstract = abstract_div.get_text(separator=' ', strip=True) if abstract_div else '暂无摘要'

            title_cn = translate_with_kimi(paper.get('title'))
            abstract_cn = translate_with_kimi(abstract)

            processed_results.append({
                'title': paper.get('title'),
                'title_cn': title_cn,
                'authors': process_authors(paper.get('authors', [])),
                'abstract': abstract,
                'abstract_cn': abstract_cn,
                'url': paper_url
            })
        except Exception as e:
            print(f"  处理论文 {paper.get('title')} 时出错: {e}")

    return processed_results

def generate_markdown(results):
    """根据处理结果生成 Markdown 文本"""
    if not results:
        return "本周暂无新论文更新。"

    # 第一部分：论文标题列表
    title_list_parts = [f"*(Updated on: {datetime.now().strftime('%Y-%m-%d')})*\n"]
    for i, res in enumerate(results):
        title_list_parts.append(
            f"{i+1}. **[{res['title']}]({res['url']})**<br/>{res['title_cn']}\n"
            f"   - *Authors: {', '.join(res['authors'])}*"
        )
    
    # 第二部分：详细摘要
    details_parts = ["\n---\n\n## 文章概览\n"]
    for res in results:
        details_parts.extend([
            f"### {res['title_cn']}",
            f"**[{res['title']}]({res['url']})**\n",
            f"**Authors**: {', '.join(res['authors'])}\n",
            f"**Abstract**: {res['abstract']}\n",
            f"**摘要**: {res['abstract_cn']}\n",
            "---"
        ])
    
    return "\n".join(title_list_parts) + "\n\n" + "\n".join(details_parts)

def update_readme(content):
    """将新内容写入 README.md 的指定位置"""
    try:
        with open(README_PATH, 'r', encoding='utf-8') as f:
            readme_content = f.read()

        # 使用 re.DOTALL 标志使 `.` 匹配换行符
        pattern = f"({re.escape(START_COMMENT)})(.*?)({re.escape(END_COMMENT)})"
        
        new_readme = re.sub(
            pattern,
            f"\\1\n{content}\n\\3",
            readme_content,
            flags=re.DOTALL
        )

        with open(README_PATH, 'w', encoding='utf-8') as f:
            f.write(new_readme)
        print("README.md 更新成功！")

    except FileNotFoundError:
        print(f"错误: {README_PATH} 文件未找到。")
    except Exception as e:
        print(f"更新 README.md 时发生错误: {e}")


if __name__ == "__main__":
    if not kimi_client:
        exit(1) # 如果 Kimi客户端未初始化，则退出
        
    papers_data = fetch_and_process_papers()
    if papers_data:
        markdown_output = generate_markdown(papers_data)
        update_readme(markdown_output)
    else:
        # 如果没有新论文，也更新一下提示信息
        update_readme(f"*(Updated on: {datetime.now().strftime('%Y-%m-%d')})*\n\n本周暂无新论文。")
