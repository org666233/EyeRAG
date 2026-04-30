# ---- 前端 ----
FROM node:18-alpine AS build

WORKDIR /app/frontend
COPY frontend/package*.json .
RUN npm ci

COPY frontend/ .
RUN npm run build

# 生产环境
FROM nginx:alpine
COPY --from=build /app/frontend/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
