#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"""

Web 前端：在浏览器中登录、选择分类/页数、查看封面并下载所选视频。



运行：

    pip install flask requests pycryptodome

    python web_app.py

然后访问 http://127.0.0.1:5000/

"""



from __future__ import annotations



from typing import Any, Dict, List



from flask import Flask, jsonify, render_template_string, request



from maomi_spider import MaomiClient, SUPPORTED_CHANNELS



app = Flask(__name__)






INDEX_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <title>猫咪采集演示控制台</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif;
      margin: 0;
      padding: 0;
      background: #f5f7fb;
      color: #111827;
    }
    header {
      background: linear-gradient(120deg, #7928ca, #ff0080);
      color: #fff;
      padding: 32px;
      box-shadow: 0 20px 45px rgba(121, 40, 202, 0.25);
    }
    header h1 { margin: 0 0 8px; font-size: 32px; font-weight: 600; }
    header p { margin: 4px 0 0; opacity: 0.9; }
    main { padding: 32px; max-width: 1200px; margin: 0 auto; }
    .panel {
      background: #fff;
      border-radius: 18px;
      padding: 24px;
      margin-bottom: 28px;
      box-shadow: 0 25px 60px rgba(15, 23, 42, 0.07);
    }
    .form-grid {
      display: grid;
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }
    label { display: block; margin-bottom: 6px; font-weight: 600; }
    input, select {
      width: 100%;
      padding: 12px;
      border: 1px solid #d6dae5;
      border-radius: 10px;
      font-size: 15px;
      background: #fbfbfe;
    }
    input:focus, select:focus {
      border-color: #7928ca;
      outline: none;
      box-shadow: 0 0 0 3px rgba(121, 40, 202, 0.18);
    }
    button {
      border: none;
      border-radius: 10px;
      padding: 12px 24px;
      font-size: 15px;
      cursor: pointer;
      transition: transform 0.1s ease, box-shadow 0.1s ease;
    }
    button.primary { background: #ff0080; color: #fff; box-shadow: 0 15px 30px rgba(255, 0, 128, 0.35); }
    button.secondary { background: #eef2ff; color: #4338ca; }
    button:hover { transform: translateY(-1px); }
    button:active { transform: translateY(0); box-shadow: none; }
    .actions-row { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 16px; }
    .cards-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 20px;
    }
    .card {
      border-radius: 16px;
      background: #fff;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
      padding: 18px 20px;
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .card-title { font-size: 16px; font-weight: 600; margin-bottom: 6px; }
    .card-meta { font-size: 13px; color: #475467; line-height: 1.5; }
    .badge {
      display: inline-flex;
      padding: 2px 10px;
      border-radius: 999px;
      font-size: 12px;
      background: #eef2ff;
      color: #3730a3;
      margin-right: 6px;
    }
    .card-actions {
      display: flex;
      gap: 12px;
      margin-top: 12px;
      flex-wrap: wrap;
    }
    .card-actions button { flex: 1 1 120px; }
    #status {
      background: #0b1221;
      color: #2df3a0;
      padding: 14px;
      border-radius: 12px;
      min-height: 120px;
      max-height: 320px;
      overflow: auto;
      font-family: Consolas, "SFMono-Regular", monospace;
      font-size: 13px;
    }
    .panel-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px; }
    #result-counter { color: #6b7280; font-size: 14px; }
    .topic-columns { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 18px; }
    .topic-meta-box { background: #f9f5ff; border-radius: 12px; padding: 14px; border: 1px solid #f0e1ff; }
    .modal { position: fixed; inset: 0; background: rgba(15, 23, 42, 0.55); display: flex; align-items: center; justify-content: center; padding: 24px; z-index: 1000; }
    .modal-content { background: #fff; border-radius: 18px; max-width: 820px; width: 100%; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 35px 90px rgba(15, 23, 42, 0.35); }
    .modal-head { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px 0; }
    .modal-head h3 { margin: 0; font-size: 18px; }
    .modal-body { padding: 16px 24px 24px; overflow: auto; }
    #detail-json { font-family: Consolas, "SFMono-Regular", monospace; font-size: 13px; background: #0b1221; color: #f8fafc; border-radius: 12px; padding: 16px; }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <header>
    <h1>猫咪 VIP 采集演示</h1>
    <p>仅用于协议分析 / 逆向学习，不内置账号密码，不提供下载链路。</p>
  </header>
  <main>
    <section class="panel">
      <div class="form-grid">
        <div>
          <label>账号</label>
          <input id="username" placeholder="请输入猫咪账号" />
        </div>
        <div>
          <label>密码</label>
          <input id="password" type="password" placeholder="请输入密码" />
        </div>
      </div>
      <div class="form-grid" style="margin-top:18px;">
        <div>
          <label>分类</label>
          <select id="category">
            <option value="">请先加载分类</option>
          </select>
        </div>
        <div>
          <label>抓取页数（从第 1 页开始）</label>
          <input id="pages" type="number" min="1" value="1" />
        </div>
      </div>
      <div class="actions-row">
        <button class="secondary" onclick="loadCategories()">加载分类</button>
        <button class="primary" onclick="startFetch()">开始采集</button>
      </div>
    </section>
    <section id="topic-meta-panel" class="panel hidden">
      <h2>专题信息</h2>
      <div id="topic-meta"></div>
    </section>
    <section class="panel">
      <div class="panel-head">
        <h2>视频列表</h2>
        <div id="result-counter">尚未采集</div>
      </div>
      <div id="videos" class="cards-grid">等待采集...</div>
    </section>
    <section class="panel">
      <h2>状态 / 调试日志</h2>
      <pre id="status">等待操作...</pre>
    </section>
  </main>
  <div id="detail-modal" class="modal hidden">
    <div class="modal-content">
      <div class="modal-head">
        <h3 id="detail-title">视频详情</h3>
        <button class="secondary" onclick="closeModal()">关闭</button>
      </div>
      <div class="modal-body">
        <pre id="detail-json">{}</pre>
      </div>
    </div>
  </div>
  <script>
    const state = {
      videos: [],
      categories: [],
      topicMeta: null,
    };

    function logStatus(message, payload) {
      const now = new Date().toLocaleTimeString();
      const pre = document.getElementById('status');
      const lines = [`[${now}] ${message}`];
      if (payload) {
        lines.push(JSON.stringify(payload, null, 2));
      }
      pre.textContent = lines.join('\\n') + '\\n\\n' + pre.textContent;
    }

    function collectCredentialPayload() {
      const username = document.getElementById('username').value.trim();
      const password = document.getElementById('password').value.trim();
      if (!username || !password) {
        alert('请输入账号和密码');
        throw new Error('missing credential');
      }
      return { username, password };
    }

    async function loadCategories() {
      let payload;
      try {
        payload = collectCredentialPayload();
      } catch (error) {
        return;
      }
      logStatus('开始加载分类...', null);
      try {
        const res = await fetch('/api/categories', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          alert(data.message || '加载失败');
          logStatus('分类加载失败', data);
          return;
        }
        state.categories = data;
        const select = document.getElementById('category');
        select.innerHTML = '';
        data.forEach((item, idx) => {
          const option = document.createElement('option');
          option.value = idx;
          option.textContent = `[${item.section}] ${item.name}`;
          select.appendChild(option);
        });
        logStatus(`已载入 ${data.length} 条分类`, null);
      } catch (error) {
        alert('加载失败：' + error);
        logStatus('分类加载异常', { error: String(error) });
      }
    }

    function resolveCategorySelection() {
      const select = document.getElementById('category');
      if (!state.categories.length || select.value === '') {
        alert('请先加载并选择分类');
        return null;
      }
      return state.categories[Number(select.value)];
    }

    async function startFetch() {
      let credentials;
      try {
        credentials = collectCredentialPayload();
      } catch (error) {
        return;
      }
      const category = resolveCategorySelection();
      if (!category) return;
      const pages = Number(document.getElementById('pages').value) || 1;
      if (pages < 1 || pages > 5) {
        alert('页数建议在 1-5 之间');
        return;
      }
      const identifier = category.jump_name || category.slug || category.name;
      const payload = {
        ...credentials,
        category: identifier,
        pages,
      };
      logStatus('开始采集...', { category: category.name, pages });
      try {
        const res = await fetch('/api/scrape', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        const data = await res.json();
        if (!res.ok) {
          alert('采集失败：' + data.message);
          logStatus('采集失败', data);
          return;
        }
        state.videos = data.videos || [];
        state.topicMeta = (data.category && data.category.topic_meta) || null;
        renderTopicMeta(state.topicMeta);
        renderVideos(state.videos);
        logStatus(`采集完成，共 ${state.videos.length} 条`, {
          channel: data.category && data.category.channel,
        });
      } catch (error) {
        alert('采集异常：' + error);
        logStatus('采集异常', { error: String(error) });
      }
    }

    function renderTopicMeta(meta) {
      const panel = document.getElementById('topic-meta-panel');
      const container = document.getElementById('topic-meta');
      if (!meta || (!meta.title && !meta.desc)) {
        panel.classList.add('hidden');
        container.innerHTML = '';
        return;
      }
      panel.classList.remove('hidden');
      container.innerHTML = `
        <div class="topic-columns">
          <div class="topic-meta-box">
            <strong>标题：</strong>${meta.title || '-'}<br/>
            <strong>描述：</strong>${meta.desc || '-'}
          </div>
          <div class="topic-meta-box">
            <strong>售价：</strong>${meta.price != null ? meta.price : '-'}<br/>
            <strong>VIP 售价：</strong>${meta.vip_price != null ? meta.vip_price : '-'}
          </div>
          ${meta.file ? `<div class="topic-meta-box"><a href="${meta.file}" target="_blank" rel="noopener noreferrer">打开专属资源</a></div>` : ''}
        </div>
      `;
    }

    function formatTags(value) {
      if (!value) return '无标签';
      if (Array.isArray(value)) return value.join('、');
      return value;
    }

    function renderVideos(list) {
      const container = document.getElementById('videos');
      const counter = document.getElementById('result-counter');
      if (!list.length) {
        container.textContent = '没有匹配的视频';
        counter.textContent = '0 条结果';
        return;
      }
      container.innerHTML = '';
      counter.textContent = `共 ${list.length} 条视频`;
      list.forEach((video, idx) => {
        const card = document.createElement('div');
        card.className = 'card';
        const duration = video.duration_hms || (video.duration_seconds ? video.duration_seconds + 's' : '未知');
        const sources = [
          video.video_mp4 ? '<span class="badge">MP4</span>' : '',
          video.video_m3u8 ? '<span class="badge">HLS</span>' : '',
        ].join('');
        card.innerHTML = `
          <div class="card-title">${video.title || '未命名视频'}</div>
          <div class="card-meta">ID：${video.id != null ? video.id : '-'}</div>
          <div class="card-meta">标签：${formatTags(video.tags)}</div>
          <div class="card-meta">时长：${duration}</div>
          <div class="card-meta">可用流：${sources || '暂无'}</div>
          <div class="card-actions">
            ${video.detail_url ? `<button class="secondary" onclick="openDetail('${video.detail_url}')">原站页面</button>` : ''}
            <button class="primary" onclick="showVideoJson(${idx})">详情(JSON)</button>
          </div>
        `;
        container.appendChild(card);
      });
    }

    function openDetail(url) {
      if (url) window.open(url, '_blank');
    }

    function showVideoJson(index) {
      const video = state.videos[index];
      if (!video) return;
      const modal = document.getElementById('detail-modal');
      document.getElementById('detail-title').textContent = video.title || '视频详情';
      document.getElementById('detail-json').textContent = JSON.stringify(video, null, 2);
      modal.classList.remove('hidden');
    }

    function closeModal() {
      document.getElementById('detail-modal').classList.add('hidden');
    }

    document.getElementById('detail-modal').addEventListener('click', (evt) => {
      if (evt.target.id === 'detail-modal') {
        closeModal();
      }
    });
    window.addEventListener('keydown', (evt) => {
      if (evt.key === 'Escape') {
        closeModal();
      }
    });
  </script>
</body>
</html>

"""







