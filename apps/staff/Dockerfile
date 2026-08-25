FROM node:22-alpine AS build
ARG CORE_API_URL=http://api:8000
ENV CORE_API_URL=${CORE_API_URL}
WORKDIR /app
COPY apps/staff/package.json ./package.json
RUN npm install
COPY apps/staff ./
RUN npm run build

FROM node:22-alpine
ARG CORE_API_URL=http://api:8000
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    CORE_API_URL=${CORE_API_URL}
WORKDIR /app
COPY --from=build /app ./
USER node
EXPOSE 3002
CMD ["npm", "run", "start"]
