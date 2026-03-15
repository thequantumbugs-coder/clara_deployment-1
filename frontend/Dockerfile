# Stage 1: Build the frontend
FROM node:20-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Build args for env vars needed at build time
ARG VITE_WS_URL=ws://localhost:6969/ws/clara
ARG VITE_VOICE_INPUT_MODE=browser
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_VOICE_INPUT_MODE=$VITE_VOICE_INPUT_MODE

RUN npm run build

# Stage 2: Serve with nginx
FROM nginx:stable-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
