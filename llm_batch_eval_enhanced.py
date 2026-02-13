#!/usr/bin/env python3
"""
大模型智商评测脚本 - 强化版（60题）- 带详细日志
"""

import requests
import json
import time
import sys
from typing import List, Dict, Tuple
from datetime import datetime

print(f"[{datetime.now().strftime('%H:%M:%S')}] [INIT] 脚本启动...", flush=True)

# ============ 强化版题目库 ============
print(f"[{datetime.now().strftime('%H:%M:%S')}] [INIT] 加载题目库...", flush=True)

REASONING_QUESTIONS = [
    {"question": "解方程组：2x+3y-z=10, x-y+2z=-5, 3x+2y+z=8。请用矩阵消元法求解。", "answer_type": "math_system"},
    {"question": "计算定积分：∫(0到π) x·sin(x) dx，给出详细步骤。", "answer_type": "calculus"},
    {"question": "数列a₁=1,a₂=3,aₙ=2aₙ₋₁+aₙ₋₂。求a₆并证明通项公式。", "answer_type": "sequence"},
    {"question": "概率题：袋中有5红球、3蓝球、2绿球。连续抽3次（不放回），求至少抽到2个红球的概率。", "answer_type": "probability"},
    {"question": "五人跑步：A在B前面，C第三，D紧跟E后，B不在最后。请推断所有名次，列出所有可能。", "answer_type": "logical_race"},
    {"question": "逻辑：如果下雨则地湿。地是湿的。能得出下雨了吗？分析充分条件和必要条件的区别。", "answer_type": "logical_conditional"},
    {"question": "判断推理：所有哺乳动物恒温，鲸鱼是哺乳动物，所以鲸鱼恒温。用三段论规则分析。", "answer_type": "syllogism"},
    {"question": "排除法：三盒装苹果、橙子。第一人说第一盒是苹果（假），第二人说第一盒是橙子（假）。推断各盒子。", "answer_type": "elimination"},
    {"question": "条件悖论：如果这句话是真，你给我100元；是假，你不用给我100元。分析这个悖论的逻辑结构。", "answer_type": "paradox"},
    {"question": "量化逻辑：用谓词逻辑表示'所有学生都至少有一门课不及格'，并给出否定命题。", "answer_type": "predicate_logic"},
    {"question": "TSP问题：4城A、B、C、D。距离：A-B=10,A-C=15,A-D=20,B-C=35,B-D=25,C-D=30。用最近邻算法求近似最优路径。", "answer_type": "tsp"},
    {"question": "背包问题：物品重量[2,3,4,5]，价值[3,4,5,6]，背包容量8。用动态规划求最大价值，展示表格过程。", "answer_type": "knapsack"},
    {"question": "项目排程：任务A(3天)→B(2天)、C(4天)并行→D(2天需B、C完成)。绘制甘特图，计算最短完成时间。", "answer_type": "scheduling"},
    {"question": "资源分配：公司3项目，预算100万。收益[30,50,40]，风险[0.2,0.5,0.3]。用整数规划找风险最小化且收益最大化方案。", "answer_type": "optimization"},
    {"question": "倒水问题：5升和3升容器，无刻度。精确量出4升水，给出步骤并证明。", "answer_type": "water_puzzle"},
    {"question": "棋盘推理：国际象棋马从任意位置出发，3步内能到达任意位置吗？请数学证明。", "answer_type": "chess_knight"},
    {"question": "细菌分裂：每20分钟分裂一次。初始1个，4小时后有多少？用指数增长模型计算。", "answer_type": "exponential"},
    {"question": "帽子颜色：3人排一列，各看前面人帽。3顶2白1黑。从最后一人开始问是否知自己颜色。分析每个人推理。", "answer_type": "hat_problem"},
    {"question": "电梯等待：10楼，电梯在3楼。电梯上升0.5层/秒，启动/停止各2秒。步行每层5秒。计算哪个更快到1楼。", "answer_type": "realworld_math"},
    {"question": "密码破解：4位数字。条件：第一位=第二位+1，第二位×第三位=24，第三位=第四位-2。找出所有可能密码。", "answer_type": "constraint_solving"},
]

