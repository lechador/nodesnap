FROM node:24-slim
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile --config.strict-dep-builds=false
COPY . .
# Rewrites are baked into the build output, so the API origin must be a build arg.
ARG NODESNAP_API=http://localhost:8000
ENV NODESNAP_API=$NODESNAP_API
RUN pnpm build
CMD ["pnpm", "start", "--port", "3000"]
