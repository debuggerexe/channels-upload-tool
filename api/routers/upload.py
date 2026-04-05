"""
上传控制路由
提供上传任务的开始、停止和状态查询接口
"""

import asyncio
import subprocess
import sys
import signal
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

BASE_DIR = Path(__file__).parent.parent.parent
UPLOAD_SCRIPT = BASE_DIR / "upload_wechat_videos.py"

# 全局上传任务状态
upload_process: Optional[asyncio.subprocess.Process] = None
upload_task: Optional[asyncio.Task] = None
upload_status = {
    "is_running": False,
    "mode": None,
    "publish_mode": None,
    "current_video": None,
    "progress": 0,
    "logs": []
}


class UploadRequest(BaseModel):
    mode: str  # "local" 或 "notion"
    publish_mode: str  # "1"=定时发布, "2"=保存草稿


@router.get("/status")
async def get_upload_status():
    """获取上传任务状态"""
    return upload_status


@router.post("/start")
async def start_upload(request: UploadRequest, background_tasks: BackgroundTasks):
    """开始上传任务"""
    global upload_task, upload_status
    
    if upload_status["is_running"]:
        raise HTTPException(status_code=400, detail="上传任务已在运行中")
    
    if not UPLOAD_SCRIPT.exists():
        raise HTTPException(status_code=500, detail="上传脚本不存在")
    
    # 重置状态
    upload_status["is_running"] = True
    upload_status["mode"] = request.mode
    upload_status["publish_mode"] = request.publish_mode
    upload_status["current_video"] = None
    upload_status["progress"] = 0
    upload_status["logs"] = ["开始上传任务..."]
    
    # 在后台运行上传任务
    background_tasks.add_task(run_upload, request.mode, request.publish_mode)
    
    return {"success": True, "message": "上传任务已启动"}


@router.post("/stop")
async def stop_upload():
    """停止上传任务"""
    global upload_process, upload_task, upload_status
    
    if not upload_status["is_running"]:
        return {"success": True, "message": "没有正在运行的上传任务"}
    
    # 终止子进程
    if upload_process and upload_process.returncode is None:
        try:
            # 先尝试优雅终止
            upload_process.terminate()
            # 给进程一些时间退出
            await asyncio.wait_for(upload_process.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            # 超时则强制杀死
            try:
                upload_process.kill()
                await upload_process.wait()
            except Exception:
                pass
        except Exception as e:
            upload_status["logs"].append(f"⚠️ 终止进程时出错: {str(e)}")
    
    # 取消任务
    if upload_task and not upload_task.done():
        upload_task.cancel()
        try:
            await upload_task
        except asyncio.CancelledError:
            pass
    
    upload_status["is_running"] = False
    upload_status["logs"].append("🛑 上传任务已停止")
    
    return {"success": True, "message": "上传任务已停止"}


async def run_upload(mode: str, publish_mode: str):
    """在后台运行上传脚本"""
    global upload_process, upload_task, upload_status
    
    upload_task = asyncio.current_task()
    
    try:
        # 构建命令
        cmd = [sys.executable, str(UPLOAD_SCRIPT), "--mode", mode, "--publish", publish_mode, "--no-interactive"]
        
        # 运行子进程
        upload_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(BASE_DIR)
        )
        
        upload_status["logs"].append(f"启动进程: {UPLOAD_SCRIPT.name}")
        
        # 读取输出
        while True:
            # 检查是否被取消
            if asyncio.current_task().cancelled():
                break
            
            # 使用 wait_for 来允许检查取消状态
            try:
                line = await asyncio.wait_for(upload_process.stdout.readline(), timeout=0.5)
            except asyncio.TimeoutError:
                # 检查进程是否还在运行
                if upload_process.returncode is not None:
                    break
                continue
            
            if not line:
                break
            
            message = line.decode('utf-8').strip()
            if message:
                upload_status["logs"].append(message)
                # 限制日志条数
                if len(upload_status["logs"]) > 500:
                    upload_status["logs"] = upload_status["logs"][-500:]
        
        # 等待进程完成（如果还在运行）
        if upload_process.returncode is None:
            await upload_process.wait()
        
        if upload_process.returncode == 0:
            upload_status["logs"].append("✅ 上传任务完成")
        elif upload_process.returncode == -signal.SIGTERM or upload_process.returncode == -15:
            upload_status["logs"].append("🛑 上传任务被终止")
        else:
            upload_status["logs"].append(f"❌ 上传任务失败 (返回码: {upload_process.returncode})")
    
    except asyncio.CancelledError:
        upload_status["logs"].append("🛑 上传任务被取消")
        # 确保子进程也被终止
        if upload_process and upload_process.returncode is None:
            try:
                upload_process.kill()
                await upload_process.wait()
            except Exception:
                pass
        raise
    
    except Exception as e:
        upload_status["logs"].append(f"❌ 上传任务异常: {str(e)}")
    
    finally:
        upload_status["is_running"] = False
        upload_process = None
        upload_task = None
