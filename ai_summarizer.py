from openai import OpenAI
import os
from typing import Dict, List
import json

class MarketSummarizer:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
        
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        else:
            self.client = None
            print("Warning: OPENAI_API_KEY not found in environment variables.")

    def summarize_market(self, stocks_data: List[Dict]) -> str:
        """
        Generates a summary of the market status for the provided stocks.
        """
        if not self.client:
            return "无法生成总结：未配置 OpenAI API Key。"

        if not stocks_data:
            return "没有股票数据可供总结。"

        # Prepare data for prompt
        # Simplify data to save tokens and reduce noise
        simple_data = []
        for s in stocks_data:
            if "error" in s:
                continue
            simple_data.append(f"{s['name']}({s['symbol']}): 价格 {s.get('price')}, 涨跌幅 {s.get('change_percent')}%")

        if not simple_data:
            return "无法获取有效的股票数据进行总结。"

        data_str = "\n".join(simple_data)
        
        prompt = f"""
        请根据以下股票今日行情数据，用中文写一段简短的市场分析总结。
        重点关注涨跌幅度较大的股票，并给出整体市场情绪的判断。
        
        数据列表：
        {data_str}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "在回答中使用纯文本，而不是使用markdown。你是一个专业的金融市场分析师。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"生成总结时出错: {e}"

    def summarize_overall_market(self, indices_data: List[Dict]) -> str:
        """
        Generates a summary of the overall market status based on major indices.
        """
        if not self.client:
            return "无法生成市场总结：未配置 OpenAI API Key。"

        if not indices_data:
            return "没有市场指数数据可供总结。"

        data_str = "\n".join([
             f"{item['name']}({item['market']}): 现价 {item.get('price', 0):.2f}, 涨跌幅 {item.get('change_percent', 0):.2f}%"
             for item in indices_data if "error" not in item
        ])
        
        prompt = f"""
        请根据以下主要市场指数的今日行情，用中文写一段简短的全球/区域股市行情综述。
        请分别点评中国市场（A股）和美国市场的表现。
        
        指数数据：
        {data_str}
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的金融市场分析师。请用简练的语言进行点评，无需罗列所有数据，着重分析趋势。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"生成市场总结时出错: {e}"
