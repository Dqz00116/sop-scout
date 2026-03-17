# Windows 部署指南

本文档指导如何在 Windows 系统上部署 SOP 提取工作流。

## 前置要求

### 1. 安装 Python 3.10+
- 下载地址：https://www.python.org/downloads/
- 安装时勾选 "Add Python to PATH"

### 2. 验证 Python 安装
```cmd
python --version
```

### 3. 安装 Git（可选）
- 下载地址：https://git-scm.com/download/win

### 4. 安装 7-Zip（用于解压测试文件）
- 下载地址：https://www.7-zip.org/

## 环境配置

### 1. 创建虚拟环境
```cmd
cd C:\projects\sop-extraction
python -m venv venv
```

### 2. 激活虚拟环境
```cmd
venv\Scripts\activate
```

### 3. 安装依赖
```cmd
pip install -r requirements.txt
```

## 跨平台兼容性修改

### 已修改的文件（自动处理）
项目已自动处理跨平台兼容性，以下文件已使用跨平台路径处理：

1. **`src/graphs/nodes/merge_results_node.py`**
   - 原代码：`file_path = f"/tmp/sop_batch_{file_index}.jsonl"`
   - 修改为：使用 `tempfile.gettempdir()` 获取系统临时目录

2. **`src/utils/file/file.py`**
   - 原代码：`DOWNLOAD_DIR = "/tmp"`
   - 修改为：`DOWNLOAD_DIR = tempfile.gettempdir()`

### Windows 特殊路径说明
- **临时目录**：`C:\Users\用户名\AppData\Local\Temp`
- **项目根目录**：使用 `COZE_WORKSPACE_PATH` 环境变量指定

## 环境变量配置

### 方式1：使用命令行设置（临时）
```cmd
set COZE_WORKSPACE_PATH=C:\projects\sop-extraction
set COZE_BUCKET_ENDPOINT_URL=https://your-endpoint.com
set COZE_BUCKET_NAME=your-bucket-name
set COZE_API_KEY=your-api-key
```

### 方式2：使用 .env 文件（推荐）
在项目根目录创建 `.env` 文件：

```env
COZE_WORKSPACE_PATH=C:\projects\sop-extraction
COZE_BUCKET_ENDPOINT_URL=https://your-endpoint.com
COZE_BUCKET_NAME=your-bucket-name
COZE_API_KEY=your-api-key
SOP_CONCURRENCY=50
SOP_BATCH_SIZE=10
```

### 方式3：使用系统环境变量（永久）
1. 右键点击"此电脑" → "属性" → "高级系统设置"
2. 点击"环境变量"
3. 添加用户变量或系统变量

## LLM API 配置

### 1. 豆包 API（推荐）
```env
# 方式1：环境变量
set COZE_API_KEY=your-doubao-api-key

# 方式2：在 .env 文件中
COZE_API_KEY=your-doubao-api-key
```

### 2. 其他 LLM 提供商
如果使用其他 LLM 提供商，需要修改 `config/extract_sop_cfg.json` 中的 `model` 字段。

## 启动服务

### 方式1：命令行启动
```cmd
python -m src.main
```

### 方式2：使用 uvicorn 启动
```cmd
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式3：使用 Windows 服务（生产环境推荐）
使用 `nssm` 或 `winsw` 将应用注册为 Windows 服务。

```cmd
# 使用 nssm 安装服务
nssm install SOPExtraction python C:\projects\sop-extraction\venv\Scripts\python.exe -m src.main
nssm start SOPExtraction
```

## 测试部署

### 1. 健康检查
```cmd
curl http://localhost:8000/health
```

### 2. 提交测试任务
```cmd
curl -X POST http://localhost:8000/run ^
  -H "Content-Type: application/json" ^
  -d "{\"zip_file\": {\"url\": \"C:\\projects\\sop-extraction\\test.zip\", \"file_type\": \"document\"}}"
```

### 3. 查询进度
```cmd
curl http://localhost:8000/progress/{run_id}
```

## Windows 特殊注意事项

### 1. 文件路径分隔符
- Windows 使用反斜杠 `\`
- Python 的 `os.path.join()` 会自动处理，无需手动修改
- 在 JSON 中使用双反斜杠 `\\` 或正斜杠 `/`

### 2. 文件权限
- Windows 的文件权限系统与 Linux 不同
- 确保 Python 进程有读写临时目录的权限

### 3. 防火墙设置
- 如果需要远程访问，需要配置 Windows 防火墙
- 允许端口 8000（或自定义端口）的入站连接

### 4. 日志文件位置
- Linux：`/app/work/logs/bypass/app.log`
- Windows：`C:\projects\sop-extraction\logs\app.log`
- 需要确保日志目录存在并有写入权限

### 5. 多进程/多线程
- Windows 对多进程的支持与 Linux 不同
- 项目使用 `ThreadPoolExecutor`，与 Windows 兼容
- 避免使用 `os.fork()`，改用 `multiprocessing`

### 6. 长路径支持
- Windows 默认路径长度限制为 260 字符
- 如果文件路径过长，需要启用长路径支持
- 修改注册表或使用组策略启用长路径

## 常见问题

### 1. ModuleNotFoundError: No module named 'xxx'
**解决方法**：
```cmd
pip install -r requirements.txt
```

### 2. 临时目录权限错误
**错误信息**：`PermissionError: [Errno 13] Permission denied: 'C:\\Users\\...'`

**解决方法**：
- 以管理员身份运行
- 或将临时目录修改到有权限的目录

### 3. 编码错误
**错误信息**：`UnicodeDecodeError: 'utf-8' codec can't decode byte...`

**解决方法**：
- 确保 Python 文件使用 UTF-8 编码保存
- 在文件读取时明确指定编码：`open(file_path, 'r', encoding='utf-8')`

### 4. 端口被占用
**错误信息**：`Address already in use`

**解决方法**：
```cmd
# 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <进程ID> /F
```

### 5. 防火墙阻止连接
**解决方法**：
```cmd
# 添加防火墙规则
netsh advfirewall firewall add rule name="SOP Extraction" dir=in action=allow protocol=TCP localport=8000
```

## 性能优化建议

### 1. 调整并发数
```env
SOP_CONCURRENCY=50  # 根据CPU核心数调整
```

### 2. 调整批处理大小
```env
SOP_BATCH_SIZE=10  # 根据内存大小调整
```

### 3. 使用 SSD
- 将临时目录和日志目录放在 SSD 上提升性能

### 4. 调整 Python 内存限制
```cmd
python -m src.main --max-memory=4GB
```

## 生产环境部署清单

- [ ] 安装 Python 3.10+
- [ ] 创建虚拟环境
- [ ] 安装依赖包
- [ ] 配置环境变量
- [ ] 配置 LLM API
- [ ] 配置对象存储
- [ ] 创建日志目录
- [ ] 配置防火墙
- [ ] 测试健康检查
- [ ] 测试完整流程
- [ ] 配置自动重启（使用 Windows 服务或任务计划程序）
- [ ] 配置日志轮转
- [ ] 配置监控告警
- [ ] 备份配置文件
- [ ] 编写运维文档

## 联系支持

如有问题，请联系技术支持或查看项目文档：
- README.md
- AGENTS.md
- docs/API.md