def create_client(data: Dict[str, Any]) -> MaomiClient:

    username = (data.get("username") or "").strip()

    password = (data.get("password") or "").strip()

    if not username or not password:

        raise ValueError("必须提供用户名和密码")

    return MaomiClient(username, password)







@app.get("/")

def index() -> str:

    return render_template_string(INDEX_HTML)







@app.post("/api/categories")

def api_categories():

    try:

        client = create_client(request.json or {})

        client.login()

        categories = client.fetch_categories()

        data = [

            {

                "section": cat.section,

                "name": cat.name,

                "jump_name": cat.slug,

                "channel": cat.channel,

                "topic_id": cat.topic_id,

                "supported": cat.channel in SUPPORTED_CHANNELS or cat.channel == "topic",

            }

            for cat in categories

        ]

        return jsonify(data)

    except Exception as exc:  # noqa: BLE001

        return jsonify({"message": str(exc)}), 400







@app.post("/api/scrape")

def api_scrape():

    try:

        payload = request.json or {}

        pages = max(1, int(payload.get("pages") or 1))

        category = (payload.get("category") or "").strip()

        if not category:

            raise ValueError("category 不能为空")




        client = create_client(payload)

        login_res = client.login()

        categories = client.fetch_categories()

        identifier = category.lower()

        matches = [

            cat for cat in categories if cat.slug.lower() == identifier or cat.name.lower() == identifier

        ]

        if not matches:

            raise ValueError(f"未找到分类：{category}")

        target = matches[0]

        videos, topic_meta = client.fetch_videos_for_category(target, pages)

        return jsonify(

            {                "account": {

                    "vip_level": login_res.raw.get("vip_level"),

                    "is_vip": login_res.raw.get("is_vip"),

                },

                "category": {

                    "section": target.section,

                    "name": target.name,

                    "jump_name": target.slug,

                    "channel": target.channel,

                    "pages_requested": pages,

                    "videos_found": len(videos),

                    "topic_meta": topic_meta,

                },

                "videos": videos,

            }

        )

    except Exception as exc:  # noqa: BLE001

        return jsonify({"message": str(exc)}), 400







def run(host: str = "0.0.0.0", port: int = 5000) -> None:

    app.run(host=host, port=port, debug=False)







if __name__ == "__main__":

    run()




















