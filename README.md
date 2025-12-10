**本人不会编程,所有代码由 Gemini3-pro 交互完成**

**ollama开放了cloud api，普通用户可以免费使用ollama提供的大语言模型,大多数第三方llama平台支持openai api,而ollama cloud的api无法直接与其他平台直接进行对接**

**为白嫖ollama的cloud api,固此项目诞生。**

# 💡 Ollamacloud-Proxy
本项目旨在开发一个轻量级的 API 转换代理层（API Proxy），核心功能是将客户端发送的 OpenAI 兼容 的 Chat Completion 请求格式无缝地转换为 Ollama Cloud API 所要求的格式，并反向处理 Ollama Cloud 的响应，使其以标准的 OpenAI Server-Sent Events (SSE) 流式格式返回给客户端。



# 📌 项目目标与核心价值
- 实现兼容性与互操作性：

使任何已经适配 OpenAI API 规则 的现有工具、框架（如 LangChain、各种 LLM 前端应用）或企业内部系统，无需修改代码即可直接调用 Ollama Cloud 的模型服务。

- 降低集成成本：

通过标准化接口，极大地降低了在智慧园区或企业信息化项目中集成 Ollama Cloud 大模型的门槛和时间成本，实现快速切换和部署。

- 标准化流式输出：

精确处理 Ollama 的逐行 JSON 响应流，并将其转换为符合 OpenAI 规范的 SSE 流格式，确保高效、稳定的流式输出体验。

# ⚙️ 技术栈与架构
编程语言/框架： Python / Flask

关键技术： HTTP 请求代理、JSON 数据结构转换、Server-Sent Events (SSE) 响应流处理。

# 🎯 适用场景
本项目特别适用于需要利用 Ollama Cloud 提供的强大模型能力，同时又希望在已有的、遵循 OpenAI 生态标准的系统架构中快速接入的场景。例如：

- 企业内部开发： 在不改动核心应用代码的前提下，利用 Ollama Cloud 提供的模型（如 gpt-oss:120b-cloud）替换现有 OpenAI 调用。

- 平台集成： 作为智慧园区或智慧城市平台的一个微服务网关，统一对外提供符合行业标准的 AI 接口。


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

