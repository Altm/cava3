FROM node:18 AS build
WORKDIR /app

RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .

ARG VITE_API_BASE_PATH=http://backend:8000
ARG VITE_USE_MOCK=false
ENV VITE_API_BASE_PATH=${VITE_API_BASE_PATH}
ENV VITE_USE_MOCK=${VITE_USE_MOCK}

RUN pnpm format
RUN pnpm run build:pro

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 4000
CMD ["nginx", "-g", "daemon off;"]
