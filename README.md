# Ollamacloud-Proxy
本项目旨在开发一个轻量级的 API 转换代理层（API Proxy），核心功能是将客户端发送的 OpenAI 兼容 的 Chat Completion 请求格式无缝地转换为 Ollama Cloud API 所要求的格式，并反向处理 Ollama Cloud 的响应，使其以标准的 OpenAI Server-Sent Events (SSE) 流式格式返回给客户端。
