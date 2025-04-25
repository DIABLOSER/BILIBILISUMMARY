# 在文件顶部确保正确加载环境变量
from dotenv import load_dotenv
load_dotenv()  # 加载.env文件

# 新增python-docx库导入（在文件顶部导入）
from docx import Document

#服务端测试
from flask import Flask, jsonify, request, send_file, Response, make_response
import requests
from flask_cors import CORS
import time
from io import BytesIO
import logging
import os
import json
import hashlib
import urllib.parse
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 数据库配置
DATABASE_URL = "sqlite:///summaries.db"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# 更新导入路径以符合 SQLAlchemy 2.0 的推荐用法
from sqlalchemy.orm import declarative_base
Base = declarative_base()

# 文档表模型
class VideoSummary(Base):
    __tablename__ = 'video_summaries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    video_id = Column(String(50), nullable=False)
    summary_text = Column(Text, nullable=False)  # 确保字段名与前端一致
    summary_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)

# 删除旧的数据库表并重新创建
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
#数据可视化部分依赖
import re
import jieba
from wordcloud import WordCloud
from io import BytesIO
import base64
import matplotlib.pyplot as plt

from concurrent.futures import ThreadPoolExecutor
app = Flask(__name__)

# 设置日志级别为 DEBUG
logging.basicConfig(level=logging.DEBUG)
# logging.basicConfig(level=logging.WARNING)
# 设置 Matplotlib 后端为 Agg
plt.switch_backend('Agg')
# 允许跨域请求，并支持携带凭证
CORS(
    app,
    supports_credentials=True,
    resources={r"/*": {
        "origins": ["http://localhost:5173"],  # 替换为你的前端域名
        "allow_headers": ["*"]
    }}
)
# Bilibili API 密钥（需定期更新）
APP_KEY = "aae92bc66f3edfab"
APP_SEC = "af125a0d5279fd576c1b4418a3e8276d"

# 生成签名
def generate_sign(params: dict) -> str:
    """生成 Bilibili API 签名"""
    params_str = ""
    for key in sorted(params.keys()):
        params_str += f"{key}={urllib.parse.quote(str(params[key]))}&"
    params_str = params_str[:-1]
    sign_str = params_str + APP_SEC
    return hashlib.md5(sign_str.encode("utf-8")).hexdigest()
# 获取 Bilibili 登录二维码
@app.route('/api/get_qr_code', methods=['GET'])
def get_qr_code():
    try:
        url = "https://passport.bilibili.com/x/passport-login/web/qrcode/generate"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/"
        }
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return jsonify(response.json())  # 转发 Bilibili API 的响应
        else:
            logging.error(f"Failed to get QR code from Bilibili: {response.status_code} {response.text}")
            return jsonify({"error": "Failed to get QR code from Bilibili"}), 500
    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 检查二维码状态
@app.route('/api/check_qr_code', methods=['POST'])
def check_qr_code():
    try:
        data = request.get_json()
        logging.debug(f"收到的二维码校验请求数据: {data}")

        oauth_key = data.get("oauthKey")
        logging.debug(f"oauthKey: {oauth_key}")
        if not oauth_key:
            logging.error("oauthKey 为空")
            return jsonify({"error": "Missing oauthKey"}), 400

        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={oauth_key}"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/"
        }

        response = requests.get(url, headers=headers)
        result = response.json()
        logging.debug(f"Bilibili API 响应: {result}")

        if result.get('code') == 0:
            logging.info("二维码扫描成功，登录完成")
            return jsonify({"code": 0, "message": "登录成功", "status": True, "data": result.get('data')}), 200
        elif result.get('code') == 86038:
            logging.info("二维码未扫描，等待扫码")
            return jsonify({"code": 86038, "message": "等待扫码", "status": False}), 200
        elif result.get('code') == 200000:
            logging.info("二维码已过期")
            return jsonify({"code": 200000, "message": "二维码已过期", "status": False}), 200
        else:
            logging.error(f"未知错误: {result}")
            return jsonify({"error": "未知错误", "status": False}), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 获取用户信息
