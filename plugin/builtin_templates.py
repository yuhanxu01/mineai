LAN_TRANSFER_PLUGIN_HTML = r'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>局域网大文件直传</title>
  <style>
    :root {
      --bg: #0b0d12;
      --panel: #121722;
      --muted: #9aa4b2;
      --text: #e6ebf2;
      --line: #20283a;
      --gold: #c9a86c;
      --cyan: #62c2d7;
      --danger: #d46a6a;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: "Noto Sans SC", system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); }
    .wrap { max-width: 920px; margin: 0 auto; padding: 16px; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 10px; padding: 14px; margin-bottom: 12px; }
    .title { font-size: 20px; font-weight: 600; margin: 0 0 8px; color: var(--gold); }
    .muted { font-size: 12px; color: var(--muted); }
    .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
    input, button { height: 36px; border-radius: 8px; border: 1px solid var(--line); }
    input { background: #0d1320; color: var(--text); padding: 0 10px; min-width: 220px; }
    button { background: #1d2737; color: var(--text); padding: 0 12px; cursor: pointer; }
    button.primary { background: var(--gold); color: #111; border-color: #b8924f; }
    button:disabled { opacity: .45; cursor: not-allowed; }
    .status { font-size: 12px; color: var(--muted); margin-top: 8px; }
    .bar { height: 8px; background: #0d1320; border-radius: 999px; overflow: hidden; border: 1px solid var(--line); }
    .fill-send { height: 100%; width: 0; background: var(--gold); }
    .fill-recv { height: 100%; width: 0; background: var(--cyan); }
    .err { color: var(--danger); }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="card">
      <h1 class="title">局域网大文件直传</h1>
      <div class="muted">服务器仅做信令协商。文件数据走 WebRTC 点对点传输，不占服务器流量带宽。</div>
    </div>

    <div class="card">
      <div class="row">
        <button id="btnCreate" class="primary">创建房间</button>
        <input id="joinCode" maxlength="8" placeholder="输入房间码后加入" />
        <button id="btnJoin">加入房间</button>
      </div>
      <div id="roomText" class="status">未加入房间</div>
    </div>

    <div class="card">
      <div class="row" style="margin-bottom:8px;">
        <button id="btnPickDir">准备接收目录（推荐）</button>
        <span id="dirText" class="muted">未选择目录，将使用浏览器下载模式。</span>
      </div>
      <div class="row" style="margin-bottom:8px;">
        <input id="fileInput" type="file" disabled />
        <button id="btnSend" class="primary" disabled>发送文件</button>
      </div>
      <div id="sendText" class="status">发送状态：等待连接</div>
      <div class="bar"><div id="sendFill" class="fill-send"></div></div>
      <div id="recvText" class="status" style="margin-top:10px;">接收状态：等待连接</div>
      <div class="bar"><div id="recvFill" class="fill-recv"></div></div>
    </div>
  </div>

  <script>
  (function(){
    const apiBase = '/lan-transfer/api';
    const state = {
      roomCode: '',
      peerId: '',
      isHost: false,
      sinceId: 0,
      remotePeerId: '',
      offerStarted: false,
      pc: null,
      channel: null,
      pendingCandidates: [],
      pollTimer: null,
      roomTimer: null,
      dirHandle: null,
      recvCtx: null,
    };

    const $ = (id) => document.getElementById(id);
    const roomText = $('roomText');
    const sendText = $('sendText');
    const recvText = $('recvText');
    const sendFill = $('sendFill');
    const recvFill = $('recvFill');
    const dirText = $('dirText');
    const btnPickDir = $('btnPickDir');
    const fileInput = $('fileInput');
    const btnSend = $('btnSend');

    const setText = (el, text, isError) => {
      el.textContent = text;
      if (isError) el.classList.add('err'); else el.classList.remove('err');
    };
    const setPct = (el, p) => { el.style.width = Math.max(0, Math.min(100, p)) + '%'; };

    async function apiPost(path, data) {
      const body = new URLSearchParams(data);
      const resp = await fetch(apiBase + path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8' },
        body,
      });
      const json = await resp.json();
      if (!resp.ok || !json.ok) throw new Error(json.error || ('HTTP ' + resp.status));
      return json;
    }

    async function apiGet(path, data) {
      const qs = new URLSearchParams(data);
      const resp = await fetch(apiBase + path + '?' + qs.toString());
      const json = await resp.json();
      if (!resp.ok || !json.ok) throw new Error(json.error || ('HTTP ' + resp.status));
      return json;
    }

    function ensurePC() {
      if (state.pc) return state.pc;
      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
        iceCandidatePoolSize: 8,
      });
      pc.onicecandidate = async (ev) => {
        if (!ev.candidate) return;
        try { await sendSignal('candidate', ev.candidate); } catch (_) {}
      };
      pc.ondatachannel = (ev) => bindChannel(ev.channel);
      pc.onconnectionstatechange = () => {
        const st = pc.connectionState;
        if (st === 'connected') setText(roomText, '房间 ' + state.roomCode + ' 已建立 P2P 连接');
        if (st === 'failed' || st === 'disconnected') setText(roomText, '连接状态：' + st + '，请确认双方在同一局域网', true);
      };
      state.pc = pc;
      return pc;
    }

    function bindChannel(ch) {
      state.channel = ch;
      ch.binaryType = 'arraybuffer';
      ch.bufferedAmountLowThreshold = 2 * 1024 * 1024;
      ch.onopen = () => {
        fileInput.disabled = false;
        btnSend.disabled = false;
        setText(sendText, '发送状态：通道已连接');
        setText(recvText, '接收状态：通道已连接');
      };
      ch.onclose = () => {
        fileInput.disabled = true;
        btnSend.disabled = true;
        setText(sendText, '发送状态：连接已关闭', true);
        setText(recvText, '接收状态：连接已关闭', true);
      };
      ch.onerror = () => setText(sendText, '发送状态：通道异常', true);
      ch.onmessage = async (ev) => {
        if (typeof ev.data === 'string') {
          let msg = null;
          try { msg = JSON.parse(ev.data); } catch (_) { return; }
          if (msg.type === 'meta') await onRecvMeta(msg);
          if (msg.type === 'eof') await onRecvEnd();
          return;
        }
        await onRecvChunk(ev.data);
      };
    }

    async function sendSignal(kind, payload) {
      await apiPost('/signal/', {
        room_code: state.roomCode,
        peer_id: state.peerId,
        target_peer_id: state.remotePeerId || '',
        kind,
        payload: JSON.stringify(payload),
      });
    }

    async function flushPending() {
      const pc = state.pc;
      if (!pc || !pc.remoteDescription) return;
      for (const c of state.pendingCandidates) await pc.addIceCandidate(c);
      state.pendingCandidates = [];
    }

    async function onSignal(msg) {
      const pc = ensurePC();
      if (msg.kind === 'offer') {
        await pc.setRemoteDescription(new RTCSessionDescription(msg.payload));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        await sendSignal('answer', answer);
        await flushPending();
        return;
      }
      if (msg.kind === 'answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(msg.payload));
        await flushPending();
        return;
      }
      if (msg.kind === 'candidate') {
        const c = new RTCIceCandidate(msg.payload);
        if (!pc.remoteDescription) state.pendingCandidates.push(c);
        else await pc.addIceCandidate(c);
      }
    }

    async function sendOffer() {
      const pc = ensurePC();
      if (!state.channel) bindChannel(pc.createDataChannel('file', { ordered: true }));
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await sendSignal('offer', offer);
    }

    function startPolling() {
      if (state.pollTimer) clearInterval(state.pollTimer);
      state.pollTimer = setInterval(async () => {
        if (!state.roomCode || !state.peerId) return;
        try {
          const json = await apiGet('/poll/', { room_code: state.roomCode, peer_id: state.peerId, since_id: state.sinceId });
          state.sinceId = json.since_id;
          for (const msg of json.messages) {
            state.remotePeerId = msg.sender_peer_id;
            await onSignal(msg);
          }
        } catch (e) {
          setText(roomText, '信令异常：' + e.message, true);
        }
      }, 900);
    }

    function startRoomWatch() {
      if (state.roomTimer) clearInterval(state.roomTimer);
      state.roomTimer = setInterval(async () => {
        if (!state.roomCode || !state.peerId) return;
        try {
          const info = await apiGet('/room-info/', { room_code: state.roomCode, peer_id: state.peerId });
          setText(roomText, '房间 ' + info.room_code + '，在线 ' + info.peer_count + '/2，' + (info.is_ready ? '可传输' : '等待对端'));
          if (state.isHost && info.is_ready && !state.offerStarted) {
            state.offerStarted = true;
            await sendOffer();
          }
        } catch (e) {
          setText(roomText, '房间异常：' + e.message, true);
        }
      }, 1400);
    }

    function afterJoin(data, host) {
      state.roomCode = data.room_code;
      state.peerId = data.peer_id;
      state.isHost = host;
      state.sinceId = 0;
      state.offerStarted = false;
      state.remotePeerId = '';
      ensurePC();
      startPolling();
      startRoomWatch();
      setPct(sendFill, 0);
      setPct(recvFill, 0);
      setText(roomText, '已加入房间 ' + data.room_code + '，等待对端');
    }

    async function createRoom() {
      try {
        const data = await apiPost('/create-room/', {});
        afterJoin(data, true);
      } catch (e) { setText(roomText, '创建失败：' + e.message, true); }
    }

    async function joinRoom() {
      const code = $('joinCode').value.trim().toUpperCase();
      if (!code) return setText(roomText, '请先输入房间码', true);
      try {
        const data = await apiPost('/join-room/', { room_code: code });
        afterJoin(data, false);
      } catch (e) { setText(roomText, '加入失败：' + e.message, true); }
    }

    async function pickDir() {
      if (!window.showDirectoryPicker) {
        setText(dirText, '浏览器不支持目录选择，建议 Chrome/Edge', true);
        return;
      }
      try {
        const dir = await window.showDirectoryPicker({ mode: 'readwrite' });
        state.dirHandle = dir;
        setText(dirText, '已选择目录，接收将直接写入磁盘。');
      } catch (e) {
        setText(dirText, '目录选择失败：' + e.message, true);
      }
    }

    async function waitBufferedLow(ch, max = 8 * 1024 * 1024) {
      if (ch.bufferedAmount < max) return;
      await new Promise((resolve) => {
        const fn = () => { ch.removeEventListener('bufferedamountlow', fn); resolve(); };
        ch.addEventListener('bufferedamountlow', fn);
      });
    }

    async function sendFile() {
      const file = fileInput.files && fileInput.files[0];
      const ch = state.channel;
      if (!file) return setText(sendText, '发送状态：请先选择文件', true);
      if (!ch || ch.readyState !== 'open') return setText(sendText, '发送状态：通道未连接', true);

      setText(sendText, '发送中：' + file.name);
      setPct(sendFill, 0);

      try {
        ch.send(JSON.stringify({ type: 'meta', name: file.name, size: file.size, mime: file.type || 'application/octet-stream', ts: Date.now() }));
        let sent = 0;
        const reader = file.stream().getReader();
        while (true) {
          const r = await reader.read();
          if (r.done) break;
          await waitBufferedLow(ch);
          ch.send(r.value.buffer);
          sent += r.value.byteLength;
          setPct(sendFill, (sent / file.size) * 100);
        }
        ch.send(JSON.stringify({ type: 'eof' }));
        setPct(sendFill, 100);
        setText(sendText, '发送完成：' + file.name);
      } catch (e) {
        setText(sendText, '发送失败：' + e.message, true);
      }
    }

    async function onRecvMeta(meta) {
      setPct(recvFill, 0);
      const ctx = {
        name: meta.name || ('recv-' + Date.now()),
        size: Number(meta.size || 0),
        mime: meta.mime || 'application/octet-stream',
        received: 0,
        chunks: [],
        writable: null,
      };

      if (state.dirHandle) {
        try {
          const handle = await state.dirHandle.getFileHandle(ctx.name, { create: true });
          ctx.writable = await handle.createWritable();
          setText(recvText, '接收中：' + ctx.name + '（目录直写）');
        } catch (e) {
          setText(recvText, '目录写入失败，回退下载：' + e.message, true);
        }
      } else {
        setText(recvText, '接收中：' + ctx.name);
      }

      state.recvCtx = ctx;
    }

    async function onRecvChunk(data) {
      const ctx = state.recvCtx;
      if (!ctx) return;
      let chunk = data;
      if (data instanceof Blob) chunk = await data.arrayBuffer();

      if (ctx.writable) await ctx.writable.write(chunk);
      else ctx.chunks.push(chunk);

      ctx.received += chunk.byteLength || 0;
      if (ctx.size > 0) setPct(recvFill, (ctx.received / ctx.size) * 100);
    }

    async function onRecvEnd() {
      const ctx = state.recvCtx;
      if (!ctx) return;
      if (ctx.writable) {
        await ctx.writable.close();
        setText(recvText, '接收完成：' + ctx.name + '（已写入目录）');
      } else {
        const blob = new Blob(ctx.chunks, { type: ctx.mime });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = ctx.name;
        a.click();
        URL.revokeObjectURL(url);
        setText(recvText, '接收完成：' + ctx.name + '（浏览器下载）');
      }
      setPct(recvFill, 100);
      state.recvCtx = null;
    }

    $('btnCreate').addEventListener('click', createRoom);
    $('btnJoin').addEventListener('click', joinRoom);
    btnPickDir.addEventListener('click', pickDir);
    btnSend.addEventListener('click', sendFile);
  })();
  </script>
</body>
</html>
'''
