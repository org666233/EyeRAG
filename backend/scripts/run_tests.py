#!/usr/bin/env python3
"""
眼科医疗知识问答系统 - 自动化测试运行脚本

使用方法:
  # 运行所有测试（不含 LLM 调用）
  python scripts/run_tests.py

  # 运行所有测试（含 LLM 测试）
  python scripts/run_tests.py --with-llm

  # 仅运行单元测试
  python scripts/run_tests.py --unit-only

  # 仅运行集成测试
  python scripts/run_tests.py --integration-only

  # 仅运行压力测试（需服务已启动）
  python scripts/run_tests.py --stress

  # 生成覆盖率报告
  python scripts/run_tests.py --coverage

  # 查看帮助
  python scripts/run_tests.py --help
"""

import subprocess
import sys
import os
import json
import time
import argparse
from pathlib import Path
from datetime import datetime

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent.resolve()


def run_command(cmd: list[str], description: str, env=None) -> int:
    """运行命令并打印输出"""
    print(f"\n{'=' * 70}")
    print(f"  {description}")
    print(f"{'=' * 70}")
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    print()

    result = subprocess.run(
        cmd,
        cwd=BACKEND_DIR,
        env=env or os.environ.copy(),
    )
    return result.returncode


def check_service(host: str, port: int, timeout: int = 30) -> bool:
    """检查服务是否可用"""
    import socket
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def generate_report(
    test_type: str,
    passed: int,
    failed: int,
    skipped: int,
    duration: float,
    output_file: str = None,
):
    """生成 JSON 格式的测试结果报告"""
    report = {
        "timestamp": datetime.now().isoformat(),
        "test_type": test_type,
        "summary": {
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "total": passed + failed + skipped,
            "duration_seconds": round(duration, 2),
            "success_rate": f"{100 * passed / max(passed + failed, 1):.1f}%",
        },
    }

    report_dir = BACKEND_DIR / "test_reports"
    report_dir.mkdir(exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_file = report_dir / f"test_report_{ts}.json"
    if output_file:
        report_file = report_dir / output_file

    with open(report_file, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n  报告已保存: {report_file}")
    return report_file


def run_unit_tests(with_llm: bool, coverage: bool) -> tuple[int, float]:
    """运行单元测试"""
    print("\n\n" + "=" * 70)
    print("  第一部分：单元测试（UNIT TESTS）")
    print("  覆盖模块：配置、认证服务、BM25、重排序、安全检查、Prompt模板")
    print("=" * 70)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/unit/",
        "-v",
        "--tb=short",
        "--color=yes",
    ]

    if coverage:
        cmd += [
            "--cov=app",
            "--cov-report=term-missing",
            f"--cov-report=html:{BACKEND_DIR}/test_reports/coverage_unit",
            "--cov-report=json",
        ]

    # 单元测试默认排除 LLM 测试（标记为 integration + llm）
    if not with_llm:
        cmd += ["-m", "not llm"]

    start = time.time()
    code = run_command(cmd, "单元测试")
    duration = time.time() - start

    return code, duration


def run_integration_tests(with_llm: bool, coverage: bool) -> tuple[int, float]:
    """运行集成测试"""
    print("\n\n" + "=" * 70)
    print("  第二部分：集成测试（INTEGRATION TESTS）")
    print("  覆盖模块：认证API、知识库API、会话管理API、聊天API")
    print("=" * 70)

    cmd = [
        sys.executable, "-m", "pytest",
        "tests/integration/",
        "-v",
        "--tb=short",
        "--color=yes",
        "-m", "integration",
    ]

    if coverage:
        cmd += [
            "--cov=app.api",
            "--cov-report=term-missing:skip-covered",
        ]

    # 如果不包含 LLM 测试，只运行标记为 no_llm 的
    if not with_llm:
        cmd += ["-m", "integration and not llm"]

    start = time.time()
    code = run_command(cmd, "集成测试")
    duration = time.time() - start

    return code, duration


def run_stress_tests(service_host: str, service_port: int, users: int, duration: str) -> int:
    """运行压力测试"""
    print("\n\n" + "=" * 70)
    print("  第三部分：压力测试（STRESS TESTS）")
    print("  工具：Locust")
    print("=" * 70)

    if not check_service(service_host, service_port):
        print(f"\n  警告: 服务 {service_host}:{service_port} 未启动")
        print("  请先启动后端服务后再运行压力测试")
        print(f"  启动命令: uvicorn app.main:app --reload --port {service_port}")
        return 1

    report_file = BACKEND_DIR / "test_reports" / f"stress_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

    cmd = [
        "locust",
        "-f", "tests/stress/locustfile.py",
        "--host", f"http://{service_host}:{service_port}",
        "--headless",
        "--html", str(report_file),
        "--csv", str(report_file.with_suffix('.csv')),
        "-u", str(users),
        "-t", duration,
    ]

    print(f"\n  压力测试参数:")
    print(f"    并发用户数: {users}")
    print(f"    持续时间: {duration}")
    print(f"    报告输出: {report_file}")

    code = run_command(cmd, f"压力测试 ({users} 用户, {duration})")
    return code


def run_all_tests(
    with_llm: bool = False,
    coverage: bool = False,
    stress: bool = False,
    unit_only: bool = False,
    integration_only: bool = False,
    stress_users: int = 20,
    stress_duration: str = "60s",
    service_host: str = "localhost",
    service_port: int = 8000,
):
    """运行所有测试"""
    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║      眼科医疗知识问答系统 - 自动化测试套件                        ║
║      测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                         ║
╚══════════════════════════════════════════════════════════════════╝
""")

    if with_llm:
        print("  ⚠️  注意: 包含 LLM 调用测试，将消耗 API Token！")
    else:
        print("  ✅ 仅运行非 LLM 测试")
    print()

    total_start = time.time()
    results = {}
    exit_code = 0

    # 1. 单元测试
    if not integration_only:
        code, duration = run_unit_tests(with_llm, coverage)
        results["unit"] = {"code": code, "duration": duration}
        if code != 0:
            exit_code = code

    # 2. 集成测试
    if not unit_only:
        code, duration = run_integration_tests(with_llm, coverage)
        results["integration"] = {"code": code, "duration": duration}
        if code != 0:
            exit_code = code

    # 3. 压力测试
    if stress:
        code = run_stress_tests(service_host, service_port, stress_users, stress_duration)
        results["stress"] = {"code": code}
        if code != 0:
            exit_code = code

    # 生成汇总报告
    total_duration = time.time() - total_start

    print(f"""
╔══════════════════════════════════════════════════════════════════╗
║                       测试执行汇总                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  单元测试:       {'✅ 通过' if results.get('unit', {}).get('code') == 0 else '❌ 失败':18} ({results.get('unit', {}).get('duration', 0):.1f}s)        ║
║  集成测试:       {'✅ 通过' if results.get('integration', {}).get('code') == 0 else '❌ 失败':18} ({results.get('integration', {}).get('duration', 0):.1f}s)        ║
║  压力测试:       {'✅ 通过' if results.get('stress', {}).get('code') == 0 else '❌ 未运行' if 'stress' not in results else '❌ 失败':18}                       ║
╠══════════════════════════════════════════════════════════════════╣
║  总耗时:         {total_duration:.1f}s                                             ║
║  报告目录:       test_reports/                                   ║
╚══════════════════════════════════════════════════════════════════╝
""")

    return exit_code


def main():
    parser = argparse.ArgumentParser(
        description="自动化测试运行脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python scripts/run_tests.py                        # 仅运行非 LLM 测试
  python scripts/run_tests.py --with-llm             # 含 LLM 测试
  python scripts/run_tests.py --coverage              # 生成覆盖率报告
  python scripts/run_tests.py --stress                # 运行压力测试
  python scripts/run_tests.py --unit-only             # 仅单元测试
  python scripts/run_tests.py --integration-only      # 仅集成测试

报告输出:
  - pytest HTML 报告: backend/test_reports/pytest_report_<时间戳>.html
  - 覆盖率报告:     backend/test_reports/coverage_*/
  - 压力测试报告:   backend/test_reports/stress_report_<时间戳>.html
  - JSON 汇总:     backend/test_reports/test_report_<时间戳>.json
        """,
    )
    parser.add_argument("--with-llm", action="store_true",
                        help="包含需要调用 LLM 的测试（会消耗 token）")
    parser.add_argument("--coverage", action="store_true",
                        help="生成代码覆盖率报告")
    parser.add_argument("--stress", action="store_true",
                        help="运行压力测试（需服务已启动）")
    parser.add_argument("--unit-only", action="store_true",
                        help="仅运行单元测试")
    parser.add_argument("--integration-only", action="store_true",
                        help="仅运行集成测试")
    parser.add_argument("--stress-users", type=int, default=20,
                        help="压力测试并发用户数（默认 20）")
    parser.add_argument("--stress-duration", type=str, default="60s",
                        help="压力测试持续时间（默认 60s）")
    parser.add_argument("--host", type=str, default="localhost",
                        help="后端服务地址（默认 localhost）")
    parser.add_argument("--port", type=int, default=8000,
                        help="后端服务端口（默认 8000）")

    args = parser.parse_args()

    exit_code = run_all_tests(
        with_llm=args.with_llm,
        coverage=args.coverage,
        stress=args.stress,
        unit_only=args.unit_only,
        integration_only=args.integration_only,
        stress_users=args.stress_users,
        stress_duration=args.stress_duration,
        service_host=args.host,
        service_port=args.port,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
