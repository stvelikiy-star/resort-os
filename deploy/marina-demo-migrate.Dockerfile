FROM node:22-alpine
WORKDIR /workspace/packages/database
COPY packages/database/package.json packages/database/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY packages/database/prisma ./prisma
CMD ["npx","prisma","migrate","deploy"]
