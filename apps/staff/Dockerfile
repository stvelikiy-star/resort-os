FROM node:22-alpine AS build
WORKDIR /app
COPY apps/staff/package.json ./package.json
RUN npm install
COPY apps/staff ./
RUN npm run build

FROM node:22-alpine
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0
WORKDIR /app
COPY --from=build /app ./
USER node
EXPOSE 3002
CMD ["npm", "run", "start"]
