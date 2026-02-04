# Trading Noobs 部署指南 (VPS - ARM 架构 - Caddy 分离版)

针对您的 VPS 配置，我们已将应用服务与 Caddy 网关解耦。您可以将 Caddy 放在独立路径下运行，以便统一管理多个站点。

## 1. 准备工作 (VPS 上执行)

git clone https://github.com/drs-ai/tradingnoobs.git


### 1.1 前置网络环境
创建一个外部 Docker 网络，允许不同路径下的 Compose 容器互通：
```bash
sudo docker network create web-proxy
```

### 1.2 设置虚拟内存 (针对 1G 内存)
```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. 部署项目应用 (当前路径)

1.  **创建环境变量**: `nano .env`
    ```env
    DOMAIN=coz.japaneast.cloudapp.azure.com
    SECRET_KEY=829e7872b061f6e473e66b647b5b8bd6882f39dfb425dc39f79dd431d697258f
    DB_PASSWORD=Cudd1314
    ```
    > ⚠️ **注意**: 在 Docker Compose 中，如果密码包含 `$` 符号，必须使用 `$$` 进行转义，否则会被当做变量解析导致密码错误。
2.  **启动应用**: `sudo docker-compose up -d --build`
    *(此路径包含 Backend, Frontend, Postgres)*

## 3. 部署 Caddy (在您的独立路径下)

在您的 Caddy 运行路径下，确保目录结构如下：
*   `Caddyfile` (见下方)
*   `docker-compose.yml` (用于 Caddy 镜像)

### 3.1 Caddyfile 配置
```caddy
{$DOMAIN} {
    # 转发前端 (使用容器名或 localhost)
    handle {
        reverse_proxy tradingnoobs-frontend:3000
    }
    
    # 转发后端 API
    handle /api/* {
        reverse_proxy tradingnoobs-backend:8000
    }

    encode gzip
}
```

### 3.2 Caddy 的 Compose (示例)
```yaml
version: '3.8'
services:
  caddy:
    image: caddy:2-alpine
    container_name: global-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    networks:
      - web-proxy

networks:
  web-proxy:
    external: true
```

## 4. 维护
*   **应用层**: `docker-compose ps`
*   **网关层**: 在 Caddy 路径下运行 `docker-compose reload` (或 restart)

## 5. 賬戶管理 (User Management)

部署完成後，您可以使用內置腳本管理用戶權限和密碼：

### 5.1 提升管理員權限
1.  在網頁端正常註冊一個賬號。
2.  在 VPS 上執行以下命令（將 `your@email.com` 替換為您的註冊郵箱）：
    ```bash
    sudo docker exec -it tradingnoobs-backend python manage_users.py promote-admin your@email.com
    ```
3.  重新登錄後即可看到管理員功能。

### 5.2 重置用戶密碼
如果您遺忘了密碼，可以通過服務器後台強制重置：
```bash
sudo docker exec -it tradingnoobs-backend python manage_users.py reset-password your@email.com new_password
```

## 6. 運維與保養 (Maintenance & Operations)

### 6.1 數據庫備份 (重要)
我們已內置備份腳本。建議定期運行：
```bash
# 給予執行權限
chmod +x backup_db.sh
# 手動執行
./backup_db.sh
```
備份文件存放在 `./backups` 目錄，建議定期下載到本地。

### 6.2 監控資源佔用
您的 VPS 只有 1G 內存，可以使用以下命令查看容器實時佔用情况：
```bash
sudo docker stats
```

### 6.3 磁盤清理
如果 60G 空間告急，可以執行以下命令清理 Docker 緩存和無效鏡像：
```bash
# 清理未使用的鏡像、容器和網絡
sudo docker system prune -f
```

### 6.4 快速更新
代碼更新後，在 VPS 執行：
```bash
git pull
sudo docker-compose up -d --build
```