@app.route("/api/user_info", methods=["GET"])
def get_user_info():
    try:
        # 从请求参数中获取 DedeUserID 和 SESSDATA
        dede_user_id = request.args.get("DedeUserID")
        sessdata = request.args.get("SESSDATA")

        if not dede_user_id or not sessdata:
            logging.error("缺少 DedeUserID 或 SESSDATA")
            return jsonify({"error": "缺少 DedeUserID 或 SESSDATA"}), 400

        # 调用 Bilibili 获取用户信息的 API
        url = "https://api.bilibili.com/x/web-interface/nav"
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
            "Cookie": f"DedeUserID={dede_user_id}; SESSDATA={sessdata};"
        }

        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            user_info = response.json()
            if user_info.get("code") == 0:
                return jsonify({"code": 0, "data": user_info.get("data")}), 200
            else:
                logging.error(f"获取用户信息失败: {user_info.get('message')}")
                return jsonify({"error": "获取用户信息失败", "message": user_info.get("message")}), 500
        else:
            logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
            return jsonify({"error": "Bilibili API 请求失败"}), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 更新视频总结文档
@app.route("/api/update_summary", methods=["PUT"])
def update_summary():
    session = None
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        video_id = data.get("video_id")
        summary_text = data.get("summary_text")

        if not user_id or not video_id or not summary_text:
            return error_response("Missing required parameters", 400)

        session = Session()
        # 查找要更新的文档
        summary = session.query(VideoSummary).filter_by(user_id=user_id, video_id=video_id).first()
        if not summary:
            return error_response("Summary not found", 404)

        # 更新数据库记录
        summary.summary_text = summary_text
        summary.created_at = datetime.now()  # 更新时间
        session.commit()
        
        return success_response({"message": "Summary updated successfully"})
    except Exception as e:
        logging.error(f"更新视频总结时出错: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
    finally:
        if session:
            session.close()

# 获取用户投稿视频
@app.route("/api/user_videos", methods=["GET"])
def get_user_videos():
    try:
        # 从请求参数中获取用户 ID 和页码
        mid = request.args.get("mid")
        pn = request.args.get("pn", default=1, type=int)
        ps = request.args.get("ps", default=30, type=int)

        if not mid:
            logging.error("缺少用户 ID (mid)")
            return jsonify({"error": "缺少用户 ID (mid)"}), 400

        # 增加重试机制
        max_retries = 3
        retry_delay = 3  # 每次重试之间的延迟时间（秒）
        for attempt in range(max_retries):
            try:
                # 调用 Bilibili API 获取用户投稿视频
                url = "https://api.bilibili.com/x/space/arc/search"
                params = {
                    "mid": mid,
                    "pn": pn,
                    "ps": ps,
                }
                headers = {
                    "User-Agent": "Mozilla/5.0",
                    "Referer": "https://www.bilibili.com/",
                }

                response = requests.get(url, params=params, headers=headers)
                logging.debug(f"Bilibili API 响应: {response.json()}")  # 打印 API 响应
                if response.status_code == 200:
                    video_data = response.json()
                    if video_data.get("code") == 0:
                        return jsonify({"code": 0, "data": video_data.get("data")}), 200
                    elif video_data.get("code") == -401:
                        # 非法访问，可能是请求过于频繁，等待一段时间后重试
                        logging.warning("非法访问，可能是请求过于频繁，等待一段时间后重试")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logging.error(f"获取视频数据失败: {video_data.get('message')}")
                        return jsonify({"error": "获取视频数据失败", "message": video_data.get("message")}), 500
                else:
                    logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
                    return jsonify({"error": "Bilibili API 请求失败"}), 500
            except Exception as e:
                logging.error(f"服务器错误: {str(e)}")
                return jsonify({"error": str(e)}), 500

        # 如果所有重试都失败，返回错误
        return jsonify({"error": "请求过于频繁，请稍后再试"}), 429
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 搜索视频
@app.route("/api/search_videos", methods=["GET"])
def search_videos():
    try:
        # 获取搜索关键词和分页参数
        keyword = request.args.get("keyword")
        pn = request.args.get("pn", default=1, type=int)
        ps = request.args.get("ps", default=20, type=int)

        if not keyword:
            logging.error("缺少搜索关键词")
            return jsonify({"error": "缺少搜索关键词"}), 400

        # 校验 Cookie
        cookie = request.headers.get("Cookie", "")
        if 'SESSDATA' not in cookie or 'DedeUserID' not in cookie:
            logging.error("未登录或 Cookie 无效")
            return jsonify({"error": "未登录或 Cookie 无效"}), 401

        # 调用 Bilibili API 搜索视频
        url = "https://api.bilibili.com/x/web-interface/search/type"
        params = {
            "keyword": keyword,
            "search_type": "video",
            "page": pn,
            "page_size": ps,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
            "Cookie": cookie,  # 传递完整 Cookie
            "Origin": "https://www.bilibili.com"
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            search_data = response.json()
            if search_data.get("code") == 0:
                return jsonify({"code": 0, "data": search_data.get("data")}), 200
            else:
                logging.error(f"搜索视频失败: {search_data.get('message')}")
                return jsonify({"error": "搜索视频失败", "message": search_data.get("message")}), 500
        else:
            logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
            return jsonify({"error": "Bilibili API 请求失败"}), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 获取点赞数排行前 N 的评论
@app.route("/api/top_liked_comments", methods=["GET"])
def get_top_liked_comments():
    try:
        oid = request.args.get("oid")
        if not oid:
            return error_response("Missing oid parameter", 400)

        n = request.args.get("n", default=10, type=int)
        csv_file = os.path.join("comments", f"comments_oid_{oid}.csv")
        if not os.path.exists(csv_file):
            return error_response("CSV 文件不存在", 404)

        import pandas as pd
        df = pd.read_csv(csv_file)
        top_comments = df.nlargest(n, '点赞数')[['评论内容', '点赞数']].to_dict('records')

        return jsonify({"code": 0, "data": top_comments}), 200
    except Exception as e:
        return error_response(str(e), 500)

# 获取视频评论数据
@app.route("/api/video_comments", methods=["GET"])
def get_video_comments():
    try:
        # 获取参数
        oid = request.args.get("oid")
        if not oid:
            return jsonify({"error": "Missing oid parameter"}), 400

        pn = request.args.get("pn", 1, type=int)
        ps = request.args.get("ps", 20, type=int)
        sort = request.args.get("sort", 0, type=int)
        type_ = request.args.get("type", 1, type=int)

        # 校验 Cookie
        cookie = request.headers.get("Cookie", "")
        if 'SESSDATA' not in cookie or 'DedeUserID' not in cookie:
            return jsonify({"error": "未登录或 Cookie 无效"}), 401

        # 增加请求间隔，避免触发安全策略
        #time.sleep(3)  # 增加3秒延迟

        # 生成签名参数
        params = {
            "oid": oid,
            "type": type_,
            "pn": pn,
            "ps": ps,
            "sort": sort,
            "appkey": APP_KEY,
            "ts": int(time.time()),
            "platform": "web",
            "build": "1000"
        }
        params["sign"] = generate_sign(params)

        # 调用 Bilibili API，增加重试机制
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                    "Referer": "https://www.bilibili.com/",
                    "Cookie": cookie,  # 传递完整 Cookie
                    "Origin": "https://www.bilibili.com",
                    "Accept": "application/json, text/plain, */*",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Connection": "keep-alive"
                }
                response = requests.get("https://api.bilibili.com/x/v2/reply", params=params, headers=headers)
                
                if response.status_code == 200:
                    try:
                        comment_data = response.json()

                        if comment_data.get("code") == 0:
                            # 获取 replies 字段
                            replies = comment_data.get("data", {}).get("replies", [])

                            # 如果 replies 为空列表，表示没有评论
                            if not replies:
                                return jsonify({"code": 0, "data": {"replies": []}}), 200

                            return jsonify({"code": 0, "data": comment_data.get("data")}), 200
                        else:
                            return jsonify({"error": "获取评论数据失败", "message": comment_data.get("message")}), 500
                    except ValueError as e:
                        logging.error(f"JSON 解析错误: {str(e)}")
                        return jsonify({"error": "JSON 解析错误"}), 500
                else:
                    retry_count += 1
                    time.sleep(5)  # 增加重试间隔
            except requests.exceptions.RequestException as e:
                retry_count += 1
                time.sleep(5)  # 增加重试间隔

        return jsonify({"error": "请求失败，请稍后再试"}), 500

    except Exception as e:
        return jsonify({"error": "服务器内部错误", "message": str(e)}), 500

# 封装返回方法
def success_response(data):
    return jsonify({"code": 0, "data": data}), 200

def error_response(message, code):
    return jsonify({"error": message, "code": code}), code

def save_comments_to_file(comment_data, oid, pn, ps):
    try:
        # 创建保存评论数据的目录（如果不存在）
        comments_dir = os.path.join(os.getcwd(), "comments")
        if not os.path.exists(comments_dir):
            os.makedirs(comments_dir)

        # 构建文件名
        filename = f"comments_oid_{oid}_pn_{pn}_ps_{ps}.json"
        file_path = os.path.join(comments_dir, filename)

        # 将评论数据保存为 JSON 文件
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(comment_data, f, ensure_ascii=False, indent=4)

        logging.info(f"评论数据已保存到 {file_path}")
    except Exception as e:
        logging.error(f"保存评论数据到文件时出错: {str(e)}")

def save_comments_to_csv(comments, oid):
    try:
        import csv
        from datetime import datetime
        # 创建保存评论数据的目录（如果不存在）
        comments_dir = os.path.join(os.getcwd(), "comments")
        if not os.path.exists(comments_dir):
            os.makedirs(comments_dir)

        # 构建文件名
        filename = f"comments_oid_{oid}.csv"
        file_path = os.path.join(comments_dir, filename)

        # 将评论数据保存为 CSV 文件
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['用户ID', '用户名', '性别', '位置', '评论内容', '点赞数', '评论时间']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for comment in comments:
                # 提取位置数据中的省份信息
                location = comment.get("reply_control", {}).get("location", "")
                if location and "IP属地：" in location:
                    location = location.split("IP属地：")[1]+"省"

                # 将时间戳转换为 yyyy-MM-dd hh-mm-ss 格式
                ctime = comment.get("ctime", "")
                if ctime:
                    ctime = datetime.fromtimestamp(ctime).strftime("%Y-%m-%d %H:%M:%S")

                writer.writerow({
                    '用户ID': comment.get("member", {}).get("mid", ""),
                    '用户名': comment.get("member", {}).get("uname", ""),
                    '性别': comment.get("member", {}).get("sex", ""),
                    '位置': location,
                    '评论内容': comment.get("content", {}).get("message", ""),
                    '点赞数': comment.get("like", ""),
                    '评论时间': ctime
                })

        logging.info(f"评论数据已保存到 {file_path}")
    except Exception as e:
        logging.error(f"保存评论数据到 CSV 文件时出错: {str(e)}")
# 获取视频详情
@app.route("/api/video_details", methods=["GET"])
def get_video_details():
    try:
        # 从请求参数中获取视频 ID
        aid = request.args.get("aid")
        bvid = request.args.get("bvid")

        if not aid and not bvid:
            return jsonify({"error": "缺少视频 ID (aid 或 bvid)"}), 400

        # 调用 Bilibili API 获取视频详情
        url = "https://api.bilibili.com/x/web-interface/view"
        params = {
            "aid": aid,
            "bvid": bvid,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            video_data = response.json()
            if video_data.get("code") == 0:
                video_info = video_data["data"]

                # 尝试从根级别获取 cid
                cid = video_info.get("cid")

                # 如果根级别没有 cid，则从 pages 数组中获取
                if not cid:
                    pages = video_info.get("pages")
                    if pages and len(pages) > 0:
                        cid = pages[0].get("cid")  # 获取第一个分段的 cid
                    if not cid:
                        logging.error("无法找到 cid 字段")
                        return jsonify({"error": "无法找到 cid 字段"}), 500

                # 获取视频播放 URL
                playurl_url = "https://api.bilibili.com/x/player/playurl"
                playurl_params = {
                    "bvid": video_info["bvid"],
                    "cid": cid,
                    "qn": 116,  # 116 表示 1080P 高清
                    "fnval": 0,  #16 支持 DASH 格式
                    "fnver": 0,  #16 支持 DASH 格式"
                    "fourk": 1,  # 支持 4K 分辨率
                }
            
                playurl_response = requests.get(playurl_url, params=playurl_params, headers=headers)
                if playurl_response.status_code == 200:
                    playurl_data = playurl_response.json()
                    if playurl_data.get("code") == 0:
                        if playurl_data["data"].get("durl"):
                            video_info["playurl"] = playurl_data["data"]["durl"][0]["url"]
                        elif playurl_data["data"].get("dash"):  # 如果有 DASH 格式
                            video_info["playurl"] = playurl_data["data"]["dash"]["video"][0]["baseUrl"]
                        return jsonify({"code": 0, "data": video_info}), 200
                    else:
                        logging.error(f"获取视频播放 URL 失败: {playurl_data.get('message')}")
                        return jsonify({"error": "获取视频播放 URL 失败", "message": playurl_data.get("message")}), 500
                else:
                    logging.error(f"Bilibili API 请求失败: {playurl_response.status_code} {playurl_response.text}")
                    return jsonify({"error": "Bilibili API 请求失败"}), 500
            else:
                logging.error(f"获取视频详情失败: {video_data.get('message')}")
                return jsonify({"error": "获取视频详情失败", "message": video_data.get("message")}), 500
        else:
            logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
            return jsonify({"error": "Bilibili API 请求失败"}), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 新增：保存视频总结文档
@app.route("/api/save_summary", methods=["POST"])
def save_summary():
    session = None
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        video_id = data.get("video_id")
        summary_text = data.get("summary_text")
        
        if not user_id or not video_id or not summary_text:
            return error_response("Missing required parameters", 400)
            
        # 检查是否已存在相同记录
        session = Session()
        existing_summary = session.query(VideoSummary).filter_by(user_id=user_id, video_id=video_id).first()
        if existing_summary:
            session.close()
            return success_response({"message": "文档已存在，无需重复保存"})
            
        # 保存到数据库
        new_summary = VideoSummary(
            user_id=user_id,
            video_id=video_id,
            summary_text=summary_text,
            summary_path="",  # 不再保存文件路径
            created_at=datetime.now()
        )
        session.add(new_summary)
        session.commit()
        
        return success_response({"message": "文档保存成功"})
    except Exception as e:
        logging.error(f"保存文档时出错: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
    finally:
        if session:
            session.close()
            
@app.route("/api/get_summaries", methods=["GET"])
def get_summaries():
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return error_response("Missing user_id parameter", 400)
            
        session = Session()
        summaries = session.query(VideoSummary).filter_by(user_id=user_id).all()
        
        result = []
        for summary in summaries:
            result.append({
                "id": summary.id,
                "video_id": summary.video_id,
                "created_at": summary.created_at.isoformat(),  # 使用 ISO 格式化日期时间
                "summary_text": summary.summary_text  # 添加文档内容字段
            })
            
        return success_response({"summaries": result})
    except Exception as e:
        logging.error(f"获取文档列表时出错: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
    finally:
        if 'session' in locals() and session:
            session.close()
            
@app.route("/api/delete_summary", methods=["DELETE"])
def delete_summary():
    session = None
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        video_id = data.get("video_id")

        if not user_id or not video_id:
            return error_response("Missing required parameters", 400)

        session = Session()
        # 查找要删除的文档
        summary = session.query(VideoSummary).filter_by(user_id=user_id, video_id=video_id).first()
        if not summary:
            return error_response("Summary not found", 404)

        # 删除文件
        if os.path.exists(summary.summary_path):
            os.remove(summary.summary_path)

        # 删除数据库记录
        session.delete(summary)
        session.commit()

        return success_response({"message": "Summary deleted successfully"})
    except Exception as e:
        logging.error(f"删除文档时出错: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
    finally:
        if session:
            session.close()

# 获取视频总结
@app.route("/api/video_summary", methods=["POST"])
def video_summary():
    try:
        data = request.get_json()
        bvid = data.get("bvid")

        if not bvid:
            return error_response("Missing bvid parameter", 400)

        # 验证API密钥
        bibigpt_api_key = "EyNx1lVTuXC0"
        if not bibigpt_api_key:
            logging.error("BibiGPT API密钥未配置")
            return error_response("BibiGPT API密钥未配置", 500)

        # 新的请求参数和认证方式
        payload = {
            "url": f"https://www.bilibili.com/video/{bvid}",  # 修改为正确的视频URL
            "includeDetail": True  # 使用准确参数名和布尔值
        }

        headers = {"Content-Type": "application/json"}

        # 调整API端点（根据实际文档）
        api_endpoint = f'https://api.bibigpt.co/api/open2/{bibigpt_api_key}'  # 假设真实端点

        # 增加重试机制
        max_retries = 5  # 增加重试次数
        retry_delay = 10  # 增加重试间隔时间
        for attempt in range(max_retries):
            try:
                # 调用API并设置超时
                response = requests.post(
                    api_endpoint,
                    headers=headers,
                    json=payload,
                    # timeout=120  # 增加超时时间到120秒
                )

                logging.info(f"BibiGPT响应内容：{response.text}")

                if response.status_code == 200:
                    try:
                        return success_response(response.json())  # 直接返回整个响应内容
                    except KeyError:
                        return error_response("BibiGPT响应格式错误", 500)
                else:
                    # 详细错误记录
                    logging.error(f"BibiGPT API返回错误: {response.status_code} {response.text}")
                    if attempt < max_retries - 1:  # 如果不是最后一次尝试
                        logging.info(f"尝试 {attempt + 1} 失败，将在 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)
                    else:
                        return error_response(f"API调用失败: {response.status_code} {response.text}", 500)
            except requests.exceptions.RequestException as req_err:
                logging.error(f"网络请求异常：{str(req_err)}")
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    logging.info(f"尝试 {attempt + 1} 失败，将在 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    return error_response(f"网络请求异常: {str(req_err)}", 500)
            except Exception as e:
                logging.error(f"发生未知错误：{str(e)}")
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    logging.info(f"尝试 {attempt + 1} 失败，将在 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)
                else:
                    return error_response(str(e), 500)

    except Exception as e:
        logging.error(f"发生未知错误：{str(e)}")
        return error_response(str(e), 500)

# 获取视频详情方法
def get_video_details2(aid):
    try:
        # 从请求参数中获取视频 ID
        if not aid:
            logging.error("缺少视频 ID (aid 或 bvid)")
            return jsonify({"error": "缺少视频 ID (aid 或 bvid)"}), 400

        # 调用 Bilibili API 获取视频详情
        url = "https://api.bilibili.com/x/web-interface/view"
        params = {
            "aid": aid,
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
        }

        response = requests.get(url, params=params, headers=headers)
        logging.debug(f"Bilibili API 响应: {response.json()}")  # 打印 API 响应
        if response.status_code == 200:
            video_data = response.json()
            if video_data.get("code") == 0:
                video_info = video_data["data"]

                # 尝试从根级别获取 cid
                cid = video_info.get("cid")

                # 如果根级别没有 cid，则从 pages 数组中获取
                if not cid:
                    pages = video_info.get("pages")
                    if pages and len(pages) > 0:
                        cid = pages[0].get("cid")  # 获取第一个分段的 cid
                    if not cid:
                        logging.error("无法找到 cid 字段")
                        return jsonify({"error": "无法找到 cid 字段"}), 500

                # 获取视频播放 URL
                playurl_url = "https://api.bilibili.com/x/player/playurl"
                playurl_params = {
                    "bvid": video_info["bvid"],
                    "cid": cid,
                    "qn": 116,  # 116 表示 1080P 高清
                    "fnval": 0,  #16 支持 DASH 格式
                    "fnver": 0,  #16 支持 DASH 格式"
                    "fourk": 1,  # 支持 4K 分辨率
                }
            
                playurl_response = requests.get(playurl_url, params=playurl_params, headers=headers)
                if playurl_response.status_code == 200:
                    playurl_data = playurl_response.json()
                    if playurl_data.get("code") == 0:
                        if playurl_data["data"].get("durl"):
                            video_info["playurl"] = playurl_data["data"]["durl"][0]["url"]
                        elif playurl_data["data"].get("dash"):  # 如果有 DASH 格式
                            video_info["playurl"] = playurl_data["data"]["dash"]["video"][0]["baseUrl"]
                        return jsonify({"code": 0, "data": video_info}), 200
                    else:
                        logging.error(f"获取视频播放 URL 失败: {playurl_data.get('message')}")
                        return jsonify({"error": "获取视频播放 URL 失败", "message": playurl_data.get("message")}), 500
                else:
                    logging.error(f"Bilibili API 请求失败: {playurl_response.status_code} {playurl_response.text}")
                    return jsonify({"error": "Bilibili API 请求失败"}), 500
            else:
                logging.error(f"获取视频详情失败: {video_data.get('message')}")
                return jsonify({"error": "获取视频详情失败", "message": video_data.get("message")}), 500
        else:
            logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
            return jsonify({"error": "Bilibili API 请求失败"}), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 推荐视频
@app.route("/api/recommended_videos", methods=["GET"])
def get_recommended_videos():
    try:
        # 从请求参数中获取分页参数
        pn = request.args.get("pn", default=1, type=int)
        ps = request.args.get("ps", default=10, type=int)
        mid = request.args.get("mid")  # 新增：获取用户 mid

        # 校验 Cookie
        cookie = request.headers.get("Cookie", "")
        if 'SESSDATA' not in cookie or 'DedeUserID' not in cookie:
            logging.error("未登录或 Cookie 无效")
            return jsonify({"error": "未登录或 Cookie 无效"}), 401

        # 调用 Bilibili API 获取推荐视频
        url = "https://api.bilibili.com/x/web-interface/index/top/feed/rcmd"
        params = {
            "pn": pn,
            "ps": ps,
            "mid": mid  # 新增：传递用户 mid
        }
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",
            "Cookie": cookie,  # 传递完整 Cookie
            "Origin": "https://www.bilibili.com"
        }

        response = requests.get(url, params=params, headers=headers)
        if response.status_code == 200:
            video_data = response.json()
            if video_data.get("code") == 0:
                # 确保返回的数据格式正确
                return jsonify({
                    "code": 0,
                    "data": video_data.get("data", {}).get("item", [])  # 获取推荐视频列表
                }), 200
            else:
                logging.error(f"获取推荐视频失败: {video_data.get('message')}")
                return jsonify({
                    "code": video_data.get("code"),
                    "error": "获取推荐视频失败",
                    "message": video_data.get("message")
                }), 500
        else:
            logging.error(f"Bilibili API 请求失败: {response.status_code} {response.text}")
            return jsonify({
                "code": response.status_code,
                "error": "Bilibili API 请求失败"
            }), 500
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({
            "code": 500,
            "error": "服务器错误",
            "message": str(e)
        }), 500

# 代理图片
@app.route('/api/proxy_image', methods=['GET'])
def proxy_image():
    try:
        image_url = request.args.get('url')
        if not image_url:
            logging.error("Missing image URL")
            return jsonify({"error": "Missing image URL"}), 400

        response = requests.get(image_url, headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/"
        })

        if response.status_code == 200:
            return send_file(BytesIO(response.content), mimetype='image/jpeg')
        else:
            logging.error(f"Failed to fetch image: {response.status_code} {response.text}")
            return jsonify({"error": "Failed to fetch image", "status_code": response.status_code}), response.status_code
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500

# 代理视频
@app.route('/api/proxy_video', methods=['GET'])
def proxy_video():
    try:
        video_url = request.args.get('url')
        if not video_url:
            logging.error("Missing video URL")
            return jsonify({"error": "Missing video URL"}), 400

        headers = {
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://www.bilibili.com/",  # 添加 Referer 验证
            "Origin": "https://www.bilibili.com/",   # 添加 Origin 验证
            "Range": request.headers.get("Range", "")  # 支持范围请求
        }

        # 发起流式请求
        response = requests.get(video_url, headers=headers, stream=True)
        if response.status_code == 200 or response.status_code == 206:  # 支持部分内容响应
            # 返回流式响应
            return Response(
                response.iter_content(chunk_size=1024),
                content_type=response.headers["Content-Type"],
                headers={"Accept-Ranges": "bytes"}  # 表明支持范围请求
            )
        else:
            return jsonify({"error": "Failed to fetch video", "status_code": response.status_code}), response.status_code
    except Exception as e:
        logging.error(f"服务器错误: {str(e)}")
        return jsonify({"error": str(e)}), 500


from sqlalchemy import create_engine, Column, Integer, String, Text
from sqlalchemy.orm import declarative_base, sessionmaker

# 数据库配置
DATABASE_URI = 'sqlite:///video_collection.db'
engine = create_engine(DATABASE_URI)
Base = declarative_base()

# 定义收藏视频的数据库模型
class VideoCollection(Base):
    __tablename__ = 'video_collection'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    video_id = Column(String, nullable=False)
    video_url = Column(String, nullable=False)
    cover_url = Column(String)  # 新增：视频封面图片链接
    # summary = Column(Text)

# 定义文档管理的数据库模型
class VideoSummary(Base):
    __tablename__ = 'video_summaries'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    video_id = Column(String(50), nullable=False)
    summary_text = Column(Text, nullable=False)
    summary_path = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)

# 删除旧的数据库表并重新创建
Base.metadata.drop_all(engine)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# 新增：收藏视频
@app.route("/api/collect_video", methods=["POST"])
def collect_video():
    session = None  # 初始化 session 变量
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        video_id = data.get("video_id")
        video_url = data.get("video_url")
        cover_url = data.get("cover_url")  # 新增：获取封面图片链接

        if not user_id or not video_id or not video_url:
            return error_response("Missing required parameters", 400)

        session = Session()
        # 检查是否已经收藏过
        existing = session.query(VideoCollection).filter_by(user_id=user_id, video_id=video_id).first()
        if existing:
            return error_response("Video already collected", 400)

        # 保存收藏记录
        new_collection = VideoCollection(
            user_id=user_id,
            video_id=video_id,
            video_url=video_url,
            cover_url=cover_url,  # 新增：保存封面图片链接
        )
        session.add(new_collection)
        session.commit()

        # 确保数据已保存到数据库
        saved_collection = session.query(VideoCollection).filter_by(user_id=user_id, video_id=video_id).first()
        if not saved_collection:
            return error_response("Failed to save video collection", 500)

        return success_response({"message": "Video collected successfully"})
    except Exception as e:
        logging.error(f"收藏视频时出错: {str(e)}", exc_info=True)  # 增加详细的错误日志
        return error_response(str(e), 500)
    finally:
        if session:
            session.close()  # 确保 session 被正确关闭
        session.close()
# 新增：获取用户收藏的视频
@app.route("/api/get_collected_videos", methods=["GET"])
def get_collected_videos():
    session = None
    try:
        user_id = request.args.get("user_id")
        if not user_id:
            return error_response("Missing user_id parameter", 400)

        session = Session()
        collections = session.query(VideoCollection).filter_by(user_id=user_id).all()

        collected_videos = []
        for collection in collections:
            # 获取视频详情
            video_details_response = get_video_details2(collection.video_id)
            if video_details_response[1] == 200:
                video_details = video_details_response[0].get_json()
                if video_details.get("code") == 0:
                    video_data = video_details.get("data", {})
                    collected_videos.append({
                        "video_id": collection.video_id,
                        "video_url": collection.video_url,
                        "cover_url": collection.cover_url,
                        "title": video_data.get("title", "未知标题"),
                        "description": video_data.get("desc", "暂无描述")
                    })
                else:
                    collected_videos.append({
                        "video_id": collection.video_id,
                        "video_url": collection.video_url,
                        "cover_url": collection.cover_url,
                        "title": "未知标题",
                        "description": "暂无描述"
                    })
            else:
                collected_videos.append({
                    "video_id": collection.video_id,
                    "video_url": collection.video_url,
                    "cover_url": collection.cover_url,
                    "title": "未知标题",
                    "description": "暂无描述"
                })

        return success_response({"collected_videos": collected_videos})
    except Exception as e:
        logging.error(f"获取收藏视频时出错: {str(e)}", exc_info=True)
        return error_response(str(e), 500)
    finally:
        if session:
            session.close()  # 确保 session 被正确关闭

# 新增：删除收藏的视频
@app.route("/api/delete_collected_video", methods=["DELETE"])
def delete_collected_video():
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        video_id = data.get("video_id")

        if not user_id or not video_id:
            return error_response("Missing required parameters", 400)

        session = Session()
        collection = session.query(VideoCollection).filter_by(user_id=user_id, video_id=video_id).first()
        if not collection:
            return error_response("Video not found in collection", 404)

        session.delete(collection)
        session.commit()

        return success_response({"message": "Video deleted from collection successfully"})
    except Exception as e:
        return error_response(str(e), 500)
    finally:
        session.close()

# 新增：KNN分类管理文档
@app.route("/api/classify_documents", methods=["POST"])
def classify_documents():
    try:
        from sklearn.neighbors import KNeighborsClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer

        user_id = request.args.get("user_id")
        if not user_id:
            return error_response("Missing user_id parameter", 400)

        session = Session()
        summaries = session.query(VideoSummary).filter_by(user_id=user_id).all()

        if not summaries:
            return error_response("No documents found for classification", 404)

        documents = [summary.summary_text for summary in summaries]
        labels = [i for i in range(len(documents))]  # 使用索引作为临时标签

        # 文本向量化
        vectorizer = TfidfVectorizer()
        X = vectorizer.fit_transform(documents)

        # KNN分类
        knn = KNeighborsClassifier(n_neighbors=3)
        knn.fit(X, labels)

        # 预测分类
        predicted_labels = knn.predict(X)

        # 返回分类结果
        classified_documents = []
        for i, label in enumerate(predicted_labels):
            classified_documents.append({
                "video_id": summaries[i].video_id,
                "summary_text": summaries[i].summary_text,
                "category": int(label)
            })

        return success_response({"classified_documents": classified_documents})
    except Exception as e:
        return error_response(str(e), 500)
    finally:
        session.close()

# 数据清洗
from datetime import datetime  # 新增：导入 datetime 模块
def clean_text(text):
    """清洗文本数据，去除标点符号、表情、停用词等"""

   # 去除@用户（@开头，直到第一个空格为止，同时去掉空格）
    text = re.sub(r"@\S+\s*", "", text)

    # 去除表情符号（包括中括号及其中内容）
    text = re.sub(r"\[[^\]]+\]", "", text)

    # 去除多余的空格（如果 @ 用户后还有空格残留）
    text = re.sub(r"\s+", " ", text).strip()
    
    # 去除标点符号和特殊字符
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9]", " ", str(text))
    # 分词
    words = jieba.cut(text)
    
    # 去除停用词
    stopwords = set()
    with open("stopwords.txt", "r", encoding="utf-8") as f:
        for line in f:
            stopwords.add(line.strip())
    
    cleaned_words = [word for word in words if word not in stopwords and len(word) > 1]  # 增加长度过滤
    
    return " ".join(cleaned_words)
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)