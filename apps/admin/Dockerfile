FROM node:22-alpine AS build
ARG CORE_API_URL=http://api:8000
ARG NEXT_PUBLIC_CORE_WS_URL=
ENV CORE_API_URL=${CORE_API_URL} \
    NEXT_PUBLIC_CORE_WS_URL=${NEXT_PUBLIC_CORE_WS_URL}
WORKDIR /app
COPY apps/admin/package.json apps/admin/package-lock.json ./
RUN npm ci
COPY apps/admin ./
RUN npm run build

FROM node:22-alpine
ARG CORE_API_URL=http://api:8000
ARG RELEASE_SHA=UNSET
LABEL org.opencontainers.image.revision="${RELEASE_SHA}"
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    CORE_API_URL=${CORE_API_URL} \
    RELEASE_SHA=${RELEASE_SHA}
WORKDIR /app
COPY --from=build /app ./
USER node
EXPOSE 3001
CMD ["npm", "run", "start"]
