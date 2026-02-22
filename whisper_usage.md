# Whisper 局域网服务使用文档

## 1. 启动服务
在项目目录执行（推荐低延迟实时参数）：

```bash
REALTIME_PARTIAL_INTERVAL_MS=300 REALTIME_PARTIAL_WINDOW_SECONDS=4 \
.venv/bin/python -m uvicorn server_mlx:app --host 0.0.0.0 --port 8000 --ws-ping-interval 20 --ws-ping-timeout 120
```

## 2. 健康检查

```bash
curl -s http://127.0.0.1:8000/health
```

期望返回：`status=ok`，并包含 `realtime_ws: /v1/realtime/transcribe`。

## 3. HTTP 文件转写（离线）
接口：`POST /transcribe`

```bash
curl -s -X POST "http://127.0.0.1:8000/transcribe?task=transcribe&language=zh" \
  -F "file=@/path/to/audio.wav"
```

返回包含：
- `text`：完整文本
- `segments`：分段时间戳
- `audio_seconds`、`rtf`、`timing_ms`

## 4. WebSocket 实时转写
接口：`ws://<IP>:8000/v1/realtime/transcribe`

### 4.1 客户端发送
1. 文本帧（JSON）先发 `start`
2. 持续发送二进制音频帧（`pcm_s16le`，单声道，16k）
3. 可选发 `flush`
4. 最后发 `stop`

`start` 示例：
```json
{"type":"start","sample_rate":16000,"format":"pcm_s16le","task":"transcribe","language":"zh","partial_interval_ms":300}
```

### 4.2 服务端返回
- `started`：会话已建立
- `partial`：中间结果（当前窗口文本，可能包含重复/修订）
- `final`：结束时最终结果（含 `segments`）
- `done`：会话完成
- `error`：错误信息

## 5. 直接用自带实时客户端测试
列麦克风设备：
```bash
.venv/bin/python realtime_client.py --list-devices
```

实时测试：
```bash
.venv/bin/python realtime_client.py \
  --url ws://127.0.0.1:8000/v1/realtime/transcribe \
  --language zh \
  --partial-interval-ms 300 \
  --ping-timeout 120
```

## 6. 常见问题
- `403 WebSocket /v1/realtime/`：路径错误，应使用 `/v1/realtime/transcribe`。
- `partial` 重复上次内容：实时模式返回“当前窗口完整文本”，不是增量。
- 偶发识别出“奇怪句子”：属于模型幻觉，已启用抑制参数；可继续调 `WHISPER_NO_SPEECH_THRESHOLD`、`WHISPER_LOGPROB_THRESHOLD`。
