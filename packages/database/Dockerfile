FROM node:22-alpine

WORKDIR /app

COPY packages/database/package*.json ./
RUN if [ -f package-lock.json ]; then \
      npm ci --no-audit --no-fund; \
    else \
      npm install --no-audit --no-fund; \
    fi

COPY packages/database/prisma ./prisma

USER node

CMD ["npx", "--no-install", "prisma", "migrate", "deploy"]