LANGUAGE_QUESTIONS = [
    {"question": "语法纠错（5处）：'The committee have made their decision yesterday. Each members was asked to submit their opinion. The data which was collected by them were analyzed careful. Neither the manager nor the workers was available. More information are needed.'", "answer_type": "grammar_error"},
    {"question": "同义改写：简化为3种不同风格。'Although the company had been experiencing significant financial difficulties for several years, and despite the recommendations of several consultants to file for bankruptcy, the CEO, who had personally invested his entire life savings into the venture, decided to continue operations.'", "answer_type": "paraphrase"},
    {"question": "词义辨析填空：1. The economy has _______ (affected/effected) by inflation. 2. His _______ (continuous/continual) talking annoyed everyone. 3. The _______ (principal/principle) reason for leaving was money.", "answer_type": "vocab_distinction"},
    {"question": "从句转换：改写为简单句、并列句、定语从句三种形式。'Because the experiment was successful, the scientist decided to publish the results immediately after verifying the data one more time.'", "answer_type": "clause_transformation"},
    {"question": "时态综合：用8种不同时态翻译'我每天学习英语'。", "answer_type": "tense_synthesis"},
    {"question": "阅读理解：Climate change impacts through extreme weather, biodiversity loss, sea-level rise. Paris Agreement aims 1.5°C limit. Current commitments = 2.7°C by 2100. 'ambition gap' needs enhanced action. 问题：1. 'ambition gap'指什么？2. 缩小差距需什么条件？3. 可推断什么？", "answer_type": "academic_reading"},
    {"question": "新闻阅读：某科技公司计划5年在AI领域投100亿美元。CEO：用于研发新一代AI芯片。分析师：市场竞争激烈，商业化面临挑战。问题：1. 投资计划？2. CEO乐观基于？3. 分析师谨慎理由？4. 整体基调？", "answer_type": "news_reading"},
    {"question": "法律阅读：《劳动合同法》第38条：未提供劳动保护、未支付劳动报酬、未缴纳社保、规章制度损害劳动者权益的，劳动者可解除合同。问题：1. 几个情形？2. 未缴社保是否？3. '劳动保护'指什么？", "answer_type": "legal_reading"},
    {"question": "图表分析：2020-2024年季度营收：Q1:120,135,128,142,155 Q2:145,150,138,160,168 Q3:130,142,155,152,175 Q4:160,175,168,185,195 问题：1. 哪年Q3同比增长最大？2. 预测2025全年 3. 整体趋势？", "answer_type": "data_reading"},
    {"question": "多文本比较：文本A：社交媒体对青少年有负面影响，超3小时使用风险增60%。文本B：社交媒体减少孤独感，适度使用提高社交技能。问题：1. 主要观点？2. 冲突/互补？3. 整合两观点？", "answer_type": "multi_text"},
    {"question": "模糊指令：'帮我看看这个报告'——提出至少3种可能理解及对应回复。", "answer_type": "ambiguous_request"},
    {"question": "噪声输入处理：用户：'我想买台电脑，主要是打游戏，预算5000-7000，请推荐' 请：1)提取关键需求 2)识别模糊点 3)追问确认 4)给出推荐。", "answer_type": "noisy_input"},
    {"question": "上下文容错：用户说：'它不好用。'（无前文）分析用户表达问题，给出回应策略。", "answer_type": "context_error"},
    {"question": "逻辑容错：用户：'用Python写排序算法，从大到小，不考虑时间复杂度，支持字符串，告诉我为什么选这个算法' 分析要求中的逻辑矛盾和冗余。", "answer_type": "requirement_contradiction"},
    {"question": "跨语言处理：用户输入：'I want to buy 一个 phone，预算 2000-3000 yuan' 分析输入特点并给出回答。", "answer_type": "code_mixing"},
    {"question": "语义消歧：'他学习雷锋好榜样'——几个可能解释？分别说明。", "answer_type": "word_sense"},
    {"question": "隐喻理解：'生活就像一盒巧克力'——表达什么？与'生活是一场旅行'有何异同？", "answer_type": "metaphor"},
    {"question": "情感分析：分析句子情感强度(1-10)和类型：1.这产品还行吧 2.简直太垃圾了 3.勉强能用 4.超乎想象的好 5.一般般", "answer_type": "sentiment"},
    {"question": "讽刺识别：'哇，你真是聪明绝顶啊，把简单的事情搞这么复杂！'分析真正含义和说话者态度。", "answer_type": "sarcasm"},
    {"question": "指代消解：'张伟告诉他妻子他要出差三天。他第二天就走了。'分析'他'分别指代谁？有什么歧义？", "answer_type": "coreference"},
]

