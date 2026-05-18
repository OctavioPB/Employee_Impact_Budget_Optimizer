FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# ── Production: serve with nginx ──────────────────────────────────────────────
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html

# Forward /api/* to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
