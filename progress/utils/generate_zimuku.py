import asyncio
from openai import AsyncOpenAI
import platform
import os
import re
import json
import base64
from typing import List, Dict
import django
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mywebsite.settings")
django.setup()

client = AsyncOpenAI(
    api_key=settings.LLM_API_KEY,
    base_url=settings.LLM_API_BASE
)

# video_upload_path = os.path.join(settings.BASE_DIR, 'progress/static/upload.mp4')
file_dir = os.path.join(settings.BASE_DIR, 'progress', 'static')
os.makedirs(file_dir, exist_ok=True)


class GenerateZimuku:
    # 单例
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GenerateZimuku, cls).__new__(cls)
        return cls._instance

    def __init__(self, file_path=None, websocket=None):
        """
        初始化读取文件路径与 websocket 实例
        """
        if not hasattr(self, '_initialized'):
            if file_path is not None:
                self.file_path = file_path
                self.save_file_path = os.path.join(file_dir, file_path)
            if websocket is not None:
                self.websocket = websocket
            self._initialized = True  # 标记初始化

    async def _send_message(self, content, file_name=''):
        """
        socket 发送消息
        """
        if self.websocket:
            content = {'content': content, 'file': file_name}
            try:
                await self.websocket.send(json.dumps(content))
            except Exception as e:
                print(f"socket进度消息发送失败: {str(e)}")

    @staticmethod
    def encode_video(video_path):
        """
        视频编码为Base64
        """
        with open(video_path, "rb") as video_file:
            return base64.b64encode(video_file.read()).decode("utf-8")

    @staticmethod
    async def get_video_description_with_timestamps(self) -> str:
        """
        调用 qwen2.5-vl-72b-instruct 模型，返回带时间节点的视频描述
        """
        print(f"视频路径：{self.file_path}")
        video_base64 = GenerateZimuku.encode_video(self.file_path)

        completion = await client.chat.completions.create(
            model="qwen2.5-vl-72b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": [{
                        "type": "text",
                        "text": "你是一个专业的视频分析助手。请按时间顺序详细描述视频内容，并为每个关键场景标注时间戳（格式为[HH:MM:SS]）。"
                    }]
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "video_url",
                            "video_url": {"url": f"data:video/mp4;base64,{video_base64}"},
                        },
                        {
                            "type": "text",
                            "text": (
                                "请按时间顺序详细描述这段视频的内容，并为每个主要场景或变化标注准确的时间戳。\n"
                                "时间戳格式必须使用 [00:00:00] 的形式，放在每个段落开头。\n"
                                "描述应包括场景内容、人物动作、重要物体等信息。"
                            )
                        },
                    ],
                }
            ],
        )

        raw_description = completion.choices[0].message.content
        print("原始模型输出：", raw_description)

        # 解析时间戳和描述
        await self._send_message(f"视频解析已完成:")
        timestamped_descriptions = GenerateZimuku.parse_timestamps(raw_description)
        for item in timestamped_descriptions:
            timestamp = item['timestamp']
            description = item['description']
            print(f"[{timestamp}] {description}")
            await self._send_message(f"[{timestamp}] {description}")
        return raw_description

    @staticmethod
    def parse_timestamps(description: str) -> List[Dict[str, str]]:
        """
        解析带时间戳的描述文本，提取时间节点和对应描述
        """
        import re
        pattern = r'\[(\d{2}:\d{2}:\d{2})\](.*?)(?=\[\d{2}:\d{2}:\d{2}\]|$)'
        matches = re.findall(pattern, description, re.DOTALL)

        parsed = []
        for timestamp, desc in matches:
            parsed.append({
                "timestamp": timestamp.strip(),
                "description": desc.strip()
            })

        return parsed if parsed else [{"timestamp": "00:00:00", "description": description}]

    @staticmethod
    def extract_json_from_text(text):
        pattern = r'```json\n(.*?)\n```'
        match = re.search(pattern, text, re.DOTALL)
        if not match:
            raise ValueError("未找到 JSON 数据")
        json_str = match.group(1).strip()
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON 解析失败: {e}")

    @staticmethod
    async def task(self, question):
        print(f"Sending question: {question}")

        response = await client.chat.completions.create(
            messages=[
                {"role": "user", "content": question}
            ],
            model="qwen-plus",
        )
        print(f"Received answer: {response.choices[0].message.content}")
        zimuku_json = GenerateZimuku.extract_json_from_text(response.choices[0].message.content)
        await self._send_message(f"视频弹幕已生成：")
        for item in zimuku_json:
            await self._send_message(f"{item}")
        return zimuku_json

    async def generate_zimuku_task(self):
        await self._send_message(f"开始生成视频弹幕，请稍等...")
        video_description = await GenerateZimuku.get_video_description_with_timestamps(self)
        prompt = f"""
        请根据以下视频描述生成至少10条弹幕：{video_description}，要求如下：
        1. 生成 DPlayer 兼容的 JSON 弹幕数据
        2. 弹幕数据格式为数组，数组元素格式为[时间(秒), 类型(0（滚动）、1（顶部）、2（底部）), 颜色(十进制 RGB), "ID"(8位随机十六进制), "弹幕"(弹幕文本)]
        3. 弹幕必须匹配视频描述的关键情节和附近时间点
        4. 内容幽默有梗，长度2-15字
        """
        return await GenerateZimuku.task(self, prompt)
