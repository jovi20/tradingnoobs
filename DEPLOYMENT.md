# Trading Noobs 部署指南 (VPS - ARM 架构)

针对您的 VPS 配置（ARM 2C/1G/60G），我们推荐使用 **Docker Compose** 进行一键部署。由于 1GB 内存对于 Next.js 编译较为吃力，请务必按照以下步骤设置 **虚拟内存 (Swap)**。

## 1. 准备工作 (VPS 上执行)

### 1.1 安装 Docker
```bash
# 更新并安装必备组件
sudo apt update && sudo apt install -y docker.io docker-compose git

# 启动 Docker 并设置开机自启
sudo systemctl start docker
sudo systemctl enable docker
```

### 1.2 设置虚拟内存 (关键：防止 1G 内存构建失败)
```bash
# 创建 2GB 的交换文件
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 设置永久生效
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. 获取代码并配置环境

### 2.1 克隆仓库
```bash
git clone <您的仓库地址> tradingnoobs
cd tradingnoobs
```

### 2.2 创建环境变量文件
创建 `.env` 文件并填入您的信息：
```bash
nano .env
```
填入以下内容：
```env
DOMAIN=yourdomain.com      # 您的域名，没有域名则填公网 IP
SECRET_KEY=yoursecretkey   # 随机长字符串，用于 JWT 加密
DB_PASSWORD=yourdbpassword # 数据库密码
```

## 3. 启动部署

使用一条命令即可完成：
*   拉取基础镜像 (ARM 自动匹配)
*   编译前端 (Next.js)
*   安装后端依赖
*   通过 Caddy 自动配置 SSL 证书

```bash
sudo docker-compose up -d --build
```

## 4. 维护与查看

*   **查看运行状态**: `sudo docker-compose ps`
*   **查看日志**: `sudo docker-compose logs -f`
*   **重启服务**: `sudo docker-compose restart`

## 5. 其他注意事项

1.  **域名解析**: 请将您的域名 A 记录指向 VPS 的公网 IP。
2.  **防火墙**: 确保 VPS 开放了 `80` (HTTP) 和 `443` (HTTPS) 端口。
3.  **无域名部署**: 如果没有域名，Caddyfile 会使用 HTTP。建议在 `.env` 中填入 IP。

---
**Trading Noobs 极简部署方案**
(ARM 架构已自动设配，Dockerfile 已针对低内存环境进行了分阶段优化)
