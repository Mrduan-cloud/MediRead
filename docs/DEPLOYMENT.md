# MediRead 部署指南

> 本文档涵盖两类部署场景：
> 1. **个人电脑（开发 / 调试 / 本地演示）** — Windows / macOS / Linux 均可
> 2. **企业私有化服务器（生产 / 内网试点 / 医院/体检机构内部部署）** — 推荐 Ubuntu 22.04 LTS

> ⚠️ MediRead 处理**用户敏感健康数据**，部署时必须严格遵循 §3.5 的数据保护清单。

---

## 1. 端口与依赖映射

| 服务       | 端口      | 用途                            | 必装                          |
| ---------- | --------- | ------------------------------- | ----------------------------- |
| api        | 8000      | FastAPI / Swagger / 业务接口    | 是                            |
| mysql      | 3306      | 业务库（报告 / 解读 / 审计）    | 是                            |
| redis      | 6379      | 会话缓存 / 限流                 | 是                            |
| milvus     | 19530     | 向量库（gRPC）                  | 是                            |
| milvus     | 9091      | Milvus 健康检查 HTTP            | 是                            |
| minio      | 9000      | 原始报告 / 解读结果归档         | 是                            |
| minio      | 9001      | MinIO Web 控制台                | 否                            |
| etcd       | 内部      | Milvus 元数据                   | 是                            |
| ollama     | 11434     | 本地 LLM（GLM-4-9B-Chat 等）    | **是（健康数据零外传的关键）** |
| Prometheus | 9090      | 指标抓取                        | 推荐                          |

> **关键依赖**：Docker 24+、Docker Compose v2、Python 3.11+（仅本地开发跑 API 非容器化时用）。

---

## 2. 个人电脑部署（开发 / 测试 / 本地演示）

### 2.1 推荐硬件配置

MediRead 本地全栈跑起来比 NutriCore 略重，主要消耗在 **PaddleOCR + Ollama LLM**：

| 资源   | 最低             | 推荐                                  | 说明                                                                          |
| ------ | ---------------- | ------------------------------------- | ----------------------------------------------------------------------------- |
| CPU    | 4 核             | **8 核+**                             | OCR 推理 CPU 也能跑（每页 1-3s）；GPU 更快                                    |
| 内存   | 16 GB            | **32 GB+**                            | Ollama 9B-Q4_K_M 常驻 ~6GB + Milvus + BGE；少于 16G 跑不动                    |
| 磁盘   | 80 GB SSD        | 200 GB SSD                            | LLM 6G + Embedding/Reranker 3G + Paddle 1G + 镜像                             |
| 显卡   | 不需要（CPU 可跑） | RTX 4090 24G / 任意 ≥ 12G 显存的 N 卡 | 装 GPU 可大幅加速 LLM（10x+）和 PaddleOCR；CPU 单页解读 30-60s，GPU < 5s    |
| 网络   | -                | -                                     | 首次下载 ~15G 内容（镜像 + 模型 + Paddle 字典）                              |

### 2.2 操作系统建议

| 系统            | 备注                                                                  |
| --------------- | --------------------------------------------------------------------- |
| **Windows 10/11** | 必须开启 WSL2 + Docker Desktop。OCR / Paddle 在 WSL2 下兼容性最好     |
| **macOS 14+**   | Apple Silicon (M1/M2/M3) 全栈兼容；OCR 走 CPU 推理                    |
| **Linux**       | Ubuntu 22.04 / 24.04 原生最佳；NVIDIA 驱动场景首选                    |

### 2.3 Windows 上一步步部署

