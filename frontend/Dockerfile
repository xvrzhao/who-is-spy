# ---- 构建阶段：编译前端静态资源 ----
FROM node:20-alpine AS build
WORKDIR /app

# 先装依赖（利用层缓存：package*.json 不变则跳过重装）
COPY package.json package-lock.json ./
RUN npm config set registry https://registry.npmmirror.com && npm ci --no-audit --no-fund

COPY . .
# npm run build = vue-tsc 类型检查 + vite build
RUN npm run build

# ---- 运行阶段：nginx 托管静态资源并反代 /api ----
FROM nginx:1.27-alpine

# 时区与后端一致
ENV TZ=Asia/Shanghai

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