CODE_QUESTIONS = [
    {"question": "【LRU缓存】用Python实现LRU缓存，get和put方法，时间复杂度O(1)。", "answer_type": "lru_cache"},
    {"question": "【发布订阅】用JS实现发布-订阅模式，subscribe、unsubscribe、publish方法。", "answer_type": "pub_sub"},
    {"question": "【感知机】用Python实现单层感知机神经网络，包含前向传播和反向传播。", "answer_type": "perceptron"},
    {"question": "【复杂SQL】员工表employees(id, name, department_id, salary, hire_date)。查询各部门工资最高的前3名，按部门排序。", "answer_type": "complex_sql"},
    {"question": "【红黑树】用Python实现红黑树插入操作，正确旋转和变色。", "answer_type": "red_black_tree"},
    {"question": "【Bug修复】以下Python代码有bug，找出并修复：def find_max(numbers): max_num=0; for i in range(len(numbers)): if numbers[i]>max_num: max_num=numbers[i]; return max_num; print(find_max([-1,-5,-3])) 期望-1", "answer_type": "bug_fix"},
    {"question": "【异步修复】修复以下Promise代码：async function fetchData() { const response = await fetch('/api/data'); const data = await response.json(); return data; } fetchData().then(data => console.log(data));", "answer_type": "async_fix"},
    {"question": "【竞态修复】Go代码存在竞态条件：var counter int; func increment() { counter++ }; func main() { for i:=0; i<1000; i++ { go increment() }; time.Sleep(time.Second); fmt.Println(counter) }", "answer_type": "race_condition"},
    {"question": "【SQL修复】修复SQL：SELECT department, AVG(salary) FROM employees WHERE AVG(salary)>5000 GROUP BY department; 说明问题并提供正确写法。", "answer_type": "sql_fix"},
    {"question": "【效率优化】优化代码：import multiprocessing; def process_item(item): return item*2; data=[1,2,3,4,5]; with multiprocessing.Pool(4) as pool: results=pool.map(process_item, data)", "answer_type": "optimization_fix"},
    {"question": "【字典树】用Python实现Trie树，insert、search、startsWith方法。", "answer_type": "trie"},
    {"question": "【堆排序】用Python手写堆排序过程，不能用heapq库。", "answer_type": "heap_sort"},
    {"question": "【二分变体】在旋转数组[4,5,6,7,0,1,2]中查找0，返回索引或-1。", "answer_type": "binary_search"},
    {"question": "【拓扑排序】用Python实现Kahn算法拓扑排序，返回结果或检测环。", "answer_type": "topological_sort"},
    {"question": "【LCS字符串】用Python实现最长公共子序列算法，返回LCS字符串（不仅长度）。", "answer_type": "lcs_string"},
    {"question": "【Token Bucket】用Python实现Token Bucket限流器，限速100请求/秒，允许突发。", "answer_type": "rate_limiter"},
    {"question": "【生产者-消费者】用Python实现，队列线程安全，最大容量100。", "answer_type": "producer_consumer"},
    {"question": "【正则匹配】匹配中国手机号（1开头，3-9位，共11位）。验证：13800138000, 18912345678, 12345678901, 1501234567, +8615012345678", "answer_type": "regex_mobile"},
    {"question": "【Pandas处理】读取CSV 'sales.csv'，计算每月总销售额，找出最高产品类别，描述月度趋势。", "answer_type": "pandas"},
    {"question": "【复杂度分析】分析以下代码时间/空间复杂度并优化：def duplicate(arr): for i in range(len(arr)): for j in range(i+1,len(arr)): if arr[i]==arr[j]: return True; return False", "answer_type": "complexity_analysis"},
]

print(f"[{datetime.now().strftime('%H:%M:%S')}] [INIT] 题目库加载完成：推理{len(REASONING_QUESTIONS)}题，语言{len(LANGUAGE_QUESTIONS)}题，代码{len(CODE_QUESTIONS)}题，共{len(REASONING_QUESTIONS)+len(LANGUAGE_QUESTIONS)+len(CODE_QUESTIONS)}题", flush=True)


# ==================== 评测器 ====================

