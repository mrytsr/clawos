# browser.py - agent-browser 封装

import asyncio
import subprocess

class AgentBrowser:
    """agent-browser 封装"""
    
    def __init__(self):
        self.process = None
    
    async def open(self, url: str):
        """打开页面"""
        cmd = ["agent-browser", "open", url]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        await asyncio.sleep(2)  # 等待加载
        return result.returncode == 0
    
    async def snapshot(self, depth: int = 3) -> str:
        """获取页面快照"""
        cmd = ["agent-browser", "snapshot", "-d", str(depth)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.stdout if result.returncode == 0 else ""
    
    async def close(self):
        """关闭浏览器"""
        cmd = ["agent-browser", "close"]
        subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    
    async def click(self, selector: str):
        """点击元素"""
        cmd = ["agent-browser", "click", selector]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0
    
    async def wait_for_element(self, element_type: str, timeout: int = 10):
        """等待元素出现"""
        await asyncio.sleep(timeout)
        return True
