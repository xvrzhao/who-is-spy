FROM python:3.14-slim

# 更换时区
ENV TZ=Asia/Shanghai

# pip 走阿里云源
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
ENV PIP_DISABLE_PIP_VERSION_CHECK=1

# apt 换阿里云源（trixie 为 deb822 格式，deb 与 security 同域名一次替换）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
# 互斥已下沉 PG（game_threads 表），多 worker 不会同一局双流；暂保持单 worker，需要横向扩容时直接加 --workers
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