class LLMEvaluator:
    def __init__(self, api_url: str, model_name: str):
        self.api_url = api_url.rstrip('/')
        self.model_name = model_name
        self.results = {
            "reasoning": {"scores": [], "response_times": []},
            "language": {"scores": [], "response_times": []},
            "code": {"scores": [], "response_times": []}
        }

    def call_api(self, messages: List[Dict], timeout: int = 300) -> Tuple[str, float]:
        ollama_payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7}
        }
        start_time = time.time()
        try:
            response = requests.post(self.api_url, json=ollama_payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if "message" in data:
                content = data["message"].get("content", str(data))
            elif "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]
            else:
                content = str(data)
        except Exception as e:
            raise Exception(f"API调用失败: {e}")
        return content, time.time() - start_time

    def evaluate_response(self, question: Dict, response: str) -> int:
        score = 0
        answer_type = question.get("answer_type", "")
        response_lower = response.lower()
        if len(response) > 100:
            score += 20
        if "步骤" in response or "because" in response_lower or "therefore" in response_lower:
            score += 20
        if any(kw in response_lower for kw in ["解", "答案", "result", "solution", "分析"]):
            score += 15
        if "def " in response_lower or "function" in response_lower or "select" in response_lower:
            score += 20
        if "return" in response_lower or "where" in response_lower or "class" in response_lower:
            score += 15
        if any(kw in response_lower for kw in ["错误", "不对", "问题", "修复", "fix", "bug"]):
            score += 10
        return min(max(score, 0), 100)

    def test_category(self, questions: List[Dict], category_key: str, category_name: str) -> Dict:
        total_score = 0
        response_times = []
        total_q = len(questions)
        for idx, q in enumerate(questions, 1):
            messages = [
                {"role": "system", "content": "你是一个智能助手，请准确简洁地回答问题。"},
                {"role": "user", "content": q['question']}
            ]
            try:
                response, response_time = self.call_api(messages)
                response_times.append(response_time)
                score = self.evaluate_response(q, response)
                total_score += score
                self.results[category_key]["scores"].append(score)
                self.results[category_key]["response_times"].append(response_time)
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] [{category_name}] {idx}/{total_q} | 得分:{score:3d} | 耗时:{response_time:6.1f}s | 累计待测:{total_q-idx}", flush=True)
            except Exception as e:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] [{category_name}] {idx}/{total_q} | 错误: {e}", flush=True)
                response_times.append(0)
        avg_score = total_score / len(questions) if questions else 0
        return {"average_score": avg_score, "average_response_time": sum(response_times)/len(response_times) if response_times else 0}

    def evaluate(self) -> Dict:
        results = {}
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 开始测试推理能力({len(REASONING_QUESTIONS)}题)...", flush=True)
        results["reasoning"] = self.test_category(REASONING_QUESTIONS, "reasoning", "推理")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 推理完成: {results['reasoning']['average_score']:.1f}/100", flush=True)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 开始测试语言能力({len(LANGUAGE_QUESTIONS)}题)...", flush=True)
        results["language"] = self.test_category(LANGUAGE_QUESTIONS, "language", "语言")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 语言完成: {results['language']['average_score']:.1f}/100", flush=True)
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 开始测试代码能力({len(CODE_QUESTIONS)}题)...", flush=True)
        results["code"] = self.test_category(CODE_QUESTIONS, "code", "代码")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 代码完成: {results['code']['average_score']:.1f}/100", flush=True)
        
        total_score = sum(r["average_score"] for r in results.values()) / 3
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{self.model_name}] 测试完成 | 综合:{total_score:.1f}/100", flush=True)
        
        return {
            "model": self.model_name,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "reasoning": results["reasoning"],
            "language": results["language"],
            "code": results["code"],
            "overall_score": total_score,
            "avg_response_time": sum(r["average_response_time"] for r in results.values()) / 3
        }


MODELS = [
    "qwen2.5:14b",
    "deepseek-r1:14b",
    "qwen3:14b",
    "erwan2/DeepSeek-R1-Distill-Qwen-14B:latest",
    "gemma3:27b",
    "deepseek-r1:32b",
    "qwq:32b"
]


