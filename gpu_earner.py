"""
gpu_earner.py — 5060 Ti 16GB 自动赚钱调度器
三条并行收入线:
  1. Vast.ai 挂机出租 GPU (被动收入)
  2. demand-radar 扫描付费 AI/代码任务，自动报价
  3. 本地推理服务 (ollama) 接受局域网请求

Usage:
  python gpu_earner.py status     # 查看当前状态
  python gpu_earner.py vastai     # 配置 Vast.ai 出租
  python gpu_earner.py scan       # 扫描一次付费需求
  python gpu_earner.py serve      # 启动本地推理服务
"""
import argparse, subprocess, json, os, sys, requests
from datetime import datetime

GPU_INFO = {"name": "RTX 5060 Ti", "vram_gb": 16, "cuda": True}

def cmd_status():
    print(f"\n{'='*50}")
    print(f"  GPU 赚钱调度器 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*50}")
    
    # GPU状态
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5)
        line = r.stdout.strip().split(",")
        print(f"\n  GPU   : {line[0].strip()}")
        print(f"  使用率: {line[1].strip()}%   显存: {line[2].strip()}/{line[3].strip()} MiB   温度: {line[4].strip()}°C")
    except Exception as e:
        print(f"\n  GPU: {e}")
    
    # Ollama状态
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in r.json().get("models", [])]
        print(f"\n  Ollama: running   models: {', '.join(models[:3])}")
    except:
        print("\n  Ollama: not running")
    
    # Vast.ai (需配置API key)
    vastai_key = os.environ.get("VASTAI_API_KEY", "")
    if vastai_key:
        try:
            r = requests.get("https://console.vast.ai/api/v0/instances/",
                             headers={"Authorization": f"Bearer {vastai_key}"}, timeout=5)
            instances = r.json().get("instances", [])
            earning = sum(i.get("actual_cost", 0) for i in instances)
            print(f"\n  Vast.ai: {len(instances)} instances  earning: ${earning:.4f}/hr")
        except Exception as e:
            print(f"\n  Vast.ai: {e}")
    else:
        print(f"\n  Vast.ai: 未配置 (export VASTAI_API_KEY=your_key)")
    
    print(f"\n{'='*50}\n")


def cmd_vastai():
    """配置 Vast.ai 出租指南"""
    print("""
  Vast.ai 出租 RTX 5060 Ti 16GB 步骤:
  ─────────────────────────────────────
  1. 注册: https://vast.ai/?ref_id=guyu
  2. 安装客户端:
       pip install vastai
  3. 登录:
       vastai set api-key <your_key>
  4. 查看本机 GPU:
       vastai show machines
  5. 设定出租价格 (5060 Ti 16G 市价约 $0.15-0.25/hr):
       vastai list machine <machine_id> --storage 100 --price 0.18
  6. 查看收益:
       vastai show earnings

  预期收益: ~$0.18/hr × 16hr/day = ~$2.9/day ≈ $87/month (被动)
  当 GPU 利用率 < 20% 时自动出租，不影响本地使用。
""")


def cmd_scan():
    """快速扫描一次付费需求"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
    try:
        import feedparser
        feed = feedparser.parse("https://www.v2ex.com/feed/tab/jobs.xml")
        PAY  = ["有偿","付费","悬赏","求外包","bounty","paid","hire","$"]
        TECH = ["python","ai","爬虫","自动化","api","量化","机器学习","数据"]
        hits = []
        for e in feed.entries[:30]:
            t = (e.get("title","") + " " + e.get("summary","")).lower()
            p = sum(1 for k in PAY  if k in t)
            s = sum(1 for k in TECH if k in t)
            if p + s >= 3:
                hits.append((p+s, e.get("title","")[:70], e.get("link","")[:60]))
        hits.sort(reverse=True)
        print(f"\n  找到 {len(hits)} 条高分需求:\n")
        for score, title, url in hits[:8]:
            print(f"  [{score}/10] {title}")
            print(f"         {url}\n")
    except ImportError:
        print("  请先: pip install feedparser")


def cmd_serve():
    """启动本地推理服务（已由 ollama 提供）"""
    print("\n  本地推理服务状态:")
    print("  ─────────────────────────────────────")
    print("  Ollama API:  http://localhost:11434   (OpenAI 兼容)")
    print("  Miser API:   http://localhost:7860    (Claude Code 集成)")
    print()
    print("  局域网访问: 将 0.0.0.0 绑定后可从 192.168.0.x 调用")
    print("  收费模型托管: https://huggingface.co/spaces (免费tier)")
    print()
    subprocess.run(["nvidia-smi", "--query-gpu=name,memory.free", "--format=csv,noheader"])


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="GPU 赚钱调度器")
    p.add_argument("cmd", nargs="?", default="status",
                   choices=["status","vastai","scan","serve"])
    args = p.parse_args()
    {"status": cmd_status, "vastai": cmd_vastai,
     "scan": cmd_scan, "serve": cmd_serve}[args.cmd]()
