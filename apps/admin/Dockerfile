FROM node:22-alpine AS build
WORKDIR /app
COPY apps/admin/package.json ./package.json
RUN npm install
COPY apps/admin ./
RUN npm run build

FROM node:22-alpine
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build /app ./
USER node
EXPOSE 3001
CMD ["npm", "run", "start"]
