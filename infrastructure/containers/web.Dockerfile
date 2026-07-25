FROM node:22-alpine

RUN corepack enable
WORKDIR /app

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/relief_contracts/package.json packages/relief_contracts/package.json
COPY packages/design_system/package.json packages/design_system/package.json
COPY packages/test_fixtures/package.json packages/test_fixtures/package.json
COPY packages/typescript_config/package.json packages/typescript_config/package.json
RUN pnpm install --frozen-lockfile

COPY apps/web apps/web
COPY packages packages
RUN pnpm --filter web build

EXPOSE 3000
CMD ["pnpm", "--filter", "web", "start"]