```powershell
# 1. 装 Docker Desktop (勾选 "Use WSL 2")
#    https://docs.docker.com/desktop/install/windows-install/

# 2. 装 Git for Windows
#    https://git-scm.com/download/win

# 3. 克隆仓库
git clone https://github.com/Mrduan-cloud/MediRead.git
cd MediRead

# 4. 准备 .env (用记事本编辑)
copy .env.example .env
# 至少改两个：
#   JWT_SECRET_KEY=自己生成的长随机串
#   MYSQL_PASSWORD=自己设置

# 5. 启动栈（第一次 5-15 分钟拉镜像）
docker compose up -d

# 6. 等所有服务 healthy
docker compose ps
# 看到 mysql/redis/minio/milvus/ollama/api 都是 (healthy)

# 7. 拉取本地 LLM（关键步骤）
docker compose exec ollama ollama pull glm4:9b-chat-q4_k_m
# 6GB 模型，下载 5-30 分钟取决于网速
# 国内网络慢可换 qwen2.5:7b-instruct (也是 ~4GB)：
#   docker compose exec ollama ollama pull qwen2.5:7b-instruct
#   然后 .env 改 LLM_MODEL=qwen2.5:7b-instruct

# 8. 初始化数据 (建表 / Milvus 集合 / 灌医学知识库 / Demo 报告)
docker compose exec api python -m scripts.seed

# 9. 验证
#   - Swagger:  http://localhost:8000/docs
#   - 健康:     http://localhost:8000/ready
#   - MinIO:    http://localhost:9001  (账号 minioadmin/minioadmin)
#   - Metrics:  http://localhost:8000/metrics

# 10. 端到端 demo
docker compose exec api python -m scripts.demo
```

### 2.4 macOS / Linux 步骤

```bash
git clone https://github.com/Mrduan-cloud/MediRead.git && cd MediRead
cp .env.example .env
nano .env                                  # 改 JWT / 密码
docker compose up -d
docker compose ps
docker compose exec ollama ollama pull glm4:9b-chat-q4_k_m
docker compose exec api python -m scripts.seed
docker compose exec api python -m scripts.demo
```

### 2.5 上传体检报告（手测 /api/upload）

```bash
# 颁个 JWT（用 demo-001 账户）
TOKEN=$(docker compose exec -T api python -c "from app.auth.jwt import create_access_token; print(create_access_token('demo-001'))")

# 上传一张体检报告图（或 PDF）
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@./your_report.pdf"
# 返回 {report_id, object_key, format, size_bytes}

# 触发解析（OCR + 6 字段抽取 + 归一化）
curl -X POST http://localhost:8000/api/parse/<report_id> \
  -H "Authorization: Bearer $TOKEN"

# 触发解读（RAG + 多指标联合 + 风险分级）
curl -X POST http://localhost:8000/api/interpret/<report_id> \
  -H "Authorization: Bearer $TOKEN"
```

### 2.6 常见坑（开发机）

| 现象                                                    | 原因 / 解决                                                                  |
| ------------------------------------------------------- | ---------------------------------------------------------------------------- |
| `docker compose up` 卡在 milvus / paddleocr 拉镜像       | 配置国内 Docker 镜像加速器（阿里云/腾讯云）                                  |
| PaddleOCR 第一次解析慢 (15-30s)                          | 首次会下载 ~600MB det/rec/cls 模型；下载完后 1-3s/页                         |
| Ollama 模型下载失败                                      | 换镜像源：`docker compose exec ollama bash` 后 `OLLAMA_HOST=... ollama pull` |
| LLM 调用极慢（30s+）                                     | 用了 9B 模型且无 GPU。换 qwen2.5:7b 或加 GPU                                |
| `api` 启动后 /ready 返回 milvus=false                    | Milvus 第一次启动要 60-90s 拉 etcd / minio 依赖；多等                       |
| OCR 输出全空                                             | 图片质量太差 / 旋转角度太大；或 dpi 不够（PDF 改 200+）                     |
| 内存 OOM                                                 | Docker Desktop → Resources → 内存调到 ≥ 16 GB                               |

---

## 3. 企业私有化服务器部署（生产）

### 3.1 服务器配置建议

> MediRead 是 OCR + RAG + 本地 LLM 工作负载，且涉及医疗数据合规。**推荐拆 2 台机：业务机 + 推理机**。
>
> 不同公司阶段的硬件选型 / 成本 / ROI 对照表见 [`docs/HARDWARE.md`](HARDWARE.md)。

