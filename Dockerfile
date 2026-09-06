FROM python:3.14-slim

# 更换时区
ENV TZ=Asia/Shanghai
RUN apt-get update && apt-get install -y --no-install-recommends tzdata \
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
