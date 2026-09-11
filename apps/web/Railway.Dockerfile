FROM node:22-alpine AS build
ARG CORE_API_URL=http://api.railway.internal:8000
ENV CORE_API_URL=${CORE_API_URL}
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . ./
RUN npm run build

FROM node:22-alpine
ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    CORE_API_URL=http://api.railway.internal:8000
WORKDIR /app
COPY --from=build /app ./
USER node
EXPOSE 3000
CMD ["npm", "run", "start"]