#### 方案 A：小公司私有化（默认推荐 ⭐）

| 角色       | 用途                              | CPU      | 内存       | 磁盘            | GPU                                              | 整机预算       |
| ---------- | --------------------------------- | -------- | ---------- | --------------- | ------------------------------------------------ | -------------- |
| 业务服务器 | API / MySQL / Milvus / MinIO / Redis | 16 核   | **64 GB**  | 1 TB SSD       | 不需要                                           | ~1.5–2 万 RMB  |
| 推理服务器 | Ollama (GLM-4-9B-Chat) + PaddleOCR + BGE + Reranker | 16 核 | 64 GB | 500 GB SSD | **单卡 RTX 4090 24G**                            | **~2.5–3 万 RMB** |

- **为什么选 4090**：9B 模型 Q4_K_M 显存 ~6GB，KV cache + PaddleOCR + BGE 全塞进 24GB 还有富余
- **成本对照**：整套 ~5 万 vs 用 A100 方案 ~30 万，差 6 倍

#### 方案 B：单机一体（POC / 单一医院/体检中心私有化部署）

| 资源 | 配置                                                     |
| ---- | -------------------------------------------------------- |
| CPU  | 16-32 核                                                 |
| 内存 | **64 GB**                                                |
| 磁盘 | 1 TB NVMe SSD                                            |
| GPU  | 单卡 RTX 4090 24G（业务 + 推理共用一台）                |

#### 方案 C：中型企业（多客户并发 / 更大模型）

| 配置                                                             | 适用场景                                          |
| ---------------------------------------------------------------- | ------------------------------------------------- |
| 推理机 A10 24G / L20 48G / A100 40G+；业务机内存 128 GB           | 多客户并发 / GLM-4-9B FP16 / 14B 模型 / 高 QPS    |
| 整机预算 **15–35 万 RMB**                                        | 已有稳定 5+ 家客户的中型 SaaS                     |

### 3.2 操作系统选择

| 系统                  | 推荐度       | 备注                                                            |
| --------------------- | ------------ | --------------------------------------------------------------- |
| **Ubuntu 22.04 LTS** | ★★★★★       | 首选；PaddlePaddle / NVIDIA 驱动 / Ollama 全部官方支持成熟      |
| Ubuntu 24.04 LTS     | ★★★★        | NVIDIA 驱动适配中；如要用 GPU 建议先用 22.04                    |
| Debian 12            | ★★★★        | 与 Ubuntu 兼容好；PaddlePaddle 需源码编译特定版本              |
| RHEL 9 / Rocky 9     | ★★★         | 国企/金融常用；OCR 系统依赖 (libgl/poppler) 需手动装           |
| OpenEuler 24.03      | ★★★         | 国产化路径；昇腾 NPU 推理时优选                                |
| Kylin V10 / UOS      | ★★          | 信创要求场景；需厂商提供 Docker + Paddle 适配包                |

### 3.3 Ubuntu 22.04 完整部署命令（生产）

