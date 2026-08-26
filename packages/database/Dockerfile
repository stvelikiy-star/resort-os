FROM node:22-alpine

WORKDIR /app

COPY packages/database/package.json ./package.json
RUN npm install --no-audit --no-fund

COPY packages/database/prisma ./prisma

USER node

CMD ["npx", "prisma", "migrate", "deploy"]
