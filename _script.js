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
    pre.textContent = lines.join('\n') + '\n\n' + pre.textContent;
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