FROM node:22-alpine AS build
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json apps/web/tsconfig.json ./
RUN npm ci
COPY apps/web/app/g ./app/g
COPY apps/web/app/guest-concierge.css apps/web/app/guest-marketplace.css apps/web/app/guest-owner-corrections.css ./app/
COPY apps/web/components/GuestConciergeRuntime.tsx apps/web/components/GuestAiAssistant.tsx apps/web/components/GuestAiAssistant.module.css apps/web/components/GuestHousekeepingPolicy.tsx apps/web/components/GuestMarketplace.tsx apps/web/components/GuestStayReview.tsx apps/web/components/GuestRoomDirections.tsx ./components/
COPY apps/web/lib/marinaGuestLocale.ts ./lib/
COPY deploy/marina/guest-web-layout.tsx ./app/layout.tsx
COPY deploy/marina/guest-web-next.config.mjs ./next.config.mjs
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM node:22-alpine
ARG RELEASE_SHA
LABEL org.opencontainers.image.revision="$RELEASE_SHA"
WORKDIR /app
ENV NODE_ENV=production HOSTNAME=0.0.0.0 PORT=3000 NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
USER node
CMD ["node", "server.js"]
