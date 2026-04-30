"""
Locust 压力测试脚本
测试系统在多用户并发场景下的性能表现

运行方式:
  # 启动后端服务后，在 backend/ 目录下运行:
  locust -f tests/stress/test_stress.py --host=http://localhost:8000

  # 或无 UI 模式（CI/自动化）:
  locust -f tests/stress/test_stress.py --host=http://localhost:8000 \
         --headless -u 50 -r 10 -t 60s --html=report.html

参数说明:
  -u 50   : 50 个并发用户
  -r 10   : 每秒启动 10 个用户
  -t 60s  : 运行 60 秒
  --html  : 生成 HTML 报告
"""

import random
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import json


# ─────────────────────────────────────────────────────────────────────────────
# 测试数据
# ─────────────────────────────────────────────────────────────────────────────

TEST_QUESTIONS = [
    "青光眼有哪些主要症状？",
    "白内障手术是怎么做的？",
    "糖尿病视网膜病变如何治疗？",
    "干眼症是怎么引起的？",
    "黄斑变性的早期症状是什么？",
    "LASIK 激光手术安全吗？",
    "青光眼手术有哪些风险？",
    "如何预防儿童近视？",
    "角膜移植需要多长时间恢复？",
    "葡萄膜炎是什么疾病？",
]

# 注册用的随机用户名后缀
_counter = 0


def next_username():
    global _counter
    _counter += 1
    return f"stresstest_{_counter}"


# ─────────────────────────────────────────────────────────────────────────────
# 公开接口压力测试（无需登录）
# ─────────────────────────────────────────────────────────────────────────────


