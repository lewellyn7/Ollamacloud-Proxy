**本人不会编程,所有代码由 Gemini3-pro 交互完成**

**ollama开放了cloud api，普通用户可以免费使用ollama提供的大语言模型,大多数第三方llama平台支持openai api,而ollama cloud的api无法直接与其他平台直接进行对接**

**为白嫖ollama的cloud api,固此项目诞生。**

# 💡 Ollamacloud-Proxy
本项目旨在开发一个轻量级的 API 转换代理层（API Proxy），核心功能是将客户端发送的 OpenAI 兼容 的 Chat Completion 请求格式无缝地转换为 Ollama Cloud API 所要求的格式，并反向处理 Ollama Cloud 的响应，使其以标准的 OpenAI Server-Sent Events (SSE) 流式格式返回给客户端。

# 📌 项目目标与核心价值
- 实现兼容性与互操作性：

使任何已经适配 OpenAI API 规则 的现有工具、框架（如 LangChain、各种 LLM 前端应用）或企业内部系统，无需修改代码即可直接调用 Ollama Cloud 的模型服务。

- 降低集成成本：

通过标准化接口，极大地降低了在项目中集成 Ollama Cloud 大模型的门槛和时间成本，实现快速切换和部署。

- 标准化流式输出：

精确处理 Ollama 的逐行 JSON 响应流，并将其转换为符合 OpenAI 规范的 SSE 流格式，确保高效、稳定的流式输出体验。

# ⚙️ 技术栈与架构
编程语言/框架： Python / Flask

关键技术： HTTP 请求代理、JSON 数据结构转换、Server-Sent Events (SSE) 响应流处理。

# 🎯 适用场景
本项目特别适用于需要利用 Ollama Cloud 提供的强大模型能力，同时又希望在已有的、遵循 OpenAI 生态标准的系统架构中快速接入的场景。例如：

- 企业内部开发： 在不改动核心应用代码的前提下，利用 Ollama Cloud 提供的模型（如 gpt-oss:120b-cloud）替换现有 OpenAI 调用。

- 平台集成： 作为一个微服务网关，统一对外提供符合行业标准的 AI 接口。

# ✅ 已实现功能清单

## 1. 核心协议转换 (Protocol Translation)
- OpenAI 标准兼容：将 Ollama 的原生接口（/api/chat）转换为标准的 OpenAI 接口格式（/v1/chat/completions）。

- 流式响应支持 (SSE)：完美支持打字机效果（Streaming），实时转换 Ollama 的流式数据为 OpenAI chunk 格式。

- 非流式响应适配：自动聚合 Ollama 的响应内容，解决第三方软件报 Reading '0' 或 undefined 的格式错误。

路径智能兼容：同时支持带 /v1 前缀（.../v1/chat/completions）和不带前缀（.../chat/completions）的请求，并未第三方客户端常见的双斜杠（//v1）错误提供自动修复中间件。

## 2. 多租户与隔离系统 (Multi-Tenancy & Isolation)
- 多用户注册/登录：支持新用户注册（含邮箱、密码），支持用户登录鉴权（Cookie/Session 管理）。

- 私有化密钥池 (Private Key Pool)：

  - 数据隔离：每个用户拥有独立的“上游 Ollama 密钥池”。
  
  - 权限控制：用户 A 的 API 请求只会轮询用户 A 提供的 Ollama Key，绝不会消耗用户 B 的额度。

- 客户端密钥管理 (Client Keys)：

  - 用户可以在后台生成多个 sk-prox-... 格式的 API Key。
  
  - 支持为 Key 添加备注（如 "Cursor专用", "手机端"）。
  
  - 支持随时撤销/删除 Key。

## 3. 高可用与智能调度 (HA & Load Balancing)
- 随机负载均衡：当用户配置了多个上游 Ollama Key 时，系统会随机打乱调用顺序，实现负载均摊。

- 智能故障转移 (Auto-Failover)：

  - 如果当前使用的 Key 返回 403 Premium Limit（额度超限）或 401 Unauthorized，系统会自动记录日志并无缝切换到池中的下一个 Key 重试。

用户端无感知，极大提高了服务的稳定性。

- 连通性测试：后台提供“测试连接”功能，能通过用户的私有 Key 池真实请求上游，列出当前可用的模型列表（如 deepseek-v3, qwen2.5 等）。

## 4. 安全防护机制 (Security)
- 防暴力破解：

  - 同一账号连续输错 5 次密码，自动锁定账号 30 分钟。

  - 同步封锁来源 IP 30 分钟，期间拒绝该 IP 的所有登录请求。

- 防恶意注册：

  - 同一 IP 地址限制注册账号数量（防止脚本批量注册）。

  - 校验用户名和邮箱的唯一性。

- 密码安全：所有密码均经过 SHA-256 哈希加密存储。

## 5. 用户体验与管理 (UX)
- Web 管理后台：

  - 基于 Vue.js 的现代化响应式界面。
  
  - 支持右上角下拉菜单进行“修改密码”和“退出登录”。
  
  - 集成 Toast 消息通知系统，操作反馈（成功/失败）清晰直观。

个人中心：提供修改密码的独立页面，需验证旧密码。

## 6. 部署与维护
- Docker 化部署：提供 Dockerfile 和 docker-compose.yml，支持一键启动。

- 自动化安装脚本：提供 setup.sh 脚本，自动生成目录结构、配置文件和数据库初始化代码，实现“零配置”部署。

- 数据持久化：所有数据（用户、Key、配置）存储在本地 SQLite 数据库文件（data/proxy.db）中，重启不丢失。

# 部署方式

- 安装 docker,docker官方安装命令:

```
wget -qO- https://get.docker.com/ | sh
```

- 拉取项目

```
git clone https://github.com/lewellyn7/Ollamacloud-Proxy.git
```

 国内用户用如下命令
 
```
git clone https://raw.githubusercontent.com/lewellyn7/Ollamacloud-Proxy.git
```

或者

```
git clone https://raw.gitmirror.com/lewellyn7/Ollamacloud-Proxy.git
```

- 进入项目文件夹
  
```
 cd  Ollamacloud-Proxy
```

- docker compose 部署
  
```
docker compose up -d --build
```

- 访问

- 默认用户名及密码均为'admin'，请登录后及时修改
  
```
admin
```

# ollama api获取

- 访问ollama官网：右上角sign in，用google 或 github 账户登录，或者按流程注册账户
  
```
https://ollama.com/
```

- 获取ollama cloud 的api：访问key地址
  
```
https://ollama.com/settings/keys
```

点击 **Add API Key** 按钮 获取新的 api key，并保存