def generate_html_report(all_results: List[Dict]) -> str:
    sorted_results = sorted(all_results, key=lambda x: x["overall_score"], reverse=True)
    def get_color(score):
        if score >= 90: return "#4CAF50"
        if score >= 80: return "#8BC34A"
        if score >= 70: return "#FFEB3B"
        if score >= 60: return "#FF9800"
        return "#f44336"
    def get_level(score):
        if score >= 90: return "S级 - 卓越"
        if score >= 80: return "A级 - 优秀"
        if score >= 70: return "B级 - 良好"
        if score >= 60: return "C级 - 一般"
        return "D级 - 待提升"
    rows = ""
    for i, r in enumerate(sorted_results, 1):
        rows += f"""
        <tr>
            <td>{i}</td>
            <td><strong>{r['model']}</strong></td>
            <td style="background:{get_color(r['reasoning']['average_score'])};color:white;font-weight:bold">{r['reasoning']['average_score']:.1f}</td>
            <td style="background:{get_color(r['language']['average_score'])};color:white;font-weight:bold">{r['language']['average_score']:.1f}</td>
            <td style="background:{get_color(r['code']['average_score'])};color:white;font-weight:bold">{r['code']['average_score']:.1f}</td>
            <td style="background:{get_color(r['overall_score'])};color:white;font-weight:bold;font-size:1.1em">{r['overall_score']:.1f}</td>
            <td>{r['avg_response_time']:.2f}s</td>
            <td><strong>{get_level(r['overall_score'])}</strong></td>
        </tr>"""
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>大模型智商评测报告（强化版）</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 40px; border-radius: 20px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }}
        h1 {{ color: #333; text-align: center; font-size: 2.5em; margin-bottom: 10px; }}
        .subtitle {{ text-align: center; color: #666; margin-bottom: 40px; }}
        .stats {{ display: flex; justify-content: space-around; margin: 30px 0; flex-wrap: wrap; gap: 20px; }}
        .stat-box {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px 40px; border-radius: 15px; text-align: center; min-width: 150px; }}
        .stat-box .val {{ font-size: 2.5em; font-weight: bold; }}
        .stat-box .lbl {{ font-size: 1em; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px 8px; text-align: center; border: 1px solid #ddd; font-size: 0.95em; }}
        th {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
        .footer {{ text-align: center; color: #999; margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧠 大模型智商评测报告（强化版）</h1>
        <p class="subtitle">测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 共{len(REASONING_QUESTIONS)+len(LANGUAGE_QUESTIONS)+len(CODE_QUESTIONS)}题/模型 | 60题×7模型</p>
        <div class="stats">
            <div class="stat-box"><div class="val">{len(all_results)}</div><div class="lbl">测试模型</div></div>
            <div class="stat-box"><div class="val">{sum(r['overall_score'] for r in all_results)/len(all_results):.1f}</div><div class="lbl">平均得分</div></div>
            <div class="stat-box"><div class="val">{max(r['overall_score'] for r in all_results):.1f}</div><div class="lbl">最高得分</div></div>
            <div class="stat-box"><div class="val">{min(r['overall_score'] for r in all_results):.1f}</div><div class="lbl">最低得分</div></div>
        </div>
        <table>
            <thead><tr><th>排名</th><th>模型</th><th>推理(20)</th><th>语言(20)</th><th>代码(20)</th><th>综合</th><th>响应</th><th>等级</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
        <div class="footer">
            <p>📚 强化版测试：推理(数学+逻辑+规划)、语言(语法+阅读+容错)、代码(编写+修复+算法)</p>
        </div>
    </div>
</body>
</html>"""
    return html


def main():
    api_url = "http://localhost:11434/api/chat"
    all_results = []
    
    print("="*80, flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [START] 开始强化版评测", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [CONFIG] API: {api_url}", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [CONFIG] 模型数: {len(MODELS)}", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [CONFIG] 每模型题目数: 推理{len(REASONING_QUESTIONS)} + 语言{len(LANGUAGE_QUESTIONS)} + 代码{len(CODE_QUESTIONS)} = {len(REASONING_QUESTIONS)+len(LANGUAGE_QUESTIONS)+len(CODE_QUESTIONS)}题", flush=True)
    print("="*80, flush=True)
    
    for model_idx, model in enumerate(MODELS, 1):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [MODEL {model_idx}/{len(MODELS)}] 开始测试模型: {model}", flush=True)
        try:
            evaluator = LLMEvaluator(api_url, model)
            result = evaluator.evaluate()
            all_results.append(result)
        except Exception as e:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [ERROR] 模型 {model} 测试失败: {e}", flush=True)
            all_results.append({"model": model, "overall_score": 0, "avg_response_time": 0, "reasoning": {"average_score": 0}, "language": {"average_score": 0}, "code": {"average_score": 0}})
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [GENERATING] 生成HTML报告...", flush=True)
    html = generate_html_report(all_results)
    with open("llm_evaluation_enhanced.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("\n" + "="*80, flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [COMPLETE] 评测完成！", flush=True)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [OUTPUT] 报告文件: llm_evaluation_enhanced.html", flush=True)
    print("="*80, flush=True)
    
    print("\n🏆 综合排行榜:", flush=True)
    for i, r in enumerate(sorted(all_results, key=lambda x: x["overall_score"], reverse=True), 1):
        print(f"  {i}. {r['model']}: {r['overall_score']:.1f}/100", flush=True)


if __name__ == "__main__":
    main()