```bash
# ============== 0. 预检 ==============
lsb_release -a
nproc && free -h && df -h
nvidia-smi             # 推理机执行，确认驱动

# ============== 1. 装 Docker ==============
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

sudo usermod -aG docker $USER
newgrp docker

# ============== 2. (GPU 机) NVIDIA Container Toolkit ==============
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi

# ============== 3. 系统调优 ==============
sudo bash -c 'cat >> /etc/security/limits.conf <<EOF
* soft nofile 65535
* hard nofile 65535
EOF'
sudo bash -c 'cat >> /etc/sysctl.conf <<EOF
vm.max_map_count=262144
vm.overcommit_memory=1
net.core.somaxconn=4096
EOF'
sudo sysctl -p
sudo swapoff -a && sudo sed -i '/ swap / s/^/#/' /etc/fstab
sudo timedatectl set-timezone Asia/Shanghai

# ============== 4. 拉代码 ==============
sudo mkdir -p /opt/mediread && sudo chown $USER /opt/mediread
cd /opt/mediread
git clone https://github.com/Mrduan-cloud/MediRead.git .

# ============== 5. 配 .env (生产化) ==============
cp .env.example .env
# 必改：
#   APP_ENV=prod
#   LOG_JSON=true
#   JWT_SECRET_KEY=$(openssl rand -hex 32)
#   MYSQL_ROOT_PASSWORD=$(openssl rand -hex 16)
#   MYSQL_PASSWORD=$(openssl rand -hex 16)
#   MINIO_ACCESS_KEY=$(openssl rand -hex 16)
#   MINIO_SECRET_KEY=$(openssl rand -hex 32)
#   CORS_ORIGINS=["https://mediread.your-company.com"]
#   LLM_BASE_URL=http://10.0.x.x:11434/v1   # 推理机内网 IP
#   UPLOAD_MAX_BYTES=52428800                # 生产可调大到 50MB
nano .env

# ============== 6. (GPU 机) 修改 docker-compose.yml 启用 GPU ==============
# 把 ollama service 下注释掉的 deploy.resources.reservations.devices 取消注释

# ============== 7. 启动 ==============
docker compose pull
docker compose up -d
watch -n 3 'docker compose ps'

# ============== 8. 拉 LLM ==============
docker compose exec ollama ollama pull glm4:9b-chat-q4_k_m
# 如需更强模型（要求更多显存）：
# docker compose exec ollama ollama pull glm4:9b-chat-fp16   (~18GB)
# docker compose exec ollama ollama pull qwen2.5:14b-instruct-q4_0

# ============== 9. 初始化 ==============
docker compose exec api python -m scripts.seed

# ============== 10. 反向代理 + HTTPS (nginx + Let's Encrypt) ==============
sudo apt install -y nginx certbot python3-certbot-nginx
sudo tee /etc/nginx/sites-available/mediread <<'EOF'
server {
    server_name mediread.your-company.com;
    client_max_body_size 50M;
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
        proxy_send_timeout 180s;
        # 单页 OCR 解析较慢，超时放大
    }
    location /metrics {
        allow 10.0.0.0/8;      # 仅内网
        deny all;
        proxy_pass http://127.0.0.1:8000/metrics;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/mediread /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d mediread.your-company.com   # 内网无外网时跳过

# ============== 11. 开机自启 ==============
sudo systemctl enable docker
```

### 3.4 离线环境部署（医院 / 内网不通公网）

```bash
# === 在能联网的同版本机器 ===
# 拉所有镜像
docker compose pull
docker pull ollama/ollama:latest

# 保存
docker save \
  mediread-api:0.2.0 \
  mysql:8.0 redis:7.2-alpine \
  minio/minio:RELEASE.2024-04-18T19-09-19Z \
  milvusdb/milvus:v2.4.0 quay.io/coreos/etcd:v3.5.5 \
  ollama/ollama:latest \
  | gzip > mediread-images.tar.gz

# 下载模型 (Ollama + BGE + Paddle)
docker run --rm -v $(pwd)/ollama-models:/root/.ollama ollama/ollama:latest ollama pull glm4:9b-chat-q4_k_m
# Paddle 模型：去 https://paddleocr.bj.bcebos.com/ 下载 ch_PP-OCRv4_det / ch_PP-OCRv4_rec / ch_ppocr_mobile_v2.0_cls
# BGE 模型：从 HF 镜像下载 BAAI/bge-large-zh-v1.5 与 BAAI/bge-reranker-large

# === 在目标内网机器 ===
scp mediread-images.tar.gz code.tar.gz ollama-models paddle-models bge-models /opt/mediread/
cd /opt/mediread
gunzip -c mediread-images.tar.gz | docker load
# 把 ollama-models 拷到 ollama_data 卷；paddle-models / bge-models 挂到 model_cache 卷
docker compose up -d
```

