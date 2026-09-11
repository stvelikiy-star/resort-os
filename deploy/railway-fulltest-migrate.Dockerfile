FROM node:22-alpine
WORKDIR /app/packages/database
COPY packages/database/package.json packages/database/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY packages/database ./
CMD ["sh","-lc","npx prisma migrate deploy && echo MIGRATIONS_OK && sleep infinity"]