class PublicUser(HttpUser):
    """
    测试公开可访问的接口（知识库统计）。
    这些接口无需认证，可模拟未登录访客。
    """
    wait_time = between(0.5, 2.0)

    @task(5)
    def get_knowledge_stats(self):
        """获取知识库统计（高频）"""
        with self.client.get(
            "/api/knowledge/stats",
            catch_response=True,
            name="/api/knowledge/stats",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "total_chunks" in data:
                        response.success()
                    else:
                        response.failure("Invalid response format")
                except Exception:
                    response.failure("JSON parse error")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def search_knowledge(self):
        """检索接口（不调用 LLM，纯向量检索）"""
        question = random.choice(TEST_QUESTIONS)
        with self.client.post(
            "/api/knowledge/search",
            json={"query": question, "top_k": 5},
            catch_response=True,
            name="/api/knowledge/search",
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "results" in data:
                        response.success()
                    else:
                        response.failure("Missing results field")
                except Exception:
                    response.failure("JSON parse error")
            elif response.status_code == 401:
                response.success()  # 无认证可能返回 401，这是预期行为
            else:
                response.failure(f"HTTP {response.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 已认证用户压力测试
# ─────────────────────────────────────────────────────────────────────────────


class AuthenticatedUser(HttpUser):
    """
    测试需要认证的接口。
    每个虚拟用户在启动时注册自己的账号，
    在整个生命周期内使用同一账号。
    """
    wait_time = between(1.0, 3.0)

    def on_start(self):
        """启动时注册并登录，获取 token"""
        username = next_username()
        password = "StressTest123!"

        # 注册
        reg_response = self.client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": password,
                "real_name": "压测用户",
            },
        )

        if reg_response.status_code == 200:
            data = reg_response.json()
            self.token = data.get("access_token", "")
        else:
            # 账号可能已存在（重名），尝试登录
            login_response = self.client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
            if login_response.status_code == 200:
                self.token = login_response.json().get("access_token", "")
            else:
                self.token = ""

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    @task(10)
    def get_conversations(self):
        """获取会话列表（高频）"""
        with self.client.get(
            "/api/chat/conversations",
            headers=self.headers,
            catch_response=True,
            name="/api/chat/conversations",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Token expired or invalid")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(8)
    def get_knowledge_documents(self):
        """获取文档列表"""
        with self.client.get(
            "/api/knowledge/documents",
            headers=self.headers,
            catch_response=True,
            name="/api/knowledge/documents",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(5)
    def get_knowledge_stats(self):
        """获取知识库统计"""
        with self.client.get(
            "/api/knowledge/stats",
            catch_response=True,
            name="/api/knowledge/stats",
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(3)
    def save_message(self):
        """保存消息（创建会话）"""
        question = random.choice(TEST_QUESTIONS)
        with self.client.post(
            "/api/chat/messages",
            json={
                "question": question,
                "answer": f"这是对「{question}」的回答（压测场景）。",
                "sources": [],
            },
            headers=self.headers,
            catch_response=True,
            name="/api/chat/messages",
        ) as response:
            if response.status_code == 200:
                response.success()
            elif response.status_code == 401:
                response.failure("Token expired")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(2)
    def delete_conversation(self):
        """删除会话（清理测试数据）"""
        # 先获取会话列表
        response = self.client.get(
            "/api/chat/conversations",
            headers=self.headers,
        )
        if response.status_code != 200:
            return

        convs = response.json()
        if not convs:
            return

        # 随机删除一个会话
        conv_id = random.choice(convs)["id"]
        with self.client.delete(
            f"/api/chat/conversations/{conv_id}",
            headers=self.headers,
            catch_response=True,
            name="/api/chat/conversations DELETE",
        ) as del_resp:
            if del_resp.status_code in [200, 404]:
                del_resp.success()
            else:
                del_resp.failure(f"HTTP {del_resp.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# LLM 问答压力测试（高 token 消耗，单独运行）
# ─────────────────────────────────────────────────────────────────────────────


class ChatUser(HttpUser):
    """
    测试问答接口（含 LLM 调用）。
    此测试会消耗大量 token，建议单独运行。
    权重设置为较低值，默认压测时不会频繁触发。

    运行专注此测试:
      locust -f tests/stress/test_stress.py --host=http://localhost:8000 \
             --headless -u 10 -r 2 -t 120s \
             --tags chat_llm --html=chat_report.html
    """
    wait_time = between(5.0, 15.0)  # 较长的等待时间，模拟真实用户思考

    def on_start(self):
        """登录获取 token"""
        username = next_username()
        password = "ChatTest123!"
        reg_resp = self.client.post(
            "/api/auth/register",
            json={"username": username, "password": password},
        )
        if reg_resp.status_code == 200:
            self.token = reg_resp.json().get("access_token", "")
        else:
            login_resp = self.client.post(
                "/api/auth/login",
                json={"username": username, "password": password},
            )
            self.token = login_resp.json().get("access_token", "")

        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        self.conv_id = None

    @task
    def chat_sync(self):
        """
        非流式问答压力测试。
        每个请求约消耗 500-2000 token。
        """
        question = random.choice(TEST_QUESTIONS)
        payload = {"question": question, "stream": False}
        if self.conv_id:
            payload["conversation_id"] = self.conv_id

        with self.client.post(
            "/api/chat/completions",
            json=payload,
            headers=self.headers,
            catch_response=True,
            name="/api/chat/completions [sync]",
            timeout=120,
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data and len(data["answer"]) > 0:
                        self.conv_id = data.get("conversation_id", self.conv_id)
                        response.success()
                    else:
                        response.failure("Empty or invalid answer")
                except Exception:
                    response.failure("JSON parse error")
            elif response.status_code == 401:
                response.failure("Unauthorized")
            elif response.status_code == 429:
                response.failure("Rate limited by LLM provider")
            else:
                response.failure(f"HTTP {response.status_code}")


# ─────────────────────────────────────────────────────────────────────────────
# 报告钩子：记录关键指标
# ─────────────────────────────────────────────────────────────────────────────

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    """每个请求完成后记录"""
    pass  # Locust 自带统计已经很完善，此处可扩展自定义指标


@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    """测试结束时输出摘要"""
    if hasattr(environment, "stats") and environment.stats.total:
        stats = environment.stats.total
        print("\n" + "=" * 60)
        print("  压力测试摘要")
        print("=" * 60)
        print(f"  总请求数   : {stats.num_requests}")
        print(f"  失败数     : {stats.num_failures}")
        print(f"  失败率     : {stats.fail_ratio * 100:.2f}%")
        print(f"  平均响应时间: {stats.avg_response_time:.2f} ms")
        print(f"  中位响应时间: {stats.get_response_time_percentile(0.5):.2f} ms")
        print(f"  P95 响应时间: {stats.get_response_time_percentile(0.95):.2f} ms")
        print(f"  P99 响应时间: {stats.get_response_time_percentile(0.99):.2f} ms")
        print(f"  最大响应时间: {stats.max_response_time:.2f} ms")
        print(f"  RPS        : {stats.total_rps:.2f}")
        print("=" * 60)
