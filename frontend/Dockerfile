# syntax=docker/dockerfile:1.7
# Multi-stage build for a Next.js 16 app with `output: 'standalone'`.
# Optimized for Cloud Run: small final image, no node_modules at runtime,
# the standalone server.js respects PORT/HOSTNAME env vars.

# ---------- Stage 1: deps ----------
FROM node:22-alpine AS deps
WORKDIR /app

# Install only what's needed to resolve native deps on alpine
RUN apk add --no-cache libc6-compat

COPY package.json package-lock.json* .npmrc* ./
RUN npm ci

# ---------- Stage 2: builder ----------
FROM node:22-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# ---------- Stage 3: runner ----------
FROM node:22-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
ENV PORT=8080

# Create a non-root user
RUN addgroup --system --gid 1001 nodejs \
 && adduser --system --uid 1001 nextjs

# Public assets and the standalone server (server.js + traced node_modules)
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

CMD ["node", "server.js"]