### 3.5 🔴 医疗数据保护清单（强制）

- [ ] `.env` 所有 SECRET / 密码已改为随机长串
- [ ] `JWT_SECRET_KEY` ≥ 32 字节
- [ ] `APP_ENV=prod` + `LOG_JSON=true`
- [ ] `CORS_ORIGINS` 设为前端真实域名
- [ ] MinIO 凭证已改、bucket 启用版本化与对象锁
- [ ] MySQL root 密码已改、远程访问关闭（仅 docker 内网）
- [ ] **绝对禁止**把任何端口（3306/6379/9000/19530/11434）直接暴露公网，仅放行 80/443
- [ ] Ollama / Embedding / Reranker **全部本地推理**，禁止配置任何第三方云 LLM URL
- [ ] **日志脱敏**：禁止把 OCR 原始内容 / 用户姓名 / 身份证号写入日志
- [ ] **审计日志** (`audit_log` 表) 保留 ≥ 6 个月，含 user_id / action / request_id
- [ ] MinIO bucket 静态加密 (SSE-S3)，配置生命周期：原始报告保留 90 天后归档冷存
- [ ] MySQL 备份：每日 dump + 异地，恢复演练 ≥ 季度一次
- [ ] 数据库与对象存储**不出本机房网络**；如需异地灾备，走专线 + 加密
- [ ] 网络隔离：业务 / 推理 / 数据库三段网，仅放行必要端口
- [ ] 渗透测试 / 等保 2.0 三级 / HIPAA / GDPR 合规自查（按客户行业要求）

### 3.6 信创 / 国产化环境特别说明

- **OpenEuler / Kylin V10**：Docker 用厂商兼容包；如必须用 podman，把 `docker compose` 换为 `podman compose`
- **昇腾 NPU**：把 Ollama 替换为华为 MindIE-LLM 容器，保持 OpenAI 兼容协议
- **PaddleOCR 昇腾版**：用 `paddlepaddle-npu` 替代 `paddlepaddle`
- **国产数据库**：MySQL 可换 OceanBase / TDSQL / 达梦；改 `MYSQL_DSN` 适配即可
- **离线 Embedding**：BGE 模型从社区镜像 (`hf-mirror.com`) 提前下载

---

## 4. 升级与运维

```bash
cd /opt/mediread && git pull
docker compose pull
docker compose up -d --build

# 健康
curl -s http://localhost:8000/ready | jq

# 备份 MySQL
docker compose exec mysql mysqldump -uroot -p$MYSQL_ROOT_PASSWORD mediread | gzip > backup-$(date +%F).sql.gz

# 备份 MinIO
docker run --rm --network host minio/mc alias set local http://localhost:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
docker run --rm --network host -v $(pwd)/minio-backup:/backup minio/mc mirror local/mediread /backup

# 滚动重启 API
docker compose restart api
```

---

## 5. 故障速查

| 症状                              | 排查                                                              |
| --------------------------------- | ----------------------------------------------------------------- |
| API 503 / 启动失败                | `docker compose logs --tail=200 api`                              |
| OCR 解析报 paddle.libpaddle 错误  | 缺 `libgl1` / `libgomp1`；Dockerfile 已装，自建镜像注意           |
| LLM 超时                          | `curl http://localhost:11434/api/tags` 确认 Ollama 服务在；查 GPU 是否被占满 |
| 报告抽取结果空                    | 体检报告图片旋转 / 像素低；调高 dpi、加预处理；查 OCR 模板归类     |
| 知识库检索 0 命中                 | 没跑 `scripts.seed`；或 `model_cache` 卷权限不对                  |
| 磁盘满                            | `du -sh /var/lib/docker/volumes/*`；清 ollama_data 旧模型         |
| OOM kill                          | `dmesg \| grep -i kill` 查；通常是 Ollama 模型太大，换小一档      |

---

> 如需 k8s 化部署、灾备双活、多模型混合推理等高级架构，请参考 `docs/architecture.md`。