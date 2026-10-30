FROM node:24-slim
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.strict-dep-builds=false
COPY . .
RUN pnpm build
CMD ["pnpm", "start", "--port", "3000"]
